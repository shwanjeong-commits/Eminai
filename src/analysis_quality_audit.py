import bootstrap  # noqa: F401

import argparse
from collections import Counter

from database import connect, init_db


QUALITY_MARKERS = ("핵심 동인:", "전달 경로:", "관찰 포인트:", "불확실성:")


def compact(text: str, limit: int = 120) -> str:
    value = " ".join((text or "").split())
    return value[:limit] + ("..." if len(value) > limit else "")


def quality_issues(row) -> list[str]:
    issues = []
    summary = row["summary_ko"] or ""
    analysis = row["analysis_ko"] or ""
    impact = float(row["impact_score"] or 0)
    risk = row["risk_level"] or ""

    if len(summary.strip()) < 45:
        issues.append("summary_too_short")
    if len(analysis.strip()) < 160:
        issues.append("analysis_too_short")
    for marker in QUALITY_MARKERS:
        if marker not in analysis:
            issues.append(f"missing_{marker.rstrip(':')}")
    if impact >= 8 and risk != "높음":
        issues.append("high_impact_low_risk_mismatch")
    if impact <= 3 and risk == "높음":
        issues.append("low_impact_high_risk_mismatch")
    if "투자 조언" in analysis or "매수" in analysis and "추천" in analysis:
        issues.append("possible_investment_advice")
    return issues


def audit(limit: int = 500, requeue: bool = False, max_requeue: int = 20) -> dict:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            """
            select id, news_date, title, summary_ko, analysis_ko, impact_score, risk_level
            from news_items
            where analysis_scope = 'analysis_target'
              and analysis_status = 'analyzed'
            order by published_at desc
            limit ?
            """,
            (limit,),
        ).fetchall()

        issue_counts = Counter()
        candidates = []
        for row in rows:
            issues = quality_issues(row)
            if not issues:
                continue
            issue_counts.update(issues)
            candidates.append(
                {
                    "id": row["id"],
                    "date": row["news_date"],
                    "title": compact(row["title"] or "제목 없음", 80),
                    "issues": issues,
                }
            )

        requeued = []
        if requeue:
            for item in candidates[:max_requeue]:
                connection.execute(
                    """
                    update news_items
                    set analysis_status = 'review',
                        summary_ko = null,
                        analysis_ko = null,
                        impact_score = null,
                        sentiment = null,
                        risk_level = null,
                        category = null,
                        updated_at = current_timestamp
                    where id = ?
                    """,
                    (item["id"],),
                )
                requeued.append(item["id"])

        return {
            "checked": len(rows),
            "candidate_count": len(candidates),
            "issue_counts": dict(issue_counts.most_common()),
            "candidates": candidates[:30],
            "requeued": requeued,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit analyzed news quality and optionally requeue weak analyses.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--requeue", action="store_true")
    parser.add_argument("--max-requeue", type=int, default=20)
    args = parser.parse_args()
    print(audit(limit=args.limit, requeue=args.requeue, max_requeue=args.max_requeue))
