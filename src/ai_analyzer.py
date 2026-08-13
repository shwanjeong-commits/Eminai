import bootstrap  # noqa: F401

import argparse
import json
import time

import httpx
from openai import AzureOpenAI, OpenAI, OpenAIError, RateLimitError

from config import load_settings
from database import connect
from situation_state import get_situation_state, update_situation_state


DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_GOOGLE_MODEL = "gemini-2.5-flash"
DEFAULT_GITHUB_MODEL = "meta/llama-3.3-70b-instruct"
GITHUB_MODELS_BASE_URL = "https://models.github.ai/inference"
ANALYZABLE_STATUSES = ("queued", "review")
CONTENT_FILTER_STATUS = "filtered"


SYSTEM_PROMPT = """
You are an economic and geopolitical intelligence analyst for a Korean dashboard.
Analyze Telegram news items in Korean. Be concise, factual, and avoid investment advice.
Use the current situation memory as accumulated context from previous analyses.
Your job is not only to summarize. Identify what changed, why it matters, how it can transmit into markets or international affairs, and what would reduce confidence in the interpretation.
Separate confirmed facts from inference. Do not invent facts that are not in the raw item or the situation memory.
Return valid JSON only.
""".strip()


JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "summary_ko": {"type": "string"},
        "analysis_ko": {"type": "string"},
        "drivers": {
            "type": "array",
            "items": {"type": "string"},
        },
        "transmission_channels": {
            "type": "array",
            "items": {"type": "string"},
        },
        "watch_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "uncertainty_ko": {"type": "string"},
        "impact_score": {"type": "number", "minimum": 0, "maximum": 10},
        "sentiment": {"type": "string", "enum": ["긍정", "부정", "혼재", "중립"]},
        "risk_level": {"type": "string", "enum": ["높음", "중간", "낮음"]},
        "category": {"type": "string", "enum": ["macro", "geopolitics", "markets", "energy"]},
    },
    "required": [
        "title",
        "summary_ko",
        "analysis_ko",
        "drivers",
        "transmission_channels",
        "watch_points",
        "uncertainty_ko",
        "impact_score",
        "sentiment",
        "risk_level",
        "category",
    ],
}


def context_digest(connection, max_chars: int = 12000) -> str:
    return get_situation_state(connection)[:max_chars]


def rows_to_analyze(connection, limit: int, force: bool = False):
    force_clause = "" if force else "and (summary_ko is null or analysis_ko is null)"
    return connection.execute(
        f"""
        select id, source_channel, telegram_message_id, published_at, news_date, raw_text,
               analysis_priority, content_type
        from news_items
        where analysis_scope = 'analysis_target'
          and analysis_status in ({','.join('?' for _ in ANALYZABLE_STATUSES)})
          {force_clause}
        order by analysis_priority desc, published_at asc
        limit ?
        """,
        (*ANALYZABLE_STATUSES, limit),
    ).fetchall()


def build_user_prompt(row, digest: str) -> str:
    text = row["raw_text"][:7000]
    return f"""
Current situation memory:
{digest}

Analyze this newly collected Telegram news item.

Metadata:
- news_date: {row['news_date']}
- published_at: {row['published_at']}
- source: {row['source_channel']}
- message_id: {row['telegram_message_id']}
- first_pass_type: {row['content_type']}

Raw text:
{text}

Output rules:
- title: short Korean title, no emoji if possible.
- summary_ko: 2 Korean sentences summarizing only confirmed facts from this item.
- analysis_ko: 3-5 Korean sentences. Explain whether this item is new information, confirmation of an existing trend, escalation, de-escalation, or noise relative to the situation memory.
- drivers: 2-4 short Korean phrases naming the main forces behind the item. Example: ["군사 긴장 확대", "에너지 공급 우려"].
- transmission_channels: 2-4 Korean phrases explaining the plausible path into economy, markets, supply chains, policy, or diplomacy. If there is no clear channel, say so.
- watch_points: 2-4 concrete follow-up signals to monitor. Avoid vague items like "시장 반응".
- uncertainty_ko: 1 Korean sentence explaining what is still uncertain or what could invalidate the interpretation.
- impact_score: 0-10 using this rubric:
  0-2: informational or routine update, little market/geopolitical transmission.
  3-4: relevant but narrow, mostly confirms known conditions.
  5-6: meaningful sector/regional signal or policy implication.
  7-8: high-impact cross-market/geopolitical signal, escalation, or major macro/policy event.
  9-10: systemic shock, military escalation with global spillover, major central-bank surprise, or direct supply disruption.
- risk_level: 높음 only when there is direct escalation, sharp market stress, policy shock, or credible supply/security threat. 중간 for uncertainty or moderate spillover. 낮음 for routine or low-spillover items.
- category: macro, geopolitics, markets, or energy.
- Never treat a schedule, rumor, or opinion as confirmed fact. Mark uncertainty clearly.
""".strip()


