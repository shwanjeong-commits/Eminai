"""Export cached FRED observations without copying the production news database."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import bootstrap  # noqa: E402,F401
from fred_indicator_data import FRED_INDICATOR_SERIES  # noqa: E402
from ism_data import ISM_SERIES_IDS  # noqa: E402


SEED_SERIES = (*FRED_INDICATOR_SERIES, *ISM_SERIES_IDS.values())


def main() -> None:
    source = ROOT / "data" / "news.db"
    target = ROOT / "deploy" / "macro_observations_seed.json"
    connection = sqlite3.connect(source)
    try:
        placeholders = ",".join("?" for _ in SEED_SERIES)
        rows = connection.execute(
            f"""select series_id, observed_at, value
                from macro_observations
                where series_id in ({placeholders})
                order by series_id, observed_at""",
            SEED_SERIES,
        ).fetchall()
    finally:
        connection.close()

    series = {series_id: [] for series_id in SEED_SERIES}
    for series_id, observed_at, value in rows:
        series[series_id].append([observed_at, value])
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "Locally cached official FRED observations",
        "series": series,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Exported {len(rows)} observations to {target}")


if __name__ == "__main__":
    main()
