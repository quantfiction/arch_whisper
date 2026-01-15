"""Claude Max OAuth credential handling."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

# Example credentials file structure:
# {
#   "claudeAiOauth": {
#     "accessToken": "...",
#     "expiresAt": "2026-01-15T12:00:00.000Z",
#     "refreshToken": "...",
#     "scopes": ["..."],
#     "subscriptionType": "claude_max"
#   }
# }


@dataclass
class ClaudeCredentials:
    """Claude Max OAuth credentials."""

    access_token: str
    expires_at: datetime | None = None

    def is_valid(self) -> bool:
        """Check if the token appears valid (not expired).

        Returns True if no expiry info available (optimistic).
        """
        if self.expires_at is None:
            return True
        return datetime.now(timezone.utc) < self.expires_at


def load_credentials() -> ClaudeCredentials | None:
    """Load Claude credentials from the credentials file.

    Returns:
        ClaudeCredentials if valid credentials found, None otherwise.
        Never logs the actual token value.
    """
    if not CREDENTIALS_PATH.exists():
        logger.debug("Credentials file not found: %s", CREDENTIALS_PATH)
        return None

    try:
        data = json.loads(CREDENTIALS_PATH.read_text())
        oauth = data.get("claudeAiOauth", {})

        token = oauth.get("accessToken")
        if not token:
            logger.warning("No accessToken in credentials file")
            return None

        expires_at = None
        if "expiresAt" in oauth:
            try:
                expires_val = oauth["expiresAt"]
                # Handle Unix timestamp (milliseconds) or ISO format string
                if isinstance(expires_val, (int, float)):
                    # Unix timestamp in milliseconds
                    expires_at = datetime.fromtimestamp(
                        expires_val / 1000, tz=timezone.utc
                    )
                elif isinstance(expires_val, str):
                    # ISO format datetime
                    if expires_val.endswith("Z"):
                        expires_val = expires_val[:-1] + "+00:00"
                    expires_at = datetime.fromisoformat(expires_val)
            except (ValueError, TypeError, OSError) as e:
                logger.debug("Could not parse expiresAt: %s", e)

        logger.info("Loaded Claude credentials (expires: %s)", expires_at)
        return ClaudeCredentials(access_token=token, expires_at=expires_at)

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in credentials file: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to load credentials: %s", e)
        return None
