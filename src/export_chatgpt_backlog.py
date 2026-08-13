import bootstrap  # noqa: F401

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from database import connect


def export_backlog(output_path: Path, limit: int = 500) -> int:
    with connect() as connection:
        rows = connection.execute(
            """
            select id, telegram_message_id, source_channel, published_at, news_date,
                   analysis_priority, content_type, raw_text
            from news_items
            where analysis_scope = 'analysis_target'
              and analysis_status in ('queued', 'review', 'filtered')
            order by published_at asc, id asc
            limit ?
            """,
            (limit,),
        ).fetchall()

    payload = {
        "format": "eminai-chatgpt-backlog-v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "item_count": len(rows),
        "items": [dict(row) for row in rows],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"exported={len(rows)}")
    print(f"output={output_path}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export queued news for manual ChatGPT analysis.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    export_backlog(args.output, max(1, args.limit))


if __name__ == "__main__":
    main()
