import bootstrap  # noqa: F401

import json
import re
from dataclasses import dataclass

from database import connect, init_db


ANALYSIS_TARGET_START = "2026-07-01"


@dataclass(frozen=True)
class RegionRule:
    name: str
    keywords: tuple[str, ...]
    risk_words: tuple[str, ...]


REGION_RULES = (
    RegionRule("미국", ("미국", "트럼프", "연준", "Fed", "FOMC", "달러", "국채", "S&P", "나스닥", "스페이스X", "레딧"), ("금리", "재정적자", "부채", "정전", "폭염", "정책", "마진콜")),
    RegionRule("중동", ("중동", "이란", "이스라엘", "호르무즈", "가자", "레바논", "예멘", "후티", "쿠웨이트"), ("공습", "보복", "미사일", "드론", "상선", "군사", "긴장", "유가")),
    RegionRule("러시아·우크라이나", ("러시아", "우크라이나", "푸틴", "젤렌스키", "러-우", "NATO"), ("전쟁", "미사일", "드론", "제재", "분쟁", "수출 제한")),
    RegionRule("중국·대만", ("중국", "대만", "BYD", "전기차", "CXMT", "창신메모리", "상하이", "USMCA"), ("관세", "무역", "공급망", "IPO", "경쟁", "규제")),
    RegionRule("유럽", ("유럽", "EU", "독일", "프랑스", "ECB", "유럽중앙은행"), ("안보", "재정", "정책", "분쟁", "의존도")),
    RegionRule("한국", ("한국", "코스피", "SK하이닉스", "삼성전자", "반도체", "AI 산업", "위성통신"), ("약세장", "하락", "투자 심리", "수급", "경쟁")),
)


def compact(text: str, length: int = 90) -> str:
    value = " ".join((text or "").split())
    return value[:length] + ("..." if len(value) > length else "")


def split_events(text: str) -> list[str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []
    normalized = re.sub(r"(습니다\.|입니다\.|한다\.|했다\.|됐다\.|된다\.|다\.|요\.|[.!?。])\s+", r"\1|", cleaned)
    normalized = re.sub(r"[\n\r]+", "|", normalized)
    parts = [part.strip(" -•·") for part in normalized.split("|") if part.strip(" -•·")]
    if len(parts) <= 1 and len(cleaned) > 180:
        parts = [part.strip() for part in re.split(r",\s*(?=[가-힣A-Z])", cleaned) if part.strip()]
    return [part for part in parts if len(part) >= 24][:12]


def match_regions(text: str) -> list[tuple[str, list[str], int]]:
    lowered = text.lower()
    matches = []
    for rule in REGION_RULES:
        keyword_hits = [keyword for keyword in rule.keywords if keyword.lower() in lowered]
        risk_hits = [keyword for keyword in rule.risk_words if keyword.lower() in lowered]
        if not keyword_hits:
            continue
        score = len(keyword_hits) * 2 + len(risk_hits)
        matches.append((rule.name, keyword_hits + risk_hits, score))
    return sorted(matches, key=lambda item: item[2], reverse=True)


def event_risk(text: str, inherited_risk: str | None) -> str:
    high_words = ("공습", "보복", "미사일", "드론", "전쟁", "긴장", "정전", "폭염", "약세장", "마진콜", "수출 제한")
    medium_words = ("관세", "금리", "부채", "경쟁", "규제", "정책", "IPO", "협상")
    if any(word in text for word in high_words):
        return "높음"
    if inherited_risk == "높음" or any(word in text for word in medium_words):
        return "중간"
    return inherited_risk or "낮음"


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


def build_news_events() -> dict:
    init_db()
    with connect() as connection:
        rows = fetch_rows(connection)
        connection.execute("delete from news_events")
        created = 0
        for row in rows:
            source = row["summary_ko"] or row["raw_text"] or row["title"] or ""
            segments = split_events(source)
            if not segments:
                segments = [compact(source, 180)] if source else []

            seen = set()
            for segment in segments:
                matched_regions = match_regions(" ".join([row["title"] or "", segment]))
                if not matched_regions:
                    continue
                for region_name, keywords, score in matched_regions[:2]:
                    key = (row["id"], region_name, compact(segment, 70))
                    if key in seen:
                        continue
                    seen.add(key)
                    impact = min(9.8, (row["impact_score"] or 5.0) + min(score * 0.12, 0.8))
                    connection.execute(
                        """
                        insert into news_events (
                          news_item_id, event_date, region_name, event_title,
                          event_summary_ko, risk_level, impact_score, keywords
                        )
                        values (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["id"],
                            row["news_date"],
                            region_name,
                            row["title"] or compact(segment, 70),
                            segment,
                            event_risk(segment, row["risk_level"]),
                            round(impact, 1),
                            json.dumps(keywords[:8], ensure_ascii=False),
                        ),
                    )
                    created += 1
        connection.commit()
        return {"events": created, "sourceNews": len(rows)}


def get_region_events(connection, region_name: str, limit: int = 10) -> list[dict]:
    rows = connection.execute(
        """
        select e.news_item_id, e.event_date, e.region_name, e.event_title,
               e.event_summary_ko, e.risk_level, e.impact_score, e.keywords,
               n.title as news_title
        from news_events e
        join news_items n on n.id = e.news_item_id
        where e.region_name = ?
        order by e.impact_score desc, e.event_date desc, e.id desc
        limit ?
        """,
        (region_name, limit),
    ).fetchall()
    return [
        {
            "newsId": row["news_item_id"],
            "date": row["event_date"],
            "region": row["region_name"],
            "title": row["event_title"],
            "summary": row["event_summary_ko"],
            "risk": row["risk_level"],
            "impact": row["impact_score"] or 0,
            "keywords": json.loads(row["keywords"] or "[]"),
            "newsTitle": row["news_title"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    print(build_news_events())
