import bootstrap  # noqa: F401

import asyncio
import os

from audit_recent_messages import audit_recent
from automation_status import update_status
from database import init_db


SERVICE_NAME = "filter_audit_worker"
AUDIT_LIMIT = int(os.getenv("FILTER_AUDIT_LIMIT", "300") or 300)
INTERVAL_SECONDS = int(os.getenv("FILTER_AUDIT_INTERVAL_SECONDS", "21600") or 21600)
MISSING_THRESHOLD = int(os.getenv("FILTER_AUDIT_MISSING_THRESHOLD", "1") or 1)
AUTO_REPAIR = os.getenv("FILTER_AUDIT_AUTO_REPAIR", "1").strip().lower() not in {"0", "false", "no", "off"}


def summarize(results: list[dict]) -> tuple[int, int, int, int, list[int]]:
    checked = sum(item["checked"] for item in results)
    expected = sum(item["expected_collect"] for item in results)
    repaired = sum(item.get("repaired", 0) for item in results)
    missing_items = [
        missing
        for item in results
        for missing in item["missing_expected"]
    ]
    remaining_missing = [item for item in missing_items if not item.get("repaired")]
    missing_ids = [int(item["id"]) for item in remaining_missing[:10]]
    return checked, expected, len(missing_items), repaired, missing_ids


def top_patterns(results: list[dict], key: str, limit: int = 3) -> str:
    totals: dict[str, int] = {}
    for item in results:
        for name, count in item.get(key, {}).items():
            totals[name] = totals.get(name, 0) + int(count)
    if not totals:
        return "-"
    return ", ".join(
        f"{name} {count}"
        for name, count in sorted(totals.items(), key=lambda pair: pair[1], reverse=True)[:limit]
    )


async def run_once() -> None:
    results = await audit_recent(AUDIT_LIMIT, repair=AUTO_REPAIR)
    checked, expected, missing_count, repaired, missing_ids = summarize(results)
    remaining_count = missing_count - repaired
    collected_pattern = top_patterns(results, "collected_types")
    ignored_pattern = top_patterns(results, "ignored_types")
    missing_pattern = top_patterns(results, "missing_types")
    if remaining_count >= MISSING_THRESHOLD:
        update_status(
            SERVICE_NAME,
            "attention",
            (
                f"checked {checked}, expected {expected}, missing {missing_count}, repaired {repaired}, "
                f"remaining {remaining_count}, ids {missing_ids}, collect_types [{collected_pattern}], "
                f"missing_types [{missing_pattern}], ignored_types [{ignored_pattern}]"
            ),
            error_delta=1,
            processed_delta=repaired,
        )
    else:
        status = "repaired" if repaired else "ok"
        update_status(
            SERVICE_NAME,
            status,
            (
                f"checked {checked}, expected {expected}, missing {missing_count}, repaired {repaired}, "
                f"remaining {remaining_count}, collect_types [{collected_pattern}], ignored_types [{ignored_pattern}]"
            ),
            processed_delta=checked + repaired,
        )


async def run_forever() -> None:
    init_db()
    update_status(
        SERVICE_NAME,
        "starting",
        f"limit={AUDIT_LIMIT}, interval={INTERVAL_SECONDS}s, auto_repair={AUTO_REPAIR}",
    )
    while True:
        try:
            await run_once()
        except Exception as error:
            update_status(SERVICE_NAME, "failed", str(error)[:200], error_delta=1)
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_forever())
