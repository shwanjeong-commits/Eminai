"""Whitelisted delayed market chart data with a short in-memory cache."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx


ASSETS = [
    {"symbol": "^GSPC", "name": "S&P 500", "group": "미국 지수", "kind": "index", "keywords": ["S&P", "미국 증시"]},
    {"symbol": "^IXIC", "name": "Nasdaq Composite", "group": "미국 지수", "kind": "index", "keywords": ["나스닥", "기술주", "AI"]},
    {"symbol": "^DJI", "name": "Dow Jones", "group": "미국 지수", "kind": "index", "keywords": ["다우", "미국 증시"]},
    {"symbol": "^RUT", "name": "Russell 2000", "group": "미국 지수", "kind": "index", "keywords": ["러셀2000", "중소형주", "미국 증시"]},
    {"symbol": "^VIX", "name": "VIX", "group": "위험·심리 지표", "kind": "indicator", "keywords": ["VIX", "변동성", "공포지수"]},
    {"symbol": "^KS11", "name": "KOSPI", "group": "한국 지수", "kind": "index", "keywords": ["코스피", "한국 증시"]},
    {"symbol": "^KQ11", "name": "KOSDAQ", "group": "한국 지수", "kind": "index", "keywords": ["코스닥", "한국 증시", "중소형주"]},
    {"symbol": "^N225", "name": "Nikkei 225", "group": "일본 지수", "kind": "index", "keywords": ["닛케이", "일본 증시", "엔화"]},
    {"symbol": "^HSI", "name": "Hang Seng", "group": "홍콩 지수", "kind": "index", "keywords": ["항셍", "홍콩 증시", "중국"]},
    {"symbol": "000001.SS", "name": "Shanghai Composite", "group": "중국 지수", "kind": "index", "keywords": ["상하이", "중국 증시", "중국"]},
    {"symbol": "^STOXX50E", "name": "Euro Stoxx 50", "group": "유럽 지수", "kind": "index", "keywords": ["유로존", "유럽 증시"]},
    {"symbol": "^FTSE", "name": "FTSE 100", "group": "영국 지수", "kind": "index", "keywords": ["FTSE", "영국 증시", "파운드"]},
    {"symbol": "^GDAXI", "name": "DAX", "group": "독일 지수", "kind": "index", "keywords": ["DAX", "독일 증시", "유럽"]},
    {"symbol": "SPY", "name": "S&P 500 ETF", "group": "ETF", "kind": "etf", "keywords": ["S&P", "미국 증시"]},
    {"symbol": "QQQ", "name": "Nasdaq 100 ETF", "group": "ETF", "kind": "etf", "keywords": ["나스닥", "AI", "기술주"]},
    {"symbol": "IWM", "name": "Russell 2000 ETF", "group": "ETF", "kind": "etf", "keywords": ["러셀2000", "미국 중소형주"]},
    {"symbol": "SOXX", "name": "Semiconductor ETF", "group": "ETF", "kind": "etf", "keywords": ["반도체", "AI", "미국 기술주"]},
    {"symbol": "AAPL", "name": "Apple", "group": "미국 주식", "kind": "stock", "keywords": ["애플", "Apple", "아이폰"]},
    {"symbol": "MSFT", "name": "Microsoft", "group": "미국 주식", "kind": "stock", "keywords": ["마이크로소프트", "Microsoft", "AI", "클라우드"]},
    {"symbol": "GOOGL", "name": "Alphabet", "group": "미국 주식", "kind": "stock", "keywords": ["구글", "Alphabet", "AI", "광고"]},
    {"symbol": "AMZN", "name": "Amazon", "group": "미국 주식", "kind": "stock", "keywords": ["아마존", "Amazon", "AWS", "소비"]},
    {"symbol": "META", "name": "Meta Platforms", "group": "미국 주식", "kind": "stock", "keywords": ["메타", "Meta", "AI", "광고"]},
    {"symbol": "NVDA", "name": "NVIDIA", "group": "주식", "kind": "stock", "keywords": ["엔비디아", "NVIDIA", "AI", "반도체"]},
    {"symbol": "AVGO", "name": "Broadcom", "group": "미국 주식", "kind": "stock", "keywords": ["브로드컴", "Broadcom", "반도체", "AI"]},
    {"symbol": "AMD", "name": "AMD", "group": "미국 주식", "kind": "stock", "keywords": ["AMD", "반도체", "AI"]},
    {"symbol": "MU", "name": "Micron", "group": "미국 주식", "kind": "stock", "keywords": ["마이크론", "Micron", "메모리", "반도체"]},
    {"symbol": "TSLA", "name": "Tesla", "group": "주식", "kind": "stock", "keywords": ["테슬라", "Tesla", "전기차"]},
    {"symbol": "JPM", "name": "JPMorgan Chase", "group": "미국 주식", "kind": "stock", "keywords": ["JP모건", "JPMorgan", "은행", "금리"]},
    {"symbol": "XOM", "name": "Exxon Mobil", "group": "미국 주식", "kind": "stock", "keywords": ["엑슨모빌", "Exxon", "에너지", "유가"]},
    {"symbol": "005930.KS", "name": "삼성전자", "group": "주식", "kind": "stock", "keywords": ["삼성전자", "반도체"]},
    {"symbol": "000660.KS", "name": "SK하이닉스", "group": "한국 주식", "kind": "stock", "keywords": ["SK하이닉스", "메모리", "HBM", "반도체"]},
    {"symbol": "005380.KS", "name": "현대차", "group": "한국 주식", "kind": "stock", "keywords": ["현대차", "자동차", "전기차"]},
    {"symbol": "035420.KS", "name": "NAVER", "group": "한국 주식", "kind": "stock", "keywords": ["네이버", "NAVER", "AI", "플랫폼"]},
    {"symbol": "012450.KS", "name": "한화에어로스페이스", "group": "한국 주식", "kind": "stock", "keywords": ["한화에어로스페이스", "방산", "우주"]},
    {"symbol": "7203.T", "name": "Toyota Motor", "group": "일본 주식", "kind": "stock", "keywords": ["도요타", "Toyota", "자동차", "엔화"]},
    {"symbol": "BTC-USD", "name": "Bitcoin", "group": "암호화폐", "kind": "other", "keywords": ["비트코인", "Bitcoin", "암호화폐"]},
    {"symbol": "ETH-USD", "name": "Ethereum", "group": "암호화폐", "kind": "other", "keywords": ["이더리움", "Ethereum", "암호화폐"]},
    {"symbol": "GC=F", "name": "Gold Futures", "group": "원자재", "kind": "other", "keywords": ["금", "골드", "안전자산"]},
    {"symbol": "CL=F", "name": "WTI Futures", "group": "원자재", "kind": "other", "keywords": ["유가", "원유", "WTI", "호르무즈"]},
    {"symbol": "KRW=X", "name": "USD/KRW", "group": "환율", "kind": "other", "keywords": ["원달러", "환율", "원화", "달러"]},
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "group": "환율", "kind": "other", "keywords": ["달러인덱스", "DXY", "달러"]},
    {"symbol": "^TNX", "name": "US 10Y Yield", "group": "채권·금리 지표", "kind": "indicator", "keywords": ["미국 10년", "국채", "금리"]},
]

ASSET_MAP = {item["symbol"]: item for item in ASSETS}
ALLOWED_RANGES = {"1mo", "3mo", "6mo", "1y", "2y", "5y"}
ALLOWED_INTERVALS = {"4h", "1d", "1wk"}
INTERVAL_RANGES = {
    "4h": {"1mo", "3mo", "6mo", "1y"},
    "1d": ALLOWED_RANGES,
    "1wk": ALLOWED_RANGES,
}
SOURCE_INTERVALS = {"4h": "1h", "1d": "1d", "1wk": "1wk"}
CACHE_TTL_SECONDS = 300
_CACHE: dict[tuple[str, str, str], tuple[float, dict]] = {}


def asset_catalog() -> list[dict]:
    return [item for item in ASSETS if item["kind"] != "indicator"]


def moving_average(values: list[float | None], window: int = 20) -> list[float | None]:
    result = []
    for index, value in enumerate(values):
        if value is None or index + 1 < window:
            result.append(None)
            continue
        sample = [item for item in values[index + 1 - window:index + 1] if item is not None]
        result.append(round(sum(sample) / len(sample), 6) if len(sample) == window else None)
    return result


def aggregate_four_hour(candles: list[dict], utc_offset: int = 0) -> list[dict]:
    """Aggregate Yahoo's one-hour candles into exchange-local four-hour buckets."""
    buckets: dict[tuple[str, int], dict] = {}
    for candle in candles:
        local_timestamp = candle["timestamp"] + utc_offset
        local_date = datetime.fromtimestamp(local_timestamp, tz=timezone.utc).date().isoformat()
        bucket_number = local_timestamp // (4 * 60 * 60)
        key = (local_date, bucket_number)
        if key not in buckets:
            bucket_timestamp = bucket_number * (4 * 60 * 60) - utc_offset
            buckets[key] = {
                "timestamp": bucket_timestamp,
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get("volume") or 0,
                "samples": 1,
            }
            continue
        bucket = buckets[key]
        bucket["high"] = max(bucket["high"], candle["high"])
        bucket["low"] = min(bucket["low"], candle["low"])
        bucket["close"] = candle["close"]
        bucket["volume"] += candle.get("volume") or 0
        bucket["samples"] += 1
    result = list(buckets.values())
    if len(result) > 1:
        last = result[-1]
        if last["samples"] == 1 and last["volume"] == 0 and last["open"] == last["high"] == last["low"] == last["close"]:
            result.pop()
    for candle in result:
        candle.pop("samples", None)
    return result


