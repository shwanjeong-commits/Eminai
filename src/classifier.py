import bootstrap  # noqa: F401

from collections import Counter
import argparse
import hashlib
import re

from database import connect


ANALYSIS_TARGET_START = "2026-07-01"

URL_ONLY_PATTERN = re.compile(r"^\s*https?://\S+\s*$", re.IGNORECASE)
SYMBOL_PATTERN = re.compile(r"\b[A-Z]{1,6}\b")

NEWS_KEYWORDS = [
    "미국",
    "중국",
    "유럽",
    "일본",
    "한국",
    "러시아",
    "우크라이나",
    "이란",
    "이스라엘",
    "중동",
    "트럼프",
    "바이든",
    "대통령",
    "정부",
    "의회",
    "상원",
    "하원",
    "연준",
    "Fed",
    "FOMC",
    "금리",
    "인플레이션",
    "CPI",
    "PPI",
    "GDP",
    "고용",
    "실업",
    "달러",
    "DXY",
    "환율",
    "국채",
    "관세",
    "제재",
    "협상",
    "회담",
    "전쟁",
    "군사",
    "공격",
    "휴전",
    "원유",
    "유가",
    "가스",
    "LNG",
    "에너지",
    "증시",
    "주가",
    "나스닥",
    "S&P",
    "다우",
    "ETF",
    "실적",
    "매출",
    "영업이익",
    "가이던스",
    "매수",
    "매도",
    "13F",
    "반도체",
    "AI",
    "엔비디아",
    "마이크론",
    "테슬라",
    "애플",
    "마이크로소프트",
    "블룸버그",
    "로이터",
    "WSJ",
    "CNBC",
    "뉴욕타임즈",
    "글로벌 뉴스 브리핑",
]

BRIEFING_HINTS = [
    "글로벌 뉴스 브리핑",
    "트럼프 발언",
    "발언 정리",
    "뉴스 브리핑",
    "Market Summary",
    "프리마켓",
]

NOISE_HINTS = [
    "제 세컨 채널",
    "많은 관심 부탁",
    "구독",
    "광고",
    "프로모션",
    "이벤트 참여",
    "무료방",
    "리딩방",
    "입장",
    "초대",
    "공지",
    "잡담",
    "ㅋㅋ",
    "ㅎㅎ",
]

LOW_VALUE_DOMAINS = [
    "t.me/honeylifetip",
]

LOW_VALUE_EXACT_HINTS = [
    "Not a financial advice",
    "매수, 매도 추천이 아니며",
    "매매에 따른 손실은",
]

LOW_VALUE_PROFILE_HINTS = [
    "TipRanks",
    "최근 커버 종목",
    "성공률:",
    "평균 수익률",
    "🧑 이름:",
]


FACTUAL_NEWS_HINTS = [
    "central bank",
    "interest rate",
    "rate hike",
    "rate cut",
    "bps",
    "bank of korea",
    "bok",
    "south korea central bank",
    "federal reserve",
    "fed",
    "israel",
    "iran",
    "lebanon",
    "ukraine",
    "russia",
    "china",
    "missile",
    "drone",
    "strike",
    "attack",
    "oil",
    "tanker",
    "spacex",
    "starlink",
    "tsmc",
    "asml",
    "nvidia",
    "apple",
    "openai",
    "중앙은행",
    "한국은행",
    "금리",
    "기준금리",
    "인상",
    "인하",
    "공습",
    "미사일",
    "드론",
    "폭발",
    "화재",
    "침몰",
    "해협",
    "원유",
    "유조선",
    "이스라엘",
    "이란",
    "레바논",
    "우크라이나",
    "러시아",
    "중국",
    "스페이스X",
    "스타링크",
    "반도체",
    "엔비디아",
    "애플",
    "오픈AI",
    "실적",
    "매출",
    "주가",
    "프리마켓",
    "인수",
    "투자",
    "공급",
    "수요",
    "ETF",
    "ADR",
]


def compact_text(text: str) -> str:
    return " ".join((text or "").split())


def duplicate_key(text: str) -> str:
    normalized = compact_text(text).lower()
    return hashlib.sha1(normalized[:500].encode("utf-8")).hexdigest()


def keyword_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in NEWS_KEYWORDS if keyword.lower() in lowered]


def factual_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in FACTUAL_NEWS_HINTS if keyword.lower() in lowered]


def has_low_value_link(text: str) -> bool:
    lowered = text.lower()
    return any(domain in lowered for domain in LOW_VALUE_DOMAINS)


