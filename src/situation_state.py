import bootstrap  # noqa: F401

from collections import Counter
import argparse

from database import connect


CATEGORY_LABELS = {
    "macro": "거시경제",
    "geopolitics": "해외 정세",
    "markets": "시장",
    "energy": "에너지",
}

RISK_WEIGHT = {"높음": 3, "중간": 2, "낮음": 1}

VARIABLE_RULES = {
    "호르무즈·원유": ["호르무즈", "원유", "유가", "해협", "해상", "봉쇄"],
    "미국·이란 긴장": ["미국", "이란", "공습", "미사일", "중부사령부", "협상"],
    "중국 무역·기술": ["중국", "관세", "수출통제", "반도체", "전기차", "제재"],
    "미국 금리·달러": ["연준", "Fed", "FOMC", "금리", "달러", "국채", "CPI"],
    "AI·반도체": ["AI", "엔비디아", "반도체", "마이크론", "데이터센터", "하이닉스"],
}


def compact(text: str, limit: int = 220) -> str:
    value = " ".join((text or "").split())
    return value[:limit] + ("..." if len(value) > limit else "")


def row_text(row) -> str:
    return " ".join(
        str(row[key] or "")
        for key in ("title", "summary_ko", "analysis_ko", "raw_text")
        if key in row.keys()
    )


def risk_weight(row) -> int:
    return RISK_WEIGHT.get(row["risk_level"] or "중간", 2)


def dimension_scores(row) -> dict:
    text = row_text(row)
    impact = float(row["impact_score"] or 0)
    category = row["category"] or "markets"
    risk = risk_weight(row)
    length_boost = min(len(text) / 1800, 1.2)

    market_hits = sum(word in text for word in ["증시", "주가", "나스닥", "S&P", "유가", "달러", "금리", "반도체", "실적"])
    geo_hits = sum(word in text for word in ["전쟁", "공격", "공습", "제재", "군사", "이란", "이스라엘", "러시아", "호르무즈"])
    persistence_hits = sum(word in text for word in ["계속", "지속", "연속", "반복", "확대", "장기", "재개", "누적"])
    spread_hits = sum(word in text for word in ["확산", "동맹", "유럽", "중국", "글로벌", "공급망", "수출", "수입", "선박"])

    market = impact * 0.58 + market_hits * 0.55 + (1.0 if category in {"markets", "macro", "energy"} else 0)
    geopolitics = impact * 0.52 + geo_hits * 0.65 + risk * 0.55 + (1.0 if category == "geopolitics" else 0)
    persistence = impact * 0.42 + persistence_hits * 0.75 + length_boost + (0.7 if risk >= 3 else 0)
    spread = impact * 0.44 + spread_hits * 0.7 + geo_hits * 0.28 + (0.5 if category in {"energy", "geopolitics"} else 0)

    return {
        "market": round(min(market, 10), 1),
        "geopolitics": round(min(geopolitics, 10), 1),
        "persistence": round(min(persistence, 10), 1),
        "spread": round(min(spread, 10), 1),
    }


