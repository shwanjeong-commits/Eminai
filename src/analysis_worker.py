import bootstrap  # noqa: F401

import os
import time

from ai_analyzer import DEFAULT_MODEL, analyze_pending
from asset_view_builder import build_asset_views
from automation_status import update_status
from config import load_settings
from daily_briefing_builder import build_daily_briefings
from database import init_db
from issue_flow_builder import build_issue_flows
from news_event_builder import build_news_events
from region_risk_builder import build_region_risks
from telegram_alerts import maybe_send_alert
from web_push_alerts import maybe_send_web_push_alert


SERVICE_NAME = "ai_analysis_worker"
BATCH_LIMIT = int(os.getenv("ANALYZER_BATCH_LIMIT", "10") or 10)
INTERVAL_SECONDS = int(os.getenv("ANALYZER_INTERVAL_SECONDS", "15") or 15)
IDLE_INTERVAL_SECONDS = int(os.getenv("ANALYZER_IDLE_INTERVAL_SECONDS", "60") or 60)
MAX_BACKOFF_SECONDS = int(os.getenv("ANALYZER_MAX_BACKOFF_SECONDS", "1800") or 1800)


def is_transient_provider_error(error: BaseException) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "429",
            "quota",
            "rate limit",
            "too many requests",
            "resource_exhausted",
            "temporarily unavailable",
            "service unavailable",
            "timeout",
            "timed out",
        )
    )


def retry_delay_seconds(failure_streak: int) -> int:
    base = max(IDLE_INTERVAL_SECONDS, 60)
    exponent = max(0, min(failure_streak - 1, 8))
    return min(base * (2**exponent), MAX_BACKOFF_SECONDS)


def rebuild_views() -> None:
    build_daily_briefings(limit_dates=14)
    build_issue_flows()
    build_asset_views()
    build_news_events()
    build_region_risks()


def dispatch_alerts(connection, settings, news_id: int, result: dict) -> None:
    maybe_send_alert(connection, settings, news_id, result)
    maybe_send_web_push_alert(connection, settings, news_id, result)


def run_once(settings=None) -> int:
    settings = settings or load_settings()
    processed = analyze_pending(
        limit=BATCH_LIMIT,
        model=DEFAULT_MODEL,
        retries=1,
        on_analyzed=lambda connection, news_id, result: dispatch_alerts(
            connection,
            settings,
            news_id,
            result,
        ),
    )
    if processed:
        rebuild_views()
    return processed


def run_forever() -> None:
    init_db()
    settings = load_settings()
    update_status(
        SERVICE_NAME,
        "starting",
        f"batch={BATCH_LIMIT}, interval={INTERVAL_SECONDS}s",
    )

    failure_streak = 0
    while True:
        try:
            update_status(SERVICE_NAME, "checking", "checking queued analysis candidates")
            processed = run_once(settings)
            failure_streak = 0
            if processed:
                update_status(
                    SERVICE_NAME,
                    "analyzed",
                    f"processed {processed} queued items",
                    processed_delta=processed,
                )
                time.sleep(INTERVAL_SECONDS)
            else:
                update_status(SERVICE_NAME, "idle", "no queued analysis candidates")
                time.sleep(IDLE_INTERVAL_SECONDS)
        except SystemExit as error:
            failure_streak += 1
            retry_seconds = retry_delay_seconds(failure_streak)
            detail = f"{str(error)[:150]} | retry in {retry_seconds}s"
            update_status(SERVICE_NAME, "deferred", detail, error_delta=1)
            time.sleep(retry_seconds)
        except Exception as error:
            failure_streak += 1
            retry_seconds = retry_delay_seconds(failure_streak)
            if is_transient_provider_error(error):
                status = "deferred"
            else:
                status = "failed"
            detail = f"{str(error)[:150]} | retry in {retry_seconds}s"
            update_status(SERVICE_NAME, status, detail, error_delta=1)
            time.sleep(retry_seconds)


if __name__ == "__main__":
    run_forever()
