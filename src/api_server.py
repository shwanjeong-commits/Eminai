import bootstrap  # noqa: F401

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from collections import defaultdict, deque
import hashlib
import hmac
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, unquote, urlparse

from asset_view_builder import get_asset_payload
from automation_status import get_status_payload
from automation_status import update_status
from config import load_dotenv, load_settings
from database import ROOT_DIR, connect, init_db
from economic_chat import NON_ECONOMIC_PROBES, answer_economic_question
from issue_flow_builder import get_issue_links_map, get_issue_payload, get_primary_issue_map
from market_data import asset_catalog, get_market_chart
from market_indicators import get_indicator_dashboard
from news_deep_analysis import generate_deep_analysis, get_deep_analysis
from news_translation import get_translations, translate_news_items
from region_risk_builder import get_region_payload
from situation_state import build_situation_payload, dimension_scores
from web_push_alerts import save_push_subscription


APP_DIR = ROOT_DIR / "app"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "4173"))
ANALYSIS_TARGET_START = "2026-07-01"
MANUAL_UPDATE_SERVICE = "manual_update"
KST = timezone(timedelta(hours=9))
AUTH_COOKIE = "eminai_auth"
AUTH_SESSION_SECONDS = 6 * 60 * 60
MAX_JSON_BODY_BYTES = int(os.getenv("MAX_JSON_BODY_BYTES", "262144"))
LOGIN_FAILURE_LIMIT = int(os.getenv("LOGIN_FAILURE_LIMIT", "5"))
LOGIN_FAILURE_WINDOW_SECONDS = int(os.getenv("LOGIN_FAILURE_WINDOW_SECONDS", "900"))
LOGIN_LOCK_SECONDS = int(os.getenv("LOGIN_LOCK_SECONDS", "900"))
LLM_RATE_LIMIT = int(os.getenv("LLM_RATE_LIMIT", "30"))
LLM_RATE_WINDOW_SECONDS = int(os.getenv("LLM_RATE_WINDOW_SECONDS", "3600"))
OPS_API_KEY_ENV = "EMINAI_OPS_API_KEY"
OPS_RATE_LIMIT = int(os.getenv("OPS_RATE_LIMIT", "60"))
OPS_RATE_WINDOW_SECONDS = int(os.getenv("OPS_RATE_WINDOW_SECONDS", "60"))

LOGGER = logging.getLogger("eminai.security")
if not LOGGER.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

_SESSION_LOCK = threading.RLock()
_AUTH_SESSIONS: dict[str, int] = {}
_LIMIT_LOCK = threading.RLock()
_LOGIN_FAILURES: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_LOCKED_UNTIL: dict[str, float] = {}
_REQUEST_BUCKETS: dict[tuple[str, str], deque[float]] = defaultdict(deque)

CATEGORY_LABELS = {
    "macro": "거시경제",
    "geopolitics": "해외 정세",
    "markets": "시장",
    "energy": "에너지",
}

KEYWORDS = {
    "macro": ["금리", "연준", "Fed", "FOMC", "고용", "실업", "CPI", "GDP", "달러", "관세"],
    "geopolitics": ["트럼프", "이란", "이스라엘", "중동", "러시아", "우크라이나", "전쟁", "제재", "회담"],
    "markets": ["증시", "주가", "나스닥", "S&P", "ETF", "실적", "AI", "반도체", "마이크론", "테슬라"],
    "energy": ["원유", "유가", "가스", "LNG", "에너지", "호르무즈", "공급"],
}

REGIONS = {
    "미국": ["미국", "트럼프", "연준", "Fed", "달러", "S&P", "나스닥"],
    "중국": ["중국", "위안", "전기차", "부양"],
    "중동": ["이란", "이스라엘", "예멘", "사우디", "호르무즈", "중동"],
    "유럽": ["유럽", "EU", "프랑스", "독일", "영국"],
    "러시아·우크라이나": ["러시아", "우크라이나", "젤렌스키"],
    "한국": ["한국", "원화", "코스피", "SK하이닉스"],
}

ASSETS = {
    "미국 기술주": ["AI", "엔비디아", "테슬라", "마이크론", "반도체", "소프트웨어"],
    "달러·금리": ["달러", "금리", "연준", "국채", "Fed", "FOMC"],
    "원유·에너지": ["원유", "유가", "가스", "LNG", "에너지"],
    "중국 전기차": ["전기차", "중국", "BYD", "테슬라"],
    "방산·지정학": ["전쟁", "군사", "방산", "공격", "제재"],
}


def site_access_password() -> str:
    load_dotenv()
    return os.getenv("SITE_ACCESS_PASSWORD", "").strip()


def telegram_daily_channel_url() -> str:
    load_dotenv()
    value = os.getenv("TELEGRAM_DAILY_CHANNEL_URL", "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc.lower() not in {"t.me", "telegram.me"}:
        return ""
    return value


def site_access_token(password: str | None = None, now: int | None = None) -> str:
    expires_at = int(time.time() if now is None else now) + AUTH_SESSION_SECONDS
    token = f"s1.{secrets.token_urlsafe(32)}"
    with _SESSION_LOCK:
        _AUTH_SESSIONS[token] = expires_at
    return token


def site_access_token_expires_at(token: str) -> int | None:
    if not isinstance(token, str) or not token.startswith("s1."):
        return None
    with _SESSION_LOCK:
        return _AUTH_SESSIONS.get(token)


def validate_site_access_token(token: str, password: str | None = None, now: int | None = None) -> bool:
    expires_at = site_access_token_expires_at(token)
    if expires_at is None:
        return False
    current_time = int(time.time() if now is None else now)
    if expires_at <= current_time:
        revoke_site_access_token(token)
        return False
    return True


def revoke_site_access_token(token: str) -> None:
    if not token:
        return
    with _SESSION_LOCK:
        _AUTH_SESSIONS.pop(token, None)


def cleanup_expired_sessions(now: int | None = None) -> None:
    current_time = int(time.time() if now is None else now)
    with _SESSION_LOCK:
        expired = [token for token, expires_at in _AUTH_SESSIONS.items() if expires_at <= current_time]
        for token in expired:
            _AUTH_SESSIONS.pop(token, None)


def access_expiry_iso(token: str) -> str | None:
    expires_at = site_access_token_expires_at(token)
    if expires_at is None:
        return None
    return datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_cookies(header: str | None) -> dict[str, str]:
    cookies = {}
    for item in (header or "").split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        cookies[key.strip()] = value.strip()
    return cookies


def cookie_security_suffix() -> str:
    secure = os.getenv("SITE_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"}
    return "; Secure" if secure else ""


def client_fingerprint(address: str) -> str:
    return hashlib.sha256(f"eminai-client:{address}".encode("utf-8")).hexdigest()[:12]


def login_retry_after(client_key: str, now: float | None = None) -> int:
    current_time = time.time() if now is None else now
    with _LIMIT_LOCK:
        locked_until = _LOGIN_LOCKED_UNTIL.get(client_key, 0)
        if locked_until <= current_time:
            _LOGIN_LOCKED_UNTIL.pop(client_key, None)
            return 0
        return max(1, int(locked_until - current_time + 0.999))


def record_login_failure(client_key: str, now: float | None = None) -> int:
    current_time = time.time() if now is None else now
    cutoff = current_time - LOGIN_FAILURE_WINDOW_SECONDS
    with _LIMIT_LOCK:
        attempts = _LOGIN_FAILURES[client_key]
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        attempts.append(current_time)
        if len(attempts) >= LOGIN_FAILURE_LIMIT:
            _LOGIN_LOCKED_UNTIL[client_key] = current_time + LOGIN_LOCK_SECONDS
            attempts.clear()
            return LOGIN_LOCK_SECONDS
    return 0


def clear_login_failures(client_key: str) -> None:
    with _LIMIT_LOCK:
        _LOGIN_FAILURES.pop(client_key, None)
        _LOGIN_LOCKED_UNTIL.pop(client_key, None)


def request_retry_after(bucket: str, client_key: str, limit: int, window_seconds: int) -> int:
    current_time = time.time()
    cutoff = current_time - window_seconds
    key = (bucket, client_key)
    with _LIMIT_LOCK:
        attempts = _REQUEST_BUCKETS[key]
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if len(attempts) >= limit:
            return max(1, int(attempts[0] + window_seconds - current_time + 0.999))
        attempts.append(current_time)
    return 0


class RequestValidationError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status

RISK_WEIGHT = {"높음": 3, "중간": 2, "낮음": 1}


def compact(text: str, length: int = 180) -> str:
    value = " ".join((text or "").split())
    return value[:length] + ("..." if len(value) > length else "")


def first_line(text: str) -> str:
    for line in (text or "").splitlines():
        cleaned = line.strip(" -•·")
        if cleaned and any(char.isalnum() for char in cleaned):
            return cleaned[:90]
    return "제목 없음"


def detect_category(text: str) -> str:
    lowered = (text or "").lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword.lower() in lowered)
        for category, keywords in KEYWORDS.items()
    }
    return max(scores, key=scores.get) if max(scores.values()) else "markets"


