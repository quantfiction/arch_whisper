"""Tests for Claude credential timestamp parsing.

This tests the actual bug we hit: expiresAt can be either a Unix
timestamp (int/float in milliseconds) or an ISO 8601 string.
"""

import json
import tempfile
import unittest
from pathlib import Path

from arch_whisper.auth import claude_max
from arch_whisper.auth.claude_max import load_credentials


class TestTimestampParsing(unittest.TestCase):
    """Tests for the timestamp parsing logic that caused a real bug."""

    def setUp(self):
        """Create a temporary credentials file."""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        self.temp_file.close()
        self.temp_path = Path(self.temp_file.name)
        self.original_path = claude_max.CREDENTIALS_PATH

    def tearDown(self):
        """Clean up temporary file."""
        claude_max.CREDENTIALS_PATH = self.original_path
        self.temp_path.unlink(missing_ok=True)

    def write_credentials(self, oauth_data):
        """Helper to write credentials file."""
        self.temp_path.write_text(json.dumps({"claudeAiOauth": oauth_data}))
        claude_max.CREDENTIALS_PATH = self.temp_path

    def test_unix_timestamp_milliseconds(self):
        """Unix timestamp in milliseconds should parse correctly."""
        ts_ms = 1736985897054  # 2025-01-16 00:04:57 UTC
        self.write_credentials({
            "accessToken": "test-token",
            "expiresAt": ts_ms,
        })

        creds = load_credentials()
        self.assertIsNotNone(creds)
        self.assertIsNotNone(creds.expires_at)
        self.assertEqual(creds.expires_at.year, 2025)
        self.assertEqual(creds.expires_at.month, 1)
        self.assertEqual(creds.expires_at.day, 16)

    def test_iso_string_with_z_suffix(self):
        """ISO 8601 string with Z suffix should parse correctly."""
        self.write_credentials({
            "accessToken": "test-token",
            "expiresAt": "2025-01-16T00:04:57.054Z",
        })

        creds = load_credentials()
        self.assertIsNotNone(creds)
        self.assertIsNotNone(creds.expires_at)
        self.assertEqual(creds.expires_at.year, 2025)

    def test_iso_string_with_timezone(self):
        """ISO 8601 string with +00:00 timezone should parse correctly."""
        self.write_credentials({
            "accessToken": "test-token",
            "expiresAt": "2025-01-16T00:04:57.054+00:00",
        })

        creds = load_credentials()
        self.assertIsNotNone(creds)
        self.assertIsNotNone(creds.expires_at)

    def test_missing_expires_at_is_valid(self):
        """Missing expiresAt should result in valid credentials (optimistic)."""
        self.write_credentials({
            "accessToken": "test-token",
        })

        creds = load_credentials()
        self.assertIsNotNone(creds)
        self.assertIsNone(creds.expires_at)
        self.assertTrue(creds.is_valid())  # Optimistic when no expiry

    def test_expired_token_is_invalid(self):
        """Expired token should be marked invalid."""
        past_ts = 1600000000000  # 2020-09-13
        self.write_credentials({
            "accessToken": "test-token",
            "expiresAt": past_ts,
        })

        creds = load_credentials()
        self.assertIsNotNone(creds)
        self.assertFalse(creds.is_valid())

    def test_missing_access_token_returns_none(self):
        """Missing accessToken should return None."""
        self.write_credentials({
            "expiresAt": 1736985897054,
        })

        creds = load_credentials()
        self.assertIsNone(creds)

    def test_malformed_json_returns_none(self):
        """Malformed JSON should return None gracefully."""
        self.temp_path.write_text("not valid json {{{")
        claude_max.CREDENTIALS_PATH = self.temp_path

        creds = load_credentials()
        self.assertIsNone(creds)


if __name__ == '__main__':
    unittest.main(verbosity=2)
