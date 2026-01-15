"""Tests for Claude post-processor.

This is critical functionality - if Claude post-processing breaks,
the app is broken for its primary use case.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from arch_whisper.config import Config
from arch_whisper.postprocess.claude import ClaudePostProcessor, CLEANUP_PROMPT


class TestClaudePostProcessorAvailability(unittest.TestCase):
    """Tests for checking if Claude is available."""

    def test_available_when_cli_exists(self):
        """Should be available when claude CLI is found."""
        with patch('shutil.which', return_value='/usr/bin/claude'):
            with patch.dict('os.environ', {}, clear=True):
                config = Config()
                config.anthropic_api_key = None
                processor = ClaudePostProcessor(config)
                self.assertTrue(processor.available)

    def test_unavailable_when_cli_missing_and_no_api_key(self):
        """Should be unavailable when claude CLI and API key are missing."""
        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                config = Config()
                config.anthropic_api_key = None
                processor = ClaudePostProcessor(config)
                self.assertFalse(processor.available)

    def test_available_with_api_key(self):
        """Should be available when API key is provided."""
        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                config = Config()
                config.anthropic_api_key = "sk-ant-test"
                processor = ClaudePostProcessor(config)
                self.assertTrue(processor.available)

    def test_api_key_from_environment(self):
        """Should use API key from environment variable."""
        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-env'}):
                config = Config()
                config.anthropic_api_key = None
                processor = ClaudePostProcessor(config)
                self.assertTrue(processor.available)

    def test_config_api_key_takes_precedence(self):
        """Config API key should take precedence over environment."""
        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-ant-env'}):
                config = Config()
                config.anthropic_api_key = "sk-ant-config"
                processor = ClaudePostProcessor(config)
                self.assertEqual(processor._api_key, "sk-ant-config")


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
            with patch.dict('os.environ', {}, clear=True):
                config = Config()
                config.anthropic_api_key = None
                processor = ClaudePostProcessor(config)

                result = processor.process("")
                self.assertEqual(result, "")

                result = processor.process("   ")
                self.assertEqual(result, "   ")

    def test_returns_raw_text_when_unavailable(self):
        """Should return raw text when Claude is not available."""
        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                config = Config()
                config.anthropic_api_key = None
                processor = ClaudePostProcessor(config)

                result = processor.process("some raw text")
                self.assertEqual(result, "some raw text")

    def test_api_processing_success(self):
        """Should return cleaned text when using API."""
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Cleaned output"
        mock_response.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                with patch('anthropic.Anthropic', return_value=mock_client):
                    config = Config()
                    config.anthropic_api_key = "sk-ant-test"
                    processor = ClaudePostProcessor(config)

                    result = processor.process("raw input with um and uh")
                    self.assertEqual(result, "Cleaned output")

    def test_api_error_returns_raw_text(self):
        """Should return raw text when API call fails."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API Error")

        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                with patch('anthropic.Anthropic', return_value=mock_client):
                    config = Config()
                    config.anthropic_api_key = "sk-ant-test"
                    processor = ClaudePostProcessor(config)

                    result = processor.process("raw input")
                    self.assertEqual(result, "raw input")

    def test_empty_api_response_returns_raw_text(self):
        """Should return raw text when API returns empty response."""
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = ""
        mock_response.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                with patch('anthropic.Anthropic', return_value=mock_client):
                    config = Config()
                    config.anthropic_api_key = "sk-ant-test"
                    processor = ClaudePostProcessor(config)

                    result = processor.process("raw input")
                    self.assertEqual(result, "raw input")


class TestClaudeIntegration(unittest.TestCase):
    """Integration-style tests that verify the full flow works."""

    def test_model_from_config_is_used(self):
        """Should use the model specified in config."""
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "cleaned"
        mock_response.content = [mock_content]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch('shutil.which', return_value=None):
            with patch.dict('os.environ', {}, clear=True):
                with patch('anthropic.Anthropic', return_value=mock_client):
                    config = Config()
                    config.anthropic_api_key = "sk-ant-test"
                    config.claude_model = "claude-test-model"
                    processor = ClaudePostProcessor(config)
                    processor.process("test input")

                    # Check that the model was passed to the API
                    call_kwargs = mock_client.messages.create.call_args[1]
                    self.assertEqual(call_kwargs['model'], "claude-test-model")


if __name__ == '__main__':
    unittest.main(verbosity=2)
