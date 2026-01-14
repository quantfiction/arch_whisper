"""Wayland paste backend using wtype or ydotool."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time

from arch_whisper.paste.clipboard import copy_to_clipboard

logger = logging.getLogger(__name__)


class WaylandPasteBackend:
    """Paste text on Wayland using wtype or ydotool."""

    def __init__(self) -> None:
        """Initialize and detect available paste tool."""
        self._paste_tool = self._detect_paste_tool()
        if self._paste_tool:
            logger.info("Wayland paste tool: %s", self._paste_tool)
        else:
            logger.warning("No Wayland paste tool found")

    def _detect_paste_tool(self) -> str | None:
        """Detect available keystroke injection tool."""
        if shutil.which("wtype"):
            return "wtype"
        if shutil.which("ydotool"):
            return "ydotool"
        return None

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

        if self._paste_tool is None:
            logger.warning("No paste tool available, text copied to clipboard only")
            return False

        # Small delay to ensure clipboard is ready
        time.sleep(0.05)

        try:
            if self._paste_tool == "wtype":
                result = subprocess.run(
                    ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                    capture_output=True,
                    timeout=5,
                )
            else:  # ydotool
                result = subprocess.run(
                    ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],  # Ctrl+V
                    capture_output=True,
                    timeout=5,
                )

            if result.returncode != 0:
                logger.error("%s failed: %s", self._paste_tool, result.stderr.decode())
                return False
            return True

        except FileNotFoundError:
            logger.error("%s not found", self._paste_tool)
            return False
        except Exception as e:
            logger.error("Wayland paste failed: %s", e)
            return False
