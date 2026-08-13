import unittest

import api_server


class SecurityLimitTest(unittest.TestCase):
    def setUp(self):
        with api_server._LIMIT_LOCK:
            api_server._LOGIN_FAILURES.clear()
            api_server._LOGIN_LOCKED_UNTIL.clear()
            api_server._REQUEST_BUCKETS.clear()

    def test_login_failures_trigger_and_expire_lock(self):
        client = "test-client"
        start = 1_800_000_000.0
        for offset in range(api_server.LOGIN_FAILURE_LIMIT - 1):
            self.assertEqual(api_server.record_login_failure(client, now=start + offset), 0)

        self.assertEqual(
            api_server.record_login_failure(client, now=start + api_server.LOGIN_FAILURE_LIMIT),
            api_server.LOGIN_LOCK_SECONDS,
        )
        self.assertGreater(api_server.login_retry_after(client, now=start + 10), 0)
        self.assertEqual(
            api_server.login_retry_after(client, now=start + api_server.LOGIN_LOCK_SECONDS + 10),
            0,
        )

    def test_success_clears_login_failures(self):
        client = "test-client"
        api_server.record_login_failure(client, now=1_800_000_000.0)
        api_server.clear_login_failures(client)
        self.assertEqual(api_server.login_retry_after(client, now=1_800_000_001.0), 0)
        self.assertNotIn(client, api_server._LOGIN_FAILURES)


if __name__ == "__main__":
    unittest.main()