def provider_from_name(settings, provider_name: str, model: str) -> dict | None:
    if provider_name == "google":
        if not settings.google_api_key:
            return None
        google_model = (
            model
            if model and model != DEFAULT_MODEL
            else settings.google_ai_model or DEFAULT_GOOGLE_MODEL
        )
        return {"provider": "google", "api_key": settings.google_api_key, "model": google_model}

    if provider_name == "github":
        if not settings.github_models_token:
            return None
        github_model = (
            model
            if model and model != DEFAULT_MODEL
            else settings.github_models_model or DEFAULT_GITHUB_MODEL
        )
        return {
            "provider": "github",
            "client": OpenAI(
                api_key=settings.github_models_token,
                base_url=GITHUB_MODELS_BASE_URL,
                default_headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2026-03-10",
                },
            ),
            "model": github_model,
        }

    if provider_name == "azure":
        missing = []
        if not settings.azure_openai_endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not settings.azure_openai_api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not settings.azure_openai_deployment:
            missing.append("AZURE_OPENAI_DEPLOYMENT")
        if missing:
            raise SystemExit("Missing Azure OpenAI settings in .env: " + ", ".join(missing))

        return {
            "provider": "openai",
            "client": AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
            ),
            "model": settings.azure_openai_deployment,
        }

    if provider_name != "openai":
        return None

    if not settings.openai_api_key:
        return None
    return {"provider": "openai", "client": OpenAI(api_key=settings.openai_api_key), "model": model}


def build_provider(settings, model: str) -> dict:
    primary = provider_from_name(settings, settings.ai_provider, model)
    if primary is None:
        if settings.ai_provider == "google":
            raise SystemExit("GEMINI_API_KEY is missing in .env")
        if settings.ai_provider == "github":
            raise SystemExit("GITHUB_MODELS_TOKEN is missing in .env")
        if settings.ai_provider == "openai":
            raise SystemExit("OPENAI_API_KEY is missing in .env")
        raise SystemExit(f"AI_PROVIDER is not configured: {settings.ai_provider}")

    fallbacks = []
    for fallback_name in settings.ai_fallback_providers:
        if fallback_name == primary["provider"]:
            continue
        fallback = provider_from_name(settings, fallback_name, model)
        if fallback is not None:
            fallbacks.append(fallback)
    primary["fallbacks"] = fallbacks
    return primary


def parse_openai_response(response) -> dict:
    text = getattr(response, "output_text", None)
    if not text:
        text = response.output[0].content[0].text
    return json.loads(text)


def parse_chat_completion_response(response) -> dict:
    return json.loads(response.choices[0].message.content)


