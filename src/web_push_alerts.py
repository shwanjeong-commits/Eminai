from __future__ import annotations

import json
import sqlite3

from automation_status import update_status
from config import Settings
from telegram_alerts import alert_reasons, format_alert_message


SERVICE_NAME = "web_push_alerts"
CHANNEL = "web_push"


def web_push_available(settings: Settings) -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key and settings.vapid_subject)


def save_push_subscription(connection: sqlite3.Connection, payload: dict) -> int:
    endpoint = payload.get("endpoint", "")
    keys = payload.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")
    if not endpoint or not p256dh or not auth:
        raise ValueError("Invalid push subscription payload")

    connection.execute(
        """
        insert into push_subscriptions (endpoint, p256dh, auth, active)
        values (?, ?, ?, 1)
        on conflict(endpoint) do update set
          p256dh = excluded.p256dh,
          auth = excluded.auth,
          active = 1,
          updated_at = current_timestamp
        """,
        (endpoint, p256dh, auth),
    )
    row = connection.execute(
        "select id from push_subscriptions where endpoint = ?",
        (endpoint,),
    ).fetchone()
    return int(row["id"])


def active_subscriptions(connection: sqlite3.Connection):
    return connection.execute(
        """
        select id, endpoint, p256dh, auth
        from push_subscriptions
        where active = 1
        order by updated_at desc
        """
    ).fetchall()


def subscription_payload(row) -> dict:
    return {
        "endpoint": row["endpoint"],
        "keys": {
            "p256dh": row["p256dh"],
            "auth": row["auth"],
        },
    }


def mark_subscription_inactive(connection: sqlite3.Connection, subscription_id: int) -> None:
    connection.execute(
        """
        update push_subscriptions
        set active = 0,
            updated_at = current_timestamp
        where id = ?
        """,
        (subscription_id,),
    )


def send_web_push(settings: Settings, subscription: dict, payload: dict) -> None:
    try:
        from pywebpush import WebPushException, webpush
    except ImportError as error:
        raise RuntimeError("pywebpush is not installed. Run pip install -r requirements.txt") from error

    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
    except WebPushException:
        raise


def notification_payload(news_id: int, analysis: dict, reasons: list[str]) -> dict:
    return {
        "title": analysis.get("title") or "뉴스 알림",
        "body": format_alert_message(news_id, analysis, reasons).replace("<b>", "").replace("</b>", "")[:900],
        "url": f"/?newsId={news_id}",
        "newsId": news_id,
        "reasons": reasons,
        "impact": float(analysis.get("impact_score") or 0),
        "risk": analysis.get("risk_level") or "-",
    }


def maybe_send_web_push_alert(
    connection: sqlite3.Connection,
    settings: Settings,
    news_id: int,
    analysis: dict,
) -> dict:
    if not web_push_available(settings):
        update_status(SERVICE_NAME, "disabled", "VAPID_PUBLIC_KEY or VAPID_PRIVATE_KEY missing")
        return {"event": "web_push_disabled", "id": news_id}

    reasons = alert_reasons(settings, analysis)
    if not reasons:
        return {"event": "web_push_not_matched", "id": news_id}

    subscriptions = active_subscriptions(connection)
    if not subscriptions:
        update_status(SERVICE_NAME, "idle", "no active push subscriptions")
        return {"event": "web_push_no_subscribers", "id": news_id}

    sent = 0
    failed = 0
    reason_text = ", ".join(reasons)
    payload = notification_payload(news_id, analysis, reasons)

    for row in subscriptions:
        alert_key = str(row["id"])
        already_sent = connection.execute(
            """
            select 1
            from alert_notifications
            where news_item_id = ?
              and channel = ?
              and alert_key = ?
              and status = 'sent'
            """,
            (news_id, CHANNEL, alert_key),
        ).fetchone()
        if already_sent:
            continue

        try:
            send_web_push(settings, subscription_payload(row), payload)
            connection.execute(
                """
                insert into alert_notifications (
                  news_item_id, channel, alert_key, status, reason, sent_at
                )
                values (?, ?, ?, 'sent', ?, current_timestamp)
                on conflict(news_item_id, channel, alert_key) do update set
                  status = 'sent',
                  reason = excluded.reason,
                  sent_at = current_timestamp,
                  error_message = null,
                  updated_at = current_timestamp
                """,
                (news_id, CHANNEL, alert_key, reason_text),
            )
            sent += 1
        except Exception as error:
            failed += 1
            error_text = str(error)[:200]
            connection.execute(
                """
                insert into alert_notifications (
                  news_item_id, channel, alert_key, status, reason, error_message
                )
                values (?, ?, ?, 'failed', ?, ?)
                on conflict(news_item_id, channel, alert_key) do update set
                  status = 'failed',
                  reason = excluded.reason,
                  error_message = excluded.error_message,
                  updated_at = current_timestamp
                """,
                (news_id, CHANNEL, alert_key, reason_text, error_text),
            )
            if "410" in error_text or "404" in error_text:
                mark_subscription_inactive(connection, row["id"])

    connection.commit()
    update_status(
        SERVICE_NAME,
        "sent" if sent else "failed" if failed else "duplicate",
        f"sent {sent}, failed {failed}",
        last_news_item_id=news_id,
        processed_delta=sent,
        error_delta=failed,
    )
    return {"event": "web_push_sent", "id": news_id, "sent": sent, "failed": failed}
