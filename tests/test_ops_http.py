from contextlib import closing
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
from http.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import api_server  # noqa: E402
import database  # noqa: E402


class OpsHttpHandlerTests(unittest.TestCase):
    OPS_KEY = "test-ops-key"

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "news.db"
        database.init_db(self.db_path)
        with closing(database.connect(self.db_path)) as connection:
            with connection:
                connection.executemany(
                    """insert into automation_status
                       (service_name, status, detail, processed_count, error_count)
                       values (?, ?, ?, ?, ?)""",
                    [
                        ("telegram_live_collector", "listening", "test collector", 3, 0),
                        ("ai_analysis_worker", "idle", "test worker", 2, 0),
                    ],
                )
                connection.execute(
                    """insert into news_items (
                        source_channel, telegram_message_id, published_at, news_date,
                        raw_text, title, content_type, analysis_status, analysis_priority,
                        analysis_scope, duplicate_key
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        "test-channel", 1, "2026-08-18T00:00:00Z", "2026-08-18",
                        "test queue item", "Test queue item", "news", "queued", 9,
                        "analysis_target", "test-channel:1",
                    ),
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), api_server.Handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.patches = [
            patch.object(api_server, "connect", side_effect=lambda: database.connect(self.db_path)),
            patch.object(api_server, "init_db", return_value=None),
            patch.object(api_server, "ops_api_key", return_value=self.OPS_KEY),
            patch.object(api_server, "update_status", side_effect=self._update_status),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.temp_dir.cleanup()

    def _request(self, method, path, body=None, key=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = {"Host": "127.0.0.1"}
        if key is not None:
            headers["X-Eminai-Ops-Key"] = key
        encoded_body = None
        if body is not None:
            encoded_body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(encoded_body))
        connection.request(method, path, body=encoded_body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        parsed = json.loads(payload.decode("utf-8")) if payload else {}
        return response.status, parsed

    def _update_status(self, service_name, status, detail=None, **_kwargs):
        with closing(database.connect(self.db_path)) as connection:
            with connection:
                connection.execute(
                    """insert into automation_status (service_name, status, detail)
                       values (?, ?, ?)
                       on conflict(service_name) do update set status=excluded.status,
                       detail=excluded.detail, updated_at=current_timestamp""",
                    (service_name, status, detail),
                )

    def test_get_status_without_ops_key_returns_401(self):
        status, payload = self._request("GET", "/api/ops/status")
        self.assertEqual(status, 401)
        self.assertFalse(payload["ok"])

    def test_get_status_with_ops_key_returns_core_payload(self):
        status, payload = self._request("GET", "/api/ops/status", key=self.OPS_KEY)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("collector", payload)
        self.assertIn("analysisWorker", payload)
        self.assertIn("queueEstimate", payload)
        self.assertEqual(payload["collector"]["status"], "listening")

    def test_manual_update_queues_existing_manual_status(self):
        status, payload = self._request("POST", "/api/ops/manual-update", key=self.OPS_KEY)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "queued")
        with closing(database.connect(self.db_path)) as connection:
            row = connection.execute(
                "select status from automation_status where service_name='manual_update'"
            ).fetchone()
        self.assertEqual(row["status"], "queued")

    def test_reanalyze_missing_id_returns_400(self):
        status, payload = self._request("POST", "/api/ops/reanalyze", body={}, key=self.OPS_KEY)
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])

    def test_reanalyze_unknown_id_returns_404(self):
        status, payload = self._request(
            "POST", "/api/ops/reanalyze", body={"id": 999999}, key=self.OPS_KEY
        )
        self.assertEqual(status, 404)
        self.assertFalse(payload["ok"])

    def test_get_news_invalid_status_and_pagination_return_400(self):
        for query in ({"status": "not-a-status"}, {"limit": "201"}):
            status, payload = self._request(
                "GET", f"/api/ops/news?{urlencode(query)}", key=self.OPS_KEY
            )
            self.assertEqual(status, 400)
            self.assertFalse(payload["ok"])


if __name__ == "__main__":
    unittest.main()
