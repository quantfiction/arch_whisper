"""Tests for terminal window detection.

The paste backend needs to detect terminal windows to use Ctrl+Shift+V
instead of Ctrl+V. This tests the WM_CLASS parsing logic.
"""

import subprocess
import unittest
from unittest.mock import patch, MagicMock

from arch_whisper.paste.x11 import (
    _get_active_window_class,
    _is_terminal_window,
    TERMINAL_KEYWORDS,
)


class TestTerminalKeywords(unittest.TestCase):
    """Verify terminal keywords cover common terminals."""

    def test_common_terminals_in_keywords(self):
        """Common terminal emulators should be in the keywords list."""
        expected = {"terminal", "konsole", "alacritty", "kitty", "wezterm", "xterm"}
        self.assertTrue(expected.issubset(TERMINAL_KEYWORDS))

    def test_keywords_are_lowercase(self):
        """All keywords should be lowercase for case-insensitive matching."""
        for kw in TERMINAL_KEYWORDS:
            self.assertEqual(kw, kw.lower(), f"Keyword '{kw}' is not lowercase")


class TestWMClassParsing(unittest.TestCase):
    """Tests for parsing xprop WM_CLASS output."""

    def test_wezterm_detection(self):
        """Wezterm should be detected from its WM_CLASS."""
        mock_output = 'wm_class(string) = "org.wezfurlong.wezterm", "org.wezfurlong.wezterm"'
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=mock_output):
            self.assertTrue(_is_terminal_window())

    def test_gnome_terminal_detection(self):
        """Gnome-terminal should be detected."""
        mock_output = 'wm_class(string) = "gnome-terminal-server", "gnome-terminal-server"'
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=mock_output):
            self.assertTrue(_is_terminal_window())

    def test_alacritty_detection(self):
        """Alacritty should be detected."""
        mock_output = 'wm_class(string) = "alacritty", "alacritty"'
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=mock_output):
            self.assertTrue(_is_terminal_window())

    def test_non_terminal_app(self):
        """Non-terminal apps should not be detected as terminals."""
        mock_output = 'wm_class(string) = "discord", "discord"'
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=mock_output):
            self.assertFalse(_is_terminal_window())

    def test_firefox_not_detected(self):
        """Firefox should not be detected as terminal."""
        mock_output = 'wm_class(string) = "navigator", "firefox"'
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=mock_output):
            self.assertFalse(_is_terminal_window())

    def test_vscode_not_detected(self):
        """VS Code should not be detected as terminal."""
        mock_output = 'wm_class(string) = "code", "code"'
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=mock_output):
            self.assertFalse(_is_terminal_window())

    def test_none_window_class(self):
        """None window class should return False."""
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=None):
            self.assertFalse(_is_terminal_window())

    def test_empty_window_class(self):
        """Empty window class should return False."""
        with patch('arch_whisper.paste.x11._get_active_window_class', return_value=""):
            self.assertFalse(_is_terminal_window())


class TestXpropIntegration(unittest.TestCase):
    """Tests for xprop subprocess integration."""

    def test_xdotool_failure_returns_none(self):
        """xdotool failure should return None gracefully."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            result = _get_active_window_class()
            self.assertIsNone(result)

    def test_xprop_failure_returns_none(self):
        """xprop failure should return None gracefully."""
        xdotool_result = MagicMock()
        xdotool_result.returncode = 0
        xdotool_result.stdout = b"12345"

        xprop_result = MagicMock()
        xprop_result.returncode = 1

        with patch('subprocess.run', side_effect=[xdotool_result, xprop_result]):
            result = _get_active_window_class()
            self.assertIsNone(result)

    def test_subprocess_timeout_returns_none(self):
        """Subprocess timeout should return None gracefully."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("cmd", 2)):
            result = _get_active_window_class()
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
