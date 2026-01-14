"""Paste manager facade for arch_whisper."""

from __future__ import annotations

import logging
from typing import Protocol

from arch_whisper.paste.clipboard import copy_to_clipboard
from arch_whisper.utils import get_session_type

logger = logging.getLogger(__name__)


class PasteBackend(Protocol):
    """Protocol for paste backends."""

    def paste(self, text: str) -> bool: ...


class PasteManager:
    """Manages pasting text across X11 and Wayland."""

    def __init__(self) -> None:
        """Initialize the paste manager."""
        self._backend: PasteBackend | None = None

        session = get_session_type()

        if session == "wayland":
            self._backend = self._try_wayland_backend()

        if self._backend is None:
            self._backend = self._try_x11_backend()

    def _try_x11_backend(self) -> PasteBackend | None:
        """Try to create X11 paste backend."""
        try:
            from arch_whisper.paste.x11 import X11PasteBackend

            return X11PasteBackend()
        except Exception as e:
            logger.warning("X11 paste backend unavailable: %s", e)
            return None

    def _try_wayland_backend(self) -> PasteBackend | None:
        """Try to create Wayland paste backend."""
        try:
            from arch_whisper.paste.wayland import WaylandPasteBackend

            backend = WaylandPasteBackend()
            # Check if a paste tool was found
            if backend._paste_tool is None:
                logger.warning("Wayland paste tools not found, falling back")
                return None
            return backend
        except Exception as e:
            logger.warning("Wayland paste backend unavailable: %s", e)
            return None

    def paste(self, text: str) -> bool:
        """Paste text into the focused application.

        Falls back to clipboard-only if paste simulation fails.

        Args:
            text: Text to paste

        Returns:
            True if paste succeeded, False if only clipboard copy succeeded
        """
        if self._backend is not None:
            if self._backend.paste(text):
                return True

        # Fallback: just copy to clipboard
        logger.warning("Paste failed, copying to clipboard only")
        return copy_to_clipboard(text)
