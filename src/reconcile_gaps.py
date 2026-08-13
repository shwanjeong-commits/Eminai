import bootstrap  # noqa: F401

import argparse
import asyncio
from itertools import islice

from config import load_settings
from database import connect, init_db
from telegram_store import save_message


def chunked(values, size: int):
    iterator = iter(values)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            return
        yield chunk


def missing_ids(connection, channel: str, min_id: int | None, max_id: int | None) -> list[int]:
    row = connection.execute(
        """
        select min(telegram_message_id) as min_id,
               max(telegram_message_id) as max_id
        from news_items
        where source_channel = ?
        """,
        (channel,),
    ).fetchone()
    if not row or row["min_id"] is None or row["max_id"] is None:
        return []

    start = min_id if min_id is not None else int(row["min_id"])
    end = max_id if max_id is not None else int(row["max_id"])
    existing = {
        int(item["telegram_message_id"])
        for item in connection.execute(
            """
            select telegram_message_id
            from news_items
            where source_channel = ?
              and telegram_message_id between ? and ?
            """,
            (channel, start, end),
        ).fetchall()
    }
    audited = {
        int(item["telegram_message_id"])
        for item in connection.execute(
            """
            select telegram_message_id
            from telegram_gap_audit
            where source_channel = ?
              and telegram_message_id between ? and ?
            """,
            (channel, start, end),
        ).fetchall()
    }
    return [
        message_id
        for message_id in range(start, end + 1)
        if message_id not in existing and message_id not in audited
    ]


def mark_gap(connection, channel: str, message_id: int, status: str) -> None:
    connection.execute(
        """
        insert into telegram_gap_audit (source_channel, telegram_message_id, status)
        values (?, ?, ?)
        on conflict(source_channel, telegram_message_id) do update set
          status = excluded.status,
          checked_at = current_timestamp
        """,
        (channel, message_id, status),
    )


async def reconcile_gaps(
    min_id: int | None = None,
    max_id: int | None = None,
    limit_gaps: int | None = None,
    chunk_size: int = 100,
) -> None:
    from telethon import TelegramClient

    settings = load_settings()
    init_db()
    client = TelegramClient(
        settings.telegram_session_path,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    async with client:
        with connect() as connection:
            for channel in settings.telegram_channels:
                ids = missing_ids(connection, channel, min_id, max_id)
                if limit_gaps is not None:
                    ids = ids[:limit_gaps]

                stats = {
                    "gap_ids": len(ids),
                    "fetched": 0,
                    "saved_text": 0,
                    "non_text_or_deleted": 0,
                }
                print({"channel": channel, "gap_ids": len(ids)}, flush=True)

                for batch in chunked(ids, chunk_size):
                    messages = await client.get_messages(channel, ids=batch)
                    stats["fetched"] += len(batch)
                    for message_id, message in zip(batch, messages):
                        if message is None:
                            stats["non_text_or_deleted"] += 1
                            mark_gap(connection, channel, message_id, "missing")
                            continue

                        news_id = save_message(connection, channel, message)
                        if news_id is None:
                            stats["non_text_or_deleted"] += 1
                            mark_gap(connection, channel, message.id, "non_text")
                        else:
                            stats["saved_text"] += 1
                            mark_gap(connection, channel, message.id, "saved_text")

                    connection.commit()
                    print(stats, flush=True)

                print({"channel": channel, "done": stats}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch missing Telegram message IDs and save text news.")
    parser.add_argument("--min-id", type=int)
    parser.add_argument("--max-id", type=int)
    parser.add_argument("--limit-gaps", type=int)
    parser.add_argument("--chunk-size", type=int, default=100)
    args = parser.parse_args()

    asyncio.run(
        reconcile_gaps(
            min_id=args.min_id,
            max_id=args.max_id,
            limit_gaps=args.limit_gaps,
            chunk_size=args.chunk_size,
        )
    )