def detect_tags(text: str) -> list[str]:
    lowered = (text or "").lower()
    tags = []
    for groups in (KEYWORDS, REGIONS, ASSETS):
        for keywords in groups.values():
            for keyword in keywords:
                if keyword.lower() in lowered and keyword not in tags:
                    tags.append(keyword)
    return tags[:8]


def risk_level(text: str) -> str:
    high_words = ["전쟁", "공격", "제재", "위기", "급락", "긴장", "핵", "군사"]
    medium_words = ["우려", "변동성", "경고", "불확실", "둔화", "협상"]
    if any(word in (text or "") for word in high_words):
        return "높음"
    if any(word in (text or "") for word in medium_words):
        return "중간"
    return "낮음"


def impact_score(text: str) -> float:
    score = 4.8
    score += min(len(text or "") / 400, 2.5)
    score += 1.2 if "http" in (text or "") else 0
    score += 1.0 if risk_level(text) == "높음" else 0
    return round(min(score, 9.5), 1)


def region_for(text: str) -> str:
    lowered = (text or "").lower()
    for region, keywords in REGIONS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return region
    return "글로벌"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def local_time(value: str | None) -> str:
    parsed = parse_datetime(value)
    if not parsed:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(KST).strftime("%H:%M")


def build_news_items(
    rows,
    issue_links: dict[int, str] | None = None,
    ranked_issue_links: dict[int, list[dict]] | None = None,
) -> list[dict]:
    issue_links = issue_links or {}
    ranked_issue_links = ranked_issue_links or {}
    items = []
    for row in rows:
        text = row["raw_text"]
        combined = " ".join([row["title"] or "", row["summary_ko"] or "", row["analysis_ko"] or "", text])
        category = row["category"] or detect_category(combined)
        risk = row["risk_level"] or risk_level(combined)
        title = row["title"] or first_line(text)
        score = row["impact_score"] or impact_score(combined)
        score_breakdown = dimension_scores(row)

        items.append(
            {
                "id": row["id"],
                "date": row["news_date"],
                "source": row["source_channel"],
                "time": local_time(row["published_at"]),
                "publishedAt": row["published_at"],
                "telegramMessageId": row["telegram_message_id"],
                "sourceUrl": f"https://t.me/{row['source_channel']}/{row['telegram_message_id']}",
                "category": category,
                "issueId": issue_links.get(row["id"], f"{category}-live"),
                "issueLinks": ranked_issue_links.get(row["id"], []),
                "title": title,
                "rawText": text,
                "summary": row["summary_ko"] or compact(text),
                "analysis": row["analysis_ko"] or "AI 분석 대기 중입니다.",
                "impact": score,
                "scoreBreakdown": {
                    "market": {"label": "시장 영향도", "score": score_breakdown["market"]},
                    "geopolitics": {"label": "지정학 위험도", "score": score_breakdown["geopolitics"]},
                    "persistence": {"label": "지속성", "score": score_breakdown["persistence"]},
                    "spread": {"label": "확산 가능성", "score": score_breakdown["spread"]},
                },
                "risk": risk,
                "region": region_for(combined),
                "sentiment": row["sentiment"] or "미분류",
                "tags": detect_tags(combined),
                "hidden": bool(row["user_hidden"]) if "user_hidden" in row.keys() else False,
                "status": row["analysis_status"],
                "reason": row["analysis_reason"],
            }
        )
    return items


def build_daily_briefings(connection) -> dict:
    briefing_rows = connection.execute(
        """
        select briefing_date, title, summary_ko, key_points, top_regions, top_assets,
               avg_impact_score, max_risk_level
        from daily_briefings
        where briefing_date >= ?
        order by briefing_date desc
        """,
        (ANALYSIS_TARGET_START,),
    ).fetchall()
    briefings = {
        row["briefing_date"]: {
            "title": row["title"],
            "summary": row["summary_ko"],
            "keyPoints": json.loads(row["key_points"] or "[]"),
            "topRegions": json.loads(row["top_regions"] or "[]"),
            "topAssets": json.loads(row["top_assets"] or "[]"),
            "avgImpact": row["avg_impact_score"],
            "maxRisk": row["max_risk_level"],
        }
        for row in briefing_rows
    }

    count_rows = connection.execute(
        """
        select news_date, count(*) count
        from news_items
        where news_date >= ?
          and analysis_status in ('analyzed', 'queued', 'review', 'filtered')
        group by news_date
        order by news_date desc
        """,
        (ANALYSIS_TARGET_START,),
    ).fetchall()
    for row in count_rows:
        if row["news_date"] in briefings:
            continue
        briefings[row["news_date"]] = {
            "title": f"{row['news_date']} 수집 뉴스 {row['count']}건",
            "summary": "수집된 뉴스 중 AI 분석이 완료된 항목부터 브리핑에 반영됩니다.",
            "keyPoints": [],
            "topRegions": [],
            "topAssets": [],
            "avgImpact": None,
            "maxRisk": None,
        }

    return dict(sorted(briefings.items(), reverse=True))


def count_matches(rows, groups: dict[str, list[str]]) -> list[tuple[str, int]]:
    counts = []
    for name, keywords in groups.items():
        count = 0
        for row in rows:
            text = " ".join(
                [
                    row["raw_text"] or "",
                    row["title"] or "",
                    row["summary_ko"] or "",
                    row["analysis_ko"] or "",
                ]
            ).lower()
            if any(keyword.lower() in text for keyword in keywords):
                count += 1
        if count:
            counts.append((name, count))
    return sorted(counts, key=lambda item: item[1], reverse=True)


def build_issues(rows, connection=None) -> list[dict]:
    if connection is not None:
        stored_issues = get_issue_payload(connection)
        if stored_issues:
            return stored_issues

    issues = []
    for category, keywords in KEYWORDS.items():
        matched = []
        for row in rows:
            text = " ".join([row["raw_text"] or "", row["title"] or "", row["analysis_ko"] or ""]).lower()
            if row["category"] == category or any(keyword.lower() in text for keyword in keywords):
                matched.append(row)
        if not matched:
            continue

        dates = sorted({row["news_date"] for row in matched})
        sorted_rows = sorted(matched, key=lambda row: row["published_at"])[-4:]
        events = [
            {
                "date": row["news_date"][5:],
                "text": compact(row["title"] or row["summary_ko"] or row["raw_text"], 100),
            }
            for row in sorted_rows
        ]
        avg_impact = sum(row["impact_score"] or impact_score(row["raw_text"]) for row in matched) / len(matched)
        issues.append(
            {
                "id": f"{category}-live",
                "title": f"{CATEGORY_LABELS.get(category, category)} 흐름",
                "status": "확대" if len(matched) >= 8 else "관찰",
                "firstSeen": dates[0],
                "updatedAt": dates[-1],
                "impact": round(min(avg_impact, 9.5), 1),
                "summary": f"최근 수집·분석된 뉴스 {len(matched)}건이 {CATEGORY_LABELS.get(category, category)} 흐름과 연결됩니다.",
                "events": events,
            }
        )
    return sorted(issues, key=lambda item: item["impact"], reverse=True)


def build_asset_views(rows, connection=None) -> list[dict]:
    if connection is not None:
        stored_assets = get_asset_payload(connection)
        if stored_assets:
            return stored_assets

    views = []
    for name, count in count_matches(rows, ASSETS):
        impact = round(min(5 + count / 3, 9.4), 1)
        views.append(
            {
                "name": name,
                "type": "자산·섹터",
                "stance": "관찰 필요" if count < 5 else "뉴스 집중",
                "impact": impact,
                "summary": f"최근 뉴스 {count}건에서 {name} 관련 표현이 감지됐습니다.",
                "watch": ASSETS[name][:3],
            }
        )
    return views