def parse_google_response(payload: dict) -> dict:
    candidates = payload.get("candidates", [])
    if not candidates:
        raise ValueError("Google AI response did not include candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if part.get("text"):
            return json.loads(part["text"])
    raise ValueError("Google AI response did not include text output")


def normalize_list(value, limit: int = 4) -> list[str]:
    if isinstance(value, list):
        items = value
    elif value:
        items = [value]
    else:
        items = []
    cleaned = []
    for item in items:
        text = " ".join(str(item or "").split())
        if text:
            cleaned.append(text[:160])
    return cleaned[:limit]


def normalize_result(result: dict) -> dict:
    result["title"] = " ".join(str(result.get("title") or "제목 없음").split())[:90]
    result["summary_ko"] = " ".join(str(result.get("summary_ko") or "").split())[:700]
    result["analysis_ko"] = " ".join(str(result.get("analysis_ko") or "").split())[:1000]
    result["drivers"] = normalize_list(result.get("drivers"), 4)
    result["transmission_channels"] = normalize_list(result.get("transmission_channels"), 4)
    result["watch_points"] = normalize_list(result.get("watch_points"), 4)
    result["uncertainty_ko"] = " ".join(str(result.get("uncertainty_ko") or "").split())[:300]
    result["impact_score"] = max(0.0, min(float(result.get("impact_score") or 0), 10.0))
    if result.get("sentiment") not in {"긍정", "부정", "혼재", "중립"}:
        result["sentiment"] = "중립"
    if result.get("risk_level") not in {"높음", "중간", "낮음"}:
        result["risk_level"] = "중간"
    if result.get("category") not in {"macro", "geopolitics", "markets", "energy"}:
        result["category"] = "markets"
    return result


def formatted_analysis(result: dict) -> str:
    sections = [result["analysis_ko"]]
    if result["drivers"]:
        sections.append("핵심 동인: " + "; ".join(result["drivers"]))
    if result["transmission_channels"]:
        sections.append("전달 경로: " + "; ".join(result["transmission_channels"]))
    if result["watch_points"]:
        sections.append("관찰 포인트: " + "; ".join(result["watch_points"]))
    if result["uncertainty_ko"]:
        sections.append("불확실성: " + result["uncertainty_ko"])
    return "\n\n".join(section for section in sections if section)


def google_response_schema(schema):
    if isinstance(schema, list):
        return [google_response_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    unsupported = {"additionalProperties", "minimum", "maximum"}
    return {key: google_response_schema(value) for key, value in schema.items() if key not in unsupported}


def analyze_row_openai(provider: dict, row, digest: str) -> dict:
    response = provider["client"].responses.create(
        model=provider["model"],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(row, digest)},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "news_analysis",
                "schema": JSON_SCHEMA,
                "strict": True,
            }
        },
    )
    return parse_openai_response(response)


def analyze_row_github(provider: dict, row, digest: str) -> dict:
    if provider["model"].startswith("openai/"):
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "news_analysis",
                "schema": JSON_SCHEMA,
                "strict": True,
            },
        }
    else:
        response_format = {"type": "json_object"}

    response = provider["client"].chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(row, digest)},
        ],
        response_format=response_format,
    )
    return parse_chat_completion_response(response)


def analyze_row_google(provider: dict, row, digest: str) -> dict:
    prompt = f"{SYSTEM_PROMPT}\n\n{build_user_prompt(row, digest)}"
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent",
        params={"key": provider["api_key"]},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": google_response_schema(JSON_SCHEMA),
            },
        },
        timeout=90,
    )
    response.raise_for_status()
    return parse_google_response(response.json())


def analyze_row(provider: dict, row, digest: str) -> dict:
    if provider["provider"] == "google":
        return normalize_result(analyze_row_google(provider, row, digest))
    if provider["provider"] == "github":
        return normalize_result(analyze_row_github(provider, row, digest))
    return normalize_result(analyze_row_openai(provider, row, digest))


def provider_label(provider: dict) -> str:
    return f"{provider['provider']}:{provider['model']}"


def retryable_provider_error(error: Exception) -> bool:
    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return should_retry_http(error)
    if isinstance(error, OpenAIError):
        message = str(error).lower()
        return any(
            marker in message
            for marker in (
                "rate limit",
                "quota",
                "429",
                "too many requests",
                "temporarily unavailable",
                "service unavailable",
            )
        )
    return False


def is_content_filter_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "content management policy",
            "content filter",
            "content_filter",
            "responsibleai policy",
        )
    )


def analyze_row_with_fallbacks(provider: dict, row, digest: str) -> dict:
    providers = [provider, *provider.get("fallbacks", [])]
    errors = []
    for index, candidate in enumerate(providers):
        try:
            if index:
                print(
                    {
                        "event": "analysis_fallback",
                        "id": row["id"],
                        "provider": provider_label(candidate),
                    },
                    flush=True,
                )
            return analyze_row(candidate, row, digest)
        except (RateLimitError, httpx.HTTPStatusError, OpenAIError) as error:
            errors.append(f"{provider_label(candidate)}: {str(error)[:180]}")
            if not retryable_provider_error(error) or index == len(providers) - 1:
                raise
    raise SystemExit("Analysis failed after provider fallback: " + " | ".join(errors))


