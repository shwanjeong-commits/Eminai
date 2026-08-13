from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

import bootstrap  # noqa: F401

from daily_report import (
    build_checkpoints,
    build_day_takeaway,
    fetch_briefing,
    fetch_counts,
    fetch_top_news,
    parse_json_list,
    split_sentences,
    unique_top_news,
)


CARD_SIZE = (1080, 1350)
MARGIN = 76
GREEN = (16, 94, 72)
GREEN_DARK = (8, 62, 49)
GREEN_SOFT = (224, 239, 232)
GREEN_PALE = (241, 248, 244)
INK = (23, 33, 39)
MUTED = (91, 111, 119)
LINE = (203, 218, 216)
PAPER = (248, 251, 248)
WHITE = (255, 255, 255)
YELLOW = (242, 190, 88)
RED = (154, 72, 44)
MAX_CARDS = 8


@dataclass
class CardContext:
    report_date: str
    counts: dict[str, int]
    briefing: sqlite3.Row | None
    top_news: list[sqlite3.Row]
    key_points: list[str]
    top_regions: list[str]
    top_assets: list[str]
    takeaway: str
    checkpoints: list[str]


def _load_pillow():
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


def _font_path(kind: str = "regular") -> str | None:
    candidates = (
        [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
        if kind == "bold"
        else [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _font(size: int, bold: bool = False):
    _, _, ImageFont = _load_pillow()
    path = _font_path("bold" if bold else "regular")
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _new_card():
    Image, ImageDraw, _ = _load_pillow()
    image = Image.new("RGB", CARD_SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((34, 34, CARD_SIZE[0] - 34, CARD_SIZE[1] - 34), radius=34, fill=WHITE)
    draw.rectangle((34, 34, CARD_SIZE[0] - 34, 52), fill=GREEN)
    return image, draw


def _rounded(draw, box, radius=26, fill=WHITE, outline=LINE, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _text_width(draw, text: str, font) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _line_height(font) -> int:
    box = font.getbbox("가나다ABC123")
    return max(1, box[3] - box[1])


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    paragraphs = [part.strip() for part in (text or "").split("\n")]
    lines: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for token in paragraph.split(" "):
            candidate = token if not current else f"{current} {token}"
            if _text_width(draw, candidate, font) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = token
            while _text_width(draw, current, font) > max_width and len(current) > 1:
                chunk = ""
                for char in current:
                    if chunk and _text_width(draw, chunk + char, font) > max_width:
                        break
                    chunk += char
                lines.append(chunk)
                current = current[len(chunk) :]
        if current:
            lines.append(current)
    return lines


def _fit_font(draw, text: str, max_width: int, max_height: int, start_size: int, min_size: int, bold: bool = False):
    for size in range(start_size, min_size - 1, -2):
        font = _font(size, bold)
        line_gap = max(6, int(size * 0.28))
        lines = _wrap_text(draw, text, font, max_width)
        height = len(lines) * _line_height(font) + max(0, len(lines) - 1) * line_gap
        if height <= max_height:
            return font, line_gap, lines
    font = _font(min_size, bold)
    line_gap = max(5, int(min_size * 0.25))
    return font, line_gap, _wrap_text(draw, text, font, max_width)


def _draw_fitted_text(
    draw,
    xy,
    text: str,
    max_width: int,
    max_height: int,
    start_size: int,
    min_size: int = 22,
    fill=INK,
    bold: bool = False,
) -> int:
    x, y = xy
    font, line_gap, lines = _fit_font(draw, text, max_width, max_height, start_size, min_size, bold)
    bottom = y + max_height
    for line in lines:
        next_y = y + _line_height(font)
        if next_y > bottom:
            break
        draw.text((x, y), line, font=font, fill=fill)
        y = next_y + line_gap
    return y


def _draw_label(draw, xy, text: str, fill=GREEN_DARK) -> None:
    draw.text(xy, text, font=_font(25, True), fill=fill)


def _header(draw, page: int, total: int, title: str, subtitle: str = "") -> None:
    draw.text((MARGIN, 58), "EMINAI WATCH", font=_font(25, True), fill=GREEN)
    draw.text((CARD_SIZE[0] - MARGIN - 88, 58), f"{page}/{total}", font=_font(24, True), fill=MUTED)
    _draw_fitted_text(draw, (MARGIN, 108), title, 900, 72, 50, 40, INK, True)
    if subtitle:
        _draw_fitted_text(draw, (MARGIN, 184), subtitle, 900, 68, 27, 23, MUTED)


def _clean(text: str | None) -> str:
    return " ".join((text or "").replace("...", "").split())


def _sentence_text(text: str | None, max_sentences: int = 2, max_chars: int = 360) -> str:
    value = _clean(text)
    if not value:
        return ""
    sentences = split_sentences(value)
    if not sentences:
        sentences = re.split(r"(?<=다)\s+", value)
    selected: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = " ".join([*selected, sentence]).strip()
        if selected and len(candidate) > max_chars:
            break
        selected.append(sentence)
        if len(selected) >= max_sentences:
            break
    return " ".join(selected).strip() or value


def _title(row: sqlite3.Row | None, fallback: str = "주요 뉴스") -> str:
    if not row:
        return fallback
    return _sentence_text(row["title"] or row["summary_ko"] or fallback, 1, 90)


def _summary(row: sqlite3.Row | None, max_sentences: int = 3, max_chars: int = 520) -> str:
    if not row:
        return "분석된 주요 뉴스가 아직 충분하지 않습니다."
    return _sentence_text(row["summary_ko"] or row["analysis_ko"] or "", max_sentences, max_chars)


def _analysis(row: sqlite3.Row | None, max_sentences: int = 3, max_chars: int = 560) -> str:
    if not row:
        return "추가 분석이 쌓이면 원인과 영향이 더 선명해집니다."
    return _sentence_text(row["analysis_ko"] or row["summary_ko"] or "", max_sentences, max_chars)


def build_card_context(connection: sqlite3.Connection, report_date: str) -> CardContext:
    briefing = fetch_briefing(connection, report_date)
    counts = fetch_counts(connection, report_date)
    top_news = unique_top_news(fetch_top_news(connection, report_date, limit=20), limit=8)
    key_points = parse_json_list(briefing["key_points"] if briefing else None)
    top_regions = parse_json_list(briefing["top_regions"] if briefing else None)[:5]
    top_assets = parse_json_list(briefing["top_assets"] if briefing else None)[:5]
    takeaway = build_day_takeaway(briefing, top_news, counts)
    checkpoints = build_checkpoints(top_news, top_assets)
    return CardContext(report_date, counts, briefing, top_news, key_points, top_regions, top_assets, takeaway, checkpoints)


def render_cover(ctx: CardContext, page: int, total: int):
    image, draw = _new_card()
    _header(draw, page, total, "오늘 무슨 일이 있었나", ctx.report_date)
    draw.text((MARGIN, 258), "Daily Intelligence Brief", font=_font(31, True), fill=GREEN)
    _draw_fitted_text(draw, (MARGIN, 322), _sentence_text(ctx.takeaway, 2, 260), 900, 185, 35, 28, INK, True)

    y = 560
    stats = [("수집", ctx.counts["total"]), ("분석", ctx.counts["analyzed"]), ("대기", ctx.counts["queued"])]
    x = MARGIN
    for label, value in stats:
        _rounded(draw, (x, y, x + 276, y + 135), 22, GREEN_SOFT, None, 0)
        draw.text((x + 28, y + 27), label, font=_font(27, True), fill=GREEN_DARK)
        draw.text((x + 28, y + 66), str(value), font=_font(48, True), fill=INK)
        x += 308

    y = 770
    draw.text((MARGIN, y), "관찰 축", font=_font(32, True), fill=INK)
    assets = ", ".join(ctx.top_assets) if ctx.top_assets else "주요 자산 데이터 부족"
    regions = ", ".join(ctx.top_regions) if ctx.top_regions else "주요 지역 데이터 부족"
    _draw_fitted_text(draw, (MARGIN, y + 58), f"자산: {assets}\n지역: {regions}", 900, 155, 29, 24, MUTED)
    draw.text((MARGIN, 1225), "목적: 하루 사건의 흐름과 시장 의미를 빠르게 파악", font=_font(25), fill=MUTED)
    return image


def render_event_card(ctx: CardContext, row: sqlite3.Row | None, page: int, total: int, label: str):
    image, draw = _new_card()
    _header(draw, page, total, label, _title(row))

    y = 270
    _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + 310), 24, GREEN_SOFT, None, 0)
    _draw_label(draw, (MARGIN + 34, y + 28), "무슨 일이 있었나")
    _draw_fitted_text(draw, (MARGIN + 34, y + 82), _summary(row, 4, 620), 840, 190, 30, 23, INK)

    y = 635
    _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + 360), 24, WHITE, LINE, 2)
    _draw_label(draw, (MARGIN + 34, y + 28), "배경과 의미")
    _draw_fitted_text(draw, (MARGIN + 34, y + 82), _analysis(row, 4, 700), 840, 235, 29, 22, MUTED)

    if row:
        y = 1062
        impact = float(row["impact_score"] or 0)
        risk = row["risk_level"] or "-"
        category = row["category"] or "-"
        _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + 122), 22, GREEN_PALE, LINE, 1)
        draw.text((MARGIN + 30, y + 34), f"영향도 {impact:.1f}", font=_font(29, True), fill=GREEN_DARK)
        draw.text((MARGIN + 300, y + 34), f"위험 {risk}", font=_font(29, True), fill=RED)
        _draw_fitted_text(draw, (MARGIN + 550, y + 34), f"분류 {category}", 360, 48, 26, 22, MUTED)
    return image


