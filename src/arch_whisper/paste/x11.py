"""X11 paste backend using xdotool."""

from __future__ import annotations

import logging
import subprocess
import time

from arch_whisper.paste.clipboard import copy_to_clipboard

logger = logging.getLogger(__name__)

# Terminal window classes that need Ctrl+Shift+V instead of Ctrl+V
TERMINAL_CLASSES = {
    "gnome-terminal",
    "konsole",
    "xterm",
    "urxvt",
    "alacritty",
    "kitty",
    "terminator",
    "tilix",
    "xfce4-terminal",
    "mate-terminal",
    "lxterminal",
    "terminology",
    "st",
    "wezterm",
    "foot",
    "contour",
}


def _get_active_window_class() -> str | None:
    """Get the WM_CLASS of the currently focused window."""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowclassname"],
            capture_output=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.decode().strip().lower()
    except Exception as e:
        logger.debug("Could not get window class: %s", e)
    return None


def _is_terminal_window() -> bool:
    """Check if the active window is a terminal emulator."""
    window_class = _get_active_window_class()
    if window_class:
        # Check for exact match or partial match (e.g., "gnome-terminal-server")
        for term_class in TERMINAL_CLASSES:
            if term_class in window_class:
                logger.debug("Detected terminal window: %s", window_class)
                return True
    return False


class X11PasteBackend:
    """Paste text using xdotool on X11."""

    def paste(self, text: str) -> bool:
        """Copy text to clipboard and simulate paste shortcut.

        Uses Ctrl+Shift+V for terminals, Ctrl+V for other apps.

        Args:
            text: Text to paste

        Returns:
            True if paste succeeded, False otherwise
        """
        if not copy_to_clipboard(text):
            logger.error("Failed to copy to clipboard")
            return False

        # Small delay to ensure clipboard is ready
        time.sleep(0.05)

        # Use Ctrl+Shift+V for terminals, Ctrl+V for other apps
        if _is_terminal_window():
            paste_keys = "ctrl+shift+v"
        else:
            paste_keys = "ctrl+v"

        try:
            result = subprocess.run(
                ["xdotool", "key", paste_keys],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.error("xdotool failed: %s", result.stderr.decode())
                return False
            logger.debug("Paste sent with %s", paste_keys)
            return True
        except FileNotFoundError:
            logger.error("xdotool not found. Install with: sudo apt install xdotool")
            return False
        except Exception as e:
            logger.error("X11 paste failed: %s", e)
            return False
