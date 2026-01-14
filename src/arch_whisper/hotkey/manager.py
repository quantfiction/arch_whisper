"""Hotkey manager facade for arch_whisper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from arch_whisper.config import Config

from arch_whisper.utils import get_session_type

logger = logging.getLogger(__name__)


class HotkeyBackend(Protocol):
    """Protocol for hotkey backends."""

    def start(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None: ...

    def stop(self) -> None: ...


class HotkeyManager:
    """Manages hotkey detection across X11 and Wayland."""

    def __init__(self, config: Config) -> None:
        """Initialize the hotkey manager.

        Args:
            config: Application configuration
        """
        self._config = config
        self._backend: HotkeyBackend | None = None

        session = get_session_type()
        logger.info("Session type: %s", session)

        if session == "wayland":
            self._backend = self._try_wayland_backend()

        if self._backend is None:
            self._backend = self._try_x11_backend()

        if self._backend is None:
            logger.error("No hotkey backend available")

    def _try_x11_backend(self) -> HotkeyBackend | None:
        """Try to create X11 backend."""
        try:
            from arch_whisper.hotkey.x11 import X11HotkeyBackend

            return X11HotkeyBackend(self._config.hotkey)
        except Exception as e:
            logger.warning("X11 backend unavailable: %s", e)
            return None

    def _try_wayland_backend(self) -> HotkeyBackend | None:
        """Try to create Wayland backend."""
        try:
            from arch_whisper.hotkey.wayland import WaylandHotkeyBackend

            backend = WaylandHotkeyBackend(self._config.hotkey)
            # Check if evdev is actually available
            if not hasattr(backend, "_find_keyboard"):
                return None
            return backend
        except Exception as e:
            logger.warning("Wayland backend unavailable: %s", e)
            return None

    def start(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        """Start listening for hotkeys.

        Args:
            on_press: Called when hotkey is pressed
            on_release: Called when hotkey is released
        """
        if self._backend is None:
            logger.error("No hotkey backend, cannot start")
            return

        self._backend.start(on_press, on_release)

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._backend is not None:
            self._backend.stop()
