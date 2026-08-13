import unittest
import sqlite3

from api_server import build_economic_evaluation
from economic_chat import answer_economic_question, is_non_economic_probe


class EconomicChatProbeTest(unittest.TestCase):
    def test_recognizes_connection_test_inputs(self):
        for question in ("hi", "HI!", " hello ", "테스트", "안녕하세요"):
            with self.subTest(question=question):
                self.assertTrue(is_non_economic_probe(question))

    def test_keeps_short_economic_questions(self):
        for question in ("금리?", "CPI", "유가"):
            with self.subTest(question=question):
                self.assertFalse(is_non_economic_probe(question))

    def test_probe_returns_guidance_without_analysis_record(self):
        result = answer_economic_question(None, "hi")

        self.assertIsNone(result["analysis_id"])
        self.assertEqual(result["provider"], "system")
        self.assertIn("경제 분석 전용 AI", result["answer"])

    def test_evaluation_excludes_existing_probe_records(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            create table economic_analyses (
              id integer primary key, question text, provider text, model text, created_at text
            );
            create table economic_analysis_scores (
              analysis_id integer primary key, total_score real, checks text
            );
            create table economic_analysis_feedback (
              analysis_id integer primary key, rating integer
            );
            create table economic_forecasts (
              status text, outcome_bucket text, base_error_pct real
            );
            create table economic_improvement_queue (
              id integer primary key, analysis_id integer, issue_type text, severity text,
              detail text, created_at text, status text
            );
            insert into economic_analyses values (1, 'hi', 'github', 'test', '2026-07-23');
            insert into economic_analyses values (2, '미국 금리를 분석해줘', 'github', 'test', '2026-07-24');
            insert into economic_analysis_scores values (1, 100, '{}');
            insert into economic_analysis_scores values (2, 72, '{}');
            """
        )

        evaluation = build_economic_evaluation(connection)

        self.assertEqual(evaluation["analysisCount"], 1)
        self.assertEqual(evaluation["averageScore"], 72)
        self.assertEqual([item["question"] for item in evaluation["recent"]], ["미국 금리를 분석해줘"])


if __name__ == "__main__":
    unittest.main()