def render_market_card(ctx: CardContext, page: int, total: int):
    image, draw = _new_card()
    _header(draw, page, total, "시장 반응", "가격과 자산군이 어디에 먼저 반응했는지 정리")
    y = 278
    rows = ctx.top_news[2:5]
    for index, row in enumerate(rows, start=1):
        height = 278
        _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + height), 24, WHITE, LINE, 2)
        draw.text((MARGIN + 28, y + 28), f"#{index}", font=_font(28, True), fill=GREEN)
        title_bottom = _draw_fitted_text(draw, (MARGIN + 86, y + 23), _title(row), 800, 74, 29, 24, INK, True)
        _draw_fitted_text(draw, (MARGIN + 86, title_bottom + 8), _summary(row, 2, 330), 800, 130, 25, 21, MUTED)
        y += height + 32
    if not rows:
        _draw_fitted_text(draw, (MARGIN, y), "시장 반응을 정리할 분석 뉴스가 아직 부족합니다.", 900, 220, 32, 24, MUTED)
    return image


def render_flow_card(ctx: CardContext, page: int, total: int):
    image, draw = _new_card()
    _header(draw, page, total, "원인에서 결과까지", "사건이 시장 판단으로 이어지는 경로")
    y = 278
    for row in ctx.top_news[:4]:
        _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + 205), 24, GREEN_SOFT, None, 0)
        draw.text((MARGIN + 28, y + 28), "원인", font=_font(25, True), fill=GREEN_DARK)
        _draw_fitted_text(draw, (MARGIN + 116, y + 24), _title(row), 760, 58, 27, 23, INK, True)
        draw.text((MARGIN + 28, y + 108), "결과", font=_font(25, True), fill=GREEN_DARK)
        _draw_fitted_text(draw, (MARGIN + 116, y + 104), _analysis(row, 2, 260), 760, 72, 24, 20, MUTED)
        y += 228
    return image


