from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        type=Path,
        default=ROOT_DIR / "data" / "insidertracking_catchup.sqlite3",
    )
    args = parser.parse_args()

    with sqlite3.connect(args.db) as connection:
        connection.row_factory = sqlite3.Row
        print("TABLE COUNTS")
        for table in (
            "telegram_messages", "message_tags", "extracted_links", "market_prices",
            "macro_observations", "source_documents", "earnings_events",
        ):
            count = connection.execute(f"select count(*) from {table}").fetchone()[0]
            print(f"{table}: {count}")

        print("\nMARKET MOVES")
        rows = connection.execute(
            """
            with ranked as (
                select *,
                    row_number() over (partition by symbol order by price_date) as first_rank,
                    row_number() over (partition by symbol order by price_date desc) as last_rank
                from market_prices
                where close is not null
                  and price_date >= date('now', '-21 days')
            ), first_last as (
                select symbol, name, country, asset_class,
                    max(case when first_rank=1 then price_date end) as start_date,
                    max(case when first_rank=1 then close end) as start_close,
                    max(case when last_rank=1 then price_date end) as end_date,
                    max(case when last_rank=1 then close end) as end_close
                from ranked
                group by symbol, name, country, asset_class
            )
            select *, round((end_close / start_close - 1) * 100, 2) as change_pct
            from first_last
            order by country, asset_class, symbol
            """
        ).fetchall()
        for row in rows:
            print(
                f"{row['symbol']:10} {row['name'][:28]:28} "
                f"{row['start_date']} {row['start_close']:.2f} -> "
                f"{row['end_date']} {row['end_close']:.2f} ({row['change_pct']:+.2f}%)"
            )

        print("\nCURATED DOCUMENTS")
        for row in connection.execute(
            "select published_at, country, topic, source, title from source_documents order by published_at"
        ):
            print(f"{row['published_at']} [{row['country']}/{row['topic']}] {row['source']} - {row['title']}")


if __name__ == "__main__":
    main()
