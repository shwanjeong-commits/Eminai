import bootstrap  # noqa: F401

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import re

from database import connect, init_db


BACKLOG_STATUSES = ("queued", "review")

CATEGORY_LABELS = {
    "macro": "거시경제",
    "geopolitics": "해외 정세",
    "markets": "시장",
    "energy": "에너지",
}

REGION_KEYWORDS = {
    "미국": ["미국", "트럼프", "Fed", "FOMC", "달러", "S&P", "나스닥", "고용", "금리"],
    "중동": ["이란", "이스라엘", "호르무즈", "쿠웨이트", "요르단", "중동", "미군", "미사일"],
    "러시아·우크라이나": ["러시아", "우크라이나", "키이우", "젤렌스키", "푸틴", "NATO"],
    "중국·대만": ["중국", "대만", "BYD", "CXMT", "TSMC", "관세", "공급망"],
    "유럽": ["유럽", "EU", "독일", "프랑스", "스페인", "ECB", "폴란드"],
    "한국": ["한국", "원화", "코스피", "삼성전자", "SK하이닉스", "한은", "반도체"],
}

ASSET_KEYWORDS = {
    "원유·에너지": ["유가", "원유", "호르무즈", "LNG", "에너지", "공급"],
    "방산·지정학": ["미사일", "공습", "군사", "전쟁", "방산", "NATO", "미군"],
    "달러·금리": ["달러", "금리", "Fed", "FOMC", "국채", "인플레이션", "고용"],
    "AI·반도체": ["AI", "반도체", "엔비디아", "TSMC", "HBM", "마이크론", "AMD", "SK하이닉스"],
    "중국 공급망": ["중국", "BYD", "CXMT", "관세", "공급망", "대만"],
}

RISK_WORDS = [
    "공습",
    "미사일",
    "공격",
    "전쟁",
    "보복",
    "긴장",
    "제재",
    "급등",
    "급락",
    "위협",
    "사망",
]


def compact(text: str, limit: int = 170) -> str:
    value = " ".join((text or "").split())
    return value[:limit] + ("..." if len(value) > limit else "")


def text_for(row) -> str:
    return " ".join(
        [
            row["title"] or "",
            row["summary_ko"] or "",
            row["analysis_ko"] or "",
            row["raw_text"] or "",
        ]
    )


def first_sentence(text: str) -> str:
    cleaned = " ".join((text or "").split())
    parts = re.split(r"(?<=[.!?。])\s+|\n+", cleaned)
    return compact(parts[0] if parts else cleaned, 120)


def count_matches(rows, groups: dict[str, list[str]]) -> Counter:
    counts = Counter()
    for row in rows:
        lowered = text_for(row).lower()
        for group, keywords in groups.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                counts[group] += 1
    return counts


def risk_score(row) -> float:
    text = text_for(row)
    score = float(row["analysis_priority"] or 0)
    score += min(len(text) / 1000, 2.5)
    score += sum(1 for word in RISK_WORDS if word in text) * 0.8
    if row["content_type"] == "long_news":
        score += 1.0
    if row["analysis_status"] == "review":
        score += 0.5
    return score


def representative_rows(rows, limit: int = 12):
    return sorted(rows, key=risk_score, reverse=True)[:limit]


