from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import urllib.parse
import urllib.request
import csv
import io


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT_DIR / "data" / "insidertracking_catchup.sqlite3"
URL_RE = re.compile(r"https?://[^\s<>]+")
SPACE_RE = re.compile(r"\s+")

CATEGORIES = {
    "monetary_policy": ("fed", "fomc", "연준", "금리", "rate cut", "rate hike", "한국은행", "한은"),
    "inflation": ("cpi", "ppi", "pce", "물가", "인플레이션", "inflation"),
    "labor": ("payroll", "고용", "실업", "jobs", "unemployment", "임금"),
    "growth": ("gdp", "pmi", "소매판매", "retail sales", "산업생산", "수출", "수입"),
    "fx_rates": ("환율", "원달러", "달러", "dollar", "treasury", "국채", "채권"),
    "equities": ("nasdaq", "s&p", "dow", "kospi", "kosdaq", "나스닥", "코스피", "주가", "증시"),
    "earnings": ("earnings", "실적", "매출", "영업이익", "순이익", "guidance", "가이던스"),
    "semiconductors": ("semiconductor", "반도체", "nvidia", "엔비디아", "삼성전자", "sk하이닉스", "tsmc"),
    "commodities": ("oil", "crude", "유가", "금값", "gold", "copper", "구리", "원자재"),
    "geopolitics": ("tariff", "관세", "전쟁", "분쟁", "제재", "sanction", "중동", "중국"),
}

ASSETS = {
    "^GSPC": ("US", "index", "S&P 500"),
    "^IXIC": ("US", "index", "Nasdaq Composite"),
    "^DJI": ("US", "index", "Dow Jones Industrial Average"),
    "^RUT": ("US", "index", "Russell 2000"),
    "^KS11": ("KR", "index", "KOSPI"),
    "^KQ11": ("KR", "index", "KOSDAQ"),
    "KRW=X": ("KR", "fx", "USD/KRW"),
    "DX-Y.NYB": ("US", "fx", "US Dollar Index"),
    "^TNX": ("US", "yield", "US 10Y Treasury yield"),
    "CL=F": ("GLOBAL", "commodity", "WTI crude oil"),
    "GC=F": ("GLOBAL", "commodity", "Gold"),
    "HG=F": ("GLOBAL", "commodity", "Copper"),
    "NVDA": ("US", "stock", "NVIDIA"),
    "MSFT": ("US", "stock", "Microsoft"),
    "AAPL": ("US", "stock", "Apple"),
    "AMZN": ("US", "stock", "Amazon"),
    "GOOGL": ("US", "stock", "Alphabet"),
    "META": ("US", "stock", "Meta Platforms"),
    "TSLA": ("US", "stock", "Tesla"),
    "AVGO": ("US", "stock", "Broadcom"),
    "JPM": ("US", "stock", "JPMorgan Chase"),
    "GS": ("US", "stock", "Goldman Sachs"),
    "BAC": ("US", "stock", "Bank of America"),
    "WFC": ("US", "stock", "Wells Fargo"),
    "C": ("US", "stock", "Citigroup"),
    "IBM": ("US", "stock", "IBM"),
    "005930.KS": ("KR", "stock", "Samsung Electronics"),
    "000660.KS": ("KR", "stock", "SK Hynix"),
    "005380.KS": ("KR", "stock", "Hyundai Motor"),
    "035420.KS": ("KR", "stock", "NAVER"),
    "035720.KS": ("KR", "stock", "Kakao"),
    "051910.KS": ("KR", "stock", "LG Chem"),
    "006400.KS": ("KR", "stock", "Samsung SDI"),
}

FRED_SERIES = {
    "CPIAUCSL": ("US", "Consumer Price Index", "Index 1982-84=100", "monthly"),
    "CPILFESL": ("US", "Core Consumer Price Index", "Index 1982-84=100", "monthly"),
    "PCEPI": ("US", "PCE Price Index", "Index 2017=100", "monthly"),
    "PCEPILFE": ("US", "Core PCE Price Index", "Index 2017=100", "monthly"),
    "PAYEMS": ("US", "Nonfarm Payroll Employment", "Thousands of persons", "monthly"),
    "UNRATE": ("US", "Unemployment Rate", "Percent", "monthly"),
    "RSAFS": ("US", "Retail Sales", "Millions of dollars", "monthly"),
    "INDPRO": ("US", "Industrial Production Index", "Index 2017=100", "monthly"),
    "FEDFUNDS": ("US", "Effective Federal Funds Rate", "Percent", "monthly"),
    "DGS2": ("US", "2-Year Treasury Yield", "Percent", "daily"),
    "DGS10": ("US", "10-Year Treasury Yield", "Percent", "daily"),
    "T10Y2Y": ("US", "10Y minus 2Y Treasury Spread", "Percent", "daily"),
    "VIXCLS": ("US", "CBOE Volatility Index", "Index", "daily"),
    "DEXKOUS": ("KR", "South Korean Won per U.S. Dollar", "KRW per USD", "daily"),
}

