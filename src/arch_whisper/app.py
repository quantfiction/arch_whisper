"""Application state and core for arch_whisper."""

from __future__ import annotations

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

if TYPE_CHECKING:
    from arch_whisper.config import Config

from arch_whisper.audio.player import play_ding
from arch_whisper.audio.recorder import AudioRecorder
from arch_whisper.hotkey.manager import HotkeyManager
from arch_whisper.notifications import init_notifications, notify
from arch_whisper.paste.manager import PasteManager
from arch_whisper.transcription.whisper import WhisperTranscriber
from arch_whisper.tray.indicator import TrayIndicator

logger = logging.getLogger(__name__)


class AppState(Enum):
    """Application state for tray indicator."""

    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()


class App:
    """Main application orchestrator."""

    def __init__(self, config: Config) -> None:
        """Initialize the application.

        Args:
            config: Application configuration
        """
        self._config = config
        self._state = AppState.IDLE

        # Initialize notifications
        init_notifications("arch-whisper")

        # Components (initialized lazily or on run)
        self._tray: TrayIndicator | None = None
        self._hotkey_manager: HotkeyManager | None = None
        self._recorder: AudioRecorder | None = None
        self._transcriber: WhisperTranscriber | None = None
        self._postprocessor = None  # Optional, P1
        self._paste_manager: PasteManager | None = None

    @property
    def state(self) -> AppState:
        """Get current application state."""
        return self._state

    def _set_state(self, state: AppState) -> None:
        """Update application state and notify tray.

        Args:
            state: New application state
        """
        self._state = state
        logger.debug("State: %s", state.name)

        if self._tray is not None:
            # Schedule UI update on GTK thread
            GLib.idle_add(self._tray.set_state, state)
