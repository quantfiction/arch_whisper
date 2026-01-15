"""Claude postprocessor for transcription cleanup using Claude Agent SDK."""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import TYPE_CHECKING

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

if TYPE_CHECKING:
    from arch_whisper.config import Config

logger = logging.getLogger(__name__)

# Cleanup prompt for transcription post-processing
CLEANUP_PROMPT = """Clean up this transcribed speech. Fix punctuation, capitalization, and obvious transcription errors. Keep the meaning identical. Do not add or remove content. Output only the cleaned text with no explanation.

Transcribed text:
{text}

Cleaned text:"""


def _claude_cli_available() -> bool:
    """Check if Claude CLI is available."""
    return shutil.which("claude") is not None


class ClaudePostProcessor:
    """Post-processes transcriptions using Claude Agent SDK (keyless mode)."""

    def __init__(self, config: Config) -> None:
        """Initialize the post-processor.

        Args:
            config: Application configuration
        """
        self._config = config
        self._cli_available = _claude_cli_available()
        if not self._cli_available:
            logger.warning("Claude CLI not found - post-processing disabled")

    @property
    def available(self) -> bool:
        """Check if Claude processing is available."""
        return self._cli_available

    def process(self, raw_text: str) -> str:
        """Process transcribed text with Claude.

        Args:
            raw_text: Raw transcription text

        Returns:
            Cleaned text, or raw_text if processing fails
        """
        if not raw_text.strip():
            return raw_text

        if not self._cli_available:
            return raw_text

        try:
            return asyncio.run(self._process_async(raw_text))
        except Exception as e:
            logger.error("Claude processing failed: %s", e)
            return raw_text

    async def _process_async(self, raw_text: str) -> str:
        """Async implementation of text processing."""
        options = ClaudeAgentOptions(
            system_prompt="You are a transcription cleanup assistant. Output only the cleaned text with no explanation or preamble.",
            max_turns=1,
            model=self._config.claude_model,
            tools=[],  # No tools needed for simple text cleanup
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

        logger.warning("Empty response from Claude, using raw text")
        return raw_text
