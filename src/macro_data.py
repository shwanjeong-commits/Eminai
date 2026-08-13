"""Sync and analyze selected public FRED macroeconomic time series."""

from __future__ import annotations

import csv
import io
from datetime import date, timedelta

import httpx


SERIES = {
    "DFF": ("미국 연방기금 실효금리", "daily", "%", ["금리", "연준", "정책금리", "fed"]),
    "CPIAUCSL": ("미국 소비자물가지수", "monthly", "index", ["물가", "인플레이션", "cpi"]),
    "PCEPILFE": ("미국 근원 PCE 물가지수", "monthly", "index", ["물가", "인플레이션", "pce", "근원 물가"]),
    "UNRATE": ("미국 실업률", "monthly", "%", ["고용", "실업", "실업률", "경기"]),
    "SAHMREALTIME": ("Sahm Rule 침체 지표", "monthly", "%p", ["경기침체", "sahm", "실업률"]),
    "ICSA": ("미국 신규 실업수당 청구", "weekly", "건", ["고용", "해고", "실업수당"]),
    "T10Y2Y": ("미국 10년-2년 금리차", "daily", "%p", ["장단기 금리차", "수익률곡선", "금리 역전"]),
    "T10Y3M": ("미국 10년-3개월 금리차", "daily", "%p", ["장단기 금리차", "수익률곡선", "금리 역전"]),
    "DFII10": ("미국 10년 실질금리", "daily", "%", ["실질금리", "tips", "할인율"]),
    "T10YIE": ("미국 10년 기대인플레이션", "daily", "%", ["기대인플레이션", "브레이크이븐", "물가 기대"]),
    "NFCI": ("Chicago Fed 금융여건지수", "weekly", "index", ["금융여건", "유동성", "신용"]),
    "BAMLH0A0HYM2": ("미국 하이일드 신용스프레드", "daily", "%p", ["하이일드", "신용스프레드", "회사채"]),
    "GDPNOW": ("Atlanta Fed GDPNow", "quarterly", "% SAAR", ["gdpnow", "성장률", "미국 gdp"]),
    "JTSJOL": ("미국 JOLTS 구인", "monthly", "천건", ["jolts", "구인", "노동수요"]),
    "UNEMPLOY": ("미국 실업자 수", "monthly", "천명", ["실업자", "구인 실업자 비율", "노동시장"]),
    "JTSQUR": ("미국 JOLTS 자발적 퇴직률", "monthly", "%", ["퇴직률", "이직", "jolts"]),
    "MARTSSM44W72USS": ("미국 자동차·주유소 제외 소매판매", "monthly", "백만달러", ["소매판매", "소비", "자동차 제외"]),
    "INDPRO": ("미국 산업생산지수", "monthly", "index", ["산업생산", "제조업", "생산"]),
    "M2SL": ("미국 M2 통화량", "monthly", "십억달러", ["m2", "통화량", "유동성"]),
    "WALCL": ("연준 총자산", "weekly", "백만달러", ["연준 자산", "대차대조표", "유동성"]),
    "WTREGEN": ("미 재무부 TGA", "weekly", "백만달러", ["tga", "재무부 일반계정", "유동성"]),
    "RRPONTSYD": ("연준 역레포", "daily", "십억달러", ["역레포", "rrp", "유동성"]),
    "DRTSCIS": ("SLOOS 소기업 대출기준 긴축", "quarterly", "%", ["sloos", "대출기준", "신용공급"]),
    "DRTSCILM": ("SLOOS 중대형기업 대출기준 긴축", "quarterly", "%", ["sloos", "대출기준", "신용공급"]),
    "UMCSENT": ("미시간대 소비심리지수", "monthly", "index", ["소비심리", "미시간대", "심리"]),
    "MICH": ("미시간대 1년 기대인플레이션", "monthly", "%", ["기대인플레이션", "미시간대", "물가 기대"]),
    "DCOILWTICO": ("WTI 원유 현물가격", "daily", "USD/barrel", ["유가", "원유", "wti", "에너지"]),
    "DEXKOUS": ("원달러 환율", "daily", "KRW/USD", ["환율", "원달러", "달러", "원화"]),
}


