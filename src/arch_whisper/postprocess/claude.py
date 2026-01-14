"""Claude postprocessor for transcription cleanup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import anthropic
from anthropic import Anthropic

if TYPE_CHECKING:
    from arch_whisper.config import Config

from arch_whisper.auth.claude_max import load_credentials

logger = logging.getLogger(__name__)

# Cleanup prompt for transcription post-processing
CLEANUP_PROMPT = """Clean up this transcribed speech. Fix punctuation, capitalization, and obvious transcription errors. Keep the meaning identical. Do not add or remove content. Output only the cleaned text with no explanation.

Transcribed text:
{text}

Cleaned text:"""


class ClaudePostProcessor:
    """Post-processes transcriptions using Claude API."""

    def __init__(self, config: Config) -> None:
        """Initialize the post-processor.

        Args:
            config: Application configuration
        """
        self._config = config
        self._credentials = load_credentials()
        self._notified_invalid = False

    @property
    def available(self) -> bool:
        """Check if Claude processing is available."""
        return self._credentials is not None and self._credentials.is_valid()

    def process(self, raw_text: str) -> str:
        """Process transcribed text with Claude.

        Args:
            raw_text: Raw transcription text

        Returns:
            Cleaned text, or raw_text if processing fails
        """
        if not raw_text.strip():
            return raw_text

        if self._credentials is None:
            logger.debug("No Claude credentials, skipping cleanup")
            return raw_text

        if not self._credentials.is_valid():
            if not self._notified_invalid:
                logger.warning("Claude credentials expired, skipping cleanup")
                self._notified_invalid = True
            return raw_text

        try:
            # Create client with OAuth token
            # Note: The Anthropic SDK uses 'auth_token' for OAuth bearer tokens
            client = Anthropic(auth_token=self._credentials.access_token)

            response = client.messages.create(
                model=self._config.claude_model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": CLEANUP_PROMPT.format(text=raw_text),
                    }
                ],
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, "text"):
                    cleaned = content_block.text.strip()
                    if cleaned:
                        logger.debug(
                            "Claude cleaned text: %d -> %d chars",
                            len(raw_text),
                            len(cleaned),
                        )
                        return cleaned

            logger.warning("Empty response from Claude, using raw text")
            return raw_text

        except anthropic.AuthenticationError:
            logger.error("Claude authentication failed - token may be invalid")
            return raw_text
        except anthropic.RateLimitError:
            logger.warning("Claude rate limit hit, using raw text")
            return raw_text
        except anthropic.APIConnectionError as e:
            logger.warning("Claude connection error: %s", e)
            return raw_text
        except anthropic.APIStatusError as e:
            logger.warning("Claude API error (%d): %s", e.status_code, e.message)
            return raw_text
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error("Claude processing failed: %s", type(e).__name__)
            return raw_text
