"""X11 paste backend using xdotool."""

from __future__ import annotations

import logging
import subprocess
import time

from arch_whisper.paste.clipboard import copy_to_clipboard

logger = logging.getLogger(__name__)

# Terminal keywords to match in WM_CLASS (case-insensitive)
# These are substrings that indicate a terminal emulator
TERMINAL_KEYWORDS = {
    "terminal",
    "konsole",
    "xterm",
    "urxvt",
    "alacritty",
    "kitty",
    "terminator",
    "tilix",
    "terminology",
    "wezterm",
    "foot",
    "contour",
    "st-256color",
    "sakura",
    "tilda",
    "guake",
    "yakuake",
    "rxvt",
}


def _get_active_window_class() -> str | None:
    """Get the WM_CLASS of the currently focused window using xprop."""
    try:
        # First get the active window ID
        win_result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True,
            timeout=2,
        )
        if win_result.returncode != 0:
            return None

        window_id = win_result.stdout.decode().strip()

        # Then get WM_CLASS using xprop
        result = subprocess.run(
            ["xprop", "-id", window_id, "WM_CLASS"],
            capture_output=True,
            timeout=2,
        )
        if result.returncode == 0:
            # Parse: WM_CLASS(STRING) = "instance", "class"
            output = result.stdout.decode().strip().lower()
            return output
    except Exception as e:
        logger.debug("Could not get window class: %s", e)
    return None


def _is_terminal_window() -> bool:
    """Check if the active window is a terminal emulator."""
    wm_class = _get_active_window_class()
    if wm_class:
        # Check if any terminal keyword appears in the WM_CLASS string
        for keyword in TERMINAL_KEYWORDS:
            if keyword in wm_class:
                logger.debug("Detected terminal window: %s (matched: %s)", wm_class, keyword)
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
