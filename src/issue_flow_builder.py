import bootstrap  # noqa: F401

from dataclasses import dataclass

from database import connect, init_db


ANALYSIS_TARGET_START = "2026-07-01"
MAX_LINKS_PER_NEWS = 3
SECONDARY_SCORE_GAP = 1.8


@dataclass(frozen=True)
class IssueTheme:
    slug: str
    title: str
    core_keywords: tuple[str, ...]
    support_keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    min_score: float = 3.0
    min_core_hits: int = 1


THEMES = (
    IssueTheme(
        slug="us-iran-military-escalation",
        title="미·이란 군사충돌",
        core_keywords=("미국-이란", "미-이란", "이란", "공습", "보복", "미군"),
        support_keywords=("호르무즈", "상선", "드론", "격추", "휴전", "침략", "군사", "기지", "정밀 타격"),
        negative_keywords=("우크라이나", "러시아", "반도체", "마이크론", "GPT"),
        categories=("geopolitics",),
        min_score=3.4,
    ),
    IssueTheme(
        slug="iran-nuclear-diplomacy",
        title="이란 핵협상·외교",
        core_keywords=("이란", "핵", "핵협상", "핵 협상", "협상", "제재 해제"),
        support_keywords=("트럼프", "파키스탄", "동결 자금", "외교", "소통", "일정", "회담", "중재"),
        negative_keywords=("공습", "상선 공격", "마이크론", "GPT"),
        categories=("geopolitics",),
        min_score=3.2,
    ),
    IssueTheme(
        slug="hormuz-oil-shipping",
        title="호르무즈·유가·해운",
        core_keywords=("호르무즈", "유가", "원유", "상선", "해운", "운송"),
        support_keywords=("보험료", "에너지", "공급망", "중동", "LNG", "OPEC", "해상", "물류", "공급"),
        negative_keywords=("GPT", "마이크론", "엔비디아", "우크라이나"),
        categories=("energy", "geopolitics", "markets"),
        min_score=3.1,
    ),
    IssueTheme(
        slug="fed-cut-expectations",
        title="연준 금리인하 기대",
        core_keywords=("연준", "Fed", "FOMC", "금리 인하", "금리"),
        support_keywords=("인플레이션", "고용", "실업", "CPI", "GDP", "기대", "통화정책", "장기 금리"),
        negative_keywords=("호르무즈", "이란", "미사일", "마이크론"),
        categories=("macro", "markets"),
        min_score=3.2,
    ),
    IssueTheme(
        slug="us-fiscal-debt-rates",
        title="미국 재정적자·장기금리",
        core_keywords=("재정적자", "부채", "이자비용", "국채", "장기 금리"),
        support_keywords=("미국", "달러", "금리", "시장", "채권", "위험자산", "유동성"),
        negative_keywords=("호르무즈", "이란", "우크라이나", "마이크론"),
        categories=("macro", "markets"),
        min_score=3.0,
    ),
    IssueTheme(
        slug="ai-model-policy",
        title="AI 모델 공개·정책",
        core_keywords=("오픈AI", "GPT", "인공지능", "AI 모델", "완전 공개"),
        support_keywords=("미국 정부", "승인", "기술 정책", "상업적 활용", "윤리", "보안", "생태계"),
        negative_keywords=("호르무즈", "이란", "러시아", "원유"),
        categories=("markets",),
        min_score=3.0,
    ),
    IssueTheme(
        slug="semiconductor-memory-cycle",
        title="반도체·메모리 사이클",
        core_keywords=("반도체", "마이크론", "메모리", "HBM", "엔비디아"),
        support_keywords=("투자자", "손실", "실적", "AI 서버", "CPU", "GPU", "데이터센터", "기술주"),
        negative_keywords=("호르무즈", "이란", "우크라이나", "러시아"),
        categories=("markets",),
        min_score=3.0,
    ),
    IssueTheme(
        slug="russia-ukraine-war",
        title="러시아·우크라이나 전쟁",
        core_keywords=("러시아", "우크라이나", "러-우", "푸틴", "젤렌스키"),
        support_keywords=("전쟁", "미사일", "드론", "NATO", "안보", "제재", "분쟁", "통화", "평화"),
        negative_keywords=("이란", "호르무즈", "반도체", "마이크론", "GPT"),
        categories=("geopolitics",),
        min_score=3.2,
    ),
    IssueTheme(
        slug="china-trade-ev-supply",
        title="중국·무역·전기차 공급망",
        core_keywords=("중국", "관세", "무역", "USMCA", "전기차", "BYD", "공급망"),
        support_keywords=("원산지", "수출", "수입", "북미", "세제", "의존도", "다변화", "대만"),
        negative_keywords=("호르무즈", "이란 핵", "마이크론 손실"),
        categories=("macro", "geopolitics", "markets"),
        min_score=3.1,
    ),
    IssueTheme(
        slug="us-energy-grid-stress",
        title="미국 전력망·에너지 수요",
        core_keywords=("전력", "전력망", "정전", "폭염", "전력 수요"),
        support_keywords=("미국", "비상 절차", "에너지", "인프라", "기후", "수요", "공급"),
        negative_keywords=("GPT", "마이크론", "우크라이나", "핵협상"),
        categories=("energy", "macro"),
        min_score=3.0,
    ),
)


