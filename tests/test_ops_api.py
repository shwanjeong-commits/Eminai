import sqlite3
import unittest

import api_server


class OpsApiTest(unittest.TestCase):
    def test_ops_key_requires_configured_nonempty_constant_time_candidate(self):
        self.assertFalse(api_server.is_valid_ops_key("", "secret"))
        self.assertFalse(api_server.is_valid_ops_key("wrong", "secret"))
        self.assertTrue(api_server.is_valid_ops_key("secret", "secret"))
        self.assertFalse(api_server.is_valid_ops_key("secret", ""))

    def test_requeue_news_item_resets_analysis_fields(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            """create table news_items (
                id integer primary key, analysis_status text, summary_ko text,
                analysis_ko text, impact_score real, sentiment text, risk_level text,
                category text, analysis_reason text, user_hidden integer,
                updated_at text
            )"""
        )
        connection.execute(
            """insert into news_items values
            (7, 'analyzed', '요약', '분석', 8.5, 'positive', '높음', 'markets',
             'old', 1, 'old')"""
        )
        self.assertTrue(api_server.requeue_news_item(connection, 7))
        row = connection.execute("select * from news_items where id=7").fetchone()
        self.assertEqual(row["analysis_status"], "queued")
        self.assertIsNone(row["summary_ko"])
        self.assertIsNone(row["analysis_ko"])
        self.assertIsNone(row["impact_score"])
        self.assertEqual(row["analysis_reason"], "user requested reanalysis")
        self.assertEqual(row["user_hidden"], 0)
        self.assertFalse(api_server.requeue_news_item(connection, 999))

    def test_ops_news_payload_filters_and_compacts_raw_text(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute(
            """create table news_items (
                id integer primary key, source_channel text, published_at text,
                title text, raw_text text, analysis_status text, analysis_priority real,
                analysis_reason text, impact_score real, sentiment text, risk_level text,
                category text, content_type text, user_hidden integer, updated_at text,
                analysis_scope text
            )"""
        )
        connection.execute(
            """insert into news_items values
            (1, 'channel', '2026-08-18T00:00:00Z', null, ?, 'queued', 9,
             'needs review', 8, 'neutral', '중간', 'macro', 'news', 0, 'now', 'analysis_target')""",
            ("x" * 600,),
        )
        items = api_server.build_ops_news(connection, "queued", 10, 0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], 1)
        self.assertLessEqual(len(items[0]["rawText"]), 503)
        self.assertEqual(items[0]["analysisStatus"], "queued")


if __name__ == "__main__":
    unittest.main()
