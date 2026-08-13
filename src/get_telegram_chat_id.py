from __future__ import annotations

import argparse

import bootstrap  # noqa: F401

import httpx

from config import load_settings


def get_updates(token: str) -> list[dict]:
    response = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(str(payload))
    return payload.get("result") or []


def main() -> None:
    parser = argparse.ArgumentParser(description="Print Telegram chat IDs that recently messaged the bot.")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    settings = load_settings()
    token = args.token or settings.telegram_bot_token
    if not token:
        raise SystemExit("missing TELEGRAM_BOT_TOKEN or --token")

    seen = set()
    for update in get_updates(token):
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or chat_id in seen:
            continue
        seen.add(chat_id)
        title = chat.get("title") or chat.get("username") or "private chat"
        print(f"{chat_id}\t{title}")

    if not seen:
        print("No chats found. Send a message to your bot in Telegram, then run this again.")


if __name__ == "__main__":
    main()
