import argparse
import json
import sqlite3
from pathlib import Path


COLUMNS = [
    "event_id", "title", "country", "category", "importance", "scheduled_at",
    "timezone", "status", "reference_period", "previous_value", "forecast_value",
    "actual_value", "unit", "source_name", "source_url", "is_confirmed", "notes",
]


CREATE_SQL = """
create table if not exists economic_calendar_events (
  event_id text primary key,
  title text not null,
  country text not null,
  category text not null,
  importance text not null,
  scheduled_at text not null,
  timezone text not null default 'Asia/Seoul',
  status text not null default 'scheduled',
  reference_period text,
  previous_value text,
  forecast_value text,
  actual_value text,
  unit text,
  source_name text not null,
  source_url text not null,
  is_confirmed integer not null default 1,
  notes text,
  created_at text not null default current_timestamp,
  updated_at text not null default current_timestamp
)
"""


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("pragma busy_timeout = 30000")
    return connection


def export_events(database: Path, output: Path) -> None:
    with connect(database) as connection:
        rows = connection.execute(
            f"select {','.join(COLUMNS)} from economic_calendar_events order by scheduled_at,event_id"
        ).fetchall()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exported={len(rows)}")


def import_events(database: Path, source: Path) -> None:
    events = json.loads(source.read_text(encoding="utf-8"))
    placeholders = ",".join("?" for _ in COLUMNS)
    updates = ",".join(
        f"{column}=excluded.{column}" for column in COLUMNS if column != "event_id"
    )
    sql = (
        f"insert into economic_calendar_events ({','.join(COLUMNS)}) values ({placeholders}) "
        f"on conflict(event_id) do update set {updates},updated_at=current_timestamp"
    )
    with connect(database) as connection:
        connection.execute(CREATE_SQL)
        connection.executemany(sql, [[event.get(column) for column in COLUMNS] for event in events])
    print(f"imported={len(events)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("database", type=Path)
    export_parser.add_argument("output", type=Path)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("database", type=Path)
    import_parser.add_argument("source", type=Path)
    args = parser.parse_args()
    if args.command == "export":
        export_events(args.database, args.output)
    else:
        import_events(args.database, args.source)


if __name__ == "__main__":
    main()
