import bootstrap  # noqa: F401

import time

from database import connect, init_db


def write_status(
    service_name: str,
    status: str,
    detail: str | None,
    last_news_item_id: int | None,
    processed_delta: int,
    error_delta: int,
) -> None:
    with connect() as connection:
        connection.execute(
            """
            insert into automation_status (
              service_name, status, detail, last_event_at, last_news_item_id,
              processed_count, error_count, updated_at
            )
            values (?, ?, ?, current_timestamp, ?, ?, ?, current_timestamp)
            on conflict(service_name) do update set
              status = excluded.status,
              detail = excluded.detail,
              last_event_at = excluded.last_event_at,
              last_news_item_id = coalesce(excluded.last_news_item_id, automation_status.last_news_item_id),
              processed_count = automation_status.processed_count + excluded.processed_count,
              error_count = automation_status.error_count + excluded.error_count,
              updated_at = current_timestamp
            """,
            (
                service_name,
                status,
                detail,
                last_news_item_id,
                processed_delta,
                error_delta,
            ),
        )


def update_status(
    service_name: str,
    status: str,
    detail: str | None = None,
    last_news_item_id: int | None = None,
    processed_delta: int = 0,
    error_delta: int = 0,
) -> None:
    schema_initialized = False
    for attempt in range(5):
        try:
            write_status(
                service_name,
                status,
                detail,
                last_news_item_id,
                processed_delta,
                error_delta,
            )
            return
        except sqlite3.OperationalError as error:
            reason = str(error).lower()
            if "no such table" in reason and not schema_initialized:
                init_db()
                schema_initialized = True
                continue
            if "locked" in reason and attempt < 4:
                time.sleep(0.1 * (2**attempt))
                continue
            raise


def get_status_payload(connection) -> list[dict]:
    rows = connection.execute(
        """
        select service_name, status, detail, last_event_at, last_news_item_id,
               processed_count, error_count, updated_at
        from automation_status
        order by service_name
        """
    ).fetchall()
    return [
        {
            "service": row["service_name"],
            "status": row["status"],
            "detail": row["detail"],
            "lastEventAt": row["last_event_at"],
            "lastNewsItemId": row["last_news_item_id"],
            "processedCount": row["processed_count"],
            "errorCount": row["error_count"],
            "updatedAt": row["updated_at"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    update_status("manual_check", "ok", "automation status table is writable")
    print("automation status ok")
import sqlite3
