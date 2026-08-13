from pathlib import Path
from contextlib import closing
import sqlite3


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "news.db"
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma busy_timeout = 30000")
    connection.execute("pragma synchronous = normal")
    connection.execute("pragma foreign_keys = on")
    return connection


def init_db(db_path: Path = DB_PATH) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with closing(connect(db_path)) as connection, connection:
        connection.execute("pragma journal_mode = wal")
        tables = {
            row["name"]
            for row in connection.execute("select name from sqlite_master where type='table'").fetchall()
        }
        if "news_items" in tables:
            legacy_columns = {
                "content_type": "text",
                "analysis_status": "text not null default 'pending'",
                "analysis_priority": "real not null default 0",
                "analysis_reason": "text",
                "analysis_scope": "text",
                "duplicate_key": "text",
                "user_hidden": "integer not null default 0",
                "user_note": "text",
            }
            for column, definition in legacy_columns.items():
                ensure_column(connection, "news_items", column, definition)
        connection.executescript(schema)
        ensure_column(connection, "economic_forecasts", "outcome_bucket", "text")
        ensure_column(connection, "economic_forecasts", "base_error_pct", "real")
        analysis_columns = {
            "key_variables": "text not null default '[]'",
            "variable_interactions": "text not null default '[]'",
            "scenario_analysis": "text not null default '[]'",
            "turning_conditions": "text not null default '[]'",
        }
        for column, definition in analysis_columns.items():
            ensure_column(connection, "economic_analyses", column, definition)


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row["name"] for row in connection.execute(f"pragma table_info({table})").fetchall()}
    if column not in existing:
        connection.execute(f"alter table {table} add column {column} {definition}")


if __name__ == "__main__":
    init_db()
    print(f"initialized {DB_PATH}")
