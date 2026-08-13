"""On-demand investor-focused deep analysis for individual news items."""

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
from situation_state import get_situation_state


SYSTEM_PROMPT = """
You are an investor-focused economic and geopolitical analyst for a Korean dashboard.
Analyze one already-collected news item. Explain the causal chain and market transmission,
but do not give buy/sell instructions or personalized investment advice.
Separate confirmed facts from inference. If the raw item is thin, say what cannot be known.
Return valid JSON only in Korean.
""".strip()


JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "investor_summary": {"type": "string"},
        "cause_effect_chain": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "cause": {"type": "string"},
                "action": {"type": "string"},
                "direct_result": {"type": "string"},
                "second_order_effects": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["cause", "action", "direct_result", "second_order_effects"],
        },
        "affected_assets": {"type": "array", "items": {"type": "string"}},
        "beneficiaries": {"type": "array", "items": {"type": "string"}},
        "hurt_parties": {"type": "array", "items": {"type": "string"}},
        "time_horizon": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "short_term": {"type": "string"},
                "medium_term": {"type": "string"},
                "long_term": {"type": "string"},
            },
            "required": ["short_term", "medium_term", "long_term"],
        },
        "priced_in_assessment": {"type": "string"},
        "numeric_indicators": {"type": "array", "items": {"type": "string"}},
        "counter_scenarios": {"type": "array", "items": {"type": "string"}},
        "confirmation_level": {
            "type": "string",
            "enum": ["공식", "보도", "발언", "루머", "추정", "불명확"],
        },
        "checklist": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "investor_summary",
        "cause_effect_chain",
        "affected_assets",
        "beneficiaries",
        "hurt_parties",
        "time_horizon",
        "priced_in_assessment",
        "numeric_indicators",
        "counter_scenarios",
        "confirmation_level",
        "checklist",
    ],
}


def normalize_text(value: object, limit: int = 900) -> str:
    return " ".join(str(value or "").split())[:limit]


def normalize_list(value: object, limit: int = 6) -> list[str]:
    if isinstance(value, list):
        source = value
    elif value:
        source = [value]
    else:
        source = []
    items = []
    for item in source:
        text = normalize_text(item, 180)
        if text:
            items.append(text)
    return items[:limit]


def normalize_result(result: dict) -> dict:
    chain = result.get("cause_effect_chain") if isinstance(result.get("cause_effect_chain"), dict) else {}
    horizon = result.get("time_horizon") if isinstance(result.get("time_horizon"), dict) else {}
    normalized = {
        "investor_summary": normalize_text(result.get("investor_summary"), 900),
        "cause_effect_chain": {
            "cause": normalize_text(chain.get("cause"), 260),
            "action": normalize_text(chain.get("action"), 260),
            "direct_result": normalize_text(chain.get("direct_result"), 260),
            "second_order_effects": normalize_list(chain.get("second_order_effects"), 5),
        },
        "affected_assets": normalize_list(result.get("affected_assets"), 8),
        "beneficiaries": normalize_list(result.get("beneficiaries"), 6),
        "hurt_parties": normalize_list(result.get("hurt_parties"), 6),
        "time_horizon": {
            "short_term": normalize_text(horizon.get("short_term"), 260),
            "medium_term": normalize_text(horizon.get("medium_term"), 260),
            "long_term": normalize_text(horizon.get("long_term"), 260),
        },
        "priced_in_assessment": normalize_text(result.get("priced_in_assessment"), 500),
        "numeric_indicators": normalize_list(result.get("numeric_indicators"), 8),
        "counter_scenarios": normalize_list(result.get("counter_scenarios"), 6),
        "confirmation_level": normalize_text(result.get("confirmation_level"), 20),
        "checklist": normalize_list(result.get("checklist"), 8),
    }
    if normalized["confirmation_level"] not in {"공식", "보도", "발언", "루머", "추정", "불명확"}:
        normalized["confirmation_level"] = "불명확"
    return normalized


