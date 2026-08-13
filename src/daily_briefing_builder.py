import bootstrap  # noqa: F401

from collections import Counter
import argparse

from classifier import ANALYSIS_TARGET_START
from database import connect
from repository import replace_daily_briefing


CATEGORY_LABELS = {
    "macro": "거시경제",
    "geopolitics": "해외 정세",
    "markets": "시장",
    "energy": "에너지",
}

RISK_WEIGHT = {"높음": 3, "중간": 2, "낮음": 1}

REGION_KEYWORDS = {
    "미국": ["미국", "트럼프", "연준", "Fed", "달러", "S&P", "나스닥"],
    "중국": ["중국", "위안", "전기차", "부양"],
    "중동": ["이란", "이스라엘", "예멘", "사우디", "호르무즈", "중동"],
    "유럽": ["유럽", "EU", "프랑스", "독일", "영국"],
    "러시아·우크라이나": ["러시아", "우크라이나", "젤렌스키"],
    "한국": ["한국", "원화", "코스피", "SK하이닉스"],
}

ASSET_KEYWORDS = {
    "미국 기술주": ["AI", "엔비디아", "테슬라", "마이크론", "반도체", "소프트웨어"],
    "달러·금리": ["달러", "금리", "연준", "국채", "Fed", "FOMC"],
    "원유·에너지": ["원유", "유가", "가스", "LNG", "에너지"],
    "중국 전기차": ["전기차", "중국", "BYD", "테슬라"],
    "방산·지정학": ["전쟁", "군사", "방산", "공격", "제재"],
}


def compact(text: str, limit: int = 180) -> str:
    value = " ".join((text or "").split())
    return value[:limit] + ("..." if len(value) > limit else "")


def match_groups(rows, groups: dict[str, list[str]]) -> list[str]:
    counts = Counter()
    for row in rows:
        text = " ".join(
            [
                row["title"] or "",
                row["summary_ko"] or "",
                row["analysis_ko"] or "",
                row["raw_text"] or "",
            ]
        ).lower()
        for name, keywords in groups.items():
            if any(keyword.lower() in text for keyword in keywords):
                counts[name] += 1
    return [name for name, _ in counts.most_common(5)]


def category_phrase(rows) -> str:
    counts = Counter(row["category"] or "markets" for row in rows)
    labels = [CATEGORY_LABELS.get(category, category) for category, _ in counts.most_common(3)]
    return "·".join(labels) if labels else "시장"


def max_risk(rows) -> str:
    if not rows:
        return "낮음"
    return max((row["risk_level"] or "낮음" for row in rows), key=lambda risk: RISK_WEIGHT.get(risk, 0))


def build_key_points(rows) -> list[str]:
    top_rows = sorted(rows, key=lambda row: row["impact_score"] or 0, reverse=True)[:5]
    points = []
    for row in top_rows:
        summary = row["summary_ko"] or row["analysis_ko"] or row["raw_text"]
        points.append(compact(summary, 160))
    return points


def build_summary(rows) -> str:
    if not rows:
        return "아직 AI 분석이 완료된 뉴스가 없습니다."

    top = sorted(rows, key=lambda row: row["impact_score"] or 0, reverse=True)[:3]
    lead = compact(top[0]["analysis_ko"] or top[0]["summary_ko"] or top[0]["raw_text"], 190)
    second = compact(top[1]["analysis_ko"] or top[1]["summary_ko"] or top[1]["raw_text"], 170) if len(top) > 1 else ""
    third = compact(top[2]["summary_ko"] or top[2]["analysis_ko"] or top[2]["raw_text"], 150) if len(top) > 2 else ""

    parts = [lead]
    if second:
        parts.append(second)
    if third:
        parts.append(third)
    return " ".join(parts)


def build_daily_briefings(limit_dates: int | None = None) -> None:
    with connect() as connection:
        dates = [
            row["news_date"]
            for row in connection.execute(
                """
                select news_date
                from news_items
                where news_date >= ?
                  and analysis_status = 'analyzed'
                group by news_date
                order by news_date desc
                """,
                (ANALYSIS_TARGET_START,),
            ).fetchall()
        ]
        if limit_dates is not None:
            dates = dates[:limit_dates]

        for news_date in dates:
            rows = connection.execute(
                """
                select id, news_date, raw_text, title, summary_ko, analysis_ko,
                       impact_score, risk_level, category, sentiment
                from news_items
                where news_date = ?
                  and analysis_status = 'analyzed'
                order by impact_score desc, published_at asc
                """,
                (news_date,),
            ).fetchall()
            if not rows:
                continue

            avg_impact = sum(row["impact_score"] or 0 for row in rows) / len(rows)
            title = f"{news_date} AI 브리핑: {category_phrase(rows)} 중심"
            replace_daily_briefing(
                connection,
                briefing_date=news_date,
                title=title,
                summary_ko=build_summary(rows),
                key_points=build_key_points(rows),
                top_regions=match_groups(rows, REGION_KEYWORDS),
                top_assets=match_groups(rows, ASSET_KEYWORDS),
                avg_impact_score=round(avg_impact, 1),
                max_risk_level=max_risk(rows),
            )
            print({"date": news_date, "analyzed_items": len(rows), "title": title}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build daily briefings from analyzed news items.")
    parser.add_argument("--limit-dates", type=int)
    args = parser.parse_args()
    build_daily_briefings(limit_dates=args.limit_dates)
