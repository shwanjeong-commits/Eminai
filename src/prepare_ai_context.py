import bootstrap  # noqa: F401

from collections import Counter
import argparse
from datetime import date

from classifier import ANALYSIS_TARGET_START
from database import connect


def month_bounds(month: str) -> tuple[str, str]:
    year, month_num = map(int, month.split("-"))
    start = date(year, month_num, 1)
    if month_num == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month_num + 1, 1)
    return start.isoformat(), end.isoformat()


def compact(text: str, limit: int = 180) -> str:
    value = " ".join(text.split())
    return value[:limit] + ("..." if len(value) > limit else "")


def first_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip(" -•━")
        if cleaned:
            return cleaned[:110]
    return compact(text, 110)


def build_context_text(month: str, rows) -> str:
    type_counts = Counter(row["content_type"] or "unknown" for row in rows)
    status_counts = Counter(row["analysis_status"] or "unknown" for row in rows)
    top_rows = sorted(rows, key=lambda row: row["analysis_priority"] or 0, reverse=True)[:80]

    lines = [
        f"# Historical Context Packet: {month}",
        "",
        "이 묶음은 2026-07-01 이후 뉴스 분석을 위한 과거 흐름 참고자료입니다.",
        "개별 뉴스 요약 대상이 아니라, 분석 AI의 배경 맥락으로 사용합니다.",
        "",
        "## Counts",
        f"- total_items: {len(rows)}",
        f"- content_types: {dict(type_counts)}",
        f"- statuses: {dict(status_counts)}",
        "",
        "## Representative Items",
    ]

    for row in top_rows:
        lines.append(
            f"- {row['news_date']} | priority {row['analysis_priority']:.2f} | "
            f"{row['content_type']} | {first_line(row['raw_text'])}"
        )

    return "\n".join(lines)


def prepare_contexts() -> None:
    with connect() as connection:
        months = [
            row["month"]
            for row in connection.execute(
                """
                select substr(news_date, 1, 7) as month
                from news_items
                where news_date < ?
                group by month
                order by month
                """,
                (ANALYSIS_TARGET_START,),
            ).fetchall()
        ]

        for month in months:
            start, end = month_bounds(month)
            rows = connection.execute(
                """
                select id, news_date, raw_text, content_type, analysis_status, analysis_priority
                from news_items
                where news_date >= ? and news_date < ?
                  and analysis_status in ('queued', 'review')
                order by analysis_priority desc, published_at asc
                """,
                (start, end),
            ).fetchall()
            if not rows:
                continue

            context_text = build_context_text(month, rows)
            connection.execute(
                """
                insert into ai_context_batches (
                  period_start, period_end, item_count, context_text, status
                )
                values (?, ?, ?, ?, 'ready')
                on conflict(period_start, period_end) do update set
                  item_count = excluded.item_count,
                  context_text = excluded.context_text,
                  status = 'ready',
                  updated_at = current_timestamp
                """,
                (start, end, len(rows), context_text),
            )
            print(f"prepared {month}: {len(rows)} items")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare historical context packets for AI analysis.")
    parser.parse_args()
    prepare_contexts()
