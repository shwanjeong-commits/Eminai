import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finbert_analyzer import FinBertAnalyzer, english_coverage


class FakePipeline:
    def __call__(self, text, truncation=True):
        return [[
            {"label": "positive", "score": 0.8},
            {"label": "negative", "score": 0.1},
            {"label": "neutral", "score": 0.1},
        ]]


class FinBertAnalyzerTests(unittest.TestCase):
    def test_skips_korean_first_text(self):
        analyzer = FinBertAnalyzer(minimum_english_coverage=0.35)
        self.assertFalse(analyzer.eligible("연준이 금리를 동결했고 시장은 상승했다 NVDA ETF"))
        self.assertIsNone(analyzer.analyze("연준이 금리를 동결했고 시장은 상승했다 NVDA ETF"))

    def test_scores_english_financial_text(self):
        analyzer = FinBertAnalyzer()
        analyzer._pipeline = FakePipeline()
        result = analyzer.analyze(
            "The company raised its annual revenue forecast after strong demand."
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.label, "positive")
        self.assertAlmostEqual(result.confidence, 0.8)

    def test_english_coverage(self):
        self.assertGreater(english_coverage("Revenue guidance increased strongly today"), 0.9)
        self.assertLess(english_coverage("매출 전망이 크게 증가했다 revenue"), 0.35)


if __name__ == "__main__":
    unittest.main()
