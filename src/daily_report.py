from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import html
import json
import os
import re
import sqlite3
import sys

import bootstrap  # noqa: F401

from automation_status import update_status
from config import load_settings
from daily_briefing_builder import build_daily_briefings
from database import connect, init_db
from telegram_alerts import send_telegram_media_group, send_telegram_message


KST = timezone(timedelta(hours=9))
SERVICE_NAME = "daily_report"
CHANNEL = "telegram_daily_report"
MAX_TELEGRAM_LENGTH = 3900


def report_cards_enabled() -> bool:
    return os.getenv("DAILY_REPORT_SEND_CARDS", "1").strip().lower() in {"1", "true", "yes", "on"}


def report_date_from_mode(mode: str) -> str:
    base = datetime.now(KST).date()
    if mode.lower() == "yesterday":
        base -= timedelta(days=1)
    return base.isoformat()


def compact(text: str | None, limit: int) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    clipped = value[:limit].rstrip()
    boundary_candidates = [
        clipped.rfind(mark)
        for mark in (".", "!", "?", "。", "다.", "요.", "니다.", "습니다.")
    ]
    boundary = max(boundary_candidates)
    if boundary >= max(30, int(limit * 0.45)):
        suffix = clipped[boundary : boundary + 4]
        if suffix.startswith(("다.", "요.")):
            return clipped[: boundary + 2].rstrip()
        if suffix.startswith(("니다.", "습니다.")):
            return clipped[: boundary + len(suffix.split(".")[0]) + 1].rstrip()
        return clipped[: boundary + 1].rstrip()

    comma_boundary = max(clipped.rfind(","), clipped.rfind("·"), clipped.rfind(";"))
    if comma_boundary >= max(30, int(limit * 0.55)):
        return clipped[:comma_boundary].rstrip()
    return clipped.rstrip()


def split_sentences(text: str | None) -> list[str]:
    value = " ".join((text or "").split())
    if not value:
        return []
    sentences: list[str] = []
    start = 0
    for index, char in enumerate(value):
        if char not in ".!?。！？":
            continue
        if (
            char == "."
            and index > 0
            and index + 1 < len(value)
            and value[index - 1].isdigit()
            and value[index + 1].isdigit()
        ):
            continue
        sentence = value[start : index + 1].strip()
        if sentence:
            sentences.append(sentence)
        start = index + 1
    tail = value[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def sentence_excerpt(text: str | None, limit: int, max_sentences: int = 2) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return compact(text, limit)

    selected: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*selected, sentence]).strip()
        if selected and len(candidate) > limit:
            break
        if len(sentence) > limit and not selected:
            return compact(sentence, limit)
        selected.append(sentence)
        if len(selected) >= max_sentences:
            break

    return " ".join(selected).strip() or compact(text, limit)


def parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
        if isinstance(data, list):
            return [str(item) for item in data if str(item).strip()]
    except json.JSONDecodeError:
        return []
    return []


