from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import bootstrap  # noqa: E402,F401
from config import load_settings, normalize_channel  # noqa: E402


SCHEMA = """
create table if not exists telegram_messages (
    id integer primary key,
    channel text not null,
    telegram_message_id integer not null,
    published_at text not null,
    collected_at text not null,
    text text,
    post_url text not null,
    views integer,
    forwards integer,
    replies integer,
    reactions_json text,
    media_type text,
    grouped_id integer,
    reply_to_message_id integer,
    unique(channel, telegram_message_id)
);

create index if not exists idx_catchup_published_at
on telegram_messages(published_at);
"""


def reaction_data(message) -> str | None:
    reactions = getattr(message, "reactions", None)
    if not reactions or not getattr(reactions, "results", None):
        return None

    rows = []
    for item in reactions.results:
        reaction = getattr(item, "reaction", None)
        value = getattr(reaction, "emoticon", None) or getattr(reaction, "document_id", None)
        rows.append({"reaction": str(value), "count": item.count})
    return json.dumps(rows, ensure_ascii=False)


async def collect(channel: str, days: int, db_path: Path) -> None:
    from telethon import TelegramClient

    settings = load_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise RuntimeError("TELEGRAM_API_ID 또는 TELEGRAM_API_HASH가 없습니다.")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(
        settings.telegram_session_path,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    saved = 0
    scanned = 0
    async with client:
        entity = await client.get_entity(channel)
        canonical_channel = getattr(entity, "username", None) or channel

        with sqlite3.connect(db_path) as connection:
            connection.executescript(SCHEMA)

            async for message in client.iter_messages(entity):
                if message.date < cutoff:
                    break
                scanned += 1

                replies = getattr(getattr(message, "replies", None), "replies", None)
                media = type(message.media).__name__ if message.media else None
                reply_to = getattr(message, "reply_to_msg_id", None)
                post_url = f"https://t.me/{canonical_channel}/{message.id}"

                cursor = connection.execute(
                    """
                    insert or ignore into telegram_messages (
                        channel, telegram_message_id, published_at, collected_at,
                        text, post_url, views, forwards, replies, reactions_json,
                        media_type, grouped_id, reply_to_message_id
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        canonical_channel,
                        message.id,
                        message.date.isoformat(),
                        datetime.now(timezone.utc).isoformat(),
                        message.message or "",
                        post_url,
                        message.views,
                        message.forwards,
                        replies,
                        reaction_data(message),
                        media,
                        message.grouped_id,
                        reply_to,
                    ),
                )
                saved += cursor.rowcount

            connection.commit()
            total = connection.execute("select count(*) from telegram_messages").fetchone()[0]
            dated = connection.execute(
                "select min(published_at), max(published_at) from telegram_messages"
            ).fetchone()

    print(f"channel={canonical_channel}")
    print(f"cutoff_utc={cutoff.isoformat()}")
    print(f"scanned={scanned}, inserted={saved}, total={total}")
    print(f"range={dated[0]} .. {dated[1]}")
    print(f"database={db_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a disposable Telegram catch-up database.")
    parser.add_argument("channel", help="Public channel username or t.me URL")
    parser.add_argument("--days", type=int, default=21)
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT_DIR / "data" / "insidertracking_catchup.sqlite3",
    )
    args = parser.parse_args()
    asyncio.run(collect(normalize_channel(args.channel), args.days, args.db))


if __name__ == "__main__":
    main()
