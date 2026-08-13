import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import bootstrap  # noqa: E402,F401
from ism_data import _parse_report  # noqa: E402


class IsmDataTests(unittest.TestCase):
    def test_parses_manufacturing_report(self):
        report = _parse_report(
            "<h1>June 2026 ISM® Manufacturing PMI® Report</h1><h2>Manufacturing PMI® at 53.3%</h2>",
            "manufacturing",
            "https://example.test/manufacturing",
        )
        self.assertEqual(report["value"], 53.3)
        self.assertEqual(report["asOf"], "2026-06-01")

    def test_parses_services_report(self):
        report = _parse_report(
            "Title: June 2026 ISM® Services PMI® Report. The Services PMI® registered 54 percent.",
            "services",
            "https://example.test/services",
        )
        self.assertEqual(report["value"], 54.0)
        self.assertEqual(report["asOf"], "2026-06-01")


if __name__ == "__main__":
    unittest.main()