def build_region_views(rows, connection=None) -> list[dict]:
    if connection is not None:
        stored_regions = get_region_payload(connection)
        if stored_regions:
            return stored_regions

    views = []
    for region, count in count_matches(rows, REGIONS):
        pressure = min(35 + count * 6, 95)
        views.append(
            {
                "region": region,
                "risk": "높음" if pressure >= 75 else "중간" if pressure >= 55 else "낮음",
                "pressure": pressure,
                "summary": f"최근 뉴스 {count}건이 {region} 관련 흐름으로 분류됐습니다.",
            }
        )
    return views


CALENDAR_SEED = [
    ("kr-gdp-2026-q2-advance", "한국 2분기 GDP 속보치", "KR", "growth", "high", "2026-07-23T08:00:00+09:00", "2026년 2분기", None, None, None, "%", "Bank of Korea", "https://www.bok.or.kr/portal/stats/statsPublictSchdul/listCldr.do?menuNo=200775", 1, "실질 국내총생산 속보치"),
    ("us-durable-goods-2026-06", "미국 6월 내구재 주문", "US", "growth", "medium", "2026-07-27T21:30:00+09:00", "2026년 6월", None, None, None, "%", "U.S. Census Bureau", "https://www.census.gov/economic-indicators/calendar-listview.html", 1, "운송 제외 주문과 핵심 자본재 주문 확인"),
    ("kr-skhynix-2026-q2", "SK하이닉스 2분기 실적", "KR", "earnings", "high", "2026-07-29T09:00:00+09:00", "2026년 2분기", None, None, None, None, "SK hynix Investor Relations", "https://www.skhynix.com/ir/UI-FR-IR01/", 1, "HBM 수요·메모리 가격·설비투자 지침이 핵심"),
    ("us-fomc-2026-07", "FOMC 금리 결정", "US", "central_bank", "high", "2026-07-30T03:00:00+09:00", "2026년 7월", "3.50~3.75", None, None, "%", "Federal Reserve", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", 1, "성명 발표 후 기자회견 예정"),
    ("us-meta-2026-q2", "Meta 2분기 실적 (미국 7/29 장후)", "US", "earnings", "high", "2026-07-30T05:30:00+09:00", "2026년 2분기", None, None, None, None, "Meta Investor Relations", "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-to-Announce-Second-Quarter-2026-Results/default.aspx", 1, "AI 자본지출·광고 매출·연간 비용 지침이 핵심"),
    ("us-microsoft-2026-q4", "Microsoft FY26 4분기 실적 (미국 7/29 장후)", "US", "earnings", "high", "2026-07-30T06:30:00+09:00", "FY2026 4분기", None, None, None, None, "Microsoft", "https://news.microsoft.com/source/2026/07/08/microsoft-announces-quarterly-earnings-release-date-68/", 1, "Azure 성장률과 AI 인프라 투자 지침이 핵심"),
    ("kr-samsung-2026-q2-final", "삼성전자 2분기 확정실적·컨퍼런스콜", "KR", "earnings", "high", "2026-07-30T10:00:00+09:00", "2026년 2분기", None, None, None, None, "Samsung Electronics Investor Relations", "https://www.samsung.com/sec/ir/reports-disclosures/notices/", 1, "반도체·HBM·파운드리 부문별 실적과 전망 확인"),
    ("us-gdp-2026-q2-advance", "미국 2분기 GDP 속보치", "US", "growth", "high", "2026-07-30T21:30:00+09:00", "2026년 2분기", None, None, None, "%", "U.S. Bureau of Economic Analysis", "https://www.bea.gov/news/schedule", 1, "연율 기준 속보치"),
    ("us-pce-2026-06", "미국 6월 PCE 물가", "US", "inflation", "high", "2026-07-30T21:30:00+09:00", "2026년 6월", None, None, None, "%", "U.S. Bureau of Economic Analysis", "https://www.bea.gov/news/schedule", 1, "개인소득·소비지출과 함께 발표"),
    ("us-eci-2026-q2", "미국 2분기 고용비용지수", "US", "labor", "medium", "2026-07-31T21:30:00+09:00", "2026년 2분기", None, None, None, "%", "U.S. Bureau of Labor Statistics", "https://www.bls.gov/schedule/", 1, "임금 압력 확인 지표"),
    ("us-amazon-2026-q2", "Amazon 2분기 실적 (미국 7/30 장후)", "US", "earnings", "high", "2026-07-31T06:00:00+09:00", "2026년 2분기", None, None, None, None, "Amazon Investor Relations", "https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-to-Webcast-Second-Quarter-2026-Financial-Results-Conference-Call/default.aspx", 1, "AWS 성장률·AI 투자·리테일 마진이 핵심"),
    ("us-ism-manufacturing-2026-07", "미국 7월 ISM 제조업 PMI", "US", "growth", "medium", "2026-08-03T23:00:00+09:00", "2026년 7월", None, None, None, "지수", "Institute for Supply Management", "https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/", 1, "신규주문·고용·가격지수 확인"),
    ("kr-cpi-2026-07", "한국 7월 소비자물가", "KR", "inflation", "high", "2026-08-04T08:00:00+09:00", "2026년 7월", None, None, None, "%", "국가데이터처", "https://mods.go.kr/cpiOaSchdlView.es?mid=b70203020000", 1, "전월비·전년비와 근원물가 확인"),
    ("us-jolts-2026-06", "미국 6월 JOLTS 구인", "US", "labor", "medium", "2026-08-04T23:00:00+09:00", "2026년 6월", None, None, None, "천건", "U.S. Bureau of Labor Statistics", "https://www.bls.gov/schedule/", 1, "구인·이직 흐름"),
    ("us-ism-services-2026-07", "미국 7월 ISM 서비스업 PMI", "US", "growth", "medium", "2026-08-05T23:00:00+09:00", "2026년 7월", None, None, None, "지수", "Institute for Supply Management", "https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/", 1, "서비스 수요·고용·가격지수 확인"),
    ("us-payroll-2026-07", "미국 7월 고용보고서", "US", "labor", "high", "2026-08-07T21:30:00+09:00", "2026년 7월", None, None, None, "천명", "U.S. Bureau of Labor Statistics", "https://www.bls.gov/schedule/news_release/empsit.htm", 1, "비농업고용·실업률·임금 동시 발표"),
    ("us-cpi-2026-07", "미국 7월 CPI", "US", "inflation", "high", "2026-08-12T21:30:00+09:00", "2026년 7월", None, None, None, "%", "U.S. Bureau of Labor Statistics", "https://www.bls.gov/schedule/2026/home.htm", 1, "헤드라인·근원 물가 동시 발표"),
    ("us-ppi-2026-07", "미국 7월 PPI", "US", "inflation", "high", "2026-08-13T21:30:00+09:00", "2026년 7월", None, None, None, "%", "U.S. Bureau of Labor Statistics", "https://www.bls.gov/schedule/2026/home.htm", 1, "최종수요 생산자물가"),
    ("us-retail-sales-2026-07", "미국 7월 소매판매", "US", "growth", "high", "2026-08-14T21:30:00+09:00", "2026년 7월", None, None, None, "%", "U.S. Census Bureau", "https://www.census.gov/economic-indicators/calendar-listview.html", 1, "헤드라인·자동차 제외·통제그룹 확인"),
    ("kr-bok-2026-08", "한국은행 금융통화위원회", "KR", "central_bank", "high", "2026-08-27T10:00:00+09:00", "2026년 8월", "2.75", None, None, "%", "Bank of Korea", "https://www.bok.or.kr/eng/bbs/E0000627/view.do?menuNo=400022&nttId=10094301", 1, "정책결정 시각은 변경될 수 있음"),
]


def seed_calendar_events(connection) -> None:
    connection.executemany(
        """insert or ignore into economic_calendar_events
        (event_id,title,country,category,importance,scheduled_at,reference_period,
         previous_value,forecast_value,actual_value,unit,source_name,source_url,is_confirmed,notes)
        values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        CALENDAR_SEED,
    )


def build_calendar_events(connection) -> list[dict]:
    rows = connection.execute(
        "select * from economic_calendar_events order by scheduled_at, importance desc, title"
    ).fetchall()
    return [
        {
            "id": row["event_id"], "title": row["title"], "country": row["country"],
            "category": row["category"], "importance": row["importance"],
            "scheduledAt": row["scheduled_at"], "timezone": row["timezone"],
            "status": row["status"], "period": row["reference_period"],
            "previous": row["previous_value"], "forecast": row["forecast_value"],
            "actual": row["actual_value"], "unit": row["unit"],
            "sourceName": row["source_name"], "sourceUrl": row["source_url"],
            "confirmed": bool(row["is_confirmed"]), "notes": row["notes"],
        }
        for row in rows
    ]


def bootstrap_payload() -> dict:
    with connect() as connection:
        seed_calendar_events(connection)
        rows = connection.execute(
            """
            select *
            from news_items
            where news_date >= ?
              and analysis_status in ('analyzed', 'queued', 'review', 'filtered')
              and coalesce(user_hidden, 0) = 0
            order by published_at desc
            limit 500
            """,
            (ANALYSIS_TARGET_START,),
        ).fetchall()

        issue_links = get_primary_issue_map(connection)
        ranked_issue_links = get_issue_links_map(connection)
        return {
            "dailyBriefings": build_daily_briefings(connection),
            "newsItems": build_news_items(rows, issue_links, ranked_issue_links),
            "issues": build_issues(rows, connection),
            "assetViews": build_asset_views(rows, connection),
            "regionViews": build_region_views(rows, connection),
            "situation": build_situation_payload(rows),
            "analysisStats": build_analysis_stats(connection),
            "aiStatus": build_ai_status(connection),
            "filterImprovement": build_filter_improvement(connection),
            "economicEvaluation": build_economic_evaluation(connection),
            "calendarEvents": build_calendar_events(connection),
            "sourceDocuments": build_source_documents(),
            "meta": build_meta_status(connection),
        }


def build_source_documents() -> list[dict]:
    database_path = ROOT_DIR / "data" / "insidertracking_catchup.sqlite3"
    if not database_path.exists():
        return []
    try:
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """select id,country,topic,title,published_at,source,source_url,factual_summary
                   from source_documents order by published_at desc limit 200"""
            ).fetchall()
        return [
            {
                "id": f"doc-{row['id']}", "country": row["country"], "topic": row["topic"],
                "title": row["title"], "publishedAt": row["published_at"], "source": row["source"],
                "sourceUrl": row["source_url"], "summary": row["factual_summary"], "document": True,
            }
            for row in rows
        ]
    except (sqlite3.Error, OSError):
        return []


def as_utc_iso(value: str | None) -> str | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace(" ", "T").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def latest_utc_iso(values: list[str | None]) -> str | None:
    normalized = [as_utc_iso(value) for value in values if value]
    return max(normalized) if normalized else None


def build_meta_status(connection) -> dict:
    daily_channel_url = telegram_daily_channel_url()
    latest_news = connection.execute(
        """
        select max(published_at) as latest_published_at,
               max(updated_at) as latest_updated_at
        from news_items
        where analysis_scope = 'analysis_target'
        """
    ).fetchone()
    latest_view = connection.execute(
        """
        select max(updated_at) as latest_view_updated_at
        from (
          select updated_at from daily_briefings
          union all
          select updated_at from issues
          union all
          select created_at as updated_at from asset_impacts
          union all
          select created_at as updated_at from region_risks
          union all
          select updated_at from ai_situation_state
        )
        """
    ).fetchone()
    manual_status = connection.execute(
        """
        select status, detail, last_event_at, updated_at
        from automation_status
        where service_name = ?
        """,
        (MANUAL_UPDATE_SERVICE,),
    ).fetchone()
    data_values = [
        latest_news["latest_published_at"] if latest_news else None,
        latest_news["latest_updated_at"] if latest_news else None,
        latest_view["latest_view_updated_at"] if latest_view else None,
    ]
    return {
        "lastUpdatedAt": latest_utc_iso(data_values),
        "latestNewsAt": as_utc_iso(latest_news["latest_published_at"] if latest_news else None),
        "latestDbUpdateAt": as_utc_iso(latest_news["latest_updated_at"] if latest_news else None),
        "latestViewUpdateAt": as_utc_iso(latest_view["latest_view_updated_at"] if latest_view else None),
        "telegramDailyChannelUrl": daily_channel_url,
        "manualUpdate": {
            "running": manual_status["status"] in {"queued", "collecting", "reconciling", "analyzing", "rebuilding"}
            if manual_status
            else False,
            "status": manual_status["status"] if manual_status else "idle",
            "detail": manual_status["detail"] if manual_status else None,
            "lastEventAt": as_utc_iso(manual_status["last_event_at"] if manual_status else None),
            "updatedAt": as_utc_iso(manual_status["updated_at"] if manual_status else None),
        },
    }


def build_economic_evaluation(connection) -> dict:
    excluded_placeholders = ",".join("?" for _ in NON_ECONOMIC_PROBES)
    excluded_params = tuple(NON_ECONOMIC_PROBES)
    summary = connection.execute(
        f"""select count(a.id) as analysis_count, avg(s.total_score) as average_score
           from economic_analyses a left join economic_analysis_scores s on s.analysis_id=a.id
           where lower(trim(a.question)) not in ({excluded_placeholders})""",
        excluded_params,
    ).fetchone()
    feedback = connection.execute(
        f"""select count(f.analysis_id) as total,
           sum(case when rating=1 then 1 else 0 end) as positive,
           sum(case when rating=-1 then 1 else 0 end) as negative
           from economic_analysis_feedback f
           join economic_analyses a on a.id=f.analysis_id
           where lower(trim(a.question)) not in ({excluded_placeholders})""",
        excluded_params,
    ).fetchone()
    forecasts = connection.execute(
        """select count(*) as total,
           sum(case when status='open' then 1 else 0 end) as open_count,
           sum(case when status='evaluated' then 1 else 0 end) as evaluated_count,
           avg(case when status='evaluated' then abs(base_error_pct) end) as mean_abs_error
           from economic_forecasts"""
    ).fetchone()
    outcomes = connection.execute(
        """select outcome_bucket,count(*) as count from economic_forecasts
           where status='evaluated' group by outcome_bucket"""
    ).fetchall()
    recent = connection.execute(
        f"""select a.id,a.question,a.provider,a.model,a.created_at,s.total_score,f.rating
           from economic_analyses a
           left join economic_analysis_scores s on s.analysis_id=a.id
           left join economic_analysis_feedback f on f.analysis_id=a.id
           where lower(trim(a.question)) not in ({excluded_placeholders})
           order by a.id desc limit 10""",
        excluded_params,
    ).fetchall()
    score_checks = connection.execute(
        f"""select s.checks from economic_analysis_scores s
            join economic_analyses a on a.id=s.analysis_id
            where lower(trim(a.question)) not in ({excluded_placeholders})""",
        excluded_params,
    ).fetchall()
    weakness_counts = {}
    for row in score_checks:
        try:
            checks = json.loads(row["checks"] or "{}")
        except json.JSONDecodeError:
            checks = {}
        for name, passed in checks.items():
            if not passed:
                weakness_counts[name] = weakness_counts.get(name, 0) + 1
    improvement_rows = connection.execute(
        f"""select q.id,q.analysis_id,q.issue_type,q.severity,q.detail,q.created_at,a.question
           from economic_improvement_queue q
           left join economic_analyses a on a.id=q.analysis_id
           where q.status='open' and lower(trim(coalesce(a.question,''))) not in ({excluded_placeholders})
           order by case q.severity when 'high' then 1 when 'medium' then 2 else 3 end,
                    q.created_at desc limit 20""",
        excluded_params,
    ).fetchall()
    feedback_total = feedback["total"] or 0
    return {
        "analysisCount": summary["analysis_count"] or 0,
        "averageScore": round(summary["average_score"] or 0, 1),
        "feedback": {
            "total": feedback_total,
            "positive": feedback["positive"] or 0,
            "negative": feedback["negative"] or 0,
            "helpfulRate": round((feedback["positive"] or 0) / feedback_total * 100, 1) if feedback_total else 0,
        },
        "forecasts": {
            "total": forecasts["total"] or 0,
            "open": forecasts["open_count"] or 0,
            "evaluated": forecasts["evaluated_count"] or 0,
            "meanAbsoluteError": round(forecasts["mean_abs_error"] or 0, 2),
            "outcomes": {row["outcome_bucket"]: row["count"] for row in outcomes},
        },
        "recent": [
            {
                "id": row["id"], "question": row["question"], "provider": row["provider"],
                "model": row["model"], "createdAt": row["created_at"],
                "score": row["total_score"], "rating": row["rating"],
            }
            for row in recent
        ],
        "weaknesses": [
            {"key": key, "count": count}
            for key, count in sorted(weakness_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "improvementQueue": [
            {
                "id": row["id"], "analysisId": row["analysis_id"],
                "type": row["issue_type"], "severity": row["severity"],
                "detail": row["detail"], "question": row["question"],
                "createdAt": row["created_at"],
            }
            for row in improvement_rows
        ],
    }


def start_manual_update() -> dict:
    update_status(MANUAL_UPDATE_SERVICE, "queued", "manual update requested")
    return {"ok": True, "started": True, "status": "queued"}


def ops_api_key() -> str:
    load_dotenv()
    return os.getenv(OPS_API_KEY_ENV, "").strip()


def is_valid_ops_key(provided: str | None, expected: str | None = None) -> bool:
    configured = (ops_api_key() if expected is None else expected).strip()
    candidate = (provided or "").strip()
    return bool(configured and candidate) and hmac.compare_digest(candidate, configured)


def build_ops_status(connection) -> dict:
    automation = get_status_payload(connection)
    analysis_stats = build_analysis_stats(connection)
    ai_status = build_ai_status(connection)
    filter_status = build_filter_improvement(connection)
    status_by_service = {item["service"]: item for item in automation}
    counts = analysis_stats.get("byStatus", {})
    return {
        "ok": True,
        "collector": status_by_service.get("telegram_live_collector", {"status": "unknown"}),
        "analysisWorker": status_by_service.get("ai_analysis_worker", {"status": "unknown"}),
        "manualUpdate": status_by_service.get(MANUAL_UPDATE_SERVICE, {"status": "idle"}),
        "filterAudit": status_by_service.get("filter_audit_worker", {"status": "unknown"}),
        "automationStatus": automation,
        "analysis": {
            "queued": int(counts.get("queued", 0) or 0),
            "failed": int(counts.get("failed", 0) or 0),
            "deferred": int(counts.get("deferred", 0) or 0),
            "analyzed": int(counts.get("analyzed", 0) or 0),
            "filtered": int(counts.get("filtered", 0) or 0),
            "stats": analysis_stats,
        },
        "lastAnalyzedAt": analysis_stats.get("queueEstimate", {}).get("lastAnalyzedAt"),
        "queueEstimate": analysis_stats.get("queueEstimate", {}),
        "aiStatus": ai_status,
        "filterAuditStatus": filter_status,
    }


def build_ops_news(connection, status: str | None, limit: int, offset: int, min_priority: float | None = None, content_type: str | None = None) -> list[dict]:
    clauses = ["analysis_scope = 'analysis_target'"]
    params: list[object] = []
    if status:
        clauses.append("analysis_status = ?")
        params.append(status)
    if min_priority is not None:
        clauses.append("analysis_priority >= ?")
        params.append(min_priority)
    if content_type:
        clauses.append("content_type = ?")
        params.append(content_type)
    params.extend([limit, offset])
    rows = connection.execute(
        f"""select id, source_channel, published_at, title, raw_text, analysis_status,
                   analysis_priority, analysis_reason, impact_score, sentiment, risk_level, category,
                   content_type, user_hidden, updated_at
            from news_items where {' and '.join(clauses)}
            order by published_at desc, id desc limit ? offset ?""",
        tuple(params),
    ).fetchall()
    return [
        {
            "id": row["id"], "sourceChannel": row["source_channel"], "publishedAt": row["published_at"],
            "title": row["title"] or compact(row["raw_text"], 180), "rawText": compact(row["raw_text"], 500),
            "analysisStatus": row["analysis_status"], "analysisPriority": row["analysis_priority"],
            "analysisReason": row["analysis_reason"], "impactScore": row["impact_score"],
            "sentiment": row["sentiment"], "riskLevel": row["risk_level"], "category": row["category"],
            "contentType": row["content_type"], "hidden": bool(row["user_hidden"]), "updatedAt": row["updated_at"],
        }
        for row in rows
    ]


def requeue_news_item(connection, news_id: int) -> bool:
    row = connection.execute("select id from news_items where id = ?", (news_id,)).fetchone()
    if not row:
        return False
    connection.execute(
        """update news_items set analysis_status='queued', summary_ko=null, analysis_ko=null,
           impact_score=null, sentiment=null, risk_level=null, category=null,
           analysis_reason='user requested reanalysis', user_hidden=0, updated_at=current_timestamp
           where id=?""",
        (news_id,),
    )
    return True


def build_analysis_stats(connection) -> dict:
    status_rows = connection.execute(
        """
        select analysis_status, count(*) as count
        from news_items
        where analysis_scope = 'analysis_target'
        group by analysis_status
        order by count desc
        """
    ).fetchall()
    type_rows = connection.execute(
        """
        select content_type, count(*) as count
        from news_items
        where content_type is not null
          and analysis_scope = 'analysis_target'
        group by content_type
        order by count desc
        """
    ).fetchall()
    throughput = connection.execute(
        """
        select
          sum(case when updated_at >= datetime('now', '-1 hour') then 1 else 0 end) as last_hour,
          sum(case when updated_at >= datetime('now', '-6 hours') then 1 else 0 end) as last_6_hours,
          sum(case when updated_at >= datetime('now', '-24 hours') then 1 else 0 end) as last_24_hours,
          max(updated_at) as last_analyzed_at
        from news_items
        where analysis_scope = 'analysis_target'
          and analysis_status = 'analyzed'
        """
    ).fetchone()
    worker = connection.execute(
        """select status, detail, updated_at
           from automation_status where service_name = 'ai_analysis_worker'"""
    ).fetchone()
    by_status = {row["analysis_status"]: row["count"] for row in status_rows}
    queued = int(by_status.get("queued", 0) or 0)
    last_hour = int(throughput["last_hour"] or 0)
    last_6_hours = int(throughput["last_6_hours"] or 0)
    last_24_hours = int(throughput["last_24_hours"] or 0)
    if last_hour >= 2:
        rate_per_hour, rate_window = float(last_hour), "1h"
    elif last_6_hours >= 3:
        rate_per_hour, rate_window = last_6_hours / 6.0, "6h"
    elif last_24_hours:
        rate_per_hour, rate_window = last_24_hours / 24.0, "24h"
    else:
        rate_per_hour, rate_window = 0.0, "none"
    eta_minutes = round((queued / rate_per_hour) * 60) if queued and rate_per_hour else (0 if not queued else None)
    worker_status = worker["status"] if worker else "unknown"
    paused = worker_status in {"deferred", "failed", "disabled"}
    worker_detail = (worker["detail"] or "")[:240] if worker else ""
    retry_seconds = None
    retry_remaining_seconds = None
    retry_remaining_minutes = None
    retry_at = None
    retry_match = re.search(r"retry\s+in\s+(\d+)s", worker_detail, re.IGNORECASE)
    if retry_match and worker and worker["updated_at"]:
        retry_seconds = int(retry_match.group(1))
        retry_clock = connection.execute(
            """
            select
              cast(strftime('%s', 'now') as integer) as now_epoch,
              cast(strftime('%s', ?) as integer) as updated_epoch,
              datetime(?, '+' || ? || ' seconds') as retry_at
            """,
            (worker["updated_at"], worker["updated_at"], retry_seconds),
        ).fetchone()
        if retry_clock and retry_clock["updated_epoch"] is not None:
            elapsed_seconds = max(0, int(retry_clock["now_epoch"]) - int(retry_clock["updated_epoch"]))
            retry_remaining_seconds = max(0, retry_seconds - elapsed_seconds)
            retry_remaining_minutes = (retry_remaining_seconds + 59) // 60
            retry_at = retry_clock["retry_at"]
    return {
        "byStatus": by_status,
        "byType": {row["content_type"]: row["count"] for row in type_rows},
        "queueEstimate": {
            "queued": queued,
            "ratePerHour": round(rate_per_hour, 1),
            "rateWindow": rate_window,
            "etaMinutes": eta_minutes,
            "lowerMinutes": round(eta_minutes * 0.8) if eta_minutes is not None else None,
            "upperMinutes": round(eta_minutes * 1.3) if eta_minutes is not None else None,
            "status": "complete" if not queued else ("paused" if paused else "running"),
            "conditional": bool(queued and paused),
            "workerStatus": worker_status,
            "workerDetail": worker_detail,
            "retrySeconds": retry_seconds,
            "retryRemainingSeconds": retry_remaining_seconds,
            "retryRemainingMinutes": retry_remaining_minutes,
            "retryAt": retry_at,
            "lastAnalyzedAt": throughput["last_analyzed_at"],
            "workerUpdatedAt": worker["updated_at"] if worker else None,
        },
    }


def build_filter_improvement(connection) -> dict:
    row = connection.execute(
        """
        select status, detail, processed_count, error_count, updated_at
        from automation_status
        where service_name = 'filter_audit_worker'
        """
    ).fetchone()
    if not row:
        return {
            "status": "unknown",
            "detail": "필터 감사 기록이 아직 없습니다.",
            "recommendations": ["filter_audit_worker가 실행되면 누락 후보를 자동으로 검사합니다."],
        }

    detail = row["detail"] or ""
    recommendations = []
    if row["status"] == "attention":
        recommendations.append("누락 후보가 남아 있습니다. 최근 텔레그램 원문과 수집 DB를 다시 대조해야 합니다.")
        recommendations.append("반복 누락되는 키워드가 있으면 classifier.py의 뉴스 판별 키워드에 추가하는 것이 좋습니다.")
    elif row["status"] == "repaired":
        recommendations.append("누락 후보를 자동 복구했습니다. 다음 감사에서 remaining이 0으로 유지되는지 확인합니다.")
    else:
        recommendations.append("최근 감사 기준 누락 후보가 없거나 자동 복구가 완료된 상태입니다.")

    if "missing" in detail or "repaired" in detail:
        recommendations.append("제외 메시지는 DB에 저장하지 않고, 뉴스로 판단되는 누락 후보만 복구합니다.")
    if "ignored_types" in detail:
        recommendations.append("ignored_types 분포를 보며 홍보·짧은 코멘트·링크 단독 메시지가 과도하게 섞이는지 점검합니다.")
    if "missing_types" in detail and "missing_types [-]" not in detail:
        recommendations.append("missing_types가 반복되면 해당 content_type의 판별 조건을 완화하거나 키워드를 보강합니다.")

    return {
        "status": row["status"],
        "detail": detail,
        "processedCount": row["processed_count"],
        "errorCount": row["error_count"],
        "updatedAt": row["updated_at"],
        "recommendations": recommendations,
    }


def build_ai_status(connection) -> dict:
    scope_rows = connection.execute(
        """
        select analysis_scope, analysis_status, count(*) as count
        from news_items
        group by analysis_scope, analysis_status
        order by analysis_scope, analysis_status
        """
    ).fetchall()
    context_rows = connection.execute(
        """
        select period_start, period_end, item_count, status
        from ai_context_batches
        order by period_start
        """
    ).fetchall()
    situation_row = connection.execute(
        """
        select state_text, source_count, last_news_item_id, updated_at
        from ai_situation_state
        where id = 1
        """
    ).fetchone()
    alert_rows = connection.execute(
        """
        select status, count(*) as count
        from alert_notifications
        group by status
        order by status
        """
    ).fetchall()
    push_row = connection.execute(
        """
        select
          count(*) as total_count,
          sum(case when active = 1 then 1 else 0 end) as active_count
        from push_subscriptions
        """
    ).fetchone()
    settings = load_settings()

    by_scope = {}
    for row in scope_rows:
        scope = row["analysis_scope"] or "unscoped"
        by_scope.setdefault(scope, {})[row["analysis_status"]] = row["count"]

    return {
        "targetStart": ANALYSIS_TARGET_START,
        "byScope": by_scope,
        "situationState": {
            "text": situation_row["state_text"] if situation_row else "아직 누적 상황판단이 없습니다.",
            "sourceCount": situation_row["source_count"] if situation_row else 0,
            "lastNewsItemId": situation_row["last_news_item_id"] if situation_row else None,
            "updatedAt": situation_row["updated_at"] if situation_row else None,
        },
        "contextBatches": [
            {
                "periodStart": row["period_start"],
                "periodEnd": row["period_end"],
                "itemCount": row["item_count"],
                "status": row["status"],
            }
            for row in context_rows
        ],
        "automationStatus": get_status_payload(connection),
        "alertNotifications": {row["status"]: row["count"] for row in alert_rows},
        "webPush": {
            "configured": bool(settings.vapid_public_key and settings.vapid_private_key),
            "publicKey": settings.vapid_public_key,
            "subscriptions": {
                "total": push_row["total_count"] if push_row else 0,
                "active": push_row["active_count"] if push_row and push_row["active_count"] is not None else 0,
            },
        },
    }


class Handler(BaseHTTPRequestHandler):
    def configured_access_password(self) -> str:
        return site_access_password()

    def provided_access_token(self) -> str:
        return parse_cookies(self.headers.get("Cookie")).get(AUTH_COOKIE, "")

    def client_key(self) -> str:
        address = self.client_address[0] if self.client_address else "unknown"
        return client_fingerprint(address)

    def authenticated_client_key(self) -> str:
        token = self.provided_access_token()
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16] if token else self.client_key()

    def is_authenticated(self) -> bool:
        password = self.configured_access_password()
        if not password:
            return False
        return validate_site_access_token(self.provided_access_token(), password)

    def auth_cookie(self, token: str, max_age: int = AUTH_SESSION_SECONDS) -> str:
        return (
            f"{AUTH_COOKIE}={token}; Path=/; SameSite=Strict; HttpOnly; "
            f"Max-Age={max_age}{cookie_security_suffix()}"
        )

    def send_unauthorized(self) -> None:
        self.send_json(
            {
                "ok": False,
                "error": "authentication required",
                "authRequired": True,
            },
            status=401,
            extra_headers={
                "Set-Cookie": self.auth_cookie("", max_age=0)
            },
        )

    def require_api_auth(self, request_path: str) -> bool:
        if request_path in {"/api/auth/status", "/api/auth/login"}:
            return True
        if self.is_authenticated():
            return True
        self.send_unauthorized()
        return False

    def require_ops_auth(self) -> bool:
        if not is_valid_ops_key(self.headers.get("X-Eminai-Ops-Key", "")):
            self.send_json({"ok": False, "error": "machine authentication required"}, status=401)
            return False
        return True

    def handle_ops_get(self, request_url) -> bool:
        if not self.require_ops_auth():
            return True
        retry_after = request_retry_after("ops", self.client_key(), OPS_RATE_LIMIT, OPS_RATE_WINDOW_SECONDS)
        if retry_after:
            self.send_rate_limited(retry_after)
            return True
        try:
            init_db()
            if request_url.path == "/api/ops/status":
                with connect() as connection:
                    self.send_json(build_ops_status(connection))
                return True
            if request_url.path == "/api/ops/news":
                query = parse_qs(request_url.query)
                status = (query.get("status") or [None])[0]
                allowed_statuses = {"pending", "queued", "analyzed", "review", "filtered", "failed", "deferred", "ignored"}
                if status and status not in allowed_statuses:
                    raise RequestValidationError("invalid status")
                limit = int((query.get("limit") or ["50"])[0])
                offset = int((query.get("offset") or ["0"])[0])
                if not 1 <= limit <= 200 or offset < 0:
                    raise RequestValidationError("invalid pagination")
                min_priority_value = (query.get("min_priority") or [None])[0]
                min_priority = float(min_priority_value) if min_priority_value not in (None, "") else None
                content_type = (query.get("content_type") or [None])[0]
                with connect() as connection:
                    items = build_ops_news(connection, status, limit, offset, min_priority, content_type)
                self.send_json({"ok": True, "items": items, "limit": limit, "offset": offset})
                return True
            self.send_json({"ok": False, "error": "not found"}, status=404)
            return True
        except Exception as error:
            self.send_exception(error, "ops request failed")
            return True

    def handle_ops_post(self, request_path: str) -> bool:
        if not self.require_ops_auth():
            return True
        retry_after = request_retry_after("ops", self.client_key(), OPS_RATE_LIMIT, OPS_RATE_WINDOW_SECONDS)
        if retry_after:
            self.send_rate_limited(retry_after)
            return True
        try:
            if request_path == "/api/ops/manual-update":
                self.send_json(start_manual_update())
                return True
            if request_path == "/api/ops/reanalyze":
                payload = self.read_json_body()
                try:
                    news_id = int(payload.get("id") or 0)
                except (TypeError, ValueError) as error:
                    raise RequestValidationError("id must be an integer") from error
                if news_id <= 0:
                    raise RequestValidationError("missing news id")
                init_db()
                with connect() as connection:
                    if not requeue_news_item(connection, news_id):
                        self.send_json({"ok": False, "error": "news item not found"}, status=404)
                        return True
                self.send_json({"ok": True, "id": news_id, "status": "queued"})
                return True
            self.send_json({"ok": False, "error": "not found"}, status=404)
            return True
        except Exception as error:
            self.send_exception(error, "ops request failed")
            return True

    def do_GET(self) -> None:
        request_url = urlparse(self.path)
        if request_url.path == "/api/auth/status":
            retry_after = request_retry_after("auth-status", self.client_key(), limit=120, window_seconds=60)
            if retry_after:
                self.send_rate_limited(retry_after)
                return
            authenticated = self.is_authenticated()
            provided_token = self.provided_access_token() if authenticated else ""
            self.send_json(
                {
                    "ok": True,
                    "authRequired": True,
                    "authenticated": authenticated,
                    "expiresAt": access_expiry_iso(provided_token),
                    "sessionHours": AUTH_SESSION_SECONDS // 3600,
                }
            )
            return
        if request_url.path.startswith("/api/ops/"):
            self.handle_ops_get(request_url)
            return
        if request_url.path.startswith("/api/") and not self.require_api_auth(request_url.path):
            return
        if request_url.path.startswith("/api/"):
            retry_after = request_retry_after(
                "api-read", self.authenticated_client_key(), limit=300, window_seconds=60
            )
            if retry_after:
                self.send_rate_limited(retry_after)
                return
        if request_url.path in {"/api/market/chart", "/api/market/indicators"}:
            retry_after = request_retry_after(
                "market-data", self.authenticated_client_key(), limit=60, window_seconds=60
            )
            if retry_after:
                self.send_rate_limited(retry_after)
                return
        if request_url.path == "/api/bootstrap":
            self.send_json(bootstrap_payload())
            return
        if request_url.path == "/api/market/assets":
            self.send_json({"assets": asset_catalog()})
            return
        if request_url.path == "/api/market/indicators":
            query = parse_qs(request_url.query)
            force = (query.get("refresh") or ["0"])[0] == "1"
            self.send_json({"ok": True, **get_indicator_dashboard(force=force)})
            return
        if request_url.path == "/api/market/chart":
            try:
                query = parse_qs(request_url.query)
                result = get_market_chart(
                    (query.get("symbol") or ["^GSPC"])[0],
                    (query.get("range") or ["6mo"])[0],
                    (query.get("interval") or ["1d"])[0],
                )
                self.send_json({"ok": True, **result})
            except Exception as error:
                self.send_exception(error, "market chart request failed")
            return
        if request_url.path == "/api/push/public-key":
            settings = load_settings()
            self.send_json(
                {
                    "configured": bool(settings.vapid_public_key and settings.vapid_private_key),
                    "publicKey": settings.vapid_public_key,
                }
            )
            return
        if request_url.path == "/api/news/deep-analysis":
            try:
                query = parse_qs(request_url.query)
                news_id = int((query.get("id") or ["0"])[0])
                with connect() as connection:
                    result = get_deep_analysis(connection, news_id)
                self.send_json({"ok": True, "deepAnalysis": result})
            except Exception as error:
                self.send_exception(error, "deep analysis lookup failed")
            return
        if request_url.path == "/api/news/translations":
            try:
                query = parse_qs(request_url.query)
                ids = [
                    int(value)
                    for value in ",".join(query.get("ids") or [""]).split(",")
                    if value.strip().isdigit()
                ][:80]
                with connect() as connection:
                    translations = get_translations(connection, ids, "en")
                self.send_json({"ok": True, "translations": list(translations.values())})
            except Exception as error:
                self.send_exception(error, "translation lookup failed")
            return

        self.serve_static()

    def do_POST(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path == "/api/auth/login":
            if not self.same_origin_request():
                self.send_json({"ok": False, "error": "cross-origin request blocked"}, status=403)
                return
            self.handle_auth_login()
            return
        if request_path == "/api/auth/logout":
            if not self.same_origin_request():
                self.send_json({"ok": False, "error": "cross-origin request blocked"}, status=403)
                return
            self.handle_auth_logout()
            return
        if request_path.startswith("/api/ops/"):
            self.handle_ops_post(request_path)
            return
        if request_path.startswith("/api/") and not self.require_api_auth(request_path):
            return
        if request_path.startswith("/api/") and not self.same_origin_request():
            self.send_json({"ok": False, "error": "cross-origin request blocked"}, status=403)
            return
        if request_path.startswith("/api/"):
            retry_after = request_retry_after(
                "api-write", self.authenticated_client_key(), limit=120, window_seconds=60
            )
            if retry_after:
                self.send_rate_limited(retry_after)
                return
        if request_path in {
            "/api/economic-chat",
            "/api/news/deep-analysis",
            "/api/news/translations",
        }:
            retry_after = request_retry_after(
                "llm", self.authenticated_client_key(), LLM_RATE_LIMIT, LLM_RATE_WINDOW_SECONDS
            )
            if retry_after:
                self.send_rate_limited(retry_after)
                return
        if request_path == "/api/push/subscribe":
            self.handle_push_subscribe()
            return
        if request_path == "/api/push/unsubscribe":
            self.handle_push_unsubscribe()
            return
        if request_path == "/api/news/action":
            self.handle_news_action()
            return
        if request_path == "/api/news/deep-analysis":
            self.handle_news_deep_analysis()
            return
        if request_path == "/api/news/translations":
            self.handle_news_translations()
            return
        if request_path == "/api/manual-update":
            self.send_json(start_manual_update())
            return
        if request_path == "/api/economic-chat":
            self.handle_economic_chat()
            return
        if request_path == "/api/economic-chat/feedback":
            self.handle_economic_feedback()
            return
        self.send_json({"ok": False, "error": "not found"}, status=404)

    def same_origin_request(self) -> bool:
        host = self.headers.get("Host", "").split(",", 1)[0].strip()
        if not host:
            return False
        origin = self.headers.get("Origin", "").strip()
        if origin:
            parsed = urlparse(origin)
            return parsed.scheme in {"http", "https"} and parsed.netloc == host
        referer = self.headers.get("Referer", "").strip()
        if referer:
            parsed = urlparse(referer)
            return parsed.scheme in {"http", "https"} and parsed.netloc == host
        return True

    def send_rate_limited(self, retry_after: int) -> None:
        self.send_json(
            {"ok": False, "error": "too many requests", "retryAfterSeconds": retry_after},
            status=429,
            extra_headers={"Retry-After": str(retry_after)},
        )

    def read_json_body(self) -> dict:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise RequestValidationError("application/json required", status=415)
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError as error:
            raise RequestValidationError("invalid content length") from error
        if length <= 0:
            return {}
        if length > MAX_JSON_BODY_BYTES:
            raise RequestValidationError("request body too large", status=413)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RequestValidationError("invalid JSON body") from error
        if not isinstance(payload, dict):
            raise RequestValidationError("JSON object required")
        return payload

    def handle_auth_login(self) -> None:
        try:
            expected_password = site_access_password()
            if not expected_password:
                LOGGER.error("authentication configuration missing")
                self.send_json({"ok": False, "error": "authentication unavailable"}, status=503)
                return

            client_key = self.client_key()
            retry_after = request_retry_after("login-attempt", client_key, limit=30, window_seconds=60)
            if retry_after:
                LOGGER.warning("login rate limited client=%s", client_key)
                self.send_rate_limited(retry_after)
                return
            retry_after = login_retry_after(client_key)
            if retry_after:
                LOGGER.warning("login blocked client=%s", client_key)
                self.send_rate_limited(retry_after)
                return

            payload = self.read_json_body()
            password = str(payload.get("password") or "")
            if not hmac.compare_digest(password, expected_password):
                locked_for = record_login_failure(client_key)
                LOGGER.warning("login failed client=%s locked=%s", client_key, bool(locked_for))
                if locked_for:
                    self.send_rate_limited(locked_for)
                    return
                self.send_json({"ok": False, "error": "invalid password"}, status=401)
                return

            clear_login_failures(client_key)
            cleanup_expired_sessions()
            token = site_access_token(expected_password)
            expires_at = access_expiry_iso(token)
            LOGGER.info("login succeeded client=%s", client_key)
            self.send_json(
                {
                    "ok": True,
                    "authRequired": True,
                    "expiresAt": expires_at,
                    "sessionHours": AUTH_SESSION_SECONDS // 3600,
                },
                extra_headers={
                    "Set-Cookie": self.auth_cookie(token)
                },
            )
        except Exception as error:
            self.send_exception(error, "login request failed")

    def handle_auth_logout(self) -> None:
        token = self.provided_access_token()
        revoke_site_access_token(token)
        LOGGER.info("logout client=%s", self.client_key())
        self.send_json(
            {"ok": True},
            extra_headers={"Set-Cookie": self.auth_cookie("", max_age=0)},
        )

    def handle_push_subscribe(self) -> None:
        try:
            payload = self.read_json_body()
            init_db()
            with connect() as connection:
                subscription_id = save_push_subscription(connection, payload)
            self.send_json({"ok": True, "subscriptionId": subscription_id})
        except Exception as error:
            self.send_exception(error, "push subscription failed")

    def handle_economic_chat(self) -> None:
        try:
            payload = self.read_json_body()
            question = str(payload.get("question") or "")
            history = payload.get("history") or []
            if not isinstance(history, list):
                raise ValueError("history must be a list")
            with connect() as connection:
                result = answer_economic_question(connection, question, history)
            self.send_json({"ok": True, **result})
        except Exception as error:
            self.send_exception(error, "economic analysis failed")

    def handle_economic_feedback(self) -> None:
        try:
            payload = self.read_json_body()
            analysis_id = int(payload.get("analysisId") or 0)
            rating = int(payload.get("rating") or 0)
            note = str(payload.get("note") or "")[:1000]
            if analysis_id <= 0 or rating not in {-1, 1}:
                raise ValueError("invalid analysis feedback")
            with connect() as connection:
                connection.execute(
                    """insert into economic_analysis_feedback(analysis_id,rating,note)
                       values (?,?,?)
                       on conflict(analysis_id) do update set rating=excluded.rating,
                         note=excluded.note,updated_at=current_timestamp""",
                    (analysis_id, rating, note),
                )
                queue_key = f"analysis:{analysis_id}:feedback"
                if rating == -1:
                    connection.execute(
                        """insert into economic_improvement_queue
                          (queue_key,analysis_id,issue_type,severity,detail)
                          values (?,?, 'negative_feedback','high',?)
                          on conflict(queue_key) do update set detail=excluded.detail,
                            severity='high',status='open',updated_at=current_timestamp""",
                        (queue_key, analysis_id, note or "사용자가 개선 필요로 평가했습니다."),
                    )
                else:
                    connection.execute(
                        "update economic_improvement_queue set status='resolved',updated_at=current_timestamp where queue_key=?",
                        (queue_key,),
                    )
            self.send_json({"ok": True, "analysisId": analysis_id, "rating": rating})
        except Exception as error:
            self.send_exception(error, "feedback request failed")

    def handle_push_unsubscribe(self) -> None:
        try:
            payload = self.read_json_body()
            endpoint = payload.get("endpoint", "")
            with connect() as connection:
                connection.execute(
                    """
                    update push_subscriptions
                    set active = 0,
                        updated_at = current_timestamp
                    where endpoint = ?
                    """,
                    (endpoint,),
                )
            self.send_json({"ok": True})
        except Exception as error:
            self.send_exception(error, "push unsubscribe failed")

    def handle_news_action(self) -> None:
        try:
            payload = self.read_json_body()
            news_id = int(payload.get("id") or 0)
            action = payload.get("action")
            if news_id <= 0:
                raise ValueError("missing news id")

            with connect() as connection:
                if action == "reanalyze":
                    requeue_news_item(connection, news_id)
                elif action == "exclude":
                    connection.execute(
                        """
                        update news_items
                        set analysis_status = 'ignored',
                            analysis_reason = 'user excluded from dashboard',
                            user_hidden = 1,
                            updated_at = current_timestamp
                        where id = ?
                        """,
                        (news_id,),
                    )
                elif action == "hide":
                    connection.execute(
                        """
                        update news_items
                        set user_hidden = 1,
                            user_note = 'hidden from dashboard',
                            updated_at = current_timestamp
                        where id = ?
                        """,
                        (news_id,),
                    )
                else:
                    raise ValueError("unknown action")
            self.send_json({"ok": True, "action": action, "id": news_id})
        except Exception as error:
            self.send_exception(error, "news action failed")

    def handle_news_deep_analysis(self) -> None:
        try:
            payload = self.read_json_body()
            news_id = int(payload.get("id") or 0)
            refresh = bool(payload.get("refresh"))
            if news_id <= 0:
                raise ValueError("missing news id")
            init_db()
            with connect() as connection:
                result = generate_deep_analysis(connection, news_id, refresh=refresh)
            self.send_json({"ok": True, "deepAnalysis": result})
        except Exception as error:
            self.send_exception(error, "deep analysis generation failed")

    def handle_news_translations(self) -> None:
        try:
            payload = self.read_json_body()
            ids = payload.get("ids") or []
            if not isinstance(ids, list):
                raise ValueError("ids must be a list")
            limit_new = max(1, min(int(payload.get("limitNew") or 8), 12))
            init_db()
            with connect() as connection:
                translations = translate_news_items(connection, ids, lang="en", limit_new=limit_new)
            self.send_json({"ok": True, "translations": list(translations.values())})
        except Exception as error:
            self.send_exception(error, "translation request failed")

    def send_exception(self, error: Exception, public_error: str = "request failed") -> None:
        status = error.status if isinstance(error, RequestValidationError) else 400
        message = str(error) if isinstance(error, RequestValidationError) else public_error
        LOGGER.exception(
            "request error client=%s method=%s path=%s",
            self.client_key(),
            self.command,
            urlparse(self.path).path,
        )
        self.send_json({"ok": False, "error": message}, status=status)

    def send_security_headers(self, *, private: bool) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("Cache-Control", "no-store" if private else "no-cache")
        if cookie_security_suffix():
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    def send_json(self, payload: dict, status: int = 200, extra_headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_security_headers(private=True)
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def serve_static(self) -> None:
        request_path = unquote(self.path.split("?", 1)[0])
        if request_path == "/eminai-watch-preview.html":
            self.send_json({"ok": False, "error": "not found"}, status=404)
            return
        relative = "index.html" if request_path == "/" else request_path.lstrip("/")
        file_path = (APP_DIR / relative).resolve()
        app_root = APP_DIR.resolve()

        if (
            not file_path.is_relative_to(app_root)
            or not file_path.is_file()
            or any(part.startswith(".") for part in file_path.relative_to(app_root).parts)
        ):
            self.send_json({"ok": False, "error": "not found"}, status=404)
            return

        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_security_headers(private=False)
        self.end_headers()
        self.wfile.write(data)

    def log_request(self, code="-", size="-") -> None:
        request_path = urlparse(getattr(self, "path", "") or "").path or "-"
        LOGGER.info(
            "http client=%s method=%s path=%s status=%s",
            self.client_key(),
            self.command,
            request_path,
            code,
        )

    def log_message(self, format, *args) -> None:
        LOGGER.warning("http protocol warning client=%s", self.client_key())


if __name__ == "__main__":
    if not site_access_password():
        raise SystemExit("SITE_ACCESS_PASSWORD must be configured; refusing to start without authentication")
    init_db()
    print(f"http://{HOST}:{PORT}")
    print("api server started")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
