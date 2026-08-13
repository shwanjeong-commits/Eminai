from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3


@dataclass(frozen=True)
class NewsInput:
    source_channel: str
    telegram_message_id: int
    published_at: str
    news_date: str
    raw_text: str
    url: str | None = None


def upsert_news_item(connection: sqlite3.Connection, item: NewsInput) -> int:
    connection.execute(
        """
        insert into news_items (
          source_channel, telegram_message_id, published_at, news_date, raw_text, url
        )
        values (?, ?, ?, ?, ?, ?)
        on conflict(source_channel, telegram_message_id) do update set
          published_at = excluded.published_at,
          news_date = excluded.news_date,
          raw_text = excluded.raw_text,
          url = excluded.url,
          updated_at = current_timestamp
        """,
        (
            item.source_channel,
            item.telegram_message_id,
            item.published_at,
            item.news_date,
            item.raw_text,
            item.url,
        ),
    )

    row = connection.execute(
        """
        select id from news_items
        where source_channel = ? and telegram_message_id = ?
        """,
        (item.source_channel, item.telegram_message_id),
    ).fetchone()
    return int(row["id"])


def replace_daily_briefing(
    connection: sqlite3.Connection,
    briefing_date: str,
    title: str,
    summary_ko: str,
    key_points: list[str],
    top_regions: list[str],
    top_assets: list[str],
    avg_impact_score: float,
    max_risk_level: str,
) -> None:
    connection.execute(
        """
        insert into daily_briefings (
          briefing_date, title, summary_ko, key_points, top_regions, top_assets,
          avg_impact_score, max_risk_level
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(briefing_date) do update set
          title = excluded.title,
          summary_ko = excluded.summary_ko,
          key_points = excluded.key_points,
          top_regions = excluded.top_regions,
          top_assets = excluded.top_assets,
          avg_impact_score = excluded.avg_impact_score,
          max_risk_level = excluded.max_risk_level,
          updated_at = current_timestamp
        """,
        (
            briefing_date,
            title,
            summary_ko,
            json.dumps(key_points, ensure_ascii=False),
            json.dumps(top_regions, ensure_ascii=False),
            json.dumps(top_assets, ensure_ascii=False),
            avg_impact_score,
            max_risk_level,
        ),
    )