def render_timeline_card(ctx: CardContext, page: int, total: int):
    image, draw = _new_card()
    _header(draw, page, total, "하루 흐름", "오늘 뉴스가 쌓인 순서대로 보는 큰 줄기")
    y = 285
    for index, row in enumerate(ctx.top_news[:5], start=1):
        draw.ellipse((MARGIN, y + 12, MARGIN + 28, y + 40), fill=GREEN)
        draw.line((MARGIN + 14, y + 45, MARGIN + 14, y + 150), fill=LINE, width=4)
        draw.text((MARGIN + 50, y), f"{index}", font=_font(25, True), fill=GREEN_DARK)
        bottom = _draw_fitted_text(draw, (MARGIN + 95, y - 3), _title(row), 810, 60, 27, 22, INK, True)
        _draw_fitted_text(draw, (MARGIN + 95, bottom + 5), _summary(row, 1, 170), 810, 64, 23, 19, MUTED)
        y += 170
    return image


def render_watch_card(ctx: CardContext, page: int, total: int):
    image, draw = _new_card()
    _header(draw, page, total, "다음에 볼 것", "후속 확인 신호와 대기 분석")
    y = 278
    for checkpoint in ctx.checkpoints[:5]:
        _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + 122), 22, WHITE, LINE, 2)
        draw.ellipse((MARGIN + 30, y + 43, MARGIN + 58, y + 71), fill=YELLOW)
        _draw_fitted_text(draw, (MARGIN + 84, y + 24), _sentence_text(checkpoint, 1, 140), 805, 74, 27, 22, INK, True)
        y += 142

    y += 22
    _rounded(draw, (MARGIN, y, CARD_SIZE[0] - MARGIN, y + 180), 24, GREEN_SOFT, None, 0)
    queued = ctx.counts["queued"]
    note = (
        f"AI 분석 대기 {queued}건이 남아 있습니다. 후속 분석이 완료되면 다음 보고에서 판단이 보강됩니다."
        if queued
        else "현재 대기 분석은 없습니다. 다음 새 뉴스가 들어오면 자동으로 반영됩니다."
    )
    draw.text((MARGIN + 34, y + 28), "자동화 상태", font=_font(30, True), fill=GREEN_DARK)
    _draw_fitted_text(draw, (MARGIN + 34, y + 84), note, 830, 72, 27, 22, INK)
    draw.text((MARGIN, 1230), "Eminai Watch | Telegram automated intelligence", font=_font(25), fill=MUTED)
    return image