def build_context(rows, existing_state: str) -> str:
    category_counts = Counter(row["category"] or "unknown" for row in rows)
    type_counts = Counter(row["content_type"] or "unknown" for row in rows)
    date_counts = Counter(row["news_date"] for row in rows)
    region_counts = count_matches(rows, REGION_KEYWORDS)
    asset_counts = count_matches(rows, ASSET_KEYWORDS)

    by_category = defaultdict(list)
    for row in rows:
        by_category[row["category"] or "unknown"].append(row)

    lines = [
        "# 현재 상황판단",
        "",
        "## AI 분석 완료 기반 판단",
        compact(existing_state, 1600),
        "",
        "## 백로그 압축 반영",
        f"- 압축 반영 시각: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 개별 AI 분석 대신 흐름 메모리로 흡수한 뉴스: {len(rows)}건",
        "- 이 묶음은 Gemini 무료 한도를 더 쓰지 않도록 개별 분석 큐에서 제외했습니다.",
        "",
        "## 백로그 분포",
        "- 날짜: "
        + ", ".join(f"{date} {count}건" for date, count in sorted(date_counts.items(), reverse=True)[:8]),
        "- 분야: "
        + ", ".join(
            f"{CATEGORY_LABELS.get(category, category)} {count}건"
            for category, count in category_counts.most_common()
        ),
        "- 메시지 유형: " + ", ".join(f"{kind} {count}건" for kind, count in type_counts.most_common()),
        "",
        "## 누적 흐름 판단",
    ]

    if region_counts:
        lines.append(
            "- 지역 압력은 "
            + ", ".join(f"{name} {count}건" for name, count in region_counts.most_common(6))
            + " 순으로 강합니다."
        )
    if asset_counts:
        lines.append(
            "- 자산/섹터 압력은 "
            + ", ".join(f"{name} {count}건" for name, count in asset_counts.most_common(6))
            + " 순으로 나타납니다."
        )

    if region_counts.get("중동", 0):
        lines.append(
            "- 중동/이란 축은 호르무즈, 미군기지, 미사일·공습 키워드가 반복되어 에너지와 방산 리스크의 중심축으로 유지됩니다."
        )
    if asset_counts.get("AI·반도체", 0):
        lines.append(
            "- AI·반도체 흐름은 엔비디아, TSMC, HBM, SK하이닉스 관련 뉴스가 많아 지정학 리스크와 별도로 구조적 성장 테마로 유지됩니다."
        )
    if asset_counts.get("달러·금리", 0):
        lines.append(
            "- 달러·금리 흐름은 고용, 물가, 중앙은행 발언과 연결되어 위험자산 밸류에이션의 핵심 변수로 남아 있습니다."
        )
    if region_counts.get("러시아·우크라이나", 0):
        lines.append(
            "- 러시아·우크라이나 흐름은 군사 충돌과 유럽 안보 부담을 통해 방산·에너지 리스크를 보조적으로 강화합니다."
        )

    lines.extend(["", "## 분야별 대표 뉴스"])
    for category, group_rows in sorted(by_category.items(), key=lambda item: len(item[1]), reverse=True):
        label = CATEGORY_LABELS.get(category, category)
        lines.append(f"### {label}")
        for row in representative_rows(group_rows, limit=5):
            title = row["title"] or first_sentence(row["raw_text"])
            lines.append(
                f"- [{row['news_date']}] {compact(title, 110)}: "
                f"{compact(row['summary_ko'] or row['raw_text'], 150)}"
            )

    lines.extend(["", "## 다음 분석 우선순위"])
    lines.append("- 새로 들어오는 뉴스는 기존처럼 개별 AI 분석 대상으로 유지합니다.")
    lines.append("- 백로그와 같은 주제의 새 뉴스가 들어오면 기존 흐름의 강화/약화/반전 여부를 우선 판단합니다.")
    lines.append("- 우선 감시 축: 중동 군사 긴장, 호르무즈·유가, 달러·금리, AI·반도체, 중국 공급망, 러시아·우크라이나.")

    return "\n".join(line for line in lines if line is not None)


def absorb_backlog(dry_run: bool = False) -> dict:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            select id, news_date, published_at, raw_text, title, summary_ko, analysis_ko,
                   analysis_priority, content_type, analysis_status, category
            from news_items
            where analysis_scope = 'analysis_target'
              and analysis_status in ('queued', 'review')
            order by published_at asc
            """
        ).fetchall()
        existing = connection.execute(
            "select state_text from ai_situation_state where id = 1"
        ).fetchone()
        existing_state = existing["state_text"] if existing else ""
        state_text = build_context(rows, existing_state)
        first_date = rows[0]["news_date"] if rows else ""
        last_date = rows[-1]["news_date"] if rows else ""

        payload = {
            "absorbed_count": len(rows),
            "first_date": first_date,
            "last_date": last_date,
            "state_chars": len(state_text),
        }

        if dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            print(state_text[:5000])
            return payload

        last_news_id = rows[-1]["id"] if rows else None
        connection.execute(
            """
            insert into ai_situation_state (id, state_text, source_count, last_news_item_id)
            values (1, ?, ?, ?)
            on conflict(id) do update set
              state_text = excluded.state_text,
              source_count = coalesce(ai_situation_state.source_count, 0) + ?,
              last_news_item_id = excluded.last_news_item_id,
              updated_at = current_timestamp
            """,
            (state_text, len(rows), last_news_id, len(rows)),
        )
        connection.execute(
            """
            insert into ai_context_batches (period_start, period_end, item_count, context_text, status)
            values (?, ?, ?, ?, 'absorbed')
            on conflict(period_start, period_end) do update set
              item_count = excluded.item_count,
              context_text = excluded.context_text,
              status = excluded.status,
              updated_at = current_timestamp
            """,
            (first_date or "unknown", last_date or "unknown", len(rows), state_text),
        )
        connection.execute(
            """
            update news_items
            set analysis_status = 'context_absorbed',
                analysis_reason = 'backlog absorbed into situation memory without individual AI analysis',
                updated_at = current_timestamp
            where analysis_scope = 'analysis_target'
              and analysis_status in ('queued', 'review')
            """
        )
        connection.commit()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Absorb queued backlog into situation memory without AI API calls.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    absorb_backlog(dry_run=args.dry_run)