def series_url(series_id: str, start: str | None = None) -> str:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    return f"{url}&cosd={start}" if start else url


def register_series(connection) -> None:
    for series_id, (title, frequency, unit, _) in SERIES.items():
        connection.execute(
            """insert into macro_series(series_id,title,provider,frequency,unit,source_url)
               values (?,?, 'FRED', ?, ?, ?)
               on conflict(series_id) do update set title=excluded.title,frequency=excluded.frequency,
                 unit=excluded.unit,source_url=excluded.source_url,updated_at=current_timestamp""",
            (series_id, title, frequency, unit, f"https://fred.stlouisfed.org/series/{series_id}"),
        )


def sync_fred_series(connection, years: int = 3) -> dict:
    register_series(connection)
    start = (date.today() - timedelta(days=365 * years)).isoformat()
    counts = {}
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        for series_id in SERIES:
            response = client.get(series_url(series_id, start))
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            count = 0
            for row in reader:
                raw = row.get(series_id)
                observed_at = row.get("DATE") or row.get("observation_date")
                if not observed_at or not raw or raw == ".":
                    continue
                connection.execute(
                    """insert into macro_observations(series_id,observed_at,value) values (?,?,?)
                       on conflict(series_id,observed_at) do update set value=excluded.value""",
                    (series_id, observed_at, float(raw)),
                )
                count += 1
            connection.execute(
                "update macro_series set last_synced_at=current_timestamp,updated_at=current_timestamp where series_id=?",
                (series_id,),
            )
            counts[series_id] = count
    settle_forecasts(connection)
    connection.commit()
    return counts


def settle_forecasts(connection) -> int:
    rows = connection.execute(
        "select * from economic_forecasts where status='open' and target_date <= date('now')"
    ).fetchall()
    settled = 0
    for forecast in rows:
        actual = connection.execute(
            """select observed_at,value from macro_observations
               where series_id=? and observed_at>=? order by observed_at limit 1""",
            (forecast["series_id"], forecast["target_date"]),
        ).fetchone()
        if not actual:
            continue
        value = actual["value"]
        midpoint_low = (forecast["favorable_value"] + forecast["base_value"]) / 2
        midpoint_high = (forecast["base_value"] + forecast["adverse_value"]) / 2
        bucket = "favorable" if value < midpoint_low else "adverse" if value > midpoint_high else "base"
        error = pct_change(value, forecast["base_value"])
        connection.execute(
            """update economic_forecasts set actual_value=?,actual_date=?,outcome_bucket=?,
               base_error_pct=?,status='evaluated',evaluated_at=current_timestamp where id=?""",
            (value, actual["observed_at"], bucket, error, forecast["id"]),
        )
        if error is not None and abs(error) >= 10:
            connection.execute(
                """insert into economic_improvement_queue
                  (queue_key,analysis_id,forecast_id,issue_type,severity,detail)
                  values (?,?,?,?,?,?) on conflict(queue_key) do update set
                  severity=excluded.severity,detail=excluded.detail,status='open',updated_at=current_timestamp""",
                (
                    f"forecast:{forecast['id']}:error", forecast["analysis_id"], forecast["id"],
                    "forecast_error", "high" if abs(error) >= 20 else "medium",
                    f"{forecast['series_id']} 기준 시나리오 대비 실제 오차 {error}%",
                ),
            )
        settled += 1
    return settled


def pct_change(current: float, previous: float | None) -> float | None:
    if previous in (None, 0):
        return None
    return round((current / previous - 1) * 100, 2)


def relevant_series(question: str) -> list[str]:
    lowered = question.lower()
    matched = [series_id for series_id, (_, _, _, words) in SERIES.items() if any(word in lowered for word in words)]
    return matched or ["DFF", "CPIAUCSL", "UNRATE", "DCOILWTICO", "DEXKOUS"]


