"""Tests for Claude post-processor.

This is critical functionality - if Claude post-processing breaks,
the app is broken for its primary use case.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from arch_whisper.config import Config
from arch_whisper.postprocess.claude import ClaudePostProcessor, CLEANUP_PROMPT


class TestClaudePostProcessorAvailability(unittest.TestCase):
    """Tests for checking if Claude is available."""

    def test_available_when_cli_exists(self):
        """Should be available when claude CLI is found."""
        with patch('shutil.which', return_value='/usr/bin/claude'):
            processor = ClaudePostProcessor(Config())
            self.assertTrue(processor.available)

    def test_unavailable_when_cli_missing(self):
        """Should be unavailable when claude CLI is not found."""
        with patch('shutil.which', return_value=None):
            processor = ClaudePostProcessor(Config())
            self.assertFalse(processor.available)


class TestCleanupPrompt(unittest.TestCase):
    """Tests for the cleanup prompt format."""

    def test_prompt_includes_filler_removal(self):
        """Prompt should explicitly mention removing filler words."""
        self.assertIn("filler", CLEANUP_PROMPT.lower())
        self.assertIn("um", CLEANUP_PROMPT.lower())

    def test_prompt_has_text_placeholder(self):
        """Prompt should have {text} placeholder for input."""
        self.assertIn("{text}", CLEANUP_PROMPT)

    def test_prompt_requests_no_explanation(self):
        """Prompt should request clean output without explanation."""
        self.assertIn("no explanation", CLEANUP_PROMPT.lower())


class TestClaudePostProcessing(unittest.TestCase):
    """Tests for the actual post-processing logic."""

    def test_empty_input_returns_empty(self):
        """Empty input should return empty without calling Claude."""
        with patch('shutil.which', return_value='/usr/bin/claude'):
            processor = ClaudePostProcessor(Config())

            result = processor.process("")
            self.assertEqual(result, "")

            result = processor.process("   ")
            self.assertEqual(result, "   ")

    def test_returns_raw_text_when_cli_unavailable(self):
        """Should return raw text when Claude CLI is not available."""
        with patch('shutil.which', return_value=None):
            processor = ClaudePostProcessor(Config())

            result = processor.process("some raw text")
            self.assertEqual(result, "some raw text")

    def test_successful_processing_returns_cleaned_text(self):
        """Should return cleaned text on successful Claude response."""
        from claude_agent_sdk import AssistantMessage, TextBlock

        # Mock the async query to return a proper response
        mock_message = MagicMock(spec=AssistantMessage)
        mock_block = MagicMock(spec=TextBlock)
        mock_block.text = "Cleaned output text"
        mock_message.content = [mock_block]

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch('shutil.which', return_value='/usr/bin/claude'):
            with patch('arch_whisper.postprocess.claude.query', mock_query):
                processor = ClaudePostProcessor(Config())
                result = processor.process("So, um, like, raw input")

                self.assertEqual(result, "Cleaned output text")

    def test_error_returns_raw_text(self):
        """Should return raw text when Claude processing fails."""
        async def mock_query_error(*args, **kwargs):
            raise Exception("API Error")
            yield  # Make it a generator

        with patch('shutil.which', return_value='/usr/bin/claude'):
            with patch('arch_whisper.postprocess.claude.query', mock_query_error):
                processor = ClaudePostProcessor(Config())
                result = processor.process("raw input that should be returned")

                self.assertEqual(result, "raw input that should be returned")

    def test_empty_response_returns_raw_text(self):
        """Should return raw text when Claude returns empty response."""
        from claude_agent_sdk import AssistantMessage, TextBlock

        # Mock empty response
        mock_message = MagicMock(spec=AssistantMessage)
        mock_block = MagicMock(spec=TextBlock)
        mock_block.text = ""  # Empty response
        mock_message.content = [mock_block]

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch('shutil.which', return_value='/usr/bin/claude'):
            with patch('arch_whisper.postprocess.claude.query', mock_query):
                processor = ClaudePostProcessor(Config())
                result = processor.process("raw input")

                # Should fall back to raw text
                self.assertEqual(result, "raw input")

    def test_whitespace_only_response_returns_raw_text(self):
        """Should return raw text when Claude returns only whitespace."""
        from claude_agent_sdk import AssistantMessage, TextBlock

        mock_message = MagicMock(spec=AssistantMessage)
        mock_block = MagicMock(spec=TextBlock)
        mock_block.text = "   \n\t  "  # Whitespace only
        mock_message.content = [mock_block]

        async def mock_query(*args, **kwargs):
            yield mock_message

        with patch('shutil.which', return_value='/usr/bin/claude'):
            with patch('arch_whisper.postprocess.claude.query', mock_query):
                processor = ClaudePostProcessor(Config())
                result = processor.process("raw input")

                self.assertEqual(result, "raw input")


class TestClaudeIntegration(unittest.TestCase):
    """Integration-style tests that verify the full flow works."""

    def test_model_from_config_is_used(self):
        """Should use the model specified in config."""
        from claude_agent_sdk import AssistantMessage, TextBlock, ClaudeAgentOptions

        captured_options = []

        mock_message = MagicMock(spec=AssistantMessage)
        mock_block = MagicMock(spec=TextBlock)
        mock_block.text = "cleaned"
        mock_message.content = [mock_block]

        original_query = None

        async def mock_query(prompt, options):
            captured_options.append(options)
            yield mock_message

        config = Config()
        config.claude_model = "claude-test-model"

        with patch('shutil.which', return_value='/usr/bin/claude'):
            with patch('arch_whisper.postprocess.claude.query', mock_query):
                processor = ClaudePostProcessor(config)
                processor.process("test input")

        self.assertEqual(len(captured_options), 1)
        self.assertEqual(captured_options[0].model, "claude-test-model")


if __name__ == '__main__':
    unittest.main(verbosity=2)
