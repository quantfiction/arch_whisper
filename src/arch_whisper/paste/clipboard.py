"""Clipboard abstraction for arch_whisper."""

from __future__ import annotations

import logging
import subprocess

import pyperclip

from arch_whisper.utils import get_session_type

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to the system clipboard.

    Args:
        text: Text to copy

    Returns:
        True if successful, False otherwise
    """
    session = get_session_type()

    if session == "wayland":
        return _wl_copy(text)
    else:
        return _x11_copy(text)


def _x11_copy(text: str) -> bool:
    """Copy using pyperclip (works on X11)."""
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.error("X11 clipboard copy failed: %s", e)
        return False


def _wl_copy(text: str) -> bool:
    """Copy using wl-copy (Wayland)."""
    try:
        result = subprocess.run(
            ["wl-copy"],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.error("wl-copy failed: %s", result.stderr.decode())
            return False
        return True
    except FileNotFoundError:
        logger.error("wl-copy not found. Install wl-clipboard.")
        return False
    except Exception as e:
        logger.error("Wayland clipboard copy failed: %s", e)
        return False
