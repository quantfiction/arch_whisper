"""X11 paste backend using xdotool."""

from __future__ import annotations

import logging
import subprocess
import time

from arch_whisper.paste.clipboard import copy_to_clipboard

logger = logging.getLogger(__name__)


class X11PasteBackend:
    """Paste text using xdotool on X11."""

    def paste(self, text: str) -> bool:
        """Copy text to clipboard and simulate Ctrl+V.

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

        try:
            result = subprocess.run(
                ["xdotool", "key", "ctrl+v"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                logger.error("xdotool failed: %s", result.stderr.decode())
                return False
            return True
        except FileNotFoundError:
            logger.error("xdotool not found. Install with: sudo apt install xdotool")
            return False
        except Exception as e:
            logger.error("X11 paste failed: %s", e)
            return False
