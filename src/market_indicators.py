"""Live economic and market indicator dashboard with interpretation bands."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html import unescape
import re
import threading
import time

import httpx

from database import connect
from fred_indicator_data import get_fred_indicator_bundle
from ism_data import fetch_ism_report
from market_data import get_market_chart


CACHE_TTL_SECONDS = 900
HTTP_TIMEOUT_SECONDS = 12
_CACHE: tuple[float, dict] | None = None
_CACHE_LOCK = threading.Lock()


VIX_BANDS = [
    {"min": None, "max": 15, "label": "안정", "tone": "low", "rangeText": "15 미만"},
    {"min": 15, "max": 20, "label": "보통", "tone": "normal", "rangeText": "15~20"},
    {"min": 20, "max": 30, "label": "경계", "tone": "watch", "rangeText": "20~30"},
    {"min": 30, "max": None, "label": "고위험", "tone": "high", "rangeText": "30 이상"},
]

US10Y_BANDS = [
    {"min": None, "max": 3, "label": "낮은 금리", "tone": "low", "rangeText": "3% 미만"},
    {"min": 3, "max": 4, "label": "중립 구간", "tone": "normal", "rangeText": "3~4%"},
    {"min": 4, "max": 5, "label": "긴축적", "tone": "watch", "rangeText": "4~5%"},
    {"min": 5, "max": None, "label": "매우 긴축적", "tone": "high", "rangeText": "5% 이상"},
]

CPI_BANDS = [
    {"min": None, "max": 2, "label": "낮음", "tone": "low", "rangeText": "2% 미만"},
    {"min": 2, "max": 3, "label": "목표 근처", "tone": "normal", "rangeText": "2~3%"},
    {"min": 3, "max": 4, "label": "높음", "tone": "watch", "rangeText": "3~4%"},
    {"min": 4, "max": None, "label": "매우 높음", "tone": "high", "rangeText": "4% 이상"},
]

CRYPTO_FLOW_BANDS = [
    {"min": None, "max": -3, "label": "강한 유출", "tone": "high", "rangeText": "-3% 미만"},
    {"min": -3, "max": -1, "label": "유출", "tone": "watch", "rangeText": "-3~-1%"},
    {"min": -1, "max": 1, "label": "중립", "tone": "normal", "rangeText": "-1~+1%"},
    {"min": 1, "max": 3, "label": "유입", "tone": "low", "rangeText": "+1~+3%"},
    {"min": 3, "max": None, "label": "강한 유입", "tone": "low", "rangeText": "+3% 이상"},
]

BOJ_BANDS = [
    {"min": None, "max": 0, "label": "초완화", "tone": "low", "rangeText": "0% 미만"},
    {"min": 0, "max": 0.5, "label": "완화적", "tone": "normal", "rangeText": "0~0.5%"},
    {"min": 0.5, "max": 1, "label": "정상화", "tone": "watch", "rangeText": "0.5~1%"},
    {"min": 1, "max": None, "label": "긴축적", "tone": "high", "rangeText": "1% 이상"},
]

CORE_PCE_BANDS = [
    {"min": None, "max": 1.5, "label": "낮음", "tone": "low", "rangeText": "1.5% 미만"},
    {"min": 1.5, "max": 2.5, "label": "목표권", "tone": "normal", "rangeText": "1.5~2.5%"},
    {"min": 2.5, "max": 3.5, "label": "높음", "tone": "watch", "rangeText": "2.5~3.5%"},
    {"min": 3.5, "max": None, "label": "매우 높음", "tone": "high", "rangeText": "3.5% 이상"},
]

REAL_POLICY_BANDS = [
    {"min": None, "max": 0, "label": "완화적", "tone": "low", "rangeText": "0%p 미만"},
    {"min": 0, "max": 1, "label": "중립권", "tone": "normal", "rangeText": "0~1%p"},
    {"min": 1, "max": 2, "label": "긴축적", "tone": "watch", "rangeText": "1~2%p"},
    {"min": 2, "max": None, "label": "매우 긴축적", "tone": "high", "rangeText": "2%p 이상"},
]

YIELD_CURVE_BANDS = [
    {"min": None, "max": -0.5, "label": "깊은 역전", "tone": "high", "rangeText": "-0.5%p 미만"},
    {"min": -0.5, "max": 0, "label": "역전", "tone": "watch", "rangeText": "-0.5~0%p"},
    {"min": 0, "max": 1, "label": "정상", "tone": "normal", "rangeText": "0~1%p"},
    {"min": 1, "max": None, "label": "가파름", "tone": "low", "rangeText": "1%p 이상"},
]

REAL_YIELD_BANDS = [
    {"min": None, "max": 0, "label": "완화적", "tone": "low", "rangeText": "0% 미만"},
    {"min": 0, "max": 1, "label": "보통", "tone": "normal", "rangeText": "0~1%"},
    {"min": 1, "max": 2, "label": "긴축", "tone": "watch", "rangeText": "1~2%"},
    {"min": 2, "max": None, "label": "강한 긴축", "tone": "high", "rangeText": "2% 이상"},
]

BREAKEVEN_BANDS = [
    {"min": None, "max": 1.5, "label": "낮은 기대", "tone": "watch", "rangeText": "1.5% 미만"},
    {"min": 1.5, "max": 2.5, "label": "안정", "tone": "normal", "rangeText": "1.5~2.5%"},
    {"min": 2.5, "max": 3, "label": "상승 경계", "tone": "watch", "rangeText": "2.5~3%"},
    {"min": 3, "max": None, "label": "고위험", "tone": "high", "rangeText": "3% 이상"},
]

SAHM_BANDS = [
    {"min": None, "max": 0.3, "label": "안정", "tone": "low", "rangeText": "0.3%p 미만"},
    {"min": 0.3, "max": 0.5, "label": "경계", "tone": "watch", "rangeText": "0.3~0.5%p"},
    {"min": 0.5, "max": None, "label": "침체 신호", "tone": "high", "rangeText": "0.5%p 이상"},
]

NFCI_BANDS = [
    {"min": None, "max": -0.5, "label": "매우 완화", "tone": "low", "rangeText": "-0.5 미만"},
    {"min": -0.5, "max": 0, "label": "완화", "tone": "normal", "rangeText": "-0.5~0"},
    {"min": 0, "max": 0.5, "label": "긴축", "tone": "watch", "rangeText": "0~0.5"},
    {"min": 0.5, "max": None, "label": "스트레스", "tone": "high", "rangeText": "0.5 이상"},
]

HIGH_YIELD_BANDS = [
    {"min": None, "max": 3, "label": "안정", "tone": "low", "rangeText": "3%p 미만"},
    {"min": 3, "max": 4, "label": "보통", "tone": "normal", "rangeText": "3~4%p"},
    {"min": 4, "max": 6, "label": "경계", "tone": "watch", "rangeText": "4~6%p"},
    {"min": 6, "max": None, "label": "스트레스", "tone": "high", "rangeText": "6%p 이상"},
]

GDP_NOW_BANDS = [
    {"min": None, "max": 0, "label": "위축", "tone": "high", "rangeText": "0% 미만"},
    {"min": 0, "max": 1, "label": "부진", "tone": "watch", "rangeText": "0~1%"},
    {"min": 1, "max": 3, "label": "보통 성장", "tone": "normal", "rangeText": "1~3%"},
    {"min": 3, "max": None, "label": "강한 성장", "tone": "low", "rangeText": "3% 이상"},
]

PMI_BANDS = [
    {"min": None, "max": 45, "label": "깊은 위축", "tone": "high", "rangeText": "45 미만"},
    {"min": 45, "max": 50, "label": "위축", "tone": "watch", "rangeText": "45~50"},
    {"min": 50, "max": 55, "label": "확장", "tone": "normal", "rangeText": "50~55"},
    {"min": 55, "max": None, "label": "강한 확장", "tone": "low", "rangeText": "55 이상"},
]

JOLTS_RATIO_BANDS = [
    {"min": None, "max": 0.8, "label": "수요 약화", "tone": "high", "rangeText": "0.8배 미만"},
    {"min": 0.8, "max": 1.0, "label": "약한 수요", "tone": "watch", "rangeText": "0.8~1.0배"},
    {"min": 1.0, "max": 1.5, "label": "균형~견조", "tone": "normal", "rangeText": "1.0~1.5배"},
    {"min": 1.5, "max": None, "label": "과열", "tone": "high", "rangeText": "1.5배 이상"},
]

QUITS_RATE_BANDS = [
    {"min": None, "max": 1.7, "label": "이직 위축", "tone": "high", "rangeText": "1.7% 미만"},
    {"min": 1.7, "max": 2.0, "label": "약함", "tone": "watch", "rangeText": "1.7~2.0%"},
    {"min": 2.0, "max": 2.5, "label": "보통", "tone": "normal", "rangeText": "2.0~2.5%"},
    {"min": 2.5, "max": None, "label": "과열", "tone": "high", "rangeText": "2.5% 이상"},
]

RETAIL_GROWTH_BANDS = [
    {"min": None, "max": -2, "label": "위축", "tone": "high", "rangeText": "-2% 미만"},
    {"min": -2, "max": 1, "label": "부진", "tone": "watch", "rangeText": "-2~1%"},
    {"min": 1, "max": 5, "label": "보통", "tone": "normal", "rangeText": "1~5%"},
    {"min": 5, "max": None, "label": "강함", "tone": "low", "rangeText": "5% 이상"},
]

INDUSTRIAL_PRODUCTION_BANDS = [
    {"min": None, "max": -2, "label": "위축", "tone": "high", "rangeText": "-2% 미만"},
    {"min": -2, "max": 0, "label": "약화", "tone": "watch", "rangeText": "-2~0%"},
    {"min": 0, "max": 3, "label": "완만한 성장", "tone": "normal", "rangeText": "0~3%"},
    {"min": 3, "max": None, "label": "강한 성장", "tone": "low", "rangeText": "3% 이상"},
]

M2_GROWTH_BANDS = [
    {"min": None, "max": 0, "label": "통화 수축", "tone": "high", "rangeText": "0% 미만"},
    {"min": 0, "max": 3, "label": "낮은 증가", "tone": "watch", "rangeText": "0~3%"},
    {"min": 3, "max": 7, "label": "보통 증가", "tone": "normal", "rangeText": "3~7%"},
    {"min": 7, "max": None, "label": "빠른 증가", "tone": "low", "rangeText": "7% 이상"},
]

NET_LIQUIDITY_BANDS = [
    {"min": None, "max": -5, "label": "강한 축소", "tone": "high", "rangeText": "-5% 미만"},
    {"min": -5, "max": 0, "label": "축소", "tone": "watch", "rangeText": "-5~0%"},
    {"min": 0, "max": 5, "label": "확대", "tone": "normal", "rangeText": "0~5%"},
    {"min": 5, "max": None, "label": "강한 확대", "tone": "low", "rangeText": "5% 이상"},
]

SLOOS_BANDS = [
    {"min": None, "max": 0, "label": "완화", "tone": "low", "rangeText": "0% 미만"},
    {"min": 0, "max": 20, "label": "소폭 긴축", "tone": "normal", "rangeText": "0~20%"},
    {"min": 20, "max": 40, "label": "긴축", "tone": "watch", "rangeText": "20~40%"},
    {"min": 40, "max": None, "label": "강한 긴축", "tone": "high", "rangeText": "40% 이상"},
]

CONSUMER_SENTIMENT_BANDS = [
    {"min": None, "max": 60, "label": "매우 비관적", "tone": "high", "rangeText": "60 미만"},
    {"min": 60, "max": 75, "label": "비관적", "tone": "watch", "rangeText": "60~75"},
    {"min": 75, "max": 90, "label": "보통", "tone": "normal", "rangeText": "75~90"},
    {"min": 90, "max": None, "label": "낙관적", "tone": "low", "rangeText": "90 이상"},
]


def selected_band(value: float, bands: list[dict]) -> dict:
    for band in bands:
        minimum = band.get("min")
        maximum = band.get("max")
        if (minimum is None or value >= minimum) and (maximum is None or value < maximum):
            return band
    return bands[-1]


def indicator_payload(
    *,
    key: str,
    name: str,
    category: str,
    value: float,
    unit: str,
    as_of: str,
    bands: list[dict],
    description: str,
    source: str,
    source_url: str,
    note: str,
    chart_symbol: str | None = None,
    change_percent: float | None = None,
    supplements: list[dict] | None = None,
) -> dict:
    band = selected_band(value, bands)
    return {
        "key": key,
        "name": name,
        "category": category,
        "available": True,
        "value": round(float(value), 3),
        "unit": unit,
        "asOf": as_of,
        "status": band["label"],
        "tone": band["tone"],
        "description": description,
        "thresholds": bands,
        "currentRange": band["rangeText"],
        "source": source,
        "sourceUrl": source_url,
        "note": note,
        "chartSymbol": chart_symbol,
        "changePercent": round(change_percent, 2) if change_percent is not None else None,
        "supplements": supplements or [],
    }


def unavailable_indicator(definition: dict, error: Exception) -> dict:
    return {
        **definition,
        "available": False,
        "value": None,
        "asOf": None,
        "status": "데이터 확인 필요",
        "tone": "muted",
        "currentRange": None,
        "changePercent": None,
        "supplements": [],
        "error": str(error)[:160],
    }


def market_chart_indicator(symbol: str, definition: dict, bands: list[dict]) -> dict:
    chart = get_market_chart(symbol, "1mo", "1d")
    candles = chart["candles"]
    previous = candles[-2]["close"] if len(candles) > 1 else None
    daily_change = (chart["price"] / previous - 1) * 100 if previous else None
    return indicator_payload(
        **definition,
        value=chart["price"],
        as_of=chart["asOf"],
        bands=bands,
        source=chart["source"],
        source_url=chart["sourceUrl"],
        chart_symbol=symbol,
        change_percent=daily_change,
    )


def fetch_vix() -> dict:
    return market_chart_indicator(
        "^VIX",
        {
            "key": "vix",
            "name": "VIX 변동성 지수",
            "category": "위험·심리",
            "unit": "pt",
            "description": "S&P 500 옵션이 반영하는 향후 30일 예상 변동성입니다.",
            "note": "구간은 시장 해석용 경험칙이며 Cboe의 공식 매매 신호가 아닙니다.",
        },
        VIX_BANDS,
    )


def fetch_us10y() -> dict:
    return market_chart_indicator(
        "^TNX",
        {
            "key": "us10y",
            "name": "미국 10년물 금리",
            "category": "채권·금리",
            "unit": "%",
            "description": "미국 장기 할인율과 글로벌 금융여건의 핵심 기준입니다.",
            "note": "절대 수준만 보지 말고 성장·물가 기대와 단기금리 방향을 함께 봐야 합니다.",
        },
        US10Y_BANDS,
    )


def cpi_from_local_database() -> tuple[float, str, float]:
    connection = connect()
    try:
        rows = connection.execute(
            """
            select observed_at, value
            from macro_observations
            where series_id = 'CPIAUCSL'
            order by observed_at desc
            limit 18
            """
        ).fetchall()
    finally:
        connection.close()
    if len(rows) < 13:
        raise ValueError("저장된 CPI 관측치가 부족합니다")
    latest = rows[0]
    year_ago = next((row for row in rows[1:] if row["observed_at"][:7] == f"{int(latest['observed_at'][:4]) - 1}{latest['observed_at'][4:7]}"), None)
    if not year_ago:
        raise ValueError("CPI 전년 동월 관측치가 없습니다")
    yoy = (float(latest["value"]) / float(year_ago["value"]) - 1) * 100
    return yoy, latest["observed_at"], float(latest["value"])


def fetch_cpi() -> dict:
    current_year = datetime.now(timezone.utc).year
    try:
        response = httpx.get(
            "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0",
            params={"startyear": current_year - 2, "endyear": current_year},
            headers={"User-Agent": "EMINAI-Watch/1.0"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        series = payload.get("Results", {}).get("series", [])
        if not series:
            raise ValueError("BLS CPI 응답에 시계열이 없습니다")
        rows = [item for item in series[0].get("data", []) if re.fullmatch(r"M(0[1-9]|1[0-2])", item.get("period", ""))]
        rows.sort(key=lambda item: (int(item["year"]), int(item["period"][1:])), reverse=True)
        latest = rows[0]
        prior = next(
            item for item in rows
            if int(item["year"]) == int(latest["year"]) - 1 and item["period"] == latest["period"]
        )
        latest_value = float(latest["value"])
        yoy = (latest_value / float(prior["value"]) - 1) * 100
        as_of = f"{latest['year']}-{latest['period'][1:]}-01"
    except Exception:
        yoy, as_of, latest_value = cpi_from_local_database()

    return indicator_payload(
        key="us_cpi",
        name="미국 CPI 전년비",
        category="물가",
        value=yoy,
        unit="% YoY",
        as_of=as_of,
        bands=CPI_BANDS,
        description="미국 소비자물가지수의 전년 동월 대비 상승률입니다.",
        source="U.S. Bureau of Labor Statistics",
        source_url="https://data.bls.gov/timeseries/CUUR0000SA0",
        note="연준의 2% 목표는 CPI가 아니라 PCE 기준입니다. 이 구간은 CPI 해석용 규칙입니다.",
        supplements=[{"label": "CPI 지수", "value": round(latest_value, 3)}],
    )


def fetch_crypto_flow() -> dict:
    response = httpx.get(
        "https://api.coingecko.com/api/v3/global",
        headers={"User-Agent": "EMINAI-Watch/1.0"},
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    value = float(data["market_cap_change_percentage_24h_usd"])
    updated_at = datetime.fromtimestamp(int(data["updated_at"]), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    market_cap = float(data.get("total_market_cap", {}).get("usd") or 0)
    volume = float(data.get("total_volume", {}).get("usd") or 0)
    dominance = float(data.get("market_cap_percentage", {}).get("btc") or 0)
    return indicator_payload(
        key="crypto_flow",
        name="크립토 자금 흐름",
        category="크립토",
        value=value,
        unit="% / 24h",
        as_of=updated_at,
        bands=CRYPTO_FLOW_BANDS,
        description="전체 암호화폐 시가총액의 24시간 증감률로 본 시장 자금 방향입니다.",
        source="CoinGecko",
        source_url="https://www.coingecko.com/en/global-charts",
        note="거래소 순입출금이 아니라 전체 시가총액 변화율을 이용한 자금 흐름 대용치입니다.",
        supplements=[
            {"label": "전체 시가총액", "value": market_cap, "format": "usdCompact"},
            {"label": "24시간 거래대금", "value": volume, "format": "usdCompact"},
            {"label": "BTC 점유율", "value": round(dominance, 2), "unit": "%"},
        ],
    )


def fetch_boj_rate() -> dict:
    response = httpx.get(
        "https://www.boj.or.jp/en/",
        headers={"User-Agent": "Mozilla/5.0 EMINAI-Watch/1.0"},
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    response.raise_for_status()
    plain = re.sub(r"<[^>]+>", " ", unescape(response.text))
    plain = re.sub(r"\s+", " ", plain)
    match = re.search(
        r"uncollateralized overnight call rate.{0,200}?around\s+([0-9.]+)\s+percent",
        plain,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(
            r"Interest Rate Applied to the Complementary Deposit Facility\s+([0-9.]+)%",
            plain,
            flags=re.IGNORECASE,
        )
    if not match:
        raise ValueError("일본은행 현재 정책금리를 찾지 못했습니다")
    date_match = re.search(
        r"Interest Rate Applied to the Complementary Deposit Facility\s+[0-9.]+%\s+since\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
        plain,
        flags=re.IGNORECASE,
    )
    as_of = date_match.group(1) if date_match else datetime.now(timezone.utc).date().isoformat()
    return indicator_payload(
        key="boj_rate",
        name="BOJ 정책금리",
        category="중앙은행",
        value=float(match.group(1)),
        unit="%",
        as_of=as_of,
        bands=BOJ_BANDS,
        description="일본은행이 유도하는 무담보 익일물 콜금리 수준입니다.",
        source="Bank of Japan",
        source_url="https://www.boj.or.jp/en/",
        note="엔화·일본 국채·글로벌 캐리 트레이드와 함께 해석해야 합니다.",
    )


def fred_series(bundle: dict[str, list[dict]], series_id: str) -> list[dict]:
    rows = sorted(bundle.get(series_id) or [], key=lambda item: item["date"])
    if not rows:
        raise ValueError(f"{series_id} 관측치가 없습니다")
    return rows


def fred_latest(bundle: dict[str, list[dict]], series_id: str) -> tuple[str, float]:
    item = fred_series(bundle, series_id)[-1]
    return item["date"], float(item["value"])


def fred_year_over_year(bundle: dict[str, list[dict]], series_id: str) -> tuple[str, float, float]:
    rows = fred_series(bundle, series_id)
    latest = rows[-1]
    year, month = map(int, latest["date"][:7].split("-"))
    prior_month = f"{year - 1:04d}-{month:02d}"
    prior = next((item for item in reversed(rows[:-1]) if item["date"][:7] == prior_month), None)
    if not prior or not float(prior["value"]):
        raise ValueError(f"{series_id} 전년 동월 관측치가 없습니다")
    latest_value = float(latest["value"])
    yoy = (latest_value / float(prior["value"]) - 1) * 100
    return latest["date"], yoy, latest_value


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("백분위를 계산할 관측치가 없습니다")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def claim_range(value: float) -> str:
    rounded = round(value / 1000) * 1000
    return f"{rounded:,.0f}건"


def claims_bands(four_week_averages: list[float]) -> list[dict]:
    q25 = percentile(four_week_averages, 0.25)
    q75 = percentile(four_week_averages, 0.75)
    q90 = percentile(four_week_averages, 0.90)
    return [
        {"min": None, "max": q25, "label": "낮음", "tone": "low", "rangeText": f"{claim_range(q25)} 미만"},
        {"min": q25, "max": q75, "label": "보통", "tone": "normal", "rangeText": f"{claim_range(q25)}~{claim_range(q75)}"},
        {"min": q75, "max": q90, "label": "경계", "tone": "watch", "rangeText": f"{claim_range(q75)}~{claim_range(q90)}"},
        {"min": q90, "max": None, "label": "고위험", "tone": "high", "rangeText": f"{claim_range(q90)} 이상"},
    ]


def build_core_pce(bundle: dict[str, list[dict]]) -> dict:
    as_of, yoy, index_value = fred_year_over_year(bundle, "PCEPILFE")
    return indicator_payload(
        key="core_pce",
        name="미국 근원 PCE 전년비",
        category="물가",
        value=yoy,
        unit="% YoY",
        as_of=as_of,
        bands=CORE_PCE_BANDS,
        description="식품과 에너지를 제외한 미국 개인소비지출 물가의 전년 대비 상승률입니다.",
        source="U.S. BEA / FRED",
        source_url="https://fred.stlouisfed.org/series/PCEPILFE",
        note="연준의 장기 물가 목표는 PCE 기준 2%입니다. 목표권은 대시보드 해석 범위입니다.",
        supplements=[{"label": "근원 PCE 지수", "value": index_value}],
    )


def build_real_policy_rate(bundle: dict[str, list[dict]]) -> dict:
    rate_date, policy_rate = fred_latest(bundle, "DFF")
    pce_date, core_pce, _ = fred_year_over_year(bundle, "PCEPILFE")
    real_rate = policy_rate - core_pce
    return indicator_payload(
        key="real_policy_rate",
        name="미국 실질 정책금리",
        category="중앙은행",
        value=real_rate,
        unit="%p",
        as_of=rate_date,
        bands=REAL_POLICY_BANDS,
        description="연방기금 실효금리에서 근원 PCE 전년비를 뺀 단순 긴축 강도입니다.",
        source="Federal Reserve / BEA via FRED",
        source_url="https://fred.stlouisfed.org/series/DFF",
        note="중립금리 추정치가 아닌 단순 대용치입니다. 성장과 고용 상황을 함께 봐야 합니다.",
        supplements=[
            {"label": "실효 정책금리", "value": policy_rate, "unit": "%"},
            {"label": f"근원 PCE ({pce_date[:7]})", "value": core_pce, "unit": "%"},
        ],
    )


def build_yield_curve(bundle: dict[str, list[dict]]) -> dict:
    as_of, spread_2y = fred_latest(bundle, "T10Y2Y")
    spread_3m_date, spread_3m = fred_latest(bundle, "T10Y3M")
    return indicator_payload(
        key="yield_curve",
        name="미국 장단기 금리차",
        category="채권·금리",
        value=spread_2y,
        unit="%p (10Y-2Y)",
        as_of=as_of,
        bands=YIELD_CURVE_BANDS,
        description="미국 10년물과 2년물 국채금리 차이로 수익률곡선의 기울기를 봅니다.",
        source="U.S. Treasury / FRED",
        source_url="https://fred.stlouisfed.org/series/T10Y2Y",
        note="역전 해소가 경기 회복만을 뜻하지는 않습니다. 단기금리 급락에 의한 재가팔라짐도 구분해야 합니다.",
        supplements=[{"label": f"10Y-3M ({spread_3m_date[5:10]})", "value": spread_3m, "unit": "%p"}],
    )


def build_real_yield(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "DFII10")
    return indicator_payload(
        key="us10y_real",
        name="미국 10년 실질금리",
        category="채권·금리",
        value=value,
        unit="%",
        as_of=as_of,
        bands=REAL_YIELD_BANDS,
        description="물가연동국채에서 관측되는 미국 10년 만기 실질 수익률입니다.",
        source="Federal Reserve H.15 / FRED",
        source_url="https://fred.stlouisfed.org/series/DFII10",
        note="실질금리가 높을수록 장기 성장주·금·부채 보유자의 할인율 부담이 커질 수 있습니다.",
    )


def build_breakeven(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "T10YIE")
    return indicator_payload(
        key="breakeven_10y",
        name="미국 10년 기대인플레이션",
        category="물가·기대",
        value=value,
        unit="%",
        as_of=as_of,
        bands=BREAKEVEN_BANDS,
        description="명목 국채와 물가연동국채의 금리 차이로 본 시장의 장기 평균 물가 기대입니다.",
        source="Federal Reserve Bank of St. Louis",
        source_url="https://fred.stlouisfed.org/series/T10YIE",
        note="위험 프리미엄과 유동성 요인도 포함하므로 순수한 물가 전망과 완전히 같지는 않습니다.",
    )


def build_sahm_rule(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "SAHMREALTIME")
    return indicator_payload(
        key="sahm_rule",
        name="Sahm Rule 침체 지표",
        category="고용·경기",
        value=value,
        unit="%p",
        as_of=as_of,
        bands=SAHM_BANDS,
        description="실업률 3개월 평균이 최근 12개월 저점보다 얼마나 상승했는지 보여줍니다.",
        source="Sahm / FRED",
        source_url="https://fred.stlouisfed.org/series/SAHMREALTIME",
        note="0.5%p 이상은 공식 규칙의 침체 시작 신호이며 미래 침체 확률 예측치는 아닙니다.",
    )


def build_initial_claims(bundle: dict[str, list[dict]]) -> dict:
    rows = fred_series(bundle, "ICSA")
    if len(rows) < 8:
        raise ValueError("ICSA 4주 평균을 계산할 관측치가 부족합니다")
    averages = [
        sum(float(item["value"]) for item in rows[index - 3:index + 1]) / 4
        for index in range(3, len(rows))
    ]
    current = averages[-1]
    bands = claims_bands(averages)
    rank = sum(value <= current for value in averages) / len(averages) * 100
    return indicator_payload(
        key="initial_claims",
        name="미국 신규 실업수당 4주 평균",
        category="고용·경기",
        value=current,
        unit="건",
        as_of=rows[-1]["date"],
        bands=bands,
        description="주간 변동을 완화한 신규 실업수당 청구 4주 평균으로 해고 흐름을 빠르게 봅니다.",
        source="U.S. Employment and Training Administration / FRED",
        source_url="https://fred.stlouisfed.org/series/ICSA",
        note="노동시장 규모와 계절성이 변하므로 고정 숫자 대신 최근 5년 분포를 기준으로 판정합니다.",
        supplements=[
            {"label": "최근 주간", "value": float(rows[-1]["value"]), "unit": "건"},
            {"label": "5년 백분위", "value": rank, "unit": "%"},
        ],
    )


def build_nfci(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "NFCI")
    return indicator_payload(
        key="nfci",
        name="Chicago Fed 금융여건지수",
        category="유동성·신용",
        value=value,
        unit="지수",
        as_of=as_of,
        bands=NFCI_BANDS,
        description="위험·신용·레버리지를 종합해 미국 금융여건이 역사적 평균보다 긴축적인지 봅니다.",
        source="Federal Reserve Bank of Chicago / FRED",
        source_url="https://fred.stlouisfed.org/series/NFCI",
        note="0보다 높으면 평균보다 긴축적, 낮으면 완화적입니다. ±0.5 구간은 대시보드 해석 규칙입니다.",
    )


def build_high_yield_spread(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "BAMLH0A0HYM2")
    return indicator_payload(
        key="high_yield_spread",
        name="미국 하이일드 신용스프레드",
        category="유동성·신용",
        value=value,
        unit="%p",
        as_of=as_of,
        bands=HIGH_YIELD_BANDS,
        description="미국 투기등급 회사채의 국채 대비 추가 금리로 신용 위험 선호를 봅니다.",
        source="ICE BofA / FRED",
        source_url="https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
        note="기업 부도율과 정확히 같지 않으며 4·6%p 기준은 시장 스트레스 해석용 경험칙입니다.",
    )


def build_gdp_now(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "GDPNOW")
    quarter = f"{as_of[:4]} Q{(int(as_of[5:7]) - 1) // 3 + 1}"
    return indicator_payload(
        key="gdp_now",
        name="Atlanta Fed GDPNow",
        category="성장",
        value=value,
        unit="% SAAR",
        as_of=as_of,
        bands=GDP_NOW_BANDS,
        description=f"공식 GDP 발표 전에 {quarter} 미국 실질 성장률을 추정하는 나우캐스트입니다.",
        source="Federal Reserve Bank of Atlanta / FRED",
        source_url="https://fred.stlouisfed.org/series/GDPNOW",
        note="애틀랜타 연은의 공식 전망이 아니며 새 경제지표 발표 때마다 같은 분기 값이 수정됩니다.",
    )


def fetch_ism_manufacturing() -> dict:
    report = fetch_ism_report("manufacturing")
    return indicator_payload(
        key="ism_manufacturing",
        name="ISM 제조업 PMI",
        category="성장·선행",
        value=report["value"],
        unit="지수",
        as_of=report["asOf"],
        bands=PMI_BANDS,
        description="미국 제조업 구매관리자 설문으로 생산·주문·고용 흐름을 빠르게 보여줍니다.",
        source="Institute for Supply Management",
        source_url=report["sourceUrl"],
        note="50 이상은 제조업 확장, 50 미만은 위축을 뜻합니다. 전체 경제의 분기점과는 다를 수 있습니다.",
    )


def fetch_ism_services() -> dict:
    report = fetch_ism_report("services")
    return indicator_payload(
        key="ism_services",
        name="ISM 서비스업 PMI",
        category="성장·선행",
        value=report["value"],
        unit="지수",
        as_of=report["asOf"],
        bands=PMI_BANDS,
        description="미국 서비스업 구매관리자 설문으로 내수와 기업활동의 확장·위축을 봅니다.",
        source="Institute for Supply Management",
        source_url=report["sourceUrl"],
        note="50 이상은 서비스업 확장, 50 미만은 위축을 뜻하며 가격·고용 세부지수와 함께 봐야 합니다.",
    )


def fred_percent_change(bundle: dict[str, list[dict]], series_id: str, periods: int) -> tuple[str, float, float]:
    rows = fred_series(bundle, series_id)
    if len(rows) <= periods:
        raise ValueError(f"{series_id} 변화율 계산 관측치가 부족합니다")
    latest = float(rows[-1]["value"])
    previous = float(rows[-1 - periods]["value"])
    if previous == 0:
        raise ValueError(f"{series_id} 이전 값이 0입니다")
    return rows[-1]["date"], (latest / previous - 1) * 100, latest


def fred_value_on_or_before(bundle: dict[str, list[dict]], series_id: str, target_date: str) -> tuple[str, float]:
    rows = [item for item in fred_series(bundle, series_id) if item["date"] <= target_date]
    if not rows:
        raise ValueError(f"{series_id} {target_date} 이전 관측치가 없습니다")
    return rows[-1]["date"], float(rows[-1]["value"])


def build_jolts_ratio(bundle: dict[str, list[dict]]) -> dict:
    openings_date, openings = fred_latest(bundle, "JTSJOL")
    unemployment_date, unemployed = fred_value_on_or_before(bundle, "UNEMPLOY", openings_date)
    ratio = openings / unemployed
    return indicator_payload(
        key="jolts_ratio",
        name="미국 구인/실업자 비율",
        category="고용·경기",
        value=ratio,
        unit="배",
        as_of=openings_date,
        bands=JOLTS_RATIO_BANDS,
        description="JOLTS 구인 건수를 실업자 수로 나눠 노동수요와 공급의 균형을 보여줍니다.",
        source="U.S. BLS / FRED",
        source_url="https://fred.stlouisfed.org/series/JTSJOL",
        note="1배 이상이면 구인 수가 실업자 수보다 많습니다. 구인의 질과 실제 채용 전환율은 별도 확인이 필요합니다.",
        supplements=[
            {"label": "구인", "value": openings, "unit": "천건"},
            {"label": f"실업자 ({unemployment_date[:7]})", "value": unemployed, "unit": "천명"},
        ],
    )


def build_jolts_quits(bundle: dict[str, list[dict]]) -> dict:
    as_of, value = fred_latest(bundle, "JTSQUR")
    return indicator_payload(
        key="jolts_quits",
        name="미국 자발적 퇴직률",
        category="고용·경기",
        value=value,
        unit="%",
        as_of=as_of,
        bands=QUITS_RATE_BANDS,
        description="근로자가 더 나은 일자리를 찾을 자신감이 있는지 보여주는 JOLTS 자발적 퇴직률입니다.",
        source="U.S. BLS / FRED",
        source_url="https://fred.stlouisfed.org/series/JTSQUR",
        note="퇴직률 하락은 임금 압력 완화와 노동시장 자신감 약화를 동시에 뜻할 수 있습니다.",
    )


def build_core_retail_sales(bundle: dict[str, list[dict]]) -> dict:
    rows = fred_series(bundle, "MARTSSM44W72USS")
    if len(rows) < 13:
        raise ValueError("핵심 소매판매 변화율 계산 관측치가 부족합니다")
    latest = float(rows[-1]["value"])
    month_change = (latest / float(rows[-2]["value"]) - 1) * 100
    year_change = (latest / float(rows[-13]["value"]) - 1) * 100
    return indicator_payload(
        key="core_retail_sales",
        name="미국 핵심 소매판매",
        category="성장·소비",
        value=year_change,
        unit="% YoY",
        as_of=rows[-1]["date"],
        bands=RETAIL_GROWTH_BANDS,
        description="변동성이 큰 자동차와 주유소를 제외한 미국 선행 소매판매의 전년 대비 증가율입니다.",
        source="U.S. Census Bureau / FRED",
        source_url="https://fred.stlouisfed.org/series/MARTSSM44W72USS",
        note="엄밀한 GDP 소매판매 통제그룹과는 범위가 다르며 명목 금액이라 물가 영향을 포함합니다.",
        supplements=[
            {"label": "전월비", "value": month_change, "unit": "%"},
            {"label": "판매액", "value": latest / 1000, "unit": "십억달러"},
        ],
    )


def build_industrial_production(bundle: dict[str, list[dict]]) -> dict:
    as_of, yoy, index_value = fred_year_over_year(bundle, "INDPRO")
    return indicator_payload(
        key="industrial_production",
        name="미국 산업생산 전년비",
        category="성장·생산",
        value=yoy,
        unit="% YoY",
        as_of=as_of,
        bands=INDUSTRIAL_PRODUCTION_BANDS,
        description="제조업·광업·유틸리티의 실물 생산량이 전년보다 얼마나 변했는지 보여줍니다.",
        source="Federal Reserve / FRED",
        source_url="https://fred.stlouisfed.org/series/INDPRO",
        note="설문인 PMI와 달리 실제 생산량 지표지만 발표 시차와 수정이 있습니다.",
        supplements=[{"label": "산업생산지수", "value": index_value}],
    )


def build_m2_growth(bundle: dict[str, list[dict]]) -> dict:
    as_of, yoy, level = fred_year_over_year(bundle, "M2SL")
    return indicator_payload(
        key="m2_growth",
        name="미국 M2 통화량 증가율",
        category="유동성·신용",
        value=yoy,
        unit="% YoY",
        as_of=as_of,
        bands=M2_GROWTH_BANDS,
        description="현금·예금·소매 머니마켓펀드 등을 포함한 광의통화 M2의 전년 대비 증가율입니다.",
        source="Federal Reserve H.6 / FRED",
        source_url="https://fred.stlouisfed.org/series/M2SL",
        note="M2 증가가 곧바로 자산가격 상승을 뜻하지 않으며 신용창출·통화유통속도와 함께 봐야 합니다.",
        supplements=[{"label": "M2 잔액", "value": level / 1000, "unit": "조달러"}],
    )


def _net_liquidity_at(bundle: dict[str, list[dict]], target_date: str) -> tuple[str, float, float, float]:
    fed_date, fed_assets = fred_value_on_or_before(bundle, "WALCL", target_date)
    _, tga = fred_value_on_or_before(bundle, "WTREGEN", fed_date)
    _, reverse_repo = fred_value_on_or_before(bundle, "RRPONTSYD", fed_date)
    net_billions = fed_assets / 1000 - tga / 1000 - reverse_repo
    return fed_date, net_billions, tga / 1000, reverse_repo


def build_net_liquidity(bundle: dict[str, list[dict]]) -> dict:
    latest_date = fred_series(bundle, "WALCL")[-1]["date"]
    as_of, current, tga, reverse_repo = _net_liquidity_at(bundle, latest_date)
    prior_target = (datetime.fromisoformat(as_of) - timedelta(days=91)).date().isoformat()
    _, prior, _, _ = _net_liquidity_at(bundle, prior_target)
    change = (current / prior - 1) * 100
    return indicator_payload(
        key="fed_net_liquidity",
        name="연준 순유동성 13주 변화",
        category="유동성·신용",
        value=change,
        unit="%",
        as_of=as_of,
        bands=NET_LIQUIDITY_BANDS,
        description="연준 총자산에서 재무부 TGA와 익일 역레포를 뺀 대시보드용 유동성 대용치의 13주 변화율입니다.",
        source="Federal Reserve / FRED",
        source_url="https://fred.stlouisfed.org/series/WALCL",
        note="공식 연준 지표가 아닌 파생 대용치이며 은행 준비금·재무부 현금흐름·시장 신용을 모두 대변하지는 않습니다.",
        supplements=[
            {"label": "순유동성", "value": current / 1000, "unit": "조달러"},
            {"label": "TGA", "value": tga, "unit": "십억달러"},
            {"label": "역레포", "value": reverse_repo, "unit": "십억달러"},
        ],
    )


def build_sloos(bundle: dict[str, list[dict]]) -> dict:
    as_of, small_firms = fred_latest(bundle, "DRTSCIS")
    large_date, large_firms = fred_latest(bundle, "DRTSCILM")
    return indicator_payload(
        key="sloos_tightening",
        name="은행 기업대출 기준 긴축",
        category="유동성·신용",
        value=small_firms,
        unit="% (순비율)",
        as_of=as_of,
        bands=SLOOS_BANDS,
        description="미국 은행 중 소기업 대상 기업대출 기준을 강화했다고 답한 은행의 순비율입니다.",
        source="Federal Reserve SLOOS / FRED",
        source_url="https://fred.stlouisfed.org/series/DRTSCIS",
        note="양수는 대출기준 순긴축, 음수는 순완화입니다. 분기 설문이라 실시간 시장지표보다 느립니다.",
        supplements=[{"label": f"중대형기업 ({large_date[:7]})", "value": large_firms, "unit": "%"}],
    )


def build_consumer_sentiment(bundle: dict[str, list[dict]]) -> dict:
    as_of, sentiment = fred_latest(bundle, "UMCSENT")
    inflation_date, inflation = fred_latest(bundle, "MICH")
    return indicator_payload(
        key="consumer_sentiment",
        name="미시간대 소비심리",
        category="성장·소비",
        value=sentiment,
        unit="지수",
        as_of=as_of,
        bands=CONSUMER_SENTIMENT_BANDS,
        description="미국 가계가 현재 경제와 향후 재정 상황을 어떻게 느끼는지 보여주는 소비심리지수입니다.",
        source="University of Michigan / FRED",
        source_url="https://fred.stlouisfed.org/series/UMCSENT",
        note="FRED 공개치는 원자료 제공 조건에 따라 한 달 지연될 수 있으며 실제 소비와 괴리가 날 수 있습니다.",
        supplements=[{"label": f"1년 기대인플레 ({inflation_date[:7]})", "value": inflation, "unit": "%"}],
    )


INDICATOR_DEFINITIONS = [
    {"key": "vix", "name": "VIX 변동성 지수", "category": "위험·심리", "unit": "pt", "thresholds": VIX_BANDS, "source": "Cboe / Yahoo Finance", "sourceUrl": "https://www.cboe.com/tradable-products/vix"},
    {"key": "us10y", "name": "미국 10년물 금리", "category": "채권·금리", "unit": "%", "thresholds": US10Y_BANDS, "source": "Yahoo Finance", "sourceUrl": "https://finance.yahoo.com/quote/%5ETNX"},
    {"key": "core_pce", "name": "미국 근원 PCE 전년비", "category": "물가", "unit": "% YoY", "thresholds": CORE_PCE_BANDS, "source": "U.S. BEA / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/PCEPILFE"},
    {"key": "real_policy_rate", "name": "미국 실질 정책금리", "category": "중앙은행", "unit": "%p", "thresholds": REAL_POLICY_BANDS, "source": "Federal Reserve / BEA via FRED", "sourceUrl": "https://fred.stlouisfed.org/series/DFF"},
    {"key": "yield_curve", "name": "미국 장단기 금리차", "category": "채권·금리", "unit": "%p (10Y-2Y)", "thresholds": YIELD_CURVE_BANDS, "source": "U.S. Treasury / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/T10Y2Y"},
    {"key": "us10y_real", "name": "미국 10년 실질금리", "category": "채권·금리", "unit": "%", "thresholds": REAL_YIELD_BANDS, "source": "Federal Reserve H.15 / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/DFII10"},
    {"key": "breakeven_10y", "name": "미국 10년 기대인플레이션", "category": "물가·기대", "unit": "%", "thresholds": BREAKEVEN_BANDS, "source": "Federal Reserve Bank of St. Louis", "sourceUrl": "https://fred.stlouisfed.org/series/T10YIE"},
    {"key": "us_cpi", "name": "미국 CPI 전년비", "category": "물가", "unit": "% YoY", "thresholds": CPI_BANDS, "source": "U.S. Bureau of Labor Statistics", "sourceUrl": "https://data.bls.gov/timeseries/CUUR0000SA0"},
    {"key": "ism_manufacturing", "name": "ISM 제조업 PMI", "category": "성장·선행", "unit": "지수", "thresholds": PMI_BANDS, "source": "Institute for Supply Management", "sourceUrl": "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/"},
    {"key": "ism_services", "name": "ISM 서비스업 PMI", "category": "성장·선행", "unit": "지수", "thresholds": PMI_BANDS, "source": "Institute for Supply Management", "sourceUrl": "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/services/"},
    {"key": "sahm_rule", "name": "Sahm Rule 침체 지표", "category": "고용·경기", "unit": "%p", "thresholds": SAHM_BANDS, "source": "Sahm / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/SAHMREALTIME"},
    {"key": "initial_claims", "name": "미국 신규 실업수당 4주 평균", "category": "고용·경기", "unit": "건", "thresholds": [], "source": "U.S. Employment and Training Administration / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/ICSA"},
    {"key": "jolts_ratio", "name": "미국 구인/실업자 비율", "category": "고용·경기", "unit": "배", "thresholds": JOLTS_RATIO_BANDS, "source": "U.S. BLS / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/JTSJOL"},
    {"key": "jolts_quits", "name": "미국 자발적 퇴직률", "category": "고용·경기", "unit": "%", "thresholds": QUITS_RATE_BANDS, "source": "U.S. BLS / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/JTSQUR"},
    {"key": "core_retail_sales", "name": "미국 핵심 소매판매", "category": "성장·소비", "unit": "% YoY", "thresholds": RETAIL_GROWTH_BANDS, "source": "U.S. Census Bureau / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/MARTSSM44W72USS"},
    {"key": "industrial_production", "name": "미국 산업생산 전년비", "category": "성장·생산", "unit": "% YoY", "thresholds": INDUSTRIAL_PRODUCTION_BANDS, "source": "Federal Reserve / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/INDPRO"},
    {"key": "nfci", "name": "Chicago Fed 금융여건지수", "category": "유동성·신용", "unit": "지수", "thresholds": NFCI_BANDS, "source": "Federal Reserve Bank of Chicago / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/NFCI"},
    {"key": "high_yield_spread", "name": "미국 하이일드 신용스프레드", "category": "유동성·신용", "unit": "%p", "thresholds": HIGH_YIELD_BANDS, "source": "ICE BofA / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2"},
    {"key": "m2_growth", "name": "미국 M2 통화량 증가율", "category": "유동성·신용", "unit": "% YoY", "thresholds": M2_GROWTH_BANDS, "source": "Federal Reserve H.6 / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/M2SL"},
    {"key": "fed_net_liquidity", "name": "연준 순유동성 13주 변화", "category": "유동성·신용", "unit": "%", "thresholds": NET_LIQUIDITY_BANDS, "source": "Federal Reserve / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/WALCL"},
    {"key": "sloos_tightening", "name": "은행 기업대출 기준 긴축", "category": "유동성·신용", "unit": "% (순비율)", "thresholds": SLOOS_BANDS, "source": "Federal Reserve SLOOS / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/DRTSCIS"},
    {"key": "consumer_sentiment", "name": "미시간대 소비심리", "category": "성장·소비", "unit": "지수", "thresholds": CONSUMER_SENTIMENT_BANDS, "source": "University of Michigan / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/UMCSENT"},
    {"key": "gdp_now", "name": "Atlanta Fed GDPNow", "category": "성장", "unit": "% SAAR", "thresholds": GDP_NOW_BANDS, "source": "Federal Reserve Bank of Atlanta / FRED", "sourceUrl": "https://fred.stlouisfed.org/series/GDPNOW"},
    {"key": "crypto_flow", "name": "크립토 자금 흐름", "category": "크립토", "unit": "% / 24h", "thresholds": CRYPTO_FLOW_BANDS, "source": "CoinGecko", "sourceUrl": "https://www.coingecko.com/en/global-charts"},
    {"key": "boj_rate", "name": "BOJ 정책금리", "category": "중앙은행", "unit": "%", "thresholds": BOJ_BANDS, "source": "Bank of Japan", "sourceUrl": "https://www.boj.or.jp/en/"},
]

FETCHERS = {
    "vix": fetch_vix,
    "us10y": fetch_us10y,
    "us_cpi": fetch_cpi,
    "ism_manufacturing": fetch_ism_manufacturing,
    "ism_services": fetch_ism_services,
    "crypto_flow": fetch_crypto_flow,
    "boj_rate": fetch_boj_rate,
}

FRED_BUILDERS = {
    "core_pce": build_core_pce,
    "real_policy_rate": build_real_policy_rate,
    "yield_curve": build_yield_curve,
    "us10y_real": build_real_yield,
    "breakeven_10y": build_breakeven,
    "sahm_rule": build_sahm_rule,
    "initial_claims": build_initial_claims,
    "jolts_ratio": build_jolts_ratio,
    "jolts_quits": build_jolts_quits,
    "core_retail_sales": build_core_retail_sales,
    "industrial_production": build_industrial_production,
    "nfci": build_nfci,
    "high_yield_spread": build_high_yield_spread,
    "m2_growth": build_m2_growth,
    "fed_net_liquidity": build_net_liquidity,
    "sloos_tightening": build_sloos,
    "consumer_sentiment": build_consumer_sentiment,
    "gdp_now": build_gdp_now,
}


def get_indicator_dashboard(force: bool = False) -> dict:
    global _CACHE
    now = time.time()
    with _CACHE_LOCK:
        if not force and _CACHE and now - _CACHE[0] < CACHE_TTL_SECONDS:
            return _CACHE[1]

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(FETCHERS) + 1) as pool:
        fred_future = pool.submit(get_fred_indicator_bundle, force)
        futures = {pool.submit(fetcher): key for key, fetcher in FETCHERS.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as error:
                definition = next(item for item in INDICATOR_DEFINITIONS if item["key"] == key)
                results[key] = unavailable_indicator(definition, error)

        try:
            fred_bundle = fred_future.result()
        except Exception:
            fred_bundle = {}
        for key, builder in FRED_BUILDERS.items():
            try:
                results[key] = builder(fred_bundle)
            except Exception as error:
                definition = next(item for item in INDICATOR_DEFINITIONS if item["key"] == key)
                results[key] = unavailable_indicator(definition, error)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "methodology": "현재 값이 어느 해석 구간에 있는지 보여주는 대시보드 규칙이며 공식 투자 신호가 아닙니다.",
        "indicators": [results[item["key"]] for item in INDICATOR_DEFINITIONS],
    }
    with _CACHE_LOCK:
        _CACHE = (now, payload)
    return payload