def get_market_chart(symbol: str, chart_range: str = "6mo", interval: str = "1d") -> dict:
    if symbol not in ASSET_MAP:
        raise ValueError("지원하지 않는 시장 종목입니다.")
    if chart_range not in ALLOWED_RANGES or interval not in ALLOWED_INTERVALS:
        raise ValueError("지원하지 않는 차트 기간입니다.")
    if chart_range not in INTERVAL_RANGES[interval]:
        raise ValueError("4시간 봉은 최근 1년 범위까지 지원합니다.")
    cache_key = (symbol, chart_range, interval)
    cached = _CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    response = httpx.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": chart_range, "interval": SOURCE_INTERVALS[interval], "events": "div,splits"},
        headers={"User-Agent": "Mozilla/5.0 EMINAI-Watch/1.0"},
        timeout=25,
    )
    response.raise_for_status()
    chart = response.json().get("chart", {})
    if chart.get("error") or not chart.get("result"):
        raise ValueError("시세 제공처에서 데이터를 받지 못했습니다.")
    result = chart["result"][0]
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    timestamps = result.get("timestamp", [])
    closes = quote.get("close", [])
    raw_candles = []
    for index, timestamp in enumerate(timestamps):
        values = {
            "open": quote.get("open", [None] * len(timestamps))[index],
            "high": quote.get("high", [None] * len(timestamps))[index],
            "low": quote.get("low", [None] * len(timestamps))[index],
            "close": closes[index],
            "volume": quote.get("volume", [None] * len(timestamps))[index],
        }
        if any(values[key] is None for key in ("open", "high", "low", "close")):
            continue
        raw_candles.append({
            "timestamp": int(timestamp),
            **{key: round(float(value), 6) if value is not None else None for key, value in values.items()},
        })
    if interval == "4h":
        raw_candles = aggregate_four_hour(raw_candles, int(result.get("meta", {}).get("gmtoffset", 0) or 0))
    averages = moving_average([item["close"] for item in raw_candles])
    candles = []
    for index, candle in enumerate(raw_candles):
        candle_time = datetime.fromtimestamp(candle["timestamp"], tz=timezone.utc)
        candles.append({
            "time": candle_time.isoformat().replace("+00:00", "Z") if interval == "4h" else candle_time.date().isoformat(),
            **{key: round(float(candle[key]), 6) if candle.get(key) is not None else None for key in ("open", "high", "low", "close", "volume")},
            "ma20": averages[index],
        })
    if not candles:
        raise ValueError("표시할 가격 데이터가 없습니다.")
    first_close = candles[0]["close"]
    latest = candles[-1]
    payload = {
        "asset": ASSET_MAP[symbol],
        "range": chart_range,
        "interval": interval,
        "currency": result.get("meta", {}).get("currency", ""),
        "exchange": result.get("meta", {}).get("exchangeName", ""),
        "timezone": result.get("meta", {}).get("exchangeTimezoneName", "UTC"),
        "timezoneShortName": result.get("meta", {}).get("timezone", "UTC"),
        "price": latest["close"],
        "changePercent": round((latest["close"] / first_close - 1) * 100, 2) if first_close else None,
        "asOf": latest["time"],
        "candles": candles,
        "source": "Yahoo Finance",
        "sourceUrl": f"https://finance.yahoo.com/quote/{symbol}",
        "delayNotice": "거래소 및 종목에 따라 지연되거나 장 마감 기준일 수 있습니다.",
    }
    _CACHE[cache_key] = (now, payload)
    return payload