def compact(text: str, length: int = 120) -> str:
    value = " ".join((text or "").split())
    return value[:length] + ("..." if len(value) > length else "")


def source_text(row) -> str:
    return " ".join(
        [
            row["title"] or "",
            row["summary_ko"] or "",
            row["analysis_ko"] or "",
            row["raw_text"] or "",
            row["category"] or "",
        ]
    )


def hits_for(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def score_theme(row, theme: IssueTheme) -> tuple[float, list[str]]:
    text = source_text(row)
    core_hits = hits_for(text, theme.core_keywords)
    support_hits = hits_for(text, theme.support_keywords)
    negative_hits = hits_for(text, theme.negative_keywords)

    score = len(core_hits) * 1.9 + len(support_hits) * 0.5 - len(negative_hits) * 0.65
    if len(core_hits) < theme.min_core_hits:
        score -= 3.0
    if len(core_hits) >= 2:
        score += 0.7
    if core_hits and support_hits:
        score += 0.45
    if row["category"] in theme.categories:
        score += 0.35
    return round(score, 3), core_hits + support_hits


def score_all_themes(row) -> list[tuple[IssueTheme, float, list[str]]]:
    scored = []
    for theme in THEMES:
        score, hits = score_theme(row, theme)
        if score >= theme.min_score:
            scored.append((theme, score, hits))
    scored.sort(key=lambda item: item[1], reverse=True)
    if not scored:
        return []

    top_score = scored[0][1]
    return [
        item
        for item in scored[:MAX_LINKS_PER_NEWS]
        if item[1] >= top_score - SECONDARY_SCORE_GAP
    ]


def event_text(row) -> str:
    return compact(row["title"] or row["summary_ko"] or row["analysis_ko"] or row["raw_text"], 110)


def impact_label(row) -> str:
    score = row["impact_score"] or 0
    risk = row["risk_level"] or "미분류"
    if score >= 8 or risk == "높음":
        return "위험도 상승"
    if score >= 6:
        return "관찰 필요"
    return "흐름 유지"


def issue_status(matches: list) -> str:
    high_risk_count = sum(1 for row, _score, _hits, _rank in matches if (row["risk_level"] or "") == "높음")
    avg_impact = sum((row["impact_score"] or 0) for row, _score, _hits, _rank in matches) / max(len(matches), 1)
    if len(matches) >= 4 or high_risk_count >= 2 or avg_impact >= 7.8:
        return "확대"
    return "관찰"


def issue_summary(theme: IssueTheme, matches: list) -> str:
    count = len(matches)
    primary_count = sum(1 for _row, _score, _hits, rank in matches if rank == 1)
    dates = sorted({row["news_date"] for row, _score, _hits, _rank in matches})
    max_impact = max((row["impact_score"] or 0) for row, _score, _hits, _rank in matches)
    strongest = max(matches, key=lambda item: ((item[0]["impact_score"] or 0), item[1]))[0]
    return (
        f"분석 뉴스 {count}건이 '{theme.title}' 흐름과 연결됩니다. "
        f"이 중 주 이슈 연결은 {primary_count}건입니다. "
        f"기간은 {dates[0]}부터 {dates[-1]}까지이며, 최고 영향도는 {max_impact:.1f}입니다. "
        f"가장 강한 신호는 '{compact(strongest['title'] or strongest['summary_ko'] or strongest['raw_text'], 70)}'입니다."
    )


def fetch_analyzed_rows(connection):
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


def clear_issue_tables(connection) -> None:
    connection.execute("delete from news_issue_links")
    connection.execute("delete from issue_events")
    connection.execute("delete from issues")


def grouped_matches(rows) -> dict[str, list]:
    grouped = {theme.slug: [] for theme in THEMES}
    for row in rows:
        for rank, (theme, score, hits) in enumerate(score_all_themes(row), start=1):
            grouped[theme.slug].append((row, score, hits, rank))
    return grouped


def build_issue_flows() -> dict:
    init_db()
    with connect() as connection:
        rows = fetch_analyzed_rows(connection)
        clear_issue_tables(connection)
        matches_by_slug = grouped_matches(rows)
        theme_by_slug = {theme.slug: theme for theme in THEMES}
        issue_ids = {}
        created = 0
        links = 0
        events = 0

        for slug, matches in matches_by_slug.items():
            if not matches:
                continue
            theme = theme_by_slug[slug]
            dates = sorted({row["news_date"] for row, _score, _hits, _rank in matches})
            avg_impact = sum((row["impact_score"] or 0) for row, _score, _hits, _rank in matches) / len(matches)
            connection.execute(
                """
                insert into issues (
                  slug, title, summary_ko, status, first_seen_date, last_seen_date,
                  impact_score, updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, current_timestamp)
                """,
                (
                    theme.slug,
                    theme.title,
                    issue_summary(theme, matches),
                    issue_status(matches),
                    dates[0],
                    dates[-1],
                    round(min(avg_impact, 9.8), 1),
                ),
            )
            issue_ids[slug] = connection.execute("select id from issues where slug = ?", (slug,)).fetchone()["id"]
            created += 1

        for slug, matches in matches_by_slug.items():
            if slug not in issue_ids:
                continue
            issue_id = issue_ids[slug]
            sorted_matches = sorted(matches, key=lambda item: (item[3] == 1, item[0]["published_at"], item[1]))[-8:]
            for row, _score, _hits, rank in sorted_matches:
                prefix = "주 이슈" if rank == 1 else "보조 이슈"
                connection.execute(
                    """
                    insert into issue_events (issue_id, news_item_id, event_date, event_summary_ko, impact_delta)
                    values (?, ?, ?, ?, ?)
                    """,
                    (issue_id, row["id"], row["news_date"], event_text(row), f"{prefix} · {impact_label(row)}"),
                )
                events += 1

            for row, score, hits, rank in matches:
                base = 0.5 + score * 0.08
                confidence = min(0.98, base + (0.08 if rank == 1 else 0))
                reason = ("주 이슈" if rank == 1 else "보조 이슈") + " · 키워드 점수: " + ", ".join(hits[:6])
                connection.execute(
                    """
                    insert into news_issue_links (news_item_id, issue_id, confidence, link_reason_ko)
                    values (?, ?, ?, ?)
                    """,
                    (row["id"], issue_id, confidence, reason),
                )
                links += 1

        connection.commit()
        return {"issues": created, "events": events, "links": links, "sourceNews": len(rows)}


def get_primary_issue_map(connection) -> dict[int, str]:
    rows = connection.execute(
        """
        select news_item_id, slug
        from (
          select
            l.news_item_id,
            i.slug,
            row_number() over (
              partition by l.news_item_id
              order by
                case when l.link_reason_ko like '주 이슈%' then 0 else 1 end,
                l.confidence desc
            ) as rank
          from news_issue_links l
          join issues i on i.id = l.issue_id
        )
        where rank = 1
        """
    ).fetchall()
    return {row["news_item_id"]: row["slug"] for row in rows}


def get_issue_links_map(connection) -> dict[int, list[dict]]:
    rows = connection.execute(
        """
        select l.news_item_id, i.slug, i.title, l.confidence, l.link_reason_ko
        from news_issue_links l
        join issues i on i.id = l.issue_id
        order by
          l.news_item_id,
          case when l.link_reason_ko like '주 이슈%' then 0 else 1 end,
          l.confidence desc
        """
    ).fetchall()
    links: dict[int, list[dict]] = {}
    for row in rows:
        reason = row["link_reason_ko"] or ""
        links.setdefault(row["news_item_id"], []).append(
            {
                "id": row["slug"],
                "title": row["title"],
                "confidence": round(row["confidence"] or 0, 2),
                "role": "primary" if reason.startswith("주 이슈") else "secondary",
                "reason": reason,
            }
        )
    return links


def get_issue_payload(connection) -> list[dict]:
    issue_rows = connection.execute(
        """
        select id, slug, title, summary_ko, status, first_seen_date, last_seen_date, impact_score
        from issues
        order by impact_score desc, last_seen_date desc
        """
    ).fetchall()
    payload = []
    for issue in issue_rows:
        event_rows = connection.execute(
            """
            select event_date, event_summary_ko, impact_delta
            from issue_events
            where issue_id = ?
            order by event_date asc, id asc
            """,
            (issue["id"],),
        ).fetchall()
        payload.append(
            {
                "id": issue["slug"],
                "title": issue["title"],
                "status": issue["status"],
                "firstSeen": issue["first_seen_date"],
                "updatedAt": issue["last_seen_date"],
                "impact": issue["impact_score"] or 0,
                "summary": issue["summary_ko"],
                "events": [
                    {
                        "date": row["event_date"][5:] if len(row["event_date"]) >= 10 else row["event_date"],
                        "text": row["event_summary_ko"],
                        "impactDelta": row["impact_delta"],
                    }
                    for row in event_rows
                ],
            }
        )
    return payload


if __name__ == "__main__":
    print(build_issue_flows())