def fetch_briefing(connection: sqlite3.Connection, report_date: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        select briefing_date, title, summary_ko, key_points, top_regions, top_assets,
               avg_impact_score, max_risk_level
        from daily_briefings
        where briefing_date = ?
        """,
        (report_date,),
    ).fetchone()


def fetch_counts(connection: sqlite3.Connection, report_date: str) -> dict[str, int]:
    row = connection.execute(
        """
        select
          count(*) as total,
          sum(case when analysis_status = 'analyzed' then 1 else 0 end) as analyzed,
          sum(case when analysis_status in ('pending', 'queued') then 1 else 0 end) as queued,
          sum(case when analysis_status = 'review' then 1 else 0 end) as review
        from news_items
        where news_date = ?
          and coalesce(user_hidden, 0) = 0
        """,
        (report_date,),
    ).fetchone()
    return {
        "total": int(row["total"] or 0),
        "analyzed": int(row["analyzed"] or 0),
        "queued": int(row["queued"] or 0),
        "review": int(row["review"] or 0),
    }


def fetch_top_news(connection: sqlite3.Connection, report_date: str, limit: int = 12) -> list[sqlite3.Row]:
    return connection.execute(
        """
        select id, title, summary_ko, analysis_ko, impact_score, risk_level, category
        from news_items
        where news_date = ?
          and analysis_status = 'analyzed'
          and coalesce(user_hidden, 0) = 0
        order by coalesce(impact_score, 0) desc, published_at asc
        limit ?
        """,
        (report_date, limit),
    ).fetchall()


def fetch_latest_analyzed_date(connection: sqlite3.Connection) -> str | None:
    row = connection.execute(
        """
        select max(news_date) as news_date
        from news_items
        where analysis_status = 'analyzed'
          and coalesce(user_hidden, 0) = 0
        """
    ).fetchone()
    return row["news_date"] if row else None


def already_sent(connection: sqlite3.Connection, report_date: str) -> bool:
    row = connection.execute(
        """
        select 1
        from daily_report_deliveries
        where report_date = ?
          and channel = ?
          and status = 'sent'
        """,
        (report_date, CHANNEL),
    ).fetchone()
    return row is not None


def record_delivery(
    connection: sqlite3.Connection,
    report_date: str,
    status: str,
    error_message: str | None = None,
) -> None:
    connection.execute(
        """
        insert into daily_report_deliveries (
          report_date, channel, status, sent_at, error_message, updated_at
        )
        values (?, ?, ?, case when ? = 'sent' then current_timestamp else null end, ?, current_timestamp)
        on conflict(report_date, channel) do update set
          status = excluded.status,
          sent_at = case when excluded.status = 'sent' then current_timestamp else daily_report_deliveries.sent_at end,
          error_message = excluded.error_message,
          updated_at = current_timestamp
        """,
        (report_date, CHANNEL, status, status, error_message),
    )


def normalize_title(title: str) -> str:
    value = re.sub(r"\s+", " ", title or "").strip().lower()
    value = re.sub(r"[^0-9a-z가-힣一-龥 ]+", "", value)
    stop_words = ["및", "관련", "언급", "개시", "급락", "상승", "브리핑"]
    for word in stop_words:
        value = value.replace(word, "")
    return re.sub(r"\s+", " ", value).strip()[:42]


def unique_top_news(rows: list[sqlite3.Row], limit: int = 5) -> list[sqlite3.Row]:
    seen: set[str] = set()
    unique_rows = []
    for row in rows:
        title = row["title"] or row["summary_ko"] or ""
        key = normalize_title(title)
        if not key:
            key = str(row["id"])
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)
        if len(unique_rows) >= limit:
            break
    return unique_rows


def build_day_takeaway(
    briefing: sqlite3.Row | None,
    top_news: list[sqlite3.Row],
    counts: dict[str, int],
) -> str:
    if not top_news:
        if counts["total"]:
            return "뉴스는 수집됐지만 아직 분석 완료분이 부족합니다. 오늘의 흐름은 후속 분석 후 보강됩니다."
        return "아직 오늘 수집된 뉴스가 없습니다."

    max_risk = briefing["max_risk_level"] if briefing else (top_news[0]["risk_level"] or "-")
    avg = briefing["avg_impact_score"] if briefing else None
    avg_text = f"평균 영향도 {avg:.1f}" if isinstance(avg, (int, float)) else "주요 사건 중심"
    return f"오늘은 {avg_text}, 최고 위험 {max_risk} 수준의 뉴스가 확인됐습니다. 아래 주요 사건으로 하루 흐름을 먼저 잡으면 됩니다."


def build_checkpoints(top_news: list[sqlite3.Row], top_assets: list[str]) -> list[str]:
    text = " ".join(
        " ".join(
            [
                row["title"] or "",
                row["summary_ko"] or "",
                row["analysis_ko"] or "",
            ]
        )
        for row in top_news
    )
    candidates = []
    lowered = text.lower()

    if any(word in lowered for word in ["이란", "호르무즈", "중동", "유가", "원유"]):
        candidates.append("유가와 중동 리스크 프리미엄이 되돌림을 보이는지 확인")
    if any(word in lowered for word in ["반도체", "엔비디아", "tsmc", "sk하이닉스", "삼성전자", "ai"]):
        candidates.append("AI/반도체 매도세가 단기 조정인지 추세 훼손인지 확인")
    if any(word in lowered for word in ["fomc", "연준", "금리", "달러", "국채"]):
        candidates.append("FOMC 전후 달러와 장기금리 변동성 확대 여부 확인")
    if any(word in lowered for word in ["중국", "관세", "수출", "duv", "asml"]):
        candidates.append("중국 정책/기술 자립 이슈가 밸류체인 재평가로 번지는지 확인")

    for asset in top_assets:
        point = f"{asset} 관련 가격 반응과 후속 뉴스 확인"
        if point not in candidates:
            candidates.append(point)

    return candidates[:4] or ["상위 영향 뉴스의 후속 보도와 가격 반응을 확인"]


def build_flow_lines(top_news: list[sqlite3.Row]) -> list[str]:
    lines = []
    for row in top_news[:3]:
        title = sentence_excerpt(row["title"] or "제목 없음", 58, 1)
        body = sentence_excerpt(row["analysis_ko"] or row["summary_ko"] or "", 180, 2)
        lines.append(f"• <b>{html.escape(title)}</b>\n  원인: 정책/사건 변화\n  영향: {html.escape(body)}")
    return lines


def build_event_lines(top_news: list[sqlite3.Row]) -> list[str]:
    lines = []
    for row in top_news[:5]:
        title = sentence_excerpt(row["title"] or "제목 없음", 62, 1)
        what_happened = sentence_excerpt(row["summary_ko"] or row["analysis_ko"] or "", 160, 2)
        context = sentence_excerpt(row["analysis_ko"] or row["summary_ko"] or "", 190, 2)
        impact = float(row["impact_score"] or 0)
        risk = row["risk_level"] or "-"
        lines.append(
            f"• <b>{html.escape(title)}</b>\n"
            f"  무슨 일: {html.escape(what_happened)}\n"
            f"  배경/의미: {html.escape(context)}\n"
            f"  영향도 {impact:.1f} · 위험 {html.escape(risk)}"
        )
    return lines


def bullet_lines(items: list[str], limit: int, item_limit: int = 95) -> list[str]:
    return [f"• {html.escape(sentence_excerpt(item, item_limit, 2))}" for item in items[:limit]]


def build_report_message(
    connection: sqlite3.Connection,
    report_date: str,
    fallback_to_latest: bool = True,
) -> tuple[str, str]:
    build_daily_briefings(limit_dates=3)
    briefing = fetch_briefing(connection, report_date)
    counts = fetch_counts(connection, report_date)

    if not briefing and counts["total"] == 0 and fallback_to_latest:
        latest = fetch_latest_analyzed_date(connection)
        if latest and latest != report_date:
            report_date = latest
            briefing = fetch_briefing(connection, report_date)
            counts = fetch_counts(connection, report_date)

    top_news = unique_top_news(fetch_top_news(connection, report_date))
    key_points = parse_json_list(briefing["key_points"] if briefing else None)
    top_regions = parse_json_list(briefing["top_regions"] if briefing else None)[:5]
    top_assets = parse_json_list(briefing["top_assets"] if briefing else None)[:5]

    title = briefing["title"] if briefing else f"{report_date} 에미나이 일일 보고"
    summary = briefing["summary_ko"] if briefing else build_day_takeaway(briefing, top_news, counts)
    takeaway = build_day_takeaway(briefing, top_news, counts)
    checkpoints = build_checkpoints(top_news, top_assets)
    event_lines = build_event_lines(top_news)

    lines = [
        f"📌 <b>에미나이 일일 보고</b> | {html.escape(report_date)}",
        f"🧭 {html.escape(sentence_excerpt(title, 80, 1))}",
        f"📊 수집 {counts['total']}건 · 분석 {counts['analyzed']}건 · 대기 {counts['queued']}건",
        "",
        "🗞️ <b>오늘 한눈에</b>",
        html.escape(sentence_excerpt(takeaway, 180, 2)),
        "",
        "📍 <b>오늘 있었던 일</b>",
    ]

    if event_lines:
        lines.extend(event_lines)
    elif key_points:
        lines.extend(bullet_lines(key_points, 4, 105))
    else:
        lines.append(f"• {html.escape(sentence_excerpt(summary, 220, 2))}")

    if key_points:
        lines.extend(["", "🧩 <b>하루 요약</b>"])
        lines.extend(bullet_lines(key_points, 3, 105))

    flow_lines = build_flow_lines(top_news)
    if flow_lines:
        lines.extend(["", "🔗 <b>흐름으로 보기</b>"])
        lines.extend(flow_lines)

    lines.extend(["", "✅ <b>시장 관찰 포인트</b>"])
    lines.extend(bullet_lines(checkpoints, 4, 90))

    if top_assets or top_regions:
        lines.extend(["", "🎯 <b>관찰 축</b>"])
        if top_assets:
            lines.append("자산: " + html.escape(", ".join(top_assets)))
        if top_regions:
            lines.append("지역: " + html.escape(", ".join(top_regions)))

    if counts["queued"]:
        lines.extend(
            [
                "",
                f"⏳ AI 분석 대기 {counts['queued']}건이 있어 후속 보고에서 판단이 보강될 수 있습니다.",
            ]
        )

    message = "\n".join(lines)
    if len(message) > MAX_TELEGRAM_LENGTH:
        message = message[: MAX_TELEGRAM_LENGTH - 38].rstrip()
        message = message.rsplit("\n", 1)[0].rstrip()
        message += "\n\n내용이 길어 일부 항목은 사이트에서 이어서 확인하세요."
    return report_date, message


def send_daily_report(report_date: str, force: bool = False, dry_run: bool = False) -> dict:
    init_db()
    settings = load_settings()
    if not dry_run and (not settings.telegram_bot_token or not settings.telegram_alert_chat_id):
        update_status(SERVICE_NAME, "disabled", "TELEGRAM_BOT_TOKEN or TELEGRAM_ALERT_CHAT_ID missing")
        return {"event": "daily_report_disabled"}

    with connect() as connection:
        if not dry_run and already_sent(connection, report_date) and not force:
            update_status(SERVICE_NAME, "duplicate", f"{report_date} already sent")
            return {"event": "daily_report_duplicate", "date": report_date}

        actual_date, message = build_report_message(connection, report_date)
        if dry_run:
            print(message)
            return {"event": "daily_report_dry_run", "date": actual_date}

        try:
            if report_cards_enabled():
                try:
                    from daily_report_cards import render_daily_report_cards

                    card_paths = render_daily_report_cards(connection, actual_date)
                    send_telegram_media_group(
                        settings,
                        card_paths,
                        caption=f"<b>에미나이 카드뉴스</b> | {html.escape(actual_date)}",
                    )
                except Exception as card_error:
                    update_status(
                        SERVICE_NAME,
                        "card_failed",
                        str(card_error)[:200],
                        error_delta=1,
                    )
            send_telegram_message(settings, message)
            record_delivery(connection, actual_date, "sent")
            connection.commit()
            update_status(SERVICE_NAME, "sent", actual_date, processed_delta=1)
            return {"event": "daily_report_sent", "date": actual_date}
        except Exception as error:
            error_text = str(error)[:200]
            record_delivery(connection, actual_date, "failed", error_text)
            connection.commit()
            update_status(SERVICE_NAME, "failed", error_text, error_delta=1)
            return {"event": "daily_report_failed", "date": actual_date, "error": error_text}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Send an Eminai daily report to Telegram.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--date-mode", default="today", choices=["today", "yesterday"])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target_date = args.date or report_date_from_mode(args.date_mode)
    print(send_daily_report(target_date, force=args.force, dry_run=args.dry_run), flush=True)
