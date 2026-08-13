import bootstrap  # noqa: F401

from classifier import classify_text
from database import connect, init_db


TARGET_STATUSES = ("queued", "review", "pending")


def cleanup_noise_queue() -> None:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            select id, raw_text, summary_ko, analysis_ko
            from news_items
            where analysis_status in (?, ?, ?)
            """,
            TARGET_STATUSES,
        ).fetchall()

        ignored = 0
        restored = 0
        checked = 0
        for row in rows:
            checked += 1
            if row["summary_ko"] and row["analysis_ko"]:
                restored += 1
                connection.execute(
                    """
                    update news_items
                    set analysis_status = 'analyzed',
                        updated_at = current_timestamp
                    where id = ?
                    """,
                    (row["id"],),
                )
                continue

            result = classify_text(row["raw_text"])
            if result["analysis_status"] != "ignored":
                continue

            ignored += 1
            connection.execute(
                """
                update news_items
                set content_type = ?,
                    analysis_status = ?,
                    analysis_priority = ?,
                    analysis_reason = ?,
                    updated_at = current_timestamp
                where id = ?
                """,
                (
                    result["content_type"],
                    result["analysis_status"],
                    result["analysis_priority"],
                    result["analysis_reason"],
                    row["id"],
                ),
            )
        connection.commit()

    print(f"checked={checked} restored={restored} ignored={ignored}")


if __name__ == "__main__":
    cleanup_noise_queue()
