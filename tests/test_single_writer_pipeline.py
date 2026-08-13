from pathlib import Path
from contextlib import closing
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import ai_analyzer  # noqa: E402
import database  # noqa: E402


class SingleWriterPipelineTests(unittest.TestCase):
    def test_live_collector_is_collection_only(self):
        source = (ROOT / "src" / "live_collector.py").read_text(encoding="utf-8")

        self.assertNotIn("analyze_news_item", source)
        self.assertNotIn("analyze_pending", source)
        self.assertNotIn("build_daily_briefings", source)
        self.assertIn("queued for analysis worker", source)

    def test_analysis_commits_before_post_analysis_callback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "news.db"
            database.init_db(db_path)
            with closing(database.connect(db_path)) as connection:
                with connection:
                    connection.execute(
                        """
                        insert into news_items (
                          source_channel, telegram_message_id, published_at, news_date,
                          raw_text, content_type, analysis_status, analysis_priority,
                          analysis_scope, duplicate_key
                        )
                        values ('test', 1, '2026-07-22T00:00:00+00:00', '2026-07-22',
                                'test economic news', 'news', 'queued', 10,
                                'analysis_target', 'test:1')
                        """
                    )

            callback_ids = []

            def callback(_connection, news_id, _result):
                # A second writer must be able to commit here. This verifies that
                # analyze_pending released its write transaction first.
                with closing(database.connect(db_path)) as status_connection:
                    with status_connection:
                        status_connection.execute(
                            """
                            insert into automation_status (service_name, status, detail)
                            values ('callback_test', 'ok', 'second writer committed')
                            """
                        )
                callback_ids.append(news_id)

            result = {
                "title": "테스트 뉴스",
                "summary_ko": "테스트 요약",
                "analysis_ko": "테스트 분석",
                "impact_score": 5,
                "sentiment": "neutral",
                "risk_level": "medium",
                "category": "macro",
            }

            with (
                patch.object(ai_analyzer, "connect", side_effect=lambda: closing(database.connect(db_path))),
                patch.object(ai_analyzer, "load_settings", return_value=object()),
                patch.object(ai_analyzer, "build_provider", return_value={"provider": "test", "model": "test"}),
                patch.object(ai_analyzer, "analyze_row_with_fallbacks", return_value=result),
            ):
                processed = ai_analyzer.analyze_pending(
                    limit=1,
                    model="test",
                    retries=0,
                    on_analyzed=callback,
                )

            self.assertEqual(processed, 1)
            self.assertEqual(len(callback_ids), 1)
            with closing(database.connect(db_path)) as connection:
                status = connection.execute(
                    "select status from automation_status where service_name = 'callback_test'"
                ).fetchone()
                analyzed = connection.execute(
                    "select analysis_status from news_items where telegram_message_id = 1"
                ).fetchone()
            self.assertEqual(status["status"], "ok")
            self.assertEqual(analyzed["analysis_status"], "analyzed")


if __name__ == "__main__":
    unittest.main()