CURATED_DOCUMENTS = [
    (
        "US", "labor", "The Employment Situation — June 2026", "2026-07-02T08:30:00-04:00",
        "U.S. Bureau of Labor Statistics", "https://www.bls.gov/news.release/empsit.htm",
        "Nonfarm payroll employment increased by 57,000; unemployment was 4.2%; average hourly earnings rose 0.3% month over month and 3.5% year over year.",
    ),
    (
        "US", "inflation", "Consumer Price Index — June 2026", "2026-07-14T08:30:00-04:00",
        "U.S. Bureau of Labor Statistics", "https://www.bls.gov/news.release/archives/cpi_07142026.htm",
        "Headline CPI fell 0.4% month over month and rose 3.5% year over year; core CPI was unchanged month over month and rose 2.6% year over year.",
    ),
    (
        "US", "inflation", "Producer Price Index — June 2026", "2026-07-15T08:30:00-04:00",
        "U.S. Bureau of Labor Statistics", "https://www.bls.gov/news.release/ppi.htm",
        "Final-demand PPI fell 0.3% month over month and rose 5.5% year over year; goods fell 1.4% and services rose 0.2%.",
    ),
    (
        "US", "monetary_policy", "Monetary Policy Report — July 2026", "2026-07-10",
        "Federal Reserve Board", "https://www.federalreserve.gov/monetarypolicy/2026-07-mpr-summary.htm",
        "The policy target remained 3.50%-3.75%. The Fed described inflation as elevated, the labor market as broadly stable, and first-quarter GDP growth as moderate.",
    ),
    (
        "US", "monetary_policy", "Minutes of the June 16-17, 2026 FOMC meeting", "2026-07-08T14:00:00-04:00",
        "Federal Reserve Board", "https://www.federalreserve.gov/monetarypolicy/files/fomcminutes20260617.pdf",
        "Official minutes for the June meeting, released July 8, covering the decision to maintain the 3.50%-3.75% target range.",
    ),
    (
        "KR", "monetary_policy", "통화정책방향(2026.7.16)", "2026-07-16",
        "한국은행", "https://www.bok.or.kr/portal/bbs/P0000559/view.do?menuNo=200690&nttId=11062942",
        "한국은행은 기준금리를 2.50%에서 2.75%로 0.25%p 인상했다. 6월 소비자물가 상승률은 3.2%, 근원물가는 2.5%로 제시했다.",
    ),
    (
        "KR", "external_balance", "2026년 5월 국제수지(잠정)", "2026-07-08",
        "한국은행", "https://www.bok.or.kr/portal/main/main.do?menuNo=200690",
        "2026년 5월 경상수지는 386.1억달러 흑자로 발표됐다.",
    ),
    (
        "KR", "earnings", "삼성전자 2026년 2분기 잠정실적", "2026-07-07",
        "Samsung Newsroom Korea", "https://news.samsung.com/kr/삼성전자-2026년-2분기-잠정실적-발표",
        "연결 기준 잠정 매출 171조원, 영업이익 89.4조원. 전분기 대비 매출 27.74%, 영업이익 56.21% 증가.",
    ),
    (
        "US", "earnings", "Goldman Sachs 2026 second-quarter results", "2026-07-14",
        "Goldman Sachs", "https://www.goldmansachs.com/pressroom/press-releases/2026/2026-07-14-q2-results",
        "Goldman Sachs reported net revenue of $20.34 billion, net earnings of $6.63 billion, diluted EPS of $20.98, and annualized ROE of 23.5%.",
    ),
    (
        "US", "earnings", "Large U.S. banks report strong second-quarter results", "2026-07-14",
        "Associated Press", "https://apnews.com/article/jpmorgan-bank-earnings-economy-trading-markets-d56b36051dbaef8be234d86b49f8f620",
        "Major banks reported strong results led by trading, investment banking, and resilient consumer activity. JPMorgan adjusted EPS was $6.14; Wells Fargo net income was $6.4 billion; Bank of America net income was $9.1 billion.",
    ),
    (
        "US", "markets", "U.S. stocks rise after June CPI release", "2026-07-14",
        "Associated Press", "https://apnews.com/article/6807d21c72974fbac48356f83eeebbce",
        "Stocks rose and Treasury yields eased after June CPI showed slowing monthly inflation; market pricing assigned less than a 17% probability to a Fed hike at the next meeting.",
    ),
    (
        "KR", "monetary_policy", "BOK hikes rate amid inflation and won weakness", "2026-07-16",
        "Reuters", "https://www.investing.com/news/economy-news/bok-hikes-rates-for-first-time-in-312-years-to-combat-inflation-won-slump-4794588",
        "The Bank of Korea raised its benchmark rate to 2.75%. The report connected the decision to persistent inflation, won weakness, and financial-stability risks.",
    ),
    (
        "KR", "trade", "2026년 6월 월간 수출입 현황 확정치", "2026-07-15",
        "관세청", "https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do?nttSn=10170123&nttSnUrl=dfb439d5b7e33bf1537aea7874715abd",
        "6월 수출은 1,022억달러로 전년 동월 대비 70.7% 증가했고 수입은 661억달러로 30.0% 증가했다. 무역수지는 361억달러 흑자였으며 반도체 수출은 449억달러였다.",
    ),
    (
        "US", "consumption", "Advance Monthly Retail Trade — June 2026", "2026-07-16T08:30:00-04:00",
        "U.S. Census Bureau", "https://www.census.gov/retail/index.html",
        "Retail sales rose 0.2% month over month after a revised 1.0% increase in May; excluding gasoline stations, sales rose 0.7%.",
    ),
    (
        "US", "production", "Industrial Production and Capacity Utilization — June 2026", "2026-07-17T09:15:00-04:00",
        "Federal Reserve Board", "https://www.federalreserve.gov/RELEASES/g17/Current/",
        "Industrial production increased 0.1% in June and grew at a 4.0% annual rate in the second quarter.",
    ),
    (
        "KR", "inflation", "2026년 6월 소비자물가동향", "2026-07-02T08:00:00+09:00",
        "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=213&list_no=445720&mid=a10301040200",
        "소비자물가는 전월 대비 0.1%, 전년 동월 대비 3.2% 상승했다. 식료품·에너지 제외 근원물가는 전월 대비 보합, 전년 대비 2.5% 상승했다.",
    ),
    (
        "KR", "labor", "2026년 6월 고용동향", "2026-07-15T08:00:00+09:00",
        "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=210&list_no=445948&mid=a10301030100",
        "취업자는 2,915만4천명으로 전년 동월 대비 6만3천명 증가했다. 실업률은 2.8%, 청년층 실업률은 7.0%, 15~64세 고용률은 70.2%였다.",
    ),
]

