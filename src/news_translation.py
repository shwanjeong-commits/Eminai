"""English translation cache for dashboard news items."""

from __future__ import annotations

import json

import httpx
from openai import OpenAIError, RateLimitError

from ai_analyzer import (
    DEFAULT_MODEL,
    build_provider,
    google_response_schema,
    parse_chat_completion_response,
    parse_google_response,
    parse_openai_response,
)
from config import load_settings


SYSTEM_PROMPT = """
You are translating a Korean geopolitical and market news dashboard for American readers.
Translate faithfully into natural U.S. English. Preserve facts, numbers, dates, names,
and uncertainty. Do not add new facts. Explain Korean shorthand only when necessary
inside the translation. Return valid JSON only.
""".strip()


JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "analysis": {"type": "string"},
        "raw_text": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "summary", "analysis", "raw_text", "tags"],
}


def clean_text(value: object, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def clean_list(value: object, limit: int = 8) -> list[str]:
    if isinstance(value, list):
        items = value
    elif value:
        items = [value]
    else:
        items = []
    result = []
    for item in items:
        text = clean_text(item, 80)
        if text:
            result.append(text)
    return result[:limit]


def normalize_result(result: dict) -> dict:
    return {
        "title": clean_text(result.get("title"), 140),
        "summary": clean_text(result.get("summary"), 1200),
        "analysis": clean_text(result.get("analysis"), 1800),
        "raw_text": str(result.get("raw_text") or "").strip()[:8000],
        "tags": clean_list(result.get("tags")),
    }


def build_prompt(row) -> str:
    return f"""
Translate this news item for an American investor or policy watcher.

Rules:
- The title should be clear, specific, and natural in English.
- The summary should be concise but complete enough to understand the event.
- The analysis should preserve the original reasoning, including risk and market transmission.
- The raw_text translation should be readable English, not word-for-word awkward translation.
- Translate tags into short English tags.
- Keep names such as Trump, Iran, Hormuz, Fed, SK Hynix, etc. recognizable.
- Do not produce investment advice.

Source metadata:
- news_id: {row['id']}
- date: {row['news_date']}
- source: {row['source_channel']}/{row['telegram_message_id']}
- category: {row['category'] or ''}
- risk: {row['risk_level'] or ''}
- impact_score: {row['impact_score'] or ''}

Korean title:
{row['title'] or ''}

Korean summary:
{row['summary_ko'] or ''}

Korean analysis:
{row['analysis_ko'] or ''}

Korean raw text:
{(row['raw_text'] or '')[:7000]}

Tags:
{row['tags'] or ''}
""".strip()


def parse_provider_response(provider: dict, prompt: str) -> dict:
    if provider["provider"] == "google":
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent",
            params={"key": provider["api_key"]},
            json={
                "contents": [{"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": google_response_schema(JSON_SCHEMA),
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        return parse_google_response(response.json())

    if provider["provider"] == "github":
        response = provider["client"].chat.completions.create(
            model=provider["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "news_translation",
                    "schema": JSON_SCHEMA,
                    "strict": True,
                },
            },
        )
        return parse_chat_completion_response(response)

    response = provider["client"].responses.create(
        model=provider["model"],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "news_translation",
                "schema": JSON_SCHEMA,
                "strict": True,
            }
        },
    )
    return parse_openai_response(response)


def translate_with_fallbacks(provider: dict, prompt: str) -> tuple[dict, dict]:
    last_error = None
    for candidate in [provider, *provider.get("fallbacks", [])]:
        try:
            return parse_provider_response(candidate, prompt), candidate
        except (RateLimitError, httpx.HTTPStatusError, OpenAIError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code not in {429, 500, 502, 503, 504}:
                break
    raise RuntimeError(f"translation failed: {str(last_error)[:240]}")


def translation_row_to_payload(row) -> dict:
    return {
        "newsItemId": row["news_item_id"],
        "title": row["title"],
        "summary": row["summary"],
        "analysis": row["analysis"],
        "rawText": row["raw_text"],
        "tags": json.loads(row["tags"] or "[]"),
        "provider": row["provider"],
        "model": row["model"],
        "updatedAt": row["updated_at"],
    }


def get_translations(connection, news_ids: list[int], lang: str = "en") -> dict[int, dict]:
    if not news_ids:
        return {}
    placeholders = ",".join("?" for _ in news_ids)
    rows = connection.execute(
        f"select * from news_translations where lang = ? and news_item_id in ({placeholders})",
        (lang, *news_ids),
    ).fetchall()
    return {row["news_item_id"]: translation_row_to_payload(row) for row in rows}


def save_translation(connection, news_id: int, result: dict, provider: dict, lang: str = "en") -> dict:
    normalized = normalize_result(result)
    connection.execute(
        """
        insert into news_translations (
          news_item_id, lang, title, summary, analysis, raw_text, tags,
          raw_result, provider, model
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(news_item_id) do update set
          lang = excluded.lang,
          title = excluded.title,
          summary = excluded.summary,
          analysis = excluded.analysis,
          raw_text = excluded.raw_text,
          tags = excluded.tags,
          raw_result = excluded.raw_result,
          provider = excluded.provider,
          model = excluded.model,
          updated_at = current_timestamp
        """,
        (
            news_id,
            lang,
            normalized["title"],
            normalized["summary"],
            normalized["analysis"],
            normalized["raw_text"],
            json.dumps(normalized["tags"], ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            provider["provider"],
            provider["model"],
        ),
    )
    return get_translations(connection, [news_id], lang)[news_id]


def translate_news_items(
    connection,
    news_ids: list[int],
    *,
    lang: str = "en",
    limit_new: int = 8,
    model: str = DEFAULT_MODEL,
) -> dict[int, dict]:
    unique_ids = list(dict.fromkeys(int(news_id) for news_id in news_ids if int(news_id) > 0))[:40]
    existing = get_translations(connection, unique_ids, lang)
    missing = [news_id for news_id in unique_ids if news_id not in existing][:limit_new]
    if not missing:
        return existing

    placeholders = ",".join("?" for _ in missing)
    rows = connection.execute(
        f"""
        select id, source_channel, telegram_message_id, news_date, raw_text, title,
               summary_ko, analysis_ko, impact_score, risk_level, category,
               coalesce(title, '') || ' ' || coalesce(summary_ko, '') as tags
        from news_items
        where id in ({placeholders})
          and analysis_status in ('analyzed', 'queued', 'review')
          and coalesce(user_hidden, 0) = 0
        """,
        missing,
    ).fetchall()
    rows_by_id = {row["id"]: row for row in rows}
    provider = build_provider(load_settings(), model)
    for news_id in missing:
        row = rows_by_id.get(news_id)
        if not row:
            continue
        result, used_provider = translate_with_fallbacks(provider, build_prompt(row))
        existing[news_id] = save_translation(connection, news_id, result, used_provider, lang)
    return existing
