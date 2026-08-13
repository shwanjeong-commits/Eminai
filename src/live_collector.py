import bootstrap  # noqa: F401
import asyncio
import os
from collections import Counter

from audit_recent_messages import audit_recent_with_client
from automation_status import update_status
from config import load_settings
from database import connect, init_db
from telegram_store import save_message


SERVICE_NAME = "telegram_live_collector"
MANUAL_UPDATE_SERVICE = "manual_update"
RECENT_POLL_LIMIT = 50
MANUAL_UPDATE_LIMIT = int(os.getenv("MANUAL_UPDATE_LIMIT", "300") or 300)
RECENT_POLL_INTERVAL_SECONDS = 60
FILTER_AUDIT_SERVICE = "filter_audit_worker"
FILTER_AUDIT_LIMIT = int(os.getenv("FILTER_AUDIT_LIMIT", "300") or 300)
FILTER_AUDIT_INTERVAL_SECONDS = int(os.getenv("FILTER_AUDIT_INTERVAL_SECONDS", "21600") or 21600)
FILTER_AUDIT_INITIAL_DELAY_SECONDS = int(os.getenv("FILTER_AUDIT_INITIAL_DELAY_SECONDS", "120") or 120)
FILTER_AUDIT_AUTO_REPAIR = os.getenv("FILTER_AUDIT_AUTO_REPAIR", "1").strip().lower() not in {"0", "false", "no", "off"}
DB_TASK_LOCK = asyncio.Lock()


def manual_update_status() -> str | None:
    with connect() as connection:
        row = connection.execute(
            """
            select status
            from automation_status
            where service_name = ?
            """,
            (MANUAL_UPDATE_SERVICE,),
        ).fetchone()
    return row["status"] if row else None


async def heartbeat_task() -> None:
    while True:
        update_status(SERVICE_NAME, "listening", "heartbeat")
        await asyncio.sleep(30)


async def collect_recent_messages(client, settings, reason: str, limit: int) -> dict:
    saved_count = 0
    checked_count = 0

    async with DB_TASK_LOCK:
        with connect() as connection:
            for channel in settings.telegram_channels:
                async for message in client.iter_messages(channel, limit=limit):
                    checked_count += 1
                    news_id = save_message(connection, channel, message)
                    if news_id is None:
                        continue
                    saved_count += 1
                    connection.commit()
            connection.commit()

    if saved_count:
        update_status(
            SERVICE_NAME,
            "poll_collected",
            f"{reason}: checked {checked_count}, saved {saved_count}",
            processed_delta=saved_count,
        )
    return {
        "checked": checked_count,
        "saved": saved_count,
    }


async def recent_poll_task(client, settings) -> None:
    while True:
        await asyncio.sleep(RECENT_POLL_INTERVAL_SECONDS)
        try:
            result = await collect_recent_messages(client, settings, "recent poll", RECENT_POLL_LIMIT)
            if result["saved"]:
                print({"event": "recent_poll", **result}, flush=True)
        except Exception as error:
            update_status(SERVICE_NAME, "poll_error", str(error)[:200], error_delta=1)


def summarize_audit(results: list[dict]) -> dict:
    missing = [item for result in results for item in result.get("missing_expected", [])]
    repaired = sum(int(result.get("repaired", 0)) for result in results)
    expected = sum(int(result.get("expected_collect", 0)) for result in results)
    checked = sum(int(result.get("checked", 0)) for result in results)
    type_counts = Counter(item.get("type", "unknown") for item in missing)
    return {
        "checked": checked,
        "expected": expected,
        "missing": len(missing),
        "repaired": repaired,
        "remaining": max(0, len(missing) - repaired),
        "types": dict(type_counts.most_common(4)),
    }


async def run_filter_audit_from_live_client(client, settings) -> dict:
    async with DB_TASK_LOCK:
        results = await audit_recent_with_client(
            client,
            settings.telegram_channels,
            FILTER_AUDIT_LIMIT,
            repair=FILTER_AUDIT_AUTO_REPAIR,
        )
    summary = summarize_audit(results)
    status = "attention" if summary["remaining"] else "repaired" if summary["repaired"] else "ok"
    update_status(
        FILTER_AUDIT_SERVICE,
        status,
        (
            f"checked {summary['checked']}, expected {summary['expected']}, "
            f"missing {summary['missing']}, repaired {summary['repaired']}, "
            f"remaining {summary['remaining']}, types {summary['types']}"
        ),
        processed_delta=summary["repaired"] or summary["checked"],
        error_delta=1 if summary["remaining"] else 0,
    )
    return summary


