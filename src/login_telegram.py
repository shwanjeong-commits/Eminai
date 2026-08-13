import bootstrap  # noqa: F401
from config import load_settings


async def login() -> None:
    from telethon import TelegramClient

    settings = load_settings()
    client = TelegramClient(
        settings.telegram_session_path,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    await client.start()
    me = await client.get_me()
    print(f"telegram session ready: {me.username or me.id}")
    await client.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(login())
