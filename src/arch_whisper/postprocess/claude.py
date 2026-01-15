"""Claude postprocessor for transcription cleanup."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arch_whisper.config import Config

logger = logging.getLogger(__name__)

# Cleanup prompt for transcription post-processing
CLEANUP_PROMPT = """Clean up this transcribed speech:
1. Fix punctuation and capitalization
2. Remove filler words (um, uh, like, you know, so, I mean, basically, actually, literally, right)
3. Fix obvious transcription errors
4. Keep the core meaning intact

Output only the cleaned text with no explanation.

Transcribed text:
{text}

Cleaned text:"""

SYSTEM_PROMPT = "You are a transcription cleanup assistant. Output only the cleaned text with no explanation or preamble."


def _claude_cli_available() -> bool:
    """Check if Claude CLI is available."""
    return shutil.which("claude") is not None


class ClaudePostProcessor:
    """Post-processes transcriptions using Claude (API key or CLI)."""

    def __init__(self, config: Config) -> None:
        """Initialize the post-processor.

        Args:
            config: Application configuration
        """
        self._config = config

        # Check for API key (config or environment variable)
        self._api_key = config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._cli_available = _claude_cli_available()

        if self._api_key:
            logger.info("Using Anthropic API key for post-processing")
        elif self._cli_available:
            logger.info("Using Claude CLI for post-processing")
        else:
            logger.warning("No Claude API key or CLI found - post-processing disabled")

    @property
    def available(self) -> bool:
        """Check if Claude processing is available."""
        return bool(self._api_key) or self._cli_available

    def process(self, raw_text: str) -> str:
        """Process transcribed text with Claude.

        Args:
            raw_text: Raw transcription text

        Returns:
            Cleaned text, or raw_text if processing fails
        """
        if not raw_text.strip():
            return raw_text

        if not self.available:
            return raw_text

        try:
            # Prefer API key if available (faster, no CLI overhead)
            if self._api_key:
                return self._process_with_api(raw_text)
            else:
                return asyncio.run(self._process_with_cli(raw_text))
        except Exception as e:
            logger.error("Claude processing failed: %s", e)
            return raw_text

    def _process_with_api(self, raw_text: str) -> str:
        """Process using Anthropic API directly."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)

        response = client.messages.create(
            model=self._config.claude_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": CLEANUP_PROMPT.format(text=raw_text)}
            ],
        )

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

        logger.warning("Empty response from Claude API, using raw text")
        return raw_text

    async def _process_with_cli(self, raw_text: str) -> str:
        """Process using Claude Code CLI (Agent SDK)."""
        from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            max_turns=1,
            model=self._config.claude_model,
            tools=[],
        )

        prompt = CLEANUP_PROMPT.format(text=raw_text)
        response_text = ""

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        cleaned = response_text.strip()
        if cleaned:
            logger.debug(
                "Claude cleaned text: %d -> %d chars",
                len(raw_text),
                len(cleaned),
            )
            return cleaned

        logger.warning("Empty response from Claude CLI, using raw text")
        return raw_text