def series_snapshot(connection, question: str, limit: int = 5) -> list[dict]:
    snapshots = []
    for series_id in relevant_series(question)[:limit]:
        metadata = connection.execute("select * from macro_series where series_id=?", (series_id,)).fetchone()
        rows = connection.execute(
            "select observed_at,value from macro_observations where series_id=? order by observed_at desc limit 370",
            (series_id,),
        ).fetchall()
        if not metadata or not rows:
            continue
        latest = rows[0]
        latest_date = date.fromisoformat(latest["observed_at"])

        def prior(days: int):
            cutoff = (latest_date - timedelta(days=days)).isoformat()
            return next((row for row in rows if row["observed_at"] <= cutoff), None)

        month = prior(30)
        year = prior(365)
        values_90d = [row["value"] for row in rows if row["observed_at"] >= (latest_date - timedelta(days=90)).isoformat()]
        snapshots.append(
            {
                "series_id": series_id,
                "title": metadata["title"],
                "date": latest["observed_at"],
                "value": latest["value"],
                "unit": metadata["unit"],
                "change_1m_pct": pct_change(latest["value"], month["value"] if month else None),
                "change_1y_pct": pct_change(latest["value"], year["value"] if year else None),
                "min_90d": round(min(values_90d), 3) if values_90d else None,
                "max_90d": round(max(values_90d), 3) if values_90d else None,
                "source_url": metadata["source_url"],
                "last_synced_at": metadata["last_synced_at"],
            }
        )
    return snapshots


def macro_prompt(snapshots: list[dict]) -> str:
    if not snapshots:
        return "동기화된 거시 시계열 없음"
    return "\n".join(
        f"[M{i}] {item['title']} ({item['series_id']}): {item['value']} {item['unit']} / 기준일 {item['date']} / 1개월 변화 {item['change_1m_pct']}% / 1년 변화 {item['change_1y_pct']}% / 최근 90일 범위 {item['min_90d']}~{item['max_90d']}"
        for i, item in enumerate(snapshots, start=1)
    )


def build_scenarios(snapshots: list[dict], news_metrics: dict) -> dict:
    risk_share = news_metrics.get("high_risk_share")
    adverse_probability = round(min(45.0, 25.0 + (risk_share or 0) * 0.2), 1)
    favorable_probability = 15.0
    base_probability = round(100.0 - adverse_probability - favorable_probability, 1)

    indicators = []
    for item in snapshots:
        lower = item.get("min_90d")
        upper = item.get("max_90d")
        current = item.get("value")
        if lower is None or upper is None:
            continue
        # For rates, inflation, unemployment, oil, and KRW/USD, a higher value is
        # treated as the stress direction for this first Korea-focused model.
        indicators.append(
            {
                "series_id": item["series_id"],
                "title": item["title"],
                "unit": item["unit"],
                "favorable": lower,
                "base": current,
                "adverse": upper,
            }
        )

    return {
        "method": "최근 90일 관측 범위 + 검색 뉴스 고위험 비중",
        "disclaimer": "확률은 의사결정 비교용 휴리스틱이며 통계적 예측모형의 확률이 아닙니다.",
        "scenarios": [
            {"key": "favorable", "label": "우호", "probability": favorable_probability},
            {"key": "base", "label": "기준", "probability": base_probability},
            {"key": "adverse", "label": "위험", "probability": adverse_probability},
        ],
        "indicators": indicators,
    }


def scenario_prompt(scenario: dict) -> str:
    if not scenario.get("indicators"):
        return "시나리오를 계산할 거시 시계열 없음"
    probabilities = ", ".join(
        f"{item['label']} {item['probability']}%" for item in scenario["scenarios"]
    )
    indicators = "\n".join(
        f"- {item['title']}: 우호 {item['favorable']} / 기준 {item['base']} / 위험 {item['adverse']} {item['unit']}"
        for item in scenario["indicators"]
    )
    return f"방법: {scenario['method']}\n비교 가중치: {probabilities}\n{indicators}\n주의: {scenario['disclaimer']}"


if __name__ == "__main__":
    from database import connect, init_db

    init_db()
    with connect() as database:
        print(sync_fred_series(database))