def classify_text(text: str) -> dict:
    compact = compact_text(text)
    length = len(compact)
    hits = keyword_hits(compact)
    factual = factual_hits(compact)
    symbols = SYMBOL_PATTERN.findall(compact)
    is_url_only = bool(URL_ONLY_PATTERN.match(compact))
    is_briefing = any(hint in compact for hint in BRIEFING_HINTS)
    has_noise = any(hint in compact for hint in NOISE_HINTS) or has_low_value_link(compact)
    market_signal = bool(symbols) or "%" in compact or "+" in compact or "$" in compact
    leading_text = compact.lstrip("━─-•·*⚡️ ")

    if not compact:
        return ignored("empty", "내용 없음")

    if any(leading_text.startswith(hint) for hint in LOW_VALUE_EXACT_HINTS):
        return ignored("disclaimer", "투자 고지 단독 메시지")

    if "🧑 이름:" in leading_text[:80] and any(hint in compact for hint in LOW_VALUE_PROFILE_HINTS):
        return ignored("analyst_profile", "애널리스트 프로필 카드")

    if is_url_only:
        return ignored("link_only", "링크만 있는 메시지")

    if has_noise and length < 220 and len(hits) < 2:
        return ignored("noise", "홍보 또는 비뉴스성 메시지")

    if length < 35 and not hits and not factual:
        return ignored("comment", "짧은 코멘트성 메시지")

    priority = 1.0
    priority += min(length / 600, 3.0)
    priority += min(len(hits) * 0.35, 3.0)
    priority += min(len(factual) * 0.25, 2.0)
    priority += min(len(set(symbols)) * 0.12, 1.2)
    priority += 2.0 if is_briefing else 0

    if is_briefing:
        content_type = "briefing"
        status = "queued"
    elif length >= 500 and hits:
        content_type = "long_news"
        status = "queued"
    elif (hits or factual) and (length >= 35 or (market_signal and length >= 20) or len(factual) >= 2):
        content_type = "news"
        status = "queued"
    elif length >= 120 and (market_signal or "http" in compact or factual):
        content_type = "possible_news"
        status = "review"
    else:
        return ignored("comment", f"뉴스 키워드 부족, 길이 {length}자")

    reason = f"키워드 {len(hits)}개, 길이 {length}자"
    if is_briefing:
        reason += ", 브리핑 형식"

    return {
        "content_type": content_type,
        "analysis_status": status,
        "analysis_priority": round(priority, 2),
        "analysis_reason": reason,
    }


def ignored(content_type: str, reason: str) -> dict:
    return {
        "content_type": content_type,
        "analysis_status": "ignored",
        "analysis_priority": 0,
        "analysis_reason": reason,
    }


def analysis_scope(news_date: str) -> str:
    return "analysis_target" if news_date >= ANALYSIS_TARGET_START else "context_history"


def classify_rows(connection, rows) -> Counter:
    counts = Counter()
    for row in rows:
        result = classify_text(row["raw_text"])
        counts[result["analysis_status"]] += 1
        counts[result["content_type"]] += 1
        connection.execute(
            """
            update news_items
            set content_type = ?,
                analysis_status = ?,
                analysis_priority = ?,
                analysis_reason = ?,
                analysis_scope = ?,
                duplicate_key = ?,
                updated_at = current_timestamp
            where id = ?
            """,
            (
                result["content_type"],
                result["analysis_status"],
                result["analysis_priority"],
                result["analysis_reason"],
                analysis_scope(row["news_date"]),
                duplicate_key(row["raw_text"]),
                row["id"],
            ),
        )
    return counts


def classify_item(connection, news_id: int) -> None:
    row = connection.execute(
        "select id, news_date, raw_text, analysis_status from news_items where id = ?",
        (news_id,),
    ).fetchone()
    if row and row["analysis_status"] in {"analyzed", "context_absorbed"}:
        return
    if row:
        classify_rows(connection, [row])


def classify_batch(limit: int | None = None, reclassify: bool = False) -> None:
    sql = """
        select id, news_date, raw_text
        from news_items
    """
    params = ()
    if not reclassify:
        sql += " where analysis_status = 'pending'"
    sql += " order by published_at desc"
    if limit is not None:
        sql += " limit ?"
        params = (limit,)

    with connect() as connection:
        rows = connection.execute(sql, params).fetchall()
        counts = classify_rows(connection, rows)

        print(f"classified: {len(rows)}")
        for key, count in counts.most_common():
            print(f"{key}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify collected Telegram messages.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--reclassify", action="store_true")
    args = parser.parse_args()
    classify_batch(limit=args.limit, reclassify=args.reclassify)