CURATED_MACRO = [
    ("KR_POLICY_RATE", "KR", "Bank of Korea Base Rate", "2026-07-16", 2.75, "Percent", "event", 2.50, "2026-07-16", "한국은행", "https://www.bok.or.kr/portal/bbs/P0000559/view.do?menuNo=200690&nttId=11062942"),
    ("KR_CPI_YOY", "KR", "Consumer Price Inflation YoY", "2026-06-01", 3.2, "Percent", "monthly", None, "2026-07-02", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=213&list_no=445720&mid=a10301040200"),
    ("KR_CORE_CPI_YOY", "KR", "Core Consumer Price Inflation YoY", "2026-06-01", 2.5, "Percent", "monthly", None, "2026-07-02", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=213&list_no=445720&mid=a10301040200"),
    ("KR_EXPORTS", "KR", "Exports", "2026-06-01", 102_166, "Million USD", "monthly", 87_605, "2026-07-15", "관세청", "https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do?nttSn=10170123&nttSnUrl=dfb439d5b7e33bf1537aea7874715abd"),
    ("KR_IMPORTS", "KR", "Imports", "2026-06-01", 66_078, "Million USD", "monthly", 60_757, "2026-07-15", "관세청", "https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do?nttSn=10170123&nttSnUrl=dfb439d5b7e33bf1537aea7874715abd"),
    ("KR_TRADE_BALANCE", "KR", "Trade Balance", "2026-06-01", 36_088, "Million USD", "monthly", 26_848, "2026-07-15", "관세청", "https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do?nttSn=10170123&nttSnUrl=dfb439d5b7e33bf1537aea7874715abd"),
    ("KR_SEMI_EXPORTS", "KR", "Semiconductor Exports", "2026-06-01", 44_900, "Million USD", "monthly", None, "2026-07-15", "관세청", "https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do?nttSn=10170123&nttSnUrl=dfb439d5b7e33bf1537aea7874715abd"),
    ("US_RETAIL_SALES_MOM", "US", "Retail Sales MoM", "2026-06-01", 0.2, "Percent", "monthly", 1.0, "2026-07-16", "U.S. Census Bureau", "https://www.census.gov/retail/index.html"),
    ("US_INDUSTRIAL_PRODUCTION_MOM", "US", "Industrial Production MoM", "2026-06-01", 0.1, "Percent", "monthly", None, "2026-07-17", "Federal Reserve Board", "https://www.federalreserve.gov/RELEASES/g17/Current/"),
    ("KR_CPI_MOM", "KR", "Consumer Price Inflation MoM", "2026-06-01", 0.1, "Percent", "monthly", None, "2026-07-02", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=213&list_no=445720&mid=a10301040200"),
    ("KR_EMPLOYED", "KR", "Employed Persons", "2026-06-01", 29_154, "Thousands of persons", "monthly", None, "2026-07-15", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=210&list_no=445948&mid=a10301030100"),
    ("KR_EMPLOYMENT_CHANGE_YOY", "KR", "Employment Change YoY", "2026-06-01", 63, "Thousands of persons", "monthly", None, "2026-07-15", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=210&list_no=445948&mid=a10301030100"),
    ("KR_UNEMPLOYMENT_RATE", "KR", "Unemployment Rate", "2026-06-01", 2.8, "Percent", "monthly", None, "2026-07-15", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=210&list_no=445948&mid=a10301030100"),
    ("KR_YOUTH_UNEMPLOYMENT_RATE", "KR", "Youth Unemployment Rate", "2026-06-01", 7.0, "Percent", "monthly", None, "2026-07-15", "국가데이터처", "https://mods.go.kr/board.es?act=view&bid=210&list_no=445948&mid=a10301030100"),
]

SCHEMA = """
alter table telegram_messages add column normalized_hash text;
"""

EXTRA_SCHEMA = """
create table if not exists message_tags (
    message_id integer not null,
    tag text not null,
    primary key (message_id, tag),
    foreign key (message_id) references telegram_messages(id)
);
create table if not exists extracted_links (
    message_id integer not null,
    url text not null,
    domain text,
    primary key (message_id, url),
    foreign key (message_id) references telegram_messages(id)
);
create table if not exists market_prices (
    symbol text not null,
    name text not null,
    country text not null,
    asset_class text not null,
    price_date text not null,
    open real,
    high real,
    low real,
    close real,
    adjusted_close real,
    volume real,
    currency text,
    source text not null,
    source_url text not null,
    collected_at text not null,
    primary key (symbol, price_date)
);
create table if not exists macro_observations (
    series_id text not null,
    country text not null,
    indicator text not null,
    observation_date text not null,
    value real,
    unit text,
    frequency text,
    previous_value real,
    release_date text,
    source text not null,
    source_url text not null,
    collected_at text not null,
    primary key (series_id, observation_date)
);
create table if not exists earnings_events (
    country text not null,
    company text not null,
    ticker text,
    fiscal_period text,
    announced_at text not null,
    revenue real,
    operating_income real,
    net_income real,
    eps real,
    currency text,
    guidance text,
    source text not null,
    source_url text not null,
    raw_json text,
    primary key (company, announced_at, fiscal_period)
);
create table if not exists source_documents (
    id integer primary key,
    country text,
    topic text not null,
    title text not null,
    published_at text,
    source text not null,
    source_url text not null unique,
    factual_summary text,
    collected_at text not null
);
"""


def ensure_schema(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("pragma table_info(telegram_messages)")}
    if "normalized_hash" not in columns:
        connection.execute(SCHEMA)
    connection.executescript(EXTRA_SCHEMA)


def normalize_text(text: str) -> str:
    text = URL_RE.sub("", text.lower())
    return SPACE_RE.sub(" ", text).strip()


def classify_messages(connection: sqlite3.Connection) -> None:
    rows = connection.execute("select id, text from telegram_messages").fetchall()
    counts = Counter()
    for message_id, text in rows:
        text = text or ""
        normalized = normalize_text(text)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else None
        connection.execute(
            "update telegram_messages set normalized_hash=? where id=?", (digest, message_id)
        )

        lowered = text.lower()
        for tag, keywords in CATEGORIES.items():
            if any(keyword in lowered for keyword in keywords):
                connection.execute(
                    "insert or ignore into message_tags(message_id, tag) values (?, ?)",
                    (message_id, tag),
                )
                counts[tag] += 1

        for url in URL_RE.findall(text):
            clean_url = url.rstrip(".,;:)]}")
            domain = urllib.parse.urlparse(clean_url).netloc.lower()
            connection.execute(
                "insert or ignore into extracted_links(message_id, url, domain) values (?, ?, ?)",
                (message_id, clean_url, domain),
            )
    print("message_tags=" + json.dumps(counts, ensure_ascii=False, sort_keys=True))


def yahoo_chart(symbol: str, start: datetime, end: datetime) -> dict:
    encoded = urllib.parse.quote(symbol, safe="")
    params = urllib.parse.urlencode(
        {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": "1d", "events": "history"}
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response), url


def collect_market_prices(connection: sqlite3.Connection, days: int) -> None:
    end = datetime.now(timezone.utc) + timedelta(days=1)
    start = end - timedelta(days=days + 10)
    collected_at = datetime.now(timezone.utc).isoformat()
    successes = 0
    failures = []

    for symbol, (country, asset_class, name) in ASSETS.items():
        try:
            payload, url = yahoo_chart(symbol, start, end)
            result = payload["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quote = result["indicators"]["quote"][0]
            adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
            currency = result.get("meta", {}).get("currency")

            for index, timestamp in enumerate(timestamps):
                price_date = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
                values = []
                for field in ("open", "high", "low", "close", "volume"):
                    series = quote.get(field, [])
                    values.append(series[index] if index < len(series) else None)
                adjusted_close = adjusted[index] if index < len(adjusted) else values[3]
                connection.execute(
                    """
                    insert or replace into market_prices values
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol, name, country, asset_class, price_date,
                        values[0], values[1], values[2], values[3], adjusted_close, values[4],
                        currency, "Yahoo Finance", url, collected_at,
                    ),
                )
            successes += 1
        except Exception as error:
            failures.append(f"{symbol}: {error}")

    print(f"market_assets={successes}/{len(ASSETS)}")
    if failures:
        print("market_failures=" + json.dumps(failures, ensure_ascii=False))


def collect_fred_series(connection: sqlite3.Connection) -> None:
    collected_at = datetime.now(timezone.utc).isoformat()
    start_date = (datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat()
    successes = 0
    failures = []

    for series_id, (country, indicator, unit, frequency) in FRED_SERIES.items():
        url = (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?"
            + urllib.parse.urlencode({"id": series_id, "cosd": start_date})
        )
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read().decode("utf-8-sig")
            observations = []
            for row in csv.DictReader(io.StringIO(content)):
                raw_value = row.get(series_id)
                if not raw_value or raw_value == ".":
                    continue
                date_value = row.get("DATE") or row.get("observation_date")
                if not date_value:
                    raise ValueError(f"Unexpected FRED columns: {list(row)}")
                observations.append((date_value, float(raw_value)))

            previous = None
            for observation_date, value in observations:
                connection.execute(
                    """
                    insert or replace into macro_observations (
                        series_id, country, indicator, observation_date, value,
                        unit, frequency, previous_value, release_date, source,
                        source_url, collected_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        series_id, country, indicator, observation_date, value,
                        unit, frequency, previous, None, "FRED", url, collected_at,
                    ),
                )
                previous = value
            successes += 1
        except Exception as error:
            failures.append(f"{series_id}: {error}")

    print(f"macro_series={successes}/{len(FRED_SERIES)}")
    if failures:
        print("macro_failures=" + json.dumps(failures, ensure_ascii=False))


def insert_curated_documents(connection: sqlite3.Connection) -> None:
    collected_at = datetime.now(timezone.utc).isoformat()
    for country, topic, title, published_at, source, url, summary in CURATED_DOCUMENTS:
        connection.execute(
            """
            insert or replace into source_documents (
                id, country, topic, title, published_at, source, source_url,
                factual_summary, collected_at
            ) values (
                (select id from source_documents where source_url=?), ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (url, country, topic, title, published_at, source, url, summary, collected_at),
        )

    for row in CURATED_MACRO:
        connection.execute(
            """
            insert or replace into macro_observations (
                series_id, country, indicator, observation_date, value,
                unit, frequency, previous_value, release_date, source,
                source_url, collected_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*row, collected_at),
        )

    connection.execute(
        """
        insert or replace into earnings_events (
            country, company, ticker, fiscal_period, announced_at, revenue,
            operating_income, net_income, eps, currency, guidance, source,
            source_url, raw_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "KR", "Samsung Electronics", "005930.KS", "2026Q2", "2026-07-07",
            171_000_000_000_000, 89_400_000_000_000, None, None, "KRW",
            "Preliminary consolidated earnings guidance; final results pending.",
            "Samsung Newsroom Korea",
            "https://news.samsung.com/kr/삼성전자-2026년-2분기-잠정실적-발표",
            json.dumps({"revenue_trillion_krw": 171, "operating_profit_trillion_krw": 89.4}),
        ),
    )

    additional_earnings = [
        (
            "US", "Goldman Sachs", "GS", "2026Q2", "2026-07-14",
            20_340_000_000, None, 6_630_000_000, 20.98, "USD",
            "Management said transaction and client-activity momentum had accelerated.",
            "Goldman Sachs",
            "https://www.goldmansachs.com/pressroom/press-releases/2026/2026-07-14-q2-results",
        ),
        (
            "US", "JPMorgan Chase", "JPM", "2026Q2", "2026-07-14",
            58_000_000_000, None, 21_200_000_000, 6.14, "USD",
            "Managed revenue; reported profit included a one-time Visa-related gain; EPS is adjusted.",
            "Reuters / Associated Press",
            "https://www.marketscreener.com/news/jpmorgan-profit-rises-on-investment-banking-boom-ce7f5edcd189f122",
        ),
        (
            "US", "Bank of America", "BAC", "2026Q2", "2026-07-14",
            None, None, 9_100_000_000, 1.21, "USD",
            "Full-year net-interest-income growth expected at the upper end of the prior 6%-8% range.",
            "Reuters",
            "https://www.investing.com/news/stock-market-news/bank-of-america-profit-rises-on-trading-boost-4790403",
        ),
        (
            "US", "Wells Fargo", "WFC", "2026Q2", "2026-07-14",
            22_600_000_000, None, 6_400_000_000, None, "USD",
            "Consumer activity improved; revenue and net income figures reported by AP from company results.",
            "Associated Press",
            "https://apnews.com/article/jpmorgan-bank-earnings-economy-trading-markets-d56b36051dbaef8be234d86b49f8f620",
        ),
    ]
    for row in additional_earnings:
        connection.execute(
            """
            insert or replace into earnings_events (
                country, company, ticker, fiscal_period, announced_at, revenue,
                operating_income, net_income, eps, currency, guidance, source,
                source_url, raw_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*row, None),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich the disposable catch-up database.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--days", type=int, default=21)
    args = parser.parse_args()

    with sqlite3.connect(args.db) as connection:
        ensure_schema(connection)
        classify_messages(connection)
        collect_market_prices(connection, args.days)
        collect_fred_series(connection)
        insert_curated_documents(connection)
        connection.commit()

        print("messages=" + str(connection.execute("select count(*) from telegram_messages").fetchone()[0]))
        print("tagged=" + str(connection.execute("select count(distinct message_id) from message_tags").fetchone()[0]))
        print("links=" + str(connection.execute("select count(*) from extracted_links").fetchone()[0]))
        print("prices=" + str(connection.execute("select count(*) from market_prices").fetchone()[0]))
        print("macro=" + str(connection.execute("select count(*) from macro_observations").fetchone()[0]))
        print("documents=" + str(connection.execute("select count(*) from source_documents").fetchone()[0]))
        print("earnings=" + str(connection.execute("select count(*) from earnings_events").fetchone()[0]))


if __name__ == "__main__":
    main()
