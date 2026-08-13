from __future__ import annotations

from datetime import timezone, timedelta
import re
from typing import Any

from classifier import classify_item, classify_text
from repository import NewsInput, upsert_news_item


URL_PATTERN = re.compile(r"https?://\S+")
KST = timezone(timedelta(hours=9))


def first_url(text: str) -> str | None:
    match = URL_PATTERN.search(text)
    return match.group(0) if match else None


def source_name(channel: str | None, chat: Any = None) -> str:
    if channel:
        return channel

    username = getattr(chat, "username", None)
    if username:
        return username

    title = getattr(chat, "title", None)
    if title:
        return title

    chat_id = getattr(chat, "id", None)
    return str(chat_id or "unknown")


def local_news_date(message_date) -> str:
    return message_date.astimezone(KST).date().isoformat()


def save_message(connection, channel: str | None, message, chat: Any = None) -> int | None:
    text = message.message
    if not text:
        return None

    source_channel = source_name(channel, chat)
    first_pass = classify_text(text)
    if first_pass["analysis_status"] == "ignored":
        return None

    existing = connection.execute(
        """
        select id
        from news_items
        where source_channel = ? and telegram_message_id = ?
        """,
        (source_channel, message.id),
    ).fetchone()
    if existing:
        return None

    news_id = upsert_news_item(
        connection,
        NewsInput(
            source_channel=source_channel,
            telegram_message_id=message.id,
            published_at=message.date.isoformat(),
            news_date=local_news_date(message.date),
            raw_text=text,
            url=first_url(text),
        ),
    )
    classify_item(connection, news_id)
    return news_id