def render_daily_report_cards(
    connection: sqlite3.Connection,
    report_date: str,
    output_dir: Path | str = "/tmp/eminai-cards",
) -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    ctx = build_card_context(connection, report_date)

    event_rows = ctx.top_news[:2]
    cards_plan = [
        ("cover", None),
        ("event", event_rows[0] if len(event_rows) > 0 else None),
        ("event", event_rows[1] if len(event_rows) > 1 else None),
        ("market", None),
        ("timeline", None),
        ("flow", None),
        ("watch", None),
    ]
    cards_plan = cards_plan[:MAX_CARDS]
    total = len(cards_plan)

    cards = []
    for page, (kind, row) in enumerate(cards_plan, start=1):
        if kind == "cover":
            cards.append(render_cover(ctx, page, total))
        elif kind == "event":
            label = "핵심 사건" if page == 2 else "두 번째 이슈"
            cards.append(render_event_card(ctx, row, page, total, label))
        elif kind == "market":
            cards.append(render_market_card(ctx, page, total))
        elif kind == "timeline":
            cards.append(render_timeline_card(ctx, page, total))
        elif kind == "flow":
            cards.append(render_flow_card(ctx, page, total))
        elif kind == "watch":
            cards.append(render_watch_card(ctx, page, total))

    paths: list[Path] = []
    for index, image in enumerate(cards, start=1):
        path = output_path / f"eminai_daily_report_{report_date}_{index:02d}.png"
        image.save(path, format="PNG", optimize=True)
        paths.append(path)
    return paths