def average(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def average_dimensions(rows) -> dict:
    scores = [dimension_scores(row) for row in rows]
    return {
        "market": {"label": "시장 영향도", "score": average([item["market"] for item in scores])},
        "geopolitics": {"label": "지정학 위험도", "score": average([item["geopolitics"] for item in scores])},
        "persistence": {"label": "지속성", "score": average([item["persistence"] for item in scores])},
        "spread": {"label": "확산 가능성", "score": average([item["spread"] for item in scores])},
    }


def key_variables(rows, limit: int = 5) -> list[dict]:
    scored = []
    for name, keywords in VARIABLE_RULES.items():
        matches = []
        score = 0.0
        for row in rows:
            text = row_text(row)
            hits = [word for word in keywords if word in text]
            if not hits:
                continue
            matches.append(row)
            score += len(hits) * 0.7 + float(row["impact_score"] or 0) * 0.35 + risk_weight(row) * 0.35
        if matches:
            strongest = max(matches, key=lambda row: row["impact_score"] or 0)
            scored.append(
                {
                    "name": name,
                    "score": round(min(score, 10), 1),
                    "reason": compact(strongest["title"] or strongest["summary_ko"] or strongest["raw_text"], 90),
                }
            )
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def build_situation_payload(rows) -> dict:
    if not rows:
        return {
            "level": "분석 대기",
            "tone": "risk-watch",
            "summary": "아직 AI가 분석한 뉴스가 없습니다. 새 뉴스가 분석되면 현재 상황판단이 갱신됩니다.",
            "reasons": ["분석 완료 뉴스가 쌓이면 자동으로 판단을 시작합니다."],
            "changes": ["전일 대비 비교 데이터가 아직 없습니다."],
            "keyVariables": [],
            "dimensionScores": average_dimensions([]),
            "topWatch": [],
        }

    latest_date = max(row["news_date"] for row in rows if row["news_date"])
    date_rows = [row for row in rows if row["news_date"] == latest_date]
    previous_dates = sorted({row["news_date"] for row in rows if row["news_date"] and row["news_date"] < latest_date}, reverse=True)
    previous_rows = [row for row in rows if previous_dates and row["news_date"] == previous_dates[0]]
    recent_rows = sorted(rows, key=lambda row: row["published_at"], reverse=True)[:80]
    high_rows = [row for row in recent_rows if (row["impact_score"] or 0) >= 8 or row["risk_level"] == "높음"]
    avg_impact = average([float(row["impact_score"] or 0) for row in recent_rows])
    dimensions = average_dimensions(recent_rows)
    variables = key_variables(recent_rows)

    if len(high_rows) >= 8 or dimensions["geopolitics"]["score"] >= 7.4:
        level, tone = "위험 상승", "risk-high"
    elif len(high_rows) >= 3 or avg_impact >= 6.4 or dimensions["spread"]["score"] >= 6.5:
        level, tone = "주의", "risk-watch"
    else:
        level, tone = "안정 관찰", "risk-low"

    category_counts = Counter(row["category"] or "markets" for row in recent_rows)
    risk_counts = Counter(row["risk_level"] or "중간" for row in recent_rows)
    top_category = CATEGORY_LABELS.get(category_counts.most_common(1)[0][0], category_counts.most_common(1)[0][0])
    top_variable = variables[0]["name"] if variables else "주요 변수 없음"
    summary = (
        f"{latest_date} 기준 최근 분석 뉴스 {len(recent_rows)}건에서 '{top_variable}' 변수가 가장 강하게 잡힙니다. "
        f"고영향 뉴스는 {len(high_rows)}건, 평균 영향도는 {avg_impact:.1f}이며 주요 분야는 {top_category}입니다."
    )

    reasons = [
        f"고영향/고위험 뉴스 {len(high_rows)}건이 최근 판단에 반영됐습니다.",
        f"리스크 분포는 " + ", ".join(f"{risk} {count}건" for risk, count in risk_counts.most_common(3)) + "입니다.",
        f"세분화 점수는 시장 {dimensions['market']['score']:.1f}, 지정학 {dimensions['geopolitics']['score']:.1f}, 지속성 {dimensions['persistence']['score']:.1f}, 확산 {dimensions['spread']['score']:.1f}입니다.",
    ]

    changes = []
    if previous_rows:
        today_avg = average([float(row["impact_score"] or 0) for row in date_rows])
        prev_avg = average([float(row["impact_score"] or 0) for row in previous_rows])
        today_high = sum(1 for row in date_rows if (row["impact_score"] or 0) >= 8 or row["risk_level"] == "높음")
        prev_high = sum(1 for row in previous_rows if (row["impact_score"] or 0) >= 8 or row["risk_level"] == "높음")
        delta = today_avg - prev_avg
        direction = "상승" if delta > 0.2 else "하락" if delta < -0.2 else "유지"
        changes.append(f"전일 대비 평균 영향도는 {abs(delta):.1f}p {direction}했습니다.")
        changes.append(f"고영향 뉴스는 전일 {prev_high}건에서 오늘 {today_high}건으로 변했습니다.")
    else:
        changes.append("전일 대비 비교 데이터가 아직 충분하지 않습니다.")

    top_watch = []
    for row in sorted(recent_rows, key=lambda row: row["impact_score"] or 0, reverse=True)[:5]:
        top_watch.append(
            {
                "id": row["id"],
                "title": row["title"] or compact(row["raw_text"], 80),
                "impact": row["impact_score"] or 0,
                "risk": row["risk_level"] or "중간",
                "category": row["category"] or "markets",
            }
        )

    return {
        "level": level,
        "tone": tone,
        "summary": summary,
        "reasons": reasons,
        "changes": changes,
        "keyVariables": variables,
        "dimensionScores": dimensions,
        "topWatch": top_watch,
        "sourceCount": len(rows),
        "latestDate": latest_date,
    }


def build_state_text(rows) -> str:
    if not rows:
        return "아직 AI가 분석한 뉴스가 없습니다. 새 뉴스가 분석되면 현재 상황판단이 갱신됩니다."

    category_counts = Counter(row["category"] or "markets" for row in rows)
    risk_counts = Counter(row["risk_level"] or "중간" for row in rows)
    top_rows = sorted(rows, key=lambda row: row["impact_score"] or 0, reverse=True)[:8]
    recent_rows = sorted(rows, key=lambda row: row["published_at"], reverse=True)[:8]

    category_line = ", ".join(
        f"{CATEGORY_LABELS.get(category, category)} {count}건"
        for category, count in category_counts.most_common()
    )
    risk_line = ", ".join(f"{risk} {count}건" for risk, count in risk_counts.most_common())

    lines = [
        "# 현재 상황판단",
        "",
        f"- 분석 반영 뉴스: {len(rows)}건",
        f"- 주요 분야: {category_line}",
        f"- 리스크 분포: {risk_line}",
        "",
        "## 핵심 판단",
    ]

    for row in top_rows[:5]:
        lines.append(
            f"- [{row['news_date']}] {row['title'] or '제목 없음'} "
            f"(영향도 {row['impact_score'] or 0:.1f}, 리스크 {row['risk_level'] or '중간'}): "
            f"{compact(row['analysis_ko'] or row['summary_ko'] or row['raw_text'], 180)}"
        )

    lines.extend(["", "## 최근 업데이트"])
    for row in recent_rows[:5]:
        lines.append(
            f"- [{row['news_date']}] {compact(row['title'] or row['summary_ko'] or row['raw_text'], 150)}"
        )

    return "\n".join(lines)


def update_situation_state(connection, last_news_item_id: int | None = None) -> str:
    rows = connection.execute(
        """
        select id, news_date, published_at, raw_text, title, summary_ko, analysis_ko,
               impact_score, risk_level, category
        from news_items
        where analysis_status = 'analyzed'
        order by published_at desc
        limit 300
        """
    ).fetchall()
    state_text = build_state_text(rows)
    source_count = len(rows)
    if last_news_item_id is None and rows:
        last_news_item_id = rows[0]["id"]

    connection.execute(
        """
        insert into ai_situation_state (id, state_text, source_count, last_news_item_id)
        values (1, ?, ?, ?)
        on conflict(id) do update set
          state_text = excluded.state_text,
          source_count = excluded.source_count,
          last_news_item_id = excluded.last_news_item_id,
          updated_at = current_timestamp
        """,
        (state_text, source_count, last_news_item_id),
    )
    return state_text


def get_situation_state(connection) -> str:
    row = connection.execute(
        "select state_text from ai_situation_state where id = 1"
    ).fetchone()
    return row["state_text"] if row else "아직 누적 상황판단이 없습니다."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild AI situation state from analyzed news.")
    parser.parse_args()
    with connect() as connection:
        state = update_situation_state(connection)
        print(state)