def save_analysis(connection, news_id: int, result: dict) -> None:
    result = normalize_result(result)
    connection.execute(
        """
        update news_items
        set title = ?,
            summary_ko = ?,
            analysis_ko = ?,
            impact_score = ?,
            sentiment = ?,
            risk_level = ?,
            category = ?,
            analysis_status = 'analyzed',
            updated_at = current_timestamp
        where id = ?
        """,
        (
            result["title"],
            result["summary_ko"],
            formatted_analysis(result),
            float(result["impact_score"]),
            result["sentiment"],
            result["risk_level"],
            result["category"],
            news_id,
        ),
    )


def analyze_news_item(connection, provider: dict, news_id: int, digest: str | None = None) -> dict | None:
    row = connection.execute(
        """
        select id, source_channel, telegram_message_id, published_at, news_date, raw_text,
               analysis_priority, content_type, analysis_status, analysis_scope
        from news_items
        where id = ?
        """,
        (news_id,),
    ).fetchone()
    if not row:
        return None
    if row["analysis_scope"] != "analysis_target":
        return None
    if row["analysis_status"] not in ANALYZABLE_STATUSES:
        return None

    result = analyze_row_with_fallbacks(provider, row, digest or context_digest(connection))
    save_analysis(connection, news_id, result)
    update_situation_state(connection, last_news_item_id=news_id)
    return result


def should_retry_http(error: httpx.HTTPStatusError) -> bool:
    return error.response.status_code in {429, 500, 502, 503, 504}


def analyze_pending(
    limit: int,
    model: str,
    force: bool = False,
    dry_run: bool = False,
    retries: int = 3,
    on_analyzed=None,
) -> int:
    settings = load_settings()
    provider = build_provider(settings, model)

    with connect() as connection:
        digest = context_digest(connection)
        rows = rows_to_analyze(connection, limit=limit, force=force)
        print(f"provider: {provider['provider']}")
        print(f"model: {provider['model']}")
        if provider.get("fallbacks"):
            print("fallback providers: " + ", ".join(provider_label(item) for item in provider["fallbacks"]))
        print(f"analysis candidates: {len(rows)}")
        processed = 0

        for index, row in enumerate(rows, start=1):
            result = None
            content_filtered = False
            for attempt in range(retries + 1):
                try:
                    result = analyze_row_with_fallbacks(provider, row, digest)
                    break
                except RateLimitError as error:
                    if getattr(error, "code", None) == "insufficient_quota":
                        raise SystemExit(
                            "OpenAI API quota is unavailable. Check API billing, credits, and monthly budget."
                        ) from error
                    if attempt >= retries:
                        raise
                    time.sleep(2**attempt)
                except httpx.HTTPStatusError as error:
                    if not should_retry_http(error) or attempt >= retries:
                        body = error.response.text[:500]
                        raise SystemExit(
                            f"Google AI API error: {error.response.status_code} {body}"
                        ) from error
                    wait_seconds = 2**attempt
                    print(
                        {
                            "event": "retry",
                            "id": row["id"],
                            "status_code": error.response.status_code,
                            "wait_seconds": wait_seconds,
                        },
                        flush=True,
                    )
                    time.sleep(wait_seconds)
                except OpenAIError as error:
                    if is_content_filter_error(error):
                        connection.execute(
                            """
                            update news_items
                            set analysis_status = ?, updated_at = current_timestamp
                            where id = ?
                            """,
                            (CONTENT_FILTER_STATUS, row["id"]),
                        )
                        connection.commit()
                        print(
                            {
                                "event": "analysis_content_filtered",
                                "id": row["id"],
                                "action": "preserved_and_skipped",
                            },
                            flush=True,
                        )
                        content_filtered = True
                        break
                    raise SystemExit(f"OpenAI API error: {error}") from error

            if content_filtered:
                continue
            if result is None:
                raise SystemExit(f"Analysis failed for news item {row['id']}")

            print(
                {
                    "index": index,
                    "id": row["id"],
                    "title": result["title"],
                    "impact_score": result["impact_score"],
                    "risk_level": result["risk_level"],
                    "category": result["category"],
                },
                flush=True,
            )
            if not dry_run:
                save_analysis(connection, row["id"], result)
                update_situation_state(connection, last_news_item_id=row["id"])
                connection.commit()
                if on_analyzed is not None:
                    on_analyzed(connection, row["id"], result)
                    connection.commit()
                processed += 1

        return processed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze queued Telegram news with OpenAI, Azure OpenAI, or Google AI.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    analyze_pending(
        limit=args.limit,
        model=args.model,
        force=args.force,
        dry_run=args.dry_run,
        retries=args.retries,
    )
