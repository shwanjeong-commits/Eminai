import bootstrap  # noqa: F401

import argparse

from config import load_settings
from database import connect, init_db
from telegram_alerts import alert_reasons, maybe_send_alert


def alert_candidates(connection, limit: int):
    return connection.execute(
        """
        select id, title, summary_ko, analysis_ko, impact_score, risk_level, category
        from news_items
        where analysis_scope = 'analysis_target'
          and analysis_status = 'analyzed'
        order by published_at desc
        limit ?
        """,
        (limit,),
    ).fetchall()


def send_pending_alerts(limit: int, dry_run: bool) -> None:
    init_db()
    settings = load_settings()
    with connect() as connection:
        for row in alert_candidates(connection, limit):
            analysis = {
                "title": row["title"],
                "summary_ko": row["summary_ko"],
                "analysis_ko": row["analysis_ko"],
                "impact_score": row["impact_score"],
                "risk_level": row["risk_level"],
                "category": row["category"],
            }
            reasons = alert_reasons(settings, analysis)
            if not reasons:
                continue

            if dry_run:
                print({"event": "alert_candidate", "id": row["id"], "reason": ", ".join(reasons)})
                continue

            result = maybe_send_alert(connection, settings, row["id"], analysis)
            connection.commit()
            print(result, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send Telegram alerts for already analyzed news.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    send_pending_alerts(limit=args.limit, dry_run=args.dry_run)
