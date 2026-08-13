import bootstrap  # noqa: F401
from database import connect


NEWS_ITEM_COLUMNS = {
    "content_type": "text",
    "analysis_status": "text not null default 'pending'",
    "analysis_priority": "real not null default 0",
    "analysis_reason": "text",
    "analysis_scope": "text",
    "duplicate_key": "text",
    "user_hidden": "integer not null default 0",
    "user_note": "text",
}

INDEXES = [
    "create index if not exists idx_news_items_analysis_status on news_items(analysis_status)",
    "create index if not exists idx_news_items_analysis_scope on news_items(analysis_scope)",
    "create index if not exists idx_news_items_analysis_priority on news_items(analysis_priority)",
    "create index if not exists idx_news_events_region_date on news_events(region_name, event_date)",
    "create index if not exists idx_alert_notifications_status on alert_notifications(status)",
    "create index if not exists idx_push_subscriptions_active on push_subscriptions(active)",
]

TABLES = [
    """
    create table if not exists ai_context_batches (
      id integer primary key autoincrement,
      period_start text not null,
      period_end text not null,
      item_count integer not null,
      context_text text not null,
      status text not null default 'ready',
      created_at text not null default current_timestamp,
      updated_at text not null default current_timestamp,
      unique(period_start, period_end)
    )
    """,
    """
    create table if not exists telegram_gap_audit (
      source_channel text not null,
      telegram_message_id integer not null,
      status text not null,
      checked_at text not null default current_timestamp,
      primary key (source_channel, telegram_message_id)
    )
    """,
    """
    create table if not exists ai_situation_state (
      id integer primary key check (id = 1),
      state_text text not null,
      source_count integer not null default 0,
      last_news_item_id integer,
      updated_at text not null default current_timestamp
    )
    """,
    """
    create table if not exists automation_status (
      service_name text primary key,
      status text not null,
      detail text,
      last_event_at text,
      last_news_item_id integer,
      processed_count integer not null default 0,
      error_count integer not null default 0,
      updated_at text not null default current_timestamp
    )
    """,
    """
    create table if not exists news_events (
      id integer primary key autoincrement,
      news_item_id integer not null references news_items(id) on delete cascade,
      event_date text not null,
      region_name text,
      event_title text not null,
      event_summary_ko text not null,
      risk_level text,
      impact_score real,
      keywords text not null default '[]',
      created_at text not null default current_timestamp
    )
    """,
    """
    create table if not exists alert_notifications (
      id integer primary key autoincrement,
      news_item_id integer not null references news_items(id) on delete cascade,
      channel text not null,
      alert_key text not null,
      status text not null,
      reason text,
      sent_at text,
      error_message text,
      created_at text not null default current_timestamp,
      updated_at text not null default current_timestamp,
      unique(news_item_id, channel, alert_key)
    )
    """,
    """
    create table if not exists daily_report_deliveries (
      report_date text not null,
      channel text not null,
      status text not null,
      sent_at text,
      error_message text,
      created_at text not null default current_timestamp,
      updated_at text not null default current_timestamp,
      primary key (report_date, channel)
    )
    """,
    """
    create table if not exists push_subscriptions (
      id integer primary key autoincrement,
      endpoint text not null unique,
      p256dh text not null,
      auth text not null,
      user_label text,
      active integer not null default 1,
      created_at text not null default current_timestamp,
      updated_at text not null default current_timestamp
    )
    """,
]


def existing_columns(connection, table_name: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"pragma table_info({table_name})").fetchall()
    }


def migrate() -> None:
    with connect() as connection:
        columns = existing_columns(connection, "news_items")
        for column, definition in NEWS_ITEM_COLUMNS.items():
            if column not in columns:
                connection.execute(f"alter table news_items add column {column} {definition}")

        for statement in TABLES:
            connection.execute(statement)

        for statement in INDEXES:
            connection.execute(statement)


if __name__ == "__main__":
    migrate()
    print("migration complete")
