import bootstrap  # noqa: F401

from datetime import datetime, timezone, timedelta

from classifier import analysis_scope
from database import connect


KST = timezone(timedelta(hours=9))


def normalize_news_dates() -> None:
    with connect() as connection:
        rows = connection.execute(
            "select id, published_at from news_items order by id"
        ).fetchall()

        changed = 0
        for row in rows:
            published_at = datetime.fromisoformat(row["published_at"])
            news_date = published_at.astimezone(KST).date().isoformat()
            connection.execute(
                """
                update news_items
                set news_date = ?,
                    analysis_scope = ?,
                    updated_at = current_timestamp
                where id = ?
                """,
                (news_date, analysis_scope(news_date), row["id"]),
            )
            changed += 1

        print(f"normalized: {changed}")


if __name__ == "__main__":
    normalize_news_dates()
