import bootstrap  # noqa: F401

import argparse
import json
from pathlib import Path

from ai_analyzer import save_analysis
from database import connect
from situation_state import update_situation_state


REQUIRED_FIELDS = {
    "id",
    "telegram_message_id",
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
}
ALLOWED_SENTIMENTS = {"긍정", "부정", "혼재", "중립"}
ALLOWED_RISKS = {"낮음", "중간", "높음"}
ALLOWED_CATEGORIES = {"macro", "geopolitics", "markets", "energy"}
IMPORTABLE_STATUSES = {"queued", "review", "filtered"}


def load_results(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        results = payload
    elif isinstance(payload, dict) and isinstance(payload.get("analyses"), list):
        results = payload["analyses"]
    else:
        raise ValueError("Expected a JSON array or an object containing an analyses array.")
    if not results:
        raise ValueError("The analysis result file is empty.")
    return results


def validate_result(item: dict) -> None:
    missing = sorted(REQUIRED_FIELDS - set(item))
    if missing:
        raise ValueError(f"id={item.get('id')}: missing fields: {', '.join(missing)}")
    if not isinstance(item["id"], int) or not isinstance(item["telegram_message_id"], int):
        raise ValueError("id and telegram_message_id must be integers.")
    for field in ("drivers", "transmission_channels", "watch_points"):
        if not isinstance(item[field], list) or not all(isinstance(value, str) for value in item[field]):
            raise ValueError(f"id={item['id']}: {field} must be a string array.")
    score = float(item["impact_score"])
    if score < 0 or score > 10:
        raise ValueError(f"id={item['id']}: impact_score must be between 0 and 10.")
    if item["sentiment"] not in ALLOWED_SENTIMENTS:
        raise ValueError(f"id={item['id']}: invalid sentiment.")
    if item["risk_level"] not in ALLOWED_RISKS:
        raise ValueError(f"id={item['id']}: invalid risk_level.")
    if item["category"] not in ALLOWED_CATEGORIES:
        raise ValueError(f"id={item['id']}: invalid category.")


def import_results(path: Path, apply: bool = False) -> dict:
    results = load_results(path)
    seen_ids: set[int] = set()
    imported = 0
    skipped_analyzed = 0

    with connect() as connection:
        for item in results:
            validate_result(item)
            news_id = item["id"]
            if news_id in seen_ids:
                raise ValueError(f"Duplicate id in result file: {news_id}")
            seen_ids.add(news_id)

            row = connection.execute(
                """
                select id, telegram_message_id, analysis_status, analysis_scope
                from news_items where id = ?
                """,
                (news_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"Unknown news id: {news_id}")
            if row["telegram_message_id"] != item["telegram_message_id"]:
                raise ValueError(f"id={news_id}: telegram_message_id mismatch.")
            if row["analysis_scope"] != "analysis_target":
                raise ValueError(f"id={news_id}: item is not an analysis target.")
            if row["analysis_status"] == "analyzed":
                skipped_analyzed += 1
                continue
            if row["analysis_status"] not in IMPORTABLE_STATUSES:
                raise ValueError(f"id={news_id}: status is not importable: {row['analysis_status']}")

            if apply:
                save_analysis(connection, news_id, item)
                update_situation_state(connection, last_news_item_id=news_id)
            imported += 1

        if apply:
            connection.commit()

    return {
        "mode": "apply" if apply else "dry-run",
        "result_count": len(results),
        "importable": imported,
        "skipped_already_analyzed": skipped_analyzed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and import manual ChatGPT backlog analyses.")
    parser.add_argument("result_file", type=Path)
    parser.add_argument("--apply", action="store_true", help="Apply validated results to the database.")
    args = parser.parse_args()
    print(json.dumps(import_results(args.result_file, apply=args.apply), ensure_ascii=False))


if __name__ == "__main__":
    main()
