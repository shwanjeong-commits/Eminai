import bootstrap  # noqa: F401

from dataclasses import dataclass

from database import connect, init_db
from news_event_builder import get_region_events


ANALYSIS_TARGET_START = "2026-07-01"


@dataclass(frozen=True)
class RegionTheme:
    name: str
    core_keywords: tuple[str, ...]
    pressure_keywords: tuple[str, ...]
    relief_keywords: tuple[str, ...] = ()
    min_score: float = 2.5


REGION_THEMES = (
    RegionTheme(
        name="미국",
        core_keywords=("미국", "트럼프", "연준", "Fed", "FOMC", "달러", "국채", "S&P"),
        pressure_keywords=("금리", "재정적자", "부채", "고용", "인플레이션", "전력", "정전", "폭염", "정책"),
        relief_keywords=("금리 인하", "완화", "협상"),
        min_score=3.0,
    ),
    RegionTheme(
        name="중동",
        core_keywords=("중동", "이란", "이스라엘", "호르무즈", "가자", "레바논", "예멘", "후티"),
        pressure_keywords=("공습", "보복", "상선", "군사", "긴장", "위협", "핵", "미군", "유가"),
        relief_keywords=("휴전", "협상", "자제", "완화"),
        min_score=3.0,
    ),
    RegionTheme(
        name="러시아·우크라이나",
        core_keywords=("러시아", "우크라이나", "푸틴", "젤렌스키", "러-우"),
        pressure_keywords=("전쟁", "미사일", "드론", "NATO", "제재", "분쟁", "안보"),
        relief_keywords=("평화", "협상", "통화"),
        min_score=2.8,
    ),
    RegionTheme(
        name="중국·대만",
        core_keywords=("중국", "대만", "BYD", "전기차", "해경", "관세", "USMCA"),
        pressure_keywords=("무역", "공급망", "의존도", "원산지", "세제", "순찰", "경쟁"),
        relief_keywords=("다변화", "협력"),
        min_score=2.8,
    ),
    RegionTheme(
        name="유럽",
        core_keywords=("유럽", "EU", "독일", "프랑스", "ECB", "유럽중앙은행"),
        pressure_keywords=("안보", "러시아", "재정", "정책", "의존도", "분쟁"),
        relief_keywords=("안정", "협력", "다변화"),
        min_score=2.5,
    ),
    RegionTheme(
        name="한국",
        core_keywords=("한국", "코스피", "SK하이닉스", "반도체", "AI 산업", "위성통신"),
        pressure_keywords=("약세장", "하락", "투자 심리", "차익 실현", "글로벌", "수급"),
        relief_keywords=("투자", "자금 유입", "미래 산업"),
        min_score=2.4,
    ),
)


def compact(text: str, length: int = 150) -> str:
    value = " ".join((text or "").split())
    return value[:length] + ("..." if len(value) > length else "")


def row_text(row) -> str:
    return " ".join(
        [
            row["title"] or "",
            row["summary_ko"] or "",
            row["raw_text"] or "",
            row["category"] or "",
        ]
    )


def hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def score_region(row, region: RegionTheme) -> tuple[float, list[str], list[str], list[str]]:
    text = row_text(row)
    core = hits(text, region.core_keywords)
    pressure = hits(text, region.pressure_keywords)
    relief = hits(text, region.relief_keywords)
    score = len(core) * 1.45 + len(pressure) * 0.65 - len(relief) * 0.25
    if not core:
        score -= 2.0
    if row["risk_level"] == "높음":
        score += 0.9
    if row["impact_score"]:
        score += min(row["impact_score"] / 12, 0.8)
    return round(score, 3), core, pressure, relief


def risk_level_for(pressure_score: float) -> str:
    if pressure_score >= 78:
        return "높음"
    if pressure_score >= 55:
        return "중간"
    return "낮음"


def summary_for(region: RegionTheme, matches: list[tuple]) -> str:
    strongest = max(matches, key=lambda item: (item[1], item[0]["impact_score"] or 0))[0]
    dates = sorted({row["news_date"] for row, *_rest in matches})
    high_risk = sum(1 for row, *_rest in matches if row["risk_level"] == "높음")
    return (
        f"{region.name} 관련 리스크 뉴스 {len(matches)}건이 감지됐습니다. "
        f"기간은 {dates[0]}부터 {dates[-1]}까지이며, 고위험 뉴스는 {high_risk}건입니다. "
        f"핵심 신호는 '{compact(strongest['title'] or strongest['summary_ko'] or strongest['raw_text'], 80)}'입니다."
    )


def fetch_rows(connection):
    return connection.execute(
        """
        select *
        from news_items
        where news_date >= ?
          and analysis_status = 'analyzed'
        order by published_at asc
        """,
        (ANALYSIS_TARGET_START,),
    ).fetchall()


def build_region_risks() -> dict:
    init_db()
    with connect() as connection:
        rows = fetch_rows(connection)
        connection.execute("delete from region_risks")
        created = 0
        for region in REGION_THEMES:
            matches = []
            for row in rows:
                score, core, pressure, relief = score_region(row, region)
                if score >= region.min_score:
                    matches.append((row, score, core, pressure, relief))
            if not matches:
                continue

            avg_impact = sum((row["impact_score"] or 0) for row, *_rest in matches) / len(matches)
            avg_match_score = sum(score for _row, score, *_rest in matches) / len(matches)
            high_risk = sum(1 for row, *_rest in matches if row["risk_level"] == "높음")
            pressure_score = min(98, round(22 + avg_impact * 3.5 + avg_match_score * 2.6 + high_risk * 1.8))
            latest_date = max(row["news_date"] for row, *_rest in matches)
            connection.execute(
                """
                insert into region_risks (
                  region_name, risk_level, pressure_score, summary_ko, news_date
                )
                values (?, ?, ?, ?, ?)
                """,
                (
                    region.name,
                    risk_level_for(pressure_score),
                    pressure_score,
                    summary_for(region, matches),
                    latest_date,
                ),
            )
            created += 1
        connection.commit()
        return {"regions": created, "sourceNews": len(rows)}


def get_region_payload(connection) -> list[dict]:
    rows = connection.execute(
        """
        select region_name, risk_level, pressure_score, summary_ko, news_date
        from region_risks
        order by pressure_score desc, news_date desc, region_name
        """
    ).fetchall()
    return [
        {
            "region": row["region_name"],
            "risk": row["risk_level"],
            "pressure": row["pressure_score"],
            "summary": row["summary_ko"],
            "updatedAt": row["news_date"],
            "events": get_region_events(connection, row["region_name"]),
        }
        for row in rows
    ]


if __name__ == "__main__":
    print(build_region_risks())
