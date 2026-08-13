import unittest

from api_server import (
    AUTH_SESSION_SECONDS,
    site_access_token,
    site_access_token_expires_at,
    revoke_site_access_token,
    validate_site_access_token,
)


class AuthExpiryTest(unittest.TestCase):
    def test_token_expires_after_six_hours(self):
        issued_at = 1_800_000_000
        token = site_access_token("test-password", now=issued_at)

        self.assertEqual(site_access_token_expires_at(token), issued_at + AUTH_SESSION_SECONDS)
        self.assertTrue(validate_site_access_token(token, "test-password", now=issued_at))
        self.assertTrue(
            validate_site_access_token(
                token,
                "test-password",
                now=issued_at + AUTH_SESSION_SECONDS - 1,
            )
        )
        self.assertFalse(
            validate_site_access_token(
                token,
                "test-password",
                now=issued_at + AUTH_SESSION_SECONDS,
            )
        )

    def test_tampered_or_legacy_token_is_rejected(self):
        token = site_access_token("test-password", now=1_800_000_000)

        self.assertFalse(validate_site_access_token(token + "x", "test-password", now=1_800_000_001))
        # Opaque server-side sessions are independent from the shared password.
        self.assertTrue(validate_site_access_token(token, "wrong-password", now=1_800_000_001))
        self.assertFalse(validate_site_access_token("legacy-token", "test-password", now=1_800_000_001))

    def test_sessions_are_random_and_individually_revocable(self):
        issued_at = 1_800_000_000
        first = site_access_token("test-password", now=issued_at)
        second = site_access_token("test-password", now=issued_at)

        self.assertNotEqual(first, second)
        self.assertTrue(validate_site_access_token(first, now=issued_at + 1))
        self.assertTrue(validate_site_access_token(second, now=issued_at + 1))

        revoke_site_access_token(first)
        self.assertFalse(validate_site_access_token(first, now=issued_at + 1))
        self.assertTrue(validate_site_access_token(second, now=issued_at + 1))


if __name__ == "__main__":
    unittest.main()
