from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time

import bootstrap  # noqa: F401

from automation_status import update_status
from daily_report import report_date_from_mode, send_daily_report
from database import init_db


KST = timezone(timedelta(hours=9))
SERVICE_NAME = "daily_report_worker"


def enabled() -> bool:
    return os.getenv("DAILY_REPORT_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def scheduled_times() -> list[str]:
    raw_value = os.getenv("DAILY_REPORT_TIME_KST", "08:00,18:00")
    times = [value.strip() for value in raw_value.split(",") if value.strip()]
    return times or ["08:00", "18:00"]


def date_mode() -> str:
    value = os.getenv("DAILY_REPORT_DATE_MODE", "today").strip().lower()
    return value if value in {"today", "yesterday"} else "today"


def run_forever() -> None:
    init_db()
    update_status(SERVICE_NAME, "starting", "daily report scheduler starting")

    last_attempt_key = ""
    while True:
        try:
            if not enabled():
                update_status(SERVICE_NAME, "disabled", "DAILY_REPORT_ENABLED is off")
                time.sleep(300)
                continue

            now = datetime.now(KST)
            times = scheduled_times()
            current_hhmm = now.strftime("%H:%M")
            matched_time = current_hhmm if current_hhmm in times else ""
            attempt_key = f"{now.date().isoformat()} {matched_time}"

            if matched_time and attempt_key != last_attempt_key:
                target_date = report_date_from_mode(date_mode())
                update_status(SERVICE_NAME, "sending", f"{target_date} at {matched_time} KST")
                result = send_daily_report(target_date)
                last_attempt_key = attempt_key
                update_status(SERVICE_NAME, result.get("event", "checked"), str(result)[:180])
                time.sleep(70)
            else:
                update_status(SERVICE_NAME, "scheduled", f"times={','.join(times)} KST, mode={date_mode()}")
                time.sleep(30)
        except Exception as error:
            update_status(SERVICE_NAME, "failed", str(error)[:200], error_delta=1)
            time.sleep(120)


if __name__ == "__main__":
    run_forever()
