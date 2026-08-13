import bootstrap  # noqa: F401
import argparse
from config import load_settings
from database import connect, init_db
from telegram_store import save_message


def current_oldest_message_id(connection, channel: str) -> int | None:
    row = connection.execute(
        """
        select min(telegram_message_id) as message_id
        from news_items
        where source_channel = ?
        """,
        (channel,),
    ).fetchone()
    return int(row["message_id"]) if row and row["message_id"] is not None else None


async def collect_recent_messages(
    limit: int | None = 500,
    quiet: bool = False,
    commit_interval: int = 100,
    resume_oldest: bool = False,
) -> None:
    from telethon import TelegramClient

    settings = load_settings()
    init_db()
    saved_count = 0
    client = TelegramClient(
        settings.telegram_session_path,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    async with client:
        with connect() as connection:
            for channel in settings.telegram_channels:
                offset_id = current_oldest_message_id(connection, channel) if resume_oldest else 0
                async for message in client.iter_messages(
                    channel,
                    limit=limit,
                    offset_id=offset_id or 0,
                ):
                    news_id = save_message(connection, channel, message)
                    if news_id is None:
                        continue

                    saved_count += 1
                    if saved_count % commit_interval == 0:
                        connection.commit()
                        print(f"committed: {saved_count}", flush=True)

                    if not quiet:
                        print(
                            {
                                "id": news_id,
                                "source_channel": channel,
                                "telegram_message_id": message.id,
                            }
                        )

            connection.commit()

    print(f"saved_or_updated: {saved_count}")


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(description="Collect Telegram channel messages.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--all", action="store_true", help="Backfill all available history.")
    parser.add_argument("--quiet", action="store_true", help="Print progress only.")
    parser.add_argument("--commit-interval", type=int, default=100)
    parser.add_argument(
        "--resume-oldest",
        action="store_true",
        help="Continue backfill from the oldest message currently stored.",
    )
    args = parser.parse_args()

    asyncio.run(
        collect_recent_messages(
            limit=None if args.all else args.limit,
            quiet=args.quiet,
            commit_interval=args.commit_interval,
            resume_oldest=args.resume_oldest,
        )
    )
