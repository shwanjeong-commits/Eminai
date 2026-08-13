"""Fetch the latest official ISM manufacturing and services PMI reports."""

from __future__ import annotations

import calendar
from datetime import date
from html import unescape
import json
from pathlib import Path
import re
import ssl
import time
from urllib.request import Request, urlopen

import certifi

from database import connect


ISM_TIMEOUT_SECONDS = 5
ISM_BASE_URL = "https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports"
ISM_SERIES_IDS = {
    "manufacturing": "ISM_MANUFACTURING_PMI",
    "services": "ISM_SERVICES_PMI",
}
ISM_SEED_PATH = Path(__file__).resolve().parent.parent / "deploy" / "macro_observations_seed.json"


def _month_candidates(today: date | None = None) -> list[str]:
    current = today or date.today()
    year = current.year
    month = current.month
    candidates = []
    for _ in range(3):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        candidates.append(calendar.month_name[month].lower())
    return candidates


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 EMINAI-Watch/1.0"})
    context = ssl.create_default_context(cafile=certifi.where())
    last_error = None
    try:
        with urlopen(request, timeout=ISM_TIMEOUT_SECONDS, context=context) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as error:
        last_error = error
        raise last_error


def _plain_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _parse_report(html: str, kind: str, source_url: str) -> dict:
    text = _plain_text(html)
    heading = re.search(r"([A-Z][a-z]+)\s+(20\d{2})\s+ISM", text)
    if not heading:
        raise ValueError("ISM 보고서 기준 월을 찾지 못했습니다")

    if kind == "manufacturing":
        patterns = [
            r"Manufacturing PMI.{0,50}?at\s+([0-9]+(?:\.[0-9]+)?)\s*%",
            r"Manufacturing PMI.{0,120}?registered\s+([0-9]+(?:\.[0-9]+)?)\s+percent",
        ]
    else:
        patterns = [
            r"Services PMI.{0,50}?at\s+([0-9]+(?:\.[0-9]+)?)\s*%",
            r"Services PMI.{0,120}?registered\s+([0-9]+(?:\.[0-9]+)?)\s+percent",
        ]

    match = next((match for pattern in patterns if (match := re.search(pattern, text, re.IGNORECASE))), None)
    if not match:
        raise ValueError("ISM PMI 수치를 찾지 못했습니다")

    month_number = list(calendar.month_name).index(heading.group(1))
    return {
        "value": float(match.group(1)),
        "asOf": f"{heading.group(2)}-{month_number:02d}-01",
        "sourceUrl": source_url,
    }


def _store_report(kind: str, report: dict) -> None:
    series_id = ISM_SERIES_IDS[kind]
    title = "ISM 제조업 PMI" if kind == "manufacturing" else "ISM 서비스업 PMI"
    connection = connect()
    try:
        connection.execute(
            """insert into macro_series(series_id,title,provider,frequency,unit,source_url)
               values (?, ?, 'ISM', 'monthly', 'index', ?)
               on conflict(series_id) do update set
                 title=excluded.title,provider='ISM',source_url=excluded.source_url,
                 last_synced_at=current_timestamp,updated_at=current_timestamp""",
            (series_id, title, report["sourceUrl"]),
        )
        connection.execute(
            """insert into macro_observations(series_id,observed_at,value)
               values (?,?,?)
               on conflict(series_id,observed_at) do update set value=excluded.value""",
            (series_id, report["asOf"], report["value"]),
        )
        connection.commit()
    finally:
        connection.close()


def _cached_report(kind: str) -> dict | None:
    connection = connect()
    try:
        row = connection.execute(
            """select o.observed_at,o.value,s.source_url
               from macro_observations o join macro_series s using(series_id)
               where o.series_id=? order by o.observed_at desc limit 1""",
            (ISM_SERIES_IDS[kind],),
        ).fetchone()
    finally:
        connection.close()
    if row:
        return {"value": float(row["value"]), "asOf": row["observed_at"], "sourceUrl": row["source_url"]}
    try:
        payload = json.loads(ISM_SEED_PATH.read_text(encoding="utf-8"))
        observations = payload.get("series", {}).get(ISM_SERIES_IDS[kind], [])
        observed_at, value = observations[-1]
    except Exception:
        return None
    segment = "pmi" if kind == "manufacturing" else "services"
    month_name = calendar.month_name[int(observed_at[5:7])].lower()
    report = {
        "value": float(value),
        "asOf": observed_at,
        "sourceUrl": f"{ISM_BASE_URL}/{segment}/{month_name}/",
    }
    try:
        _store_report(kind, report)
    except Exception:
        pass
    return report


def fetch_ism_report(kind: str) -> dict:
    if kind not in {"manufacturing", "services"}:
        raise ValueError("unknown ISM report type")
    segment = "pmi" if kind == "manufacturing" else "services"
    errors = []
    for month_name in _month_candidates()[:2]:
        url = f"{ISM_BASE_URL}/{segment}/{month_name}/"
        reader_url = "https://r.jina.ai/http://www.ismworld.org/" + url.split("ismworld.org/", 1)[1]
        for fetch_url in (url, reader_url):
            try:
                report = _parse_report(_fetch_text(fetch_url), kind, url)
                _store_report(kind, report)
                return report
            except Exception as error:
                errors.append(str(error))
    cached = _cached_report(kind)
    if cached:
        return cached
    raise ValueError("최신 ISM 보고서를 불러오지 못했습니다: " + "; ".join(errors[-2:]))
