import bootstrap  # noqa: F401

import argparse
import asyncio
from collections import Counter
from datetime import timezone, timedelta

from telethon import TelegramClient

from classifier import classify_text
from config import load_settings
from database import connect, init_db
from telegram_store import save_message


KST = timezone(timedelta(hours=9))


def existing_message_ids(connection, channel: str) -> set[int]:
    rows = connection.execute(
        """
        select telegram_message_id from news_items where source_channel = ?
        """,
        (channel,),
    ).fetchall()
    return {int(row["telegram_message_id"]) for row in rows}


async def audit_recent(limit: int, repair: bool = False) -> list[dict]:
    settings = load_settings()
    init_db()
    client = TelegramClient(
        settings.telegram_session_path,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    async with client:
        return await audit_recent_with_client(client, settings.telegram_channels, limit, repair=repair)


async def audit_recent_with_client(
    client,
    channels: list[str],
    limit: int,
    repair: bool = False,
) -> list[dict]:
    results = []
    with connect() as connection:
        for channel in channels:
            known_ids = existing_message_ids(connection, channel)
            checked = 0
            expected = 0
            ignored = 0
            collected_types = Counter()
            ignored_types = Counter()
            ignored_reasons = Counter()
            missing_types = Counter()
            missing = []
            repaired = 0

            async for message in client.iter_messages(channel, limit=limit):
                checked += 1
                text = " ".join((message.message or "").split())
                if not text:
                    ignored += 1
                    continue

                result = classify_text(text)
                should_collect = result["analysis_status"] != "ignored"
                if should_collect:
                    expected += 1
                    collected_types[result["content_type"]] += 1
                    if message.id not in known_ids:
                        missing_types[result["content_type"]] += 1
                        saved_id = None
                        if repair:
                            saved_id = save_message(connection, channel, message)
                            if saved_id is not None:
                                connection.commit()
                                known_ids.add(message.id)
                                repaired += 1
                        missing.append(
                            {
                                "id": message.id,
                                "time": message.date.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S"),
                                "type": result["content_type"],
                                "reason": result["analysis_reason"],
                                "repaired": saved_id is not None,
                                "text": text[:120],
                            }
                        )
                else:
                    ignored += 1
                    ignored_types[result["content_type"]] += 1
                    ignored_reasons[result["analysis_reason"]] += 1

            result = {
                "channel": channel,
                "checked": checked,
                "expected_collect": expected,
                "expected_ignored": ignored,
                "collected_types": dict(collected_types.most_common(8)),
                "ignored_types": dict(ignored_types.most_common(8)),
                "ignored_reasons": dict(ignored_reasons.most_common(8)),
                "missing_types": dict(missing_types.most_common(8)),
                "missing_expected": missing,
                "repaired": repaired,
            }
            results.append(result)
            print(result, flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit recent Telegram messages against local DB classification.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--repair", action="store_true", help="Save missing news-worthy messages without storing ignored messages.")
    args = parser.parse_args()
    asyncio.run(audit_recent(args.limit, repair=args.repair))
