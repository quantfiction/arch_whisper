"""Tests for configuration loading.

Verifies defaults, custom values, and error handling for config files.
"""

import tempfile
import unittest
from pathlib import Path

from arch_whisper import config as config_module
from arch_whisper.config import Config, load_config


class TestConfigDefaults(unittest.TestCase):
    """Tests for default configuration values."""

    def test_default_hotkey(self):
        """Default hotkey should be ctrl+space."""
        c = Config()
        self.assertEqual(c.hotkey, "ctrl+space")

    def test_default_whisper_model(self):
        """Default Whisper model should be 'base'."""
        c = Config()
        self.assertEqual(c.whisper_model, "base")

    def test_default_claude_model(self):
        """Default Claude model should contain 'claude'."""
        c = Config()
        self.assertIn("claude", c.claude_model)

    def test_default_threads(self):
        """Default whisper threads should be 4."""
        c = Config()
        self.assertEqual(c.whisper_threads, 4)

    def test_claude_enabled_by_default(self):
        """Claude should be enabled by default."""
        c = Config()
        self.assertTrue(c.claude_enabled)


class TestConfigLoading(unittest.TestCase):
    """Tests for loading config from file."""

    def setUp(self):
        """Save original config path."""
        self.original_path = config_module.CONFIG_PATH
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Restore original config path."""
        config_module.CONFIG_PATH = self.original_path

    def test_missing_config_uses_defaults(self):
        """Missing config file should use defaults."""
        config_module.CONFIG_PATH = Path(self.temp_dir) / "nonexistent.toml"
        c = load_config()
        self.assertEqual(c.hotkey, "ctrl+space")

    def test_custom_hotkey(self):
        """Custom hotkey should override default."""
        config_file = Path(self.temp_dir) / "config.toml"
        config_file.write_text('hotkey = "ctrl+shift+r"')
        config_module.CONFIG_PATH = config_file

        c = load_config()
        self.assertEqual(c.hotkey, "ctrl+shift+r")

    def test_custom_whisper_model(self):
        """Custom Whisper model should override default."""
        config_file = Path(self.temp_dir) / "config.toml"
        config_file.write_text('whisper_model = "large-v3"')
        config_module.CONFIG_PATH = config_file

        c = load_config()
        self.assertEqual(c.whisper_model, "large-v3")

    def test_partial_config_merges_with_defaults(self):
        """Partial config should merge with defaults."""
        config_file = Path(self.temp_dir) / "config.toml"
        config_file.write_text('whisper_model = "small"')
        config_module.CONFIG_PATH = config_file

        c = load_config()
        self.assertEqual(c.whisper_model, "small")
        self.assertEqual(c.hotkey, "ctrl+space")  # Default preserved
        self.assertEqual(c.whisper_threads, 4)  # Default preserved


class TestConfigValidation(unittest.TestCase):
    """Tests for config validation and error handling."""

    def setUp(self):
        """Save original config path."""
        self.original_path = config_module.CONFIG_PATH
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Restore original config path."""
        config_module.CONFIG_PATH = self.original_path

    def test_malformed_toml_uses_defaults(self):
        """Malformed TOML should fall back to defaults."""
        config_file = Path(self.temp_dir) / "config.toml"
        config_file.write_text('invalid toml [[[')
        config_module.CONFIG_PATH = config_file

        c = load_config()
        self.assertEqual(c.hotkey, "ctrl+space")

    def test_empty_config_uses_defaults(self):
        """Empty config file should use defaults."""
        config_file = Path(self.temp_dir) / "config.toml"
        config_file.write_text('')
        config_module.CONFIG_PATH = config_file

        c = load_config()
        self.assertEqual(c.hotkey, "ctrl+space")

    def test_unknown_keys_ignored(self):
        """Unknown config keys should be ignored."""
        config_file = Path(self.temp_dir) / "config.toml"
        config_file.write_text('unknown_key = "value"\nhotkey = "ctrl+r"')
        config_module.CONFIG_PATH = config_file

        c = load_config()
        self.assertEqual(c.hotkey, "ctrl+r")
        self.assertFalse(hasattr(c, 'unknown_key'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
