import bootstrap  # noqa: F401

import json
from dataclasses import dataclass

from database import connect, init_db


ANALYSIS_TARGET_START = "2026-07-01"


@dataclass(frozen=True)
class AssetTheme:
    name: str
    asset_type: str
    core_keywords: tuple[str, ...]
    positive_keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...]
    watch_points: tuple[str, ...]
    min_score: float = 2.5


ASSET_THEMES = (
    AssetTheme(
        name="원유·에너지",
        asset_type="원자재",
        core_keywords=("원유", "유가", "에너지", "LNG", "호르무즈", "OPEC"),
        positive_keywords=("공급 차질", "긴장", "공습", "상선", "보험료", "전력 수요", "폭염"),
        negative_keywords=("휴전", "협상", "완화", "수요 둔화"),
        watch_points=("호르무즈 해협 통항", "중동 군사충돌 강도", "유가와 운송비 반응"),
    ),
    AssetTheme(
        name="미국 국채·장기금리",
        asset_type="금리",
        core_keywords=("국채", "장기 금리", "금리", "이자비용", "재정적자", "부채"),
        positive_keywords=("인하 기대 약화", "재정적자", "부채 증가", "인플레이션", "고용"),
        negative_keywords=("금리 인하", "경기 둔화", "완화"),
        watch_points=("연준 금리 인하 기대", "미국 재정적자 뉴스", "장기금리 상승 압력"),
    ),
    AssetTheme(
        name="달러",
        asset_type="통화",
        core_keywords=("달러", "미국", "연준", "Fed", "금리", "국채"),
        positive_keywords=("안전자산", "위험 회피", "금리 상승", "고용", "인플레이션"),
        negative_keywords=("금리 인하", "유동성", "위험자산 선호"),
        watch_points=("위험자산 선호 변화", "연준 스탠스", "미국 지표 서프라이즈"),
    ),
    AssetTheme(
        name="미국 기술주·AI",
        asset_type="주식 섹터",
        core_keywords=("AI", "인공지능", "오픈AI", "GPT", "엔비디아", "기술주", "데이터센터"),
        positive_keywords=("완전 공개", "승인", "상업적 활용", "성장", "실적 호조", "투자"),
        negative_keywords=("규제", "보안", "윤리", "차익 실현", "손실"),
        watch_points=("AI 모델 정책 변화", "AI 서버 수요", "기술주 차익 실현"),
    ),
    AssetTheme(
        name="반도체·메모리",
        asset_type="주식 섹터",
        core_keywords=("반도체", "마이크론", "메모리", "HBM", "엔비디아", "GPU", "CPU"),
        positive_keywords=("AI 서버", "데이터센터", "실적 호조", "투자", "성장"),
        negative_keywords=("손실", "약세", "부진", "차익 실현", "투자 심리"),
        watch_points=("마이크론 투자자 손익", "AI 서버 수요", "반도체 투자 심리"),
    ),
    AssetTheme(
        name="방산·지정학",
        asset_type="테마",
        core_keywords=("전쟁", "군사", "공습", "미사일", "드론", "NATO", "안보", "보복"),
        positive_keywords=("긴장", "충돌", "확대", "제재", "방위", "기지"),
        negative_keywords=("휴전", "협상", "평화", "완화"),
        watch_points=("중동 군사 긴장", "러시아·우크라이나 전선", "미국 동맹 발언"),
    ),
    AssetTheme(
        name="중국 전기차·공급망",
        asset_type="주식 섹터",
        core_keywords=("중국", "전기차", "BYD", "공급망", "관세", "USMCA", "원산지"),
        positive_keywords=("북미", "확장", "수출", "다변화", "세제"),
        negative_keywords=("관세", "의존도", "폐지", "규제", "무역 갈등"),
        watch_points=("관세와 원산지 규정", "BYD 북미 전략", "중국 산업정책"),
    ),
    AssetTheme(
        name="한국 증시·AI 산업",
        asset_type="지역 주식",
        core_keywords=("한국", "코스피", "약세장", "SK하이닉스", "반도체", "AI 산업"),
        positive_keywords=("투자", "글로벌 AI", "미래 산업", "위성통신", "자금 유입"),
        negative_keywords=("약세장", "하락", "차익 실현", "투자 심리"),
        watch_points=("한국 증시 약세장 여부", "AI 투자 자금 유입", "반도체 수급"),
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
            row["analysis_ko"] or "",
            row["raw_text"] or "",
            row["category"] or "",
        ]
    )


def hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def score_asset(row, asset: AssetTheme) -> tuple[float, list[str], list[str], list[str]]:
    text = row_text(row)
    core = hits(text, asset.core_keywords)
    positive = hits(text, asset.positive_keywords)
    negative = hits(text, asset.negative_keywords)
    score = len(core) * 1.5 + len(positive) * 0.55 + len(negative) * 0.45
    if not core:
        score -= 2.0
    if row["impact_score"]:
        score += min(row["impact_score"] / 10, 0.9)
    return round(score, 3), core, positive, negative


def stance_for(matches: list[tuple]) -> str:
    positive_hits = sum(len(item[2]) for item in matches)
    negative_hits = sum(len(item[3]) for item in matches)
    high_risk = sum(1 for row, *_rest in matches if (row["risk_level"] or "") == "높음")
    if negative_hits > positive_hits and high_risk:
        return "방어적 관찰"
    if positive_hits > negative_hits and high_risk <= max(1, len(matches) // 3):
        return "상방 모멘텀"
    if high_risk >= 2:
        return "변동성 확대"
    return "관찰 필요"


def summary_for(asset: AssetTheme, matches: list[tuple]) -> str:
    top = max(matches, key=lambda item: ((item[0]["impact_score"] or 0), item[1]))[0]
    avg_impact = sum((row["impact_score"] or 0) for row, *_rest in matches) / len(matches)
    dates = sorted({row["news_date"] for row, *_rest in matches})
    return (
        f"{asset.name} 관련 뉴스 {len(matches)}건이 감지됐습니다. "
        f"기간은 {dates[0]}부터 {dates[-1]}까지이며 평균 영향도는 {avg_impact:.1f}입니다. "
        f"핵심 신호는 '{compact(top['title'] or top['summary_ko'] or top['raw_text'], 80)}'입니다."
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


def build_asset_views() -> dict:
    init_db()
    with connect() as connection:
        rows = fetch_rows(connection)
        connection.execute("delete from asset_impacts")
        created = 0
        for asset in ASSET_THEMES:
            matches = []
            for row in rows:
                score, core, positive, negative = score_asset(row, asset)
                if score >= asset.min_score:
                    matches.append((row, score, positive, negative, core))

            if not matches:
                continue

            latest_date = max(row["news_date"] for row, *_rest in matches)
            impact = sum((row["impact_score"] or 0) for row, *_rest in matches) / len(matches)
            dynamic_watch = []
            for _row, _score, positive, negative, core in matches:
                for keyword in [*core, *positive, *negative]:
                    if keyword not in dynamic_watch:
                        dynamic_watch.append(keyword)
            watch_points = list(asset.watch_points) + dynamic_watch[:4]
            connection.execute(
                """
                insert into asset_impacts (
                  asset_name, asset_type, stance, summary_ko, impact_score, watch_points, news_date
                )
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.name,
                    asset.asset_type,
                    stance_for(matches),
                    summary_for(asset, matches),
                    round(min(impact, 9.8), 1),
                    json.dumps(watch_points[:7], ensure_ascii=False),
                    latest_date,
                ),
            )
            created += 1
        connection.commit()
        return {"assets": created, "sourceNews": len(rows)}


def get_asset_payload(connection) -> list[dict]:
    rows = connection.execute(
        """
        select asset_name, asset_type, stance, summary_ko, impact_score, watch_points, news_date
        from asset_impacts
        order by impact_score desc, news_date desc, asset_name
        """
    ).fetchall()
    return [
        {
            "name": row["asset_name"],
            "type": row["asset_type"],
            "stance": row["stance"],
            "impact": row["impact_score"] or 0,
            "summary": row["summary_ko"],
            "watch": json.loads(row["watch_points"] or "[]"),
            "updatedAt": row["news_date"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    print(build_asset_views())
