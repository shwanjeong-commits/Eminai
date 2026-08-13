"""Fetch and cache the FRED series used by the economic indicator board."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
import io
import json
import os
from pathlib import Path
import ssl
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
import httpx

from config import load_dotenv
from database import connect


FRED_INDICATOR_SERIES = (
    "DFF",
    "PCEPILFE",
    "T10Y2Y",
    "T10Y3M",
    "DFII10",
    "T10YIE",
    "SAHMREALTIME",
    "ICSA",
    "NFCI",
    "BAMLH0A0HYM2",
    "GDPNOW",
    "JTSJOL",
    "UNEMPLOY",
    "JTSQUR",
    "MARTSSM44W72USS",
    "INDPRO",
    "M2SL",
    "WALCL",
    "WTREGEN",
    "RRPONTSYD",
    "DRTSCIS",
    "DRTSCILM",
    "UMCSENT",
    "MICH",
)
FRED_CACHE_TTL_SECONDS = 900
FRED_TIMEOUT_SECONDS = 6
_FRED_CACHE: tuple[float, dict[str, list[dict]]] | None = None
_FRED_CACHE_LOCK = threading.Lock()
FRED_SEED_PATH = Path(__file__).resolve().parent.parent / "deploy" / "macro_observations_seed.json"


def _start_date(years: int = 6) -> str:
    return (date.today() - timedelta(days=365 * years)).isoformat()


def _fred_graph_series(series_id: str, start: str) -> list[dict]:
    query = urlencode({"id": series_id, "cosd": start})
    request = Request(
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?{query}",
        headers={"User-Agent": "EMINAI-Watch/1.0"},
    )
    context = ssl.create_default_context(cafile=certifi.where())
    last_error = None
    try:
        with urlopen(request, timeout=FRED_TIMEOUT_SECONDS, context=context) as response:
            csv_text = response.read().decode("utf-8-sig")
    except Exception as error:
        last_error = error
        raise last_error

    observations = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        observed_at = row.get("observation_date") or row.get("DATE")
        if not observed_at:
            continue
        raw = row.get(series_id)
        if raw in (None, "", "."):
            continue
        observations.append({"date": observed_at, "value": float(raw)})
    if not observations:
        raise ValueError(f"{series_id} FRED CSV 응답에 관측치가 없습니다")
    return observations


def _fred_graph_bundle(start: str) -> dict[str, list[dict]]:
    """Fetch each series separately so a large combined CSV cannot time out."""
    bundle = {series_id: [] for series_id in FRED_INDICATOR_SERIES}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            pool.submit(_fred_graph_series, series_id, start): series_id
            for series_id in FRED_INDICATOR_SERIES
        }
        for future in as_completed(futures):
            series_id = futures[future]
            try:
                bundle[series_id] = future.result()
            except Exception:
                continue
    if not any(bundle.values()):
        raise ValueError("FRED CSV 응답에 관측치가 없습니다")
    return bundle


def _fred_api_series(series_id: str, start: str, api_key: str) -> list[dict]:
    response = httpx.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start,
            "sort_order": "asc",
        },
        headers={"User-Agent": "EMINAI-Watch/1.0"},
        timeout=FRED_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    response.raise_for_status()
    return [
        {"date": item["date"], "value": float(item["value"])}
        for item in response.json().get("observations", [])
        if item.get("value") not in (None, "", ".")
    ]


def _fred_api_bundle(start: str, api_key: str) -> dict[str, list[dict]]:
    bundle = {series_id: [] for series_id in FRED_INDICATOR_SERIES}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            pool.submit(_fred_api_series, series_id, start, api_key): series_id
            for series_id in FRED_INDICATOR_SERIES
        }
        for future in as_completed(futures):
            series_id = futures[future]
            try:
                bundle[series_id] = future.result()
            except Exception:
                continue
    return bundle


def _database_bundle(start: str) -> dict[str, list[dict]]:
    placeholders = ",".join("?" for _ in FRED_INDICATOR_SERIES)
    connection = connect()
    try:
        rows = connection.execute(
            f"""select series_id, observed_at, value
                from macro_observations
                where series_id in ({placeholders}) and observed_at >= ?
                order by observed_at""",
            (*FRED_INDICATOR_SERIES, start),
        ).fetchall()
    finally:
        connection.close()
    bundle = {series_id: [] for series_id in FRED_INDICATOR_SERIES}
    for row in rows:
        bundle[row["series_id"]].append({"date": row["observed_at"], "value": float(row["value"])})
    return bundle


def _seed_bundle(start: str) -> dict[str, list[dict]]:
    bundle = {series_id: [] for series_id in FRED_INDICATOR_SERIES}
    if not FRED_SEED_PATH.exists():
        return bundle
    try:
        payload = json.loads(FRED_SEED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return bundle
    for series_id in FRED_INDICATOR_SERIES:
        for observed_at, value in payload.get("series", {}).get(series_id, []):
            if observed_at >= start:
                bundle[series_id].append({"date": observed_at, "value": float(value)})
    return bundle


def _store_bundle(bundle: dict[str, list[dict]]) -> None:
    """Persist successful observations for use during a later FRED outage."""
    connection = connect()
    try:
        for series_id, observations in bundle.items():
            if not observations:
                continue
            connection.execute(
                """insert into macro_series(series_id,title,provider,frequency,unit,source_url)
                   values (?, ?, 'FRED', 'varies', '', ?)
                   on conflict(series_id) do update set
                     provider='FRED', source_url=excluded.source_url,
                     last_synced_at=current_timestamp, updated_at=current_timestamp""",
                (series_id, series_id, f"https://fred.stlouisfed.org/series/{series_id}"),
            )
            connection.executemany(
                """insert into macro_observations(series_id,observed_at,value)
                   values (?,?,?)
                   on conflict(series_id,observed_at) do update set value=excluded.value""",
                [(series_id, item["date"], item["value"]) for item in observations],
            )
        connection.commit()
    finally:
        connection.close()


def get_fred_indicator_bundle(force: bool = False) -> dict[str, list[dict]]:
    """Return six years of observations, preferring live FRED and then local storage."""
    global _FRED_CACHE
    now = time.time()
    with _FRED_CACHE_LOCK:
        if not force and _FRED_CACHE and now - _FRED_CACHE[0] < FRED_CACHE_TTL_SECONDS:
            return _FRED_CACHE[1]

    load_dotenv()
    start = _start_date()
    try:
        bundle = _fred_graph_bundle(start)
    except Exception:
        bundle = {series_id: [] for series_id in FRED_INDICATOR_SERIES}

    api_key = os.getenv("FRED_API_KEY", "").strip()
    if api_key and any(not bundle.get(series_id) for series_id in FRED_INDICATOR_SERIES):
        api_bundle = _fred_api_bundle(start, api_key)
        for series_id in FRED_INDICATOR_SERIES:
            if not bundle.get(series_id) and api_bundle.get(series_id):
                bundle[series_id] = api_bundle[series_id]

    try:
        _store_bundle(bundle)
    except Exception:
        pass

    local = _database_bundle(start)
    seed = _seed_bundle(start)
    seeded = {}
    for series_id in FRED_INDICATOR_SERIES:
        if not local.get(series_id) and seed.get(series_id):
            local[series_id] = seed[series_id]
            seeded[series_id] = seed[series_id]
    if seeded:
        try:
            _store_bundle(seeded)
        except Exception:
            pass
    for series_id in FRED_INDICATOR_SERIES:
        if not bundle.get(series_id) and local.get(series_id):
            bundle[series_id] = local[series_id]

    with _FRED_CACHE_LOCK:
        _FRED_CACHE = (now, bundle)
    return bundle
