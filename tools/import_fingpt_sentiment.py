from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT_DIR / "data" / "insidertracking_catchup.sqlite3"

CATEGORY_BY_RANGE = (
    (1, 9, "us_macro"),
    (10, 18, "kr_macro"),
    (19, 29, "cross_asset_markets"),
    (30, 32, "us_equities"),
    (33, 38, "kr_equities"),
    (39, 44, "earnings"),
    (45, 56, "market_drivers"),
    (57, 62, "upcoming_calendar"),
    (63, 66, "analysis_instruction"),
)

# Human review does not overwrite the model result. "mixed" is allowed because
# macro facts often have different implications across assets.
REVIEWED = {
    1: ("mixed", "Lower monthly CPI is supportive, but 3.5% YoY remains elevated."),
    2: ("positive", "Core disinflation is supportive for rate-sensitive assets."),
    3: ("mixed", "Monthly PPI fell, while the 5.5% annual rate remains high."),
    4: ("mixed", "Payroll growth was weak, but unemployment remained stable."),
    5: ("mixed", "Income growth supports consumption but can sustain inflation pressure."),
    6: ("positive", "Retail sales remained positive."),
    7: ("positive", "Production expanded."),
    8: ("neutral", "Policy was unchanged."),
    9: ("mixed", "Stable labor is positive; elevated inflation is negative."),
    10: ("mixed", "A hike can support the won but pressure equity valuations."),
    11: ("negative", "Inflation exceeded the BOK target."),
    12: ("negative", "Core inflation exceeded the BOK target."),
    13: ("positive", "Employment increased."),
    14: ("negative", "Youth unemployment was elevated."),
    15: ("positive", "Exports grew strongly."),
    16: ("mixed", "Imports grew, which can reflect demand but also higher costs."),
    17: ("positive", "A large trade surplus supports external balances."),
    18: ("positive", "Strong semiconductor exports support Korean growth."),
    19: ("positive", "The index increased."),
    20: ("negative", "The index declined."),
    21: ("neutral", "The change was close to zero."),
    22: ("negative", "The index declined."),
    23: ("negative", "The index entered a major drawdown."),
    24: ("negative", "The index declined sharply."),
    25: ("positive", "A lower USD/KRW means the won strengthened; exporter effects can differ."),
    26: ("mixed", "Higher yields help some financials but pressure duration-sensitive assets."),
    27: ("mixed", "Positive for oil exposure, negative for inflation and energy importers."),
    28: ("neutral", "The price change was close to zero."),
    29: ("positive", "Copper increased and can signal firm industrial demand."),
    30: ("positive", "The selected shares increased."),
    31: ("negative", "The selected shares declined."),
    32: ("positive", "The selected bank shares increased."),
    33: ("negative", "The share price declined sharply."),
    34: ("negative", "The share price declined sharply."),
    35: ("negative", "The share price declined."),
    36: ("negative", "The share price declined."),
    37: ("negative", "The share price declined."),
    38: ("negative", "NAVER declined and outweighed Kakao's small gain."),
    39: ("positive", "The preliminary earnings figures were strong."),
    40: ("positive", "Profitability and ROE were strong."),
    41: ("positive", "Trading and investment banking were strong."),
    42: ("positive", "The company reported strong profit."),
    43: ("positive", "Revenue and net income were strong."),
    44: ("positive", "Bank operating conditions were supportive."),
    45: ("negative", "Geopolitical supply risk increased oil and inflation risk."),
    46: ("positive", "Lower immediate Fed-hike expectations support risk assets."),
    47: ("negative", "Semiconductor shares sold off on demand concerns."),
    48: ("negative", "The KOSPI entered bear-market territory."),
    49: ("negative", "The KOSPI fell sharply amid multiple risks."),
    50: ("negative", "Strong earnings failed to prevent falling share prices."),
    51: ("negative", "Inflation and financial-stability risks prompted tightening."),
    52: ("positive", "AI spending supports Korean memory demand."),
    53: ("negative", "US semiconductor weakness can amplify Korean losses."),
    54: ("negative", "Higher oil raises inflation and import costs for Korea."),
    55: ("negative", "Higher US yields and dollar strength pressure Korean assets."),
    56: ("mixed", "Won support and equity-valuation pressure point in opposite directions."),
}


def category(number: int) -> str:
    for start, end, value in CATEGORY_BY_RANGE:
        if start <= number <= end:
            return value
    return "unknown"


def country(number: int, text: str) -> str:
    if 1 <= number <= 9 or 30 <= number <= 32:
        return "US"
    if 10 <= number <= 18 or 33 <= number <= 39:
        return "KR"
    lowered = text.lower()
    has_us = any(term in lowered for term in ("us ", "federal reserve", "fed ", "s&p", "nasdaq"))
    has_kr = any(term in lowered for term in ("korea", "kospi", "kosdaq", "won", "samsung", "hynix"))
    if has_us and has_kr:
        return "CROSS"
    if has_us:
        return "US"
    if has_kr:
        return "KR"
    return "GLOBAL"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    schema = """
    create table if not exists fingpt_sentiment_results (
        item_number integer primary key,
        text text not null,
        model_sentiment text not null,
        raw_output text,
        country text not null,
        category text not null,
        is_market_fact integer not null,
        reviewed_sentiment text,
        review_note text,
        imported_at text not null
    );
    """

    imported_at = datetime.now(timezone.utc).isoformat()
    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))

    with sqlite3.connect(args.db) as connection:
        connection.executescript(schema)
        for row in rows:
            number = int(row["number"])
            text = row["text"]
            reviewed_sentiment, note = REVIEWED.get(number, (None, None))
            is_market_fact = int(number <= 56)
            connection.execute(
                """
                insert or replace into fingpt_sentiment_results values
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    number, text, row["sentiment"], row["raw_output"],
                    country(number, text), category(number), is_market_fact,
                    reviewed_sentiment, note, imported_at,
                ),
            )
        connection.commit()

        print("all_rows=" + str(connection.execute("select count(*) from fingpt_sentiment_results").fetchone()[0]))
        print("market_facts=" + str(connection.execute("select count(*) from fingpt_sentiment_results where is_market_fact=1").fetchone()[0]))
        print("model_unknown_market_facts=" + str(connection.execute("select count(*) from fingpt_sentiment_results where is_market_fact=1 and model_sentiment='unknown'").fetchone()[0]))
        print("reviewed_distribution")
        for sentiment, count in connection.execute(
            """
            select reviewed_sentiment, count(*)
            from fingpt_sentiment_results
            where is_market_fact=1
            group by reviewed_sentiment
            order by count(*) desc
            """
        ):
            print(f"{sentiment}={count}")


if __name__ == "__main__":
    main()
