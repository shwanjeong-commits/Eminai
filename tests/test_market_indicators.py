import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import bootstrap  # noqa: E402,F401
import market_indicators  # noqa: E402
from market_data import ASSET_MAP, asset_catalog  # noqa: E402


class MarketIndicatorTests(unittest.TestCase):
    def tearDown(self):
        market_indicators._CACHE = None

    def test_threshold_boundaries_are_lower_inclusive(self):
        self.assertEqual(market_indicators.selected_band(14.99, market_indicators.VIX_BANDS)["label"], "안정")
        self.assertEqual(market_indicators.selected_band(15, market_indicators.VIX_BANDS)["label"], "보통")
        self.assertEqual(market_indicators.selected_band(30, market_indicators.VIX_BANDS)["label"], "고위험")
        self.assertEqual(market_indicators.selected_band(-3, market_indicators.CRYPTO_FLOW_BANDS)["label"], "유출")
        self.assertEqual(market_indicators.selected_band(1, market_indicators.CRYPTO_FLOW_BANDS)["label"], "유입")

    def test_indicator_symbols_stay_chartable_but_are_not_stock_catalog_items(self):
        symbols = {item["symbol"] for item in asset_catalog()}
        self.assertNotIn("^VIX", symbols)
        self.assertNotIn("^TNX", symbols)
        self.assertIn("^VIX", ASSET_MAP)
        self.assertIn("^TNX", ASSET_MAP)
        self.assertTrue({"AAPL", "MSFT", "SOXX", "000660.KS", "ETH-USD"}.issubset(symbols))

    def test_dashboard_keeps_fixed_order_and_isolates_source_failure(self):
        def success(key):
            return lambda: {"key": key, "available": True, "value": 1}

        def fail():
            raise RuntimeError("source timeout")

        fetchers = {key: success(key) for key in market_indicators.FETCHERS}
        fred_builders = {key: (lambda _bundle, item_key=key: {"key": item_key, "available": True, "value": 1}) for key in market_indicators.FRED_BUILDERS}
        fetchers["us_cpi"] = fail
        with (
            patch.object(market_indicators, "FETCHERS", fetchers),
            patch.object(market_indicators, "FRED_BUILDERS", fred_builders),
            patch.object(market_indicators, "get_fred_indicator_bundle", return_value={}),
            patch.object(market_indicators, "_CACHE", None),
        ):
            payload = market_indicators.get_indicator_dashboard(force=True)

        self.assertEqual(
            [item["key"] for item in payload["indicators"]],
            [item["key"] for item in market_indicators.INDICATOR_DEFINITIONS],
        )
        cpi = next(item for item in payload["indicators"] if item["key"] == "us_cpi")
        self.assertFalse(cpi["available"])
        self.assertEqual(cpi["status"], "데이터 확인 필요")
        self.assertIn("source timeout", cpi["error"])

    def test_first_wave_indicator_candidates_are_registered(self):
        keys = {item["key"] for item in market_indicators.INDICATOR_DEFINITIONS}
        self.assertTrue({
            "core_pce",
            "real_policy_rate",
            "yield_curve",
            "us10y_real",
            "breakeven_10y",
            "sahm_rule",
            "initial_claims",
            "nfci",
            "high_yield_spread",
            "gdp_now",
        }.issubset(keys))
        self.assertEqual(len(market_indicators.INDICATOR_DEFINITIONS), 25)

    def test_second_wave_indicator_candidates_are_registered(self):
        keys = {item["key"] for item in market_indicators.INDICATOR_DEFINITIONS}
        self.assertTrue({
            "ism_manufacturing",
            "ism_services",
            "jolts_ratio",
            "jolts_quits",
            "core_retail_sales",
            "industrial_production",
            "m2_growth",
            "fed_net_liquidity",
            "sloos_tightening",
            "consumer_sentiment",
        }.issubset(keys))

    def test_core_pce_and_real_policy_rate_are_derived_from_fred_observations(self):
        bundle = {
            "PCEPILFE": [
                {"date": "2025-05-01", "value": 100.0},
                {"date": "2026-05-01", "value": 103.0},
            ],
            "DFF": [{"date": "2026-07-20", "value": 4.5}],
        }
        pce = market_indicators.build_core_pce(bundle)
        real_rate = market_indicators.build_real_policy_rate(bundle)
        self.assertAlmostEqual(pce["value"], 3.0)
        self.assertAlmostEqual(real_rate["value"], 1.5)
        self.assertEqual(real_rate["status"], "긴축적")

    def test_initial_claims_uses_dynamic_four_week_distribution(self):
        values = [180000, 185000, 190000, 195000, 200000, 205000, 210000, 215000, 220000, 225000, 230000, 235000]
        bundle = {
            "ICSA": [
                {"date": f"2026-{index + 1:02d}-01", "value": value}
                for index, value in enumerate(values)
            ]
        }
        indicator = market_indicators.build_initial_claims(bundle)
        self.assertEqual(indicator["value"], 227500)
        self.assertEqual(len(indicator["thresholds"]), 4)
        self.assertEqual(indicator["status"], "고위험")

    def test_all_fred_indicator_builders_produce_available_cards(self):
        claims = [
            {"date": f"2026-{index + 1:02d}-01", "value": 190000 + index * 4000}
            for index in range(12)
        ]
        bundle = {
            "DFF": [{"date": "2026-07-20", "value": 4.5}],
            "PCEPILFE": [{"date": "2025-05-01", "value": 100.0}, {"date": "2026-05-01", "value": 103.0}],
            "T10Y2Y": [{"date": "2026-07-20", "value": 0.4}],
            "T10Y3M": [{"date": "2026-07-20", "value": 0.7}],
            "DFII10": [{"date": "2026-07-20", "value": 2.1}],
            "T10YIE": [{"date": "2026-07-20", "value": 2.3}],
            "SAHMREALTIME": [{"date": "2026-06-01", "value": 0.2}],
            "ICSA": claims,
            "NFCI": [{"date": "2026-07-10", "value": -0.4}],
            "BAMLH0A0HYM2": [{"date": "2026-07-20", "value": 3.2}],
            "GDPNOW": [{"date": "2026-04-01", "value": 1.7}],
            "JTSJOL": [{"date": "2026-05-01", "value": 7600}],
            "UNEMPLOY": [{"date": "2026-05-01", "value": 7100}],
            "JTSQUR": [{"date": "2026-05-01", "value": 2.1}],
            "MARTSSM44W72USS": [
                {"date": f"{2025 + (month + 4) // 12}-{(month + 4) % 12 + 1:02d}-01", "value": 500000 + month * 3000}
                for month in range(13)
            ],
            "INDPRO": [{"date": "2025-06-01", "value": 100}, {"date": "2026-06-01", "value": 102}],
            "M2SL": [{"date": "2025-05-01", "value": 22000}, {"date": "2026-05-01", "value": 23000}],
            "WALCL": [{"date": "2026-04-15", "value": 6700000}, {"date": "2026-07-15", "value": 6800000}],
            "WTREGEN": [{"date": "2026-04-15", "value": 800000}, {"date": "2026-07-15", "value": 750000}],
            "RRPONTSYD": [{"date": "2026-04-15", "value": 100}, {"date": "2026-07-15", "value": 50}],
            "DRTSCIS": [{"date": "2026-04-01", "value": 12}],
            "DRTSCILM": [{"date": "2026-04-01", "value": 8}],
            "UMCSENT": [{"date": "2026-05-01", "value": 70}],
            "MICH": [{"date": "2026-05-01", "value": 3.5}],
        }
        cards = [builder(bundle) for builder in market_indicators.FRED_BUILDERS.values()]
        self.assertEqual(len(cards), 18)
        self.assertTrue(all(card["available"] for card in cards))
        self.assertTrue(all(card["thresholds"] for card in cards))


if __name__ == "__main__":
    unittest.main()