async def filter_audit_task(client, settings) -> None:
    await asyncio.sleep(FILTER_AUDIT_INITIAL_DELAY_SECONDS)
    while True:
        try:
            summary = await run_filter_audit_from_live_client(client, settings)
            print({"event": "filter_audit", **summary}, flush=True)
        except Exception as error:
            update_status(FILTER_AUDIT_SERVICE, "failed", str(error)[:200], error_delta=1)
        await asyncio.sleep(FILTER_AUDIT_INTERVAL_SECONDS)


async def run_manual_update_from_live_client(client, settings) -> None:
    update_status(
        MANUAL_UPDATE_SERVICE,
        "collecting",
        f"collecting recent Telegram messages, limit={MANUAL_UPDATE_LIMIT}",
    )
    result = await collect_recent_messages(client, settings, "manual update collect", MANUAL_UPDATE_LIMIT)
    saved_count = result["saved"]
    checked_count = result["checked"]

    update_status(
        MANUAL_UPDATE_SERVICE,
        "completed",
        f"manual update completed: checked {checked_count}, saved {saved_count}; analysis worker handles queued items",
        processed_delta=saved_count,
    )


async def manual_update_task(client, settings) -> None:
    while True:
        await asyncio.sleep(5)
        if manual_update_status() not in {"queued", "collecting", "reconciling", "analyzing", "rebuilding"}:
            continue
        try:
            await run_manual_update_from_live_client(client, settings)
        except Exception as error:
            update_status(MANUAL_UPDATE_SERVICE, "failed", str(error)[:200], error_delta=1)


async def run_live_collector_once() -> None:
    from telethon import TelegramClient, events

    settings = load_settings()
    init_db()

    client = TelegramClient(
        settings.telegram_session_path,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )

    @client.on(events.NewMessage(chats=settings.telegram_channels))
    async def handle_new_message(event) -> None:
        try:
            chat = await event.get_chat()
            async with DB_TASK_LOCK:
                with connect() as connection:
                    news_id = save_message(connection, None, event.message, chat)
                    connection.commit()
            if news_id is not None:
                update_status(
                    SERVICE_NAME,
                    "collected",
                    "new message saved; queued for analysis worker",
                    news_id,
                    processed_delta=1,
                )
        except Exception as error:
            update_status(SERVICE_NAME, "handler_error", str(error)[:200], error_delta=1)
            raise

        if news_id is not None:
            source = getattr(chat, "username", None) or getattr(chat, "title", "unknown")
            print(
                {
                    "event": "saved",
                    "id": news_id,
                    "source_channel": source,
                    "telegram_message_id": event.message.id,
                    "published_at": event.message.date.isoformat(),
                },
                flush=True,
            )

    async with client:
        update_status(SERVICE_NAME, "listening", "connected to telegram")
        update_status(
            FILTER_AUDIT_SERVICE,
            "scheduled",
            f"integrated with live collector; first audit in {FILTER_AUDIT_INITIAL_DELAY_SECONDS}s",
        )
        heartbeat = asyncio.create_task(heartbeat_task())
        manual_update = asyncio.create_task(manual_update_task(client, settings))
        recent_poll = asyncio.create_task(recent_poll_task(client, settings))
        filter_audit = asyncio.create_task(filter_audit_task(client, settings))
        print(
            "live collector started: " + ", ".join(settings.telegram_channels),
            flush=True,
        )
        try:
            await client.run_until_disconnected()
        finally:
            heartbeat.cancel()
            manual_update.cancel()
            recent_poll.cancel()
            filter_audit.cancel()
            update_status(SERVICE_NAME, "disconnected", "telegram client disconnected")


async def run_live_collector() -> None:
    retry_delay = 5
    while True:
        try:
            await run_live_collector_once()
            retry_delay = 5
        except asyncio.CancelledError:
            update_status(SERVICE_NAME, "stopped", "collector cancelled")
            raise
        except Exception as error:
            update_status(SERVICE_NAME, "reconnecting", str(error)[:200], error_delta=1)
            print({"event": "collector_reconnecting", "delay": retry_delay, "reason": str(error)[:160]}, flush=True)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 120)


if __name__ == "__main__":
    asyncio.run(run_live_collector())