def build_user_prompt(row, situation_memory: str) -> str:
    return f"""
Current situation memory:
{situation_memory[:9000]}

News item:
- id: {row['id']}
- date: {row['news_date']}
- published_at: {row['published_at']}
- source: {row['source_channel']}/{row['telegram_message_id']}
- title: {row['title'] or ''}
- summary: {row['summary_ko'] or ''}
- existing_analysis: {row['analysis_ko'] or ''}
- impact_score: {row['impact_score'] or ''}
- risk_level: {row['risk_level'] or ''}
- category: {row['category'] or ''}

Raw text:
{(row['raw_text'] or '')[:7000]}

Investor analysis rules:
- investor_summary: 3-5 Korean sentences. Focus on what changed, why it matters, and what an investor should monitor.
- cause_effect_chain: explain cause -> action/event -> direct result -> second-order effects.
- affected_assets: name likely affected asset classes, sectors, companies, commodities, currencies, or rates. Use "unknown" only if unclear.
- beneficiaries / hurt_parties: describe possible winners and losers. Use cautious wording.
- time_horizon: short_term means days-weeks, medium_term means 1-3 months, long_term means 3 months+.
- priced_in_assessment: say whether the information is likely new, partly priced, or already known, and what evidence would confirm that.
- numeric_indicators: concrete data to watch, such as price levels, spreads, inventory, rates, FX, earnings, guidance, policy dates, shipment volume.
- counter_scenarios: what would invalidate or weaken the thesis.
- confirmation_level: one of 공식, 보도, 발언, 루머, 추정, 불명확.
- checklist: 4-8 short action-neutral monitoring points.
- Do not recommend buying or selling.
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
                    "name": "news_deep_analysis",
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
                "name": "news_deep_analysis",
                "schema": JSON_SCHEMA,
                "strict": True,
            }
        },
    )
    return parse_openai_response(response)


def provider_label(provider: dict) -> str:
    return f"{provider['provider']}:{provider['model']}"


def analyze_with_fallbacks(provider: dict, prompt: str) -> tuple[dict, dict]:
    providers = [provider, *provider.get("fallbacks", [])]
    last_error = None
    for candidate in providers:
        try:
            return parse_provider_response(candidate, prompt), candidate
        except (RateLimitError, httpx.HTTPStatusError, OpenAIError, ValueError, json.JSONDecodeError) as error:
            last_error = error
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code not in {429, 500, 502, 503, 504}:
                break
    raise RuntimeError(f"deep analysis failed: {str(last_error)[:240]}")


def row_to_payload(row) -> dict:
    return {
        "newsItemId": row["news_item_id"],
        "investorSummary": row["investor_summary"],
        "causeEffectChain": json.loads(row["cause_effect_chain"] or "{}"),
        "affectedAssets": json.loads(row["affected_assets"] or "[]"),
        "beneficiaries": json.loads(row["beneficiaries"] or "[]"),
        "hurtParties": json.loads(row["hurt_parties"] or "[]"),
        "timeHorizon": json.loads(row["time_horizon"] or "{}"),
        "pricedInAssessment": row["priced_in_assessment"],
        "numericIndicators": json.loads(row["numeric_indicators"] or "[]"),
        "counterScenarios": json.loads(row["counter_scenarios"] or "[]"),
        "confirmationLevel": row["confirmation_level"],
        "checklist": json.loads(row["checklist"] or "[]"),
        "provider": row["provider"],
        "model": row["model"],
        "updatedAt": row["updated_at"],
    }


def get_deep_analysis(connection, news_id: int) -> dict | None:
    row = connection.execute(
        "select * from news_deep_analyses where news_item_id = ?",
        (news_id,),
    ).fetchone()
    return row_to_payload(row) if row else None


def save_deep_analysis(connection, news_id: int, result: dict, provider: dict) -> dict:
    normalized = normalize_result(result)
    connection.execute(
        """
        insert into news_deep_analyses (
          news_item_id, investor_summary, cause_effect_chain, affected_assets,
          beneficiaries, hurt_parties, time_horizon, priced_in_assessment,
          numeric_indicators, counter_scenarios, confirmation_level, checklist,
          raw_result, provider, model
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(news_item_id) do update set
          investor_summary = excluded.investor_summary,
          cause_effect_chain = excluded.cause_effect_chain,
          affected_assets = excluded.affected_assets,
          beneficiaries = excluded.beneficiaries,
          hurt_parties = excluded.hurt_parties,
          time_horizon = excluded.time_horizon,
          priced_in_assessment = excluded.priced_in_assessment,
          numeric_indicators = excluded.numeric_indicators,
          counter_scenarios = excluded.counter_scenarios,
          confirmation_level = excluded.confirmation_level,
          checklist = excluded.checklist,
          raw_result = excluded.raw_result,
          provider = excluded.provider,
          model = excluded.model,
          updated_at = current_timestamp
        """,
        (
            news_id,
            normalized["investor_summary"],
            json.dumps(normalized["cause_effect_chain"], ensure_ascii=False),
            json.dumps(normalized["affected_assets"], ensure_ascii=False),
            json.dumps(normalized["beneficiaries"], ensure_ascii=False),
            json.dumps(normalized["hurt_parties"], ensure_ascii=False),
            json.dumps(normalized["time_horizon"], ensure_ascii=False),
            normalized["priced_in_assessment"],
            json.dumps(normalized["numeric_indicators"], ensure_ascii=False),
            json.dumps(normalized["counter_scenarios"], ensure_ascii=False),
            normalized["confirmation_level"],
            json.dumps(normalized["checklist"], ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            provider["provider"],
            provider["model"],
        ),
    )
    return get_deep_analysis(connection, news_id)


def generate_deep_analysis(connection, news_id: int, refresh: bool = False, model: str = DEFAULT_MODEL) -> dict:
    if not refresh:
        existing = get_deep_analysis(connection, news_id)
        if existing:
            return existing

    row = connection.execute(
        """
        select id, source_channel, telegram_message_id, published_at, news_date, raw_text,
               title, summary_ko, analysis_ko, impact_score, risk_level, category
        from news_items
        where id = ?
          and analysis_scope = 'analysis_target'
          and analysis_status = 'analyzed'
          and coalesce(user_hidden, 0) = 0
        """,
        (news_id,),
    ).fetchone()
    if not row:
        raise ValueError("analyzed news item not found")

    provider = build_provider(load_settings(), model)
    prompt = build_user_prompt(row, get_situation_state(connection))
    result, used_provider = analyze_with_fallbacks(provider, prompt)
    return save_deep_analysis(connection, news_id, result, used_provider)
