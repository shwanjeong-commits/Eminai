from __future__ import annotations

import html
import json
from pathlib import Path
import sqlite3

import httpx

from automation_status import update_status
from config import Settings


SERVICE_NAME = "telegram_alerts"
CHANNEL = "telegram_bot"
ALERT_KEY = "default"


def alert_reasons(settings: Settings, analysis: dict) -> list[str]:
    reasons = []
    impact_score = float(analysis.get("impact_score") or 0)
    risk_level = analysis.get("risk_level") or ""
    searchable = " ".join(
        str(analysis.get(key) or "")
        for key in ("title", "summary_ko", "analysis_ko", "category", "risk_level")
    ).lower()

    if impact_score >= settings.alert_min_impact:
        reasons.append(f"영향도 {impact_score:.1f}")
    if risk_level == "높음":
        reasons.append("고위험")

    for keyword in settings.alert_keywords:
        if keyword.lower() in searchable:
            reasons.append(f"키워드 {keyword}")

    return reasons


def already_notified(connection: sqlite3.Connection, news_id: int) -> bool:
    row = connection.execute(
        """
        select 1
        from alert_notifications
        where news_item_id = ?
          and channel = ?
          and alert_key = ?
          and status = 'sent'
        """,
        (news_id, CHANNEL, ALERT_KEY),
    ).fetchone()
    return row is not None


def record_notification(
    connection: sqlite3.Connection,
    news_id: int,
    status: str,
    reason: str,
    error_message: str | None = None,
) -> None:
    connection.execute(
        """
        insert into alert_notifications (
          news_item_id, channel, alert_key, status, reason, sent_at, error_message
        )
        values (?, ?, ?, ?, ?, case when ? = 'sent' then current_timestamp else null end, ?)
        on conflict(news_item_id, channel, alert_key) do update set
          status = excluded.status,
          reason = excluded.reason,
          sent_at = case when excluded.status = 'sent' then current_timestamp else alert_notifications.sent_at end,
          error_message = excluded.error_message,
          updated_at = current_timestamp
        """,
        (news_id, CHANNEL, ALERT_KEY, status, reason, status, error_message),
    )


def format_alert_message(news_id: int, analysis: dict, reasons: list[str]) -> str:
    title = html.escape(str(analysis.get("title") or "제목 없음"))
    summary = html.escape(str(analysis.get("summary_ko") or "").strip())
    category = html.escape(str(analysis.get("category") or "-"))
    risk = html.escape(str(analysis.get("risk_level") or "-"))
    impact = float(analysis.get("impact_score") or 0)
    reason_text = html.escape(", ".join(reasons))

    return "\n".join(
        [
            "<b>[뉴스 알림]</b>",
            f"<b>{title}</b>",
            "",
            f"영향도: <b>{impact:.1f}</b> / 리스크: <b>{risk}</b> / 분류: {category}",
            f"감지 사유: {reason_text}",
            "",
            summary[:900],
            "",
            f"뉴스 ID: {news_id}",
        ]
    )


def send_telegram_message(settings: Settings, message: str) -> None:
    response = httpx.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={
            "chat_id": settings.telegram_alert_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()


def send_telegram_media_group(
    settings: Settings,
    image_paths: list[Path],
    caption: str | None = None,
) -> None:
    media = []
    files = {}
    handles = []
    try:
        for index, path in enumerate(image_paths):
            field_name = f"card{index}"
            item = {
                "type": "photo",
                "media": f"attach://{field_name}",
            }
            if index == 0 and caption:
                item["caption"] = caption
                item["parse_mode"] = "HTML"
            media.append(item)
            handle = Path(path).open("rb")
            handles.append(handle)
            files[field_name] = (Path(path).name, handle, "image/png")

        response = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMediaGroup",
            data={
                "chat_id": settings.telegram_alert_chat_id,
                "media": json.dumps(media, ensure_ascii=False),
            },
            files=files,
            timeout=60,
        )
        response.raise_for_status()
    finally:
        for handle in handles:
            handle.close()


def maybe_send_alert(
    connection: sqlite3.Connection,
    settings: Settings,
    news_id: int,
    analysis: dict,
) -> dict:
    if not settings.telegram_bot_token or not settings.telegram_alert_chat_id:
        update_status(SERVICE_NAME, "disabled", "TELEGRAM_BOT_TOKEN or TELEGRAM_ALERT_CHAT_ID missing")
        return {"event": "alert_disabled", "id": news_id}

    reasons = alert_reasons(settings, analysis)
    if not reasons:
        return {"event": "alert_not_matched", "id": news_id}

    if already_notified(connection, news_id):
        return {"event": "alert_duplicate", "id": news_id}

    reason_text = ", ".join(reasons)
    try:
        send_telegram_message(settings, format_alert_message(news_id, analysis, reasons))
        record_notification(connection, news_id, "sent", reason_text)
        connection.commit()
        update_status(
            SERVICE_NAME,
            "sent",
            reason_text[:180],
            last_news_item_id=news_id,
            processed_delta=1,
        )
        return {"event": "alert_sent", "id": news_id, "reason": reason_text}
    except Exception as error:
        error_text = str(error)[:200]
        record_notification(connection, news_id, "failed", reason_text, error_text)
        connection.commit()
        update_status(
            SERVICE_NAME,
            "failed",
            error_text,
            last_news_item_id=news_id,
            error_delta=1,
        )
        return {"event": "alert_failed", "id": news_id, "reason": error_text}
