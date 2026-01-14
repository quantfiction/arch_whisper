"""Application state and core for arch_whisper."""

from __future__ import annotations

import logging
import threading
from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np
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

    def _process_recording(self, audio: np.ndarray) -> None:
        """Process recorded audio: transcribe, cleanup, paste.

        Args:
            audio: Recorded audio samples
        """
        self._set_state(AppState.PROCESSING)

        try:
            # Step 1: Transcribe
            if self._transcriber is None:
                logger.error("Transcriber not initialized")
                return

            text = self._transcriber.transcribe(audio)

            if not text.strip():
                logger.info("No speech detected, skipping paste")
                return

            # Step 2: Optional Claude cleanup
            if self._config.claude_enabled and self._postprocessor is not None:
                if self._postprocessor.available:
                    text = self._postprocessor.process(text)

            # Step 3: Paste
            if self._paste_manager is None:
                logger.error("Paste manager not initialized")
                notify("Error", "Paste manager not available")
                return

            success = self._paste_manager.paste(text)

            if not success:
                notify(
                    "Copied to clipboard",
                    "Paste simulation failed. Use Ctrl+V to paste.",
                )

        except Exception as e:
            logger.error("Processing failed: %s", e)
            notify("Error", f"Processing failed: {e}")

        finally:
            self._set_state(AppState.IDLE)

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press - start recording."""
        if self._state != AppState.IDLE:
            logger.debug("Not idle, ignoring hotkey press")
            return

        self._set_state(AppState.RECORDING)

        if self._config.ding_enabled:
            play_ding(self._config.assets_dir)

        if self._recorder is not None:
            self._recorder.start()

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release - stop recording and process."""
        if self._state != AppState.RECORDING:
            logger.debug("Not recording, ignoring hotkey release")
            return

        if self._recorder is None:
            self._set_state(AppState.IDLE)
            return

        audio = self._recorder.stop()

        # Process in background thread to keep GTK responsive
        thread = threading.Thread(
            target=self._process_recording,
            args=(audio,),
            daemon=True,
        )
        thread.start()

    def run(self) -> None:
        """Start the application."""
        logger.info("Starting arch-whisper")

        # Initialize components
        self._recorder = AudioRecorder()
        self._transcriber = WhisperTranscriber(self._config)
        self._paste_manager = PasteManager()

        # Optional Claude postprocessor
        if self._config.claude_enabled:
            try:
                from arch_whisper.postprocess.claude import ClaudePostProcessor

                self._postprocessor = ClaudePostProcessor(self._config)
            except Exception as e:
                logger.warning("Claude postprocessor unavailable: %s", e)

        # Initialize tray
        self._tray = TrayIndicator(
            on_quit=self.stop,
            assets_dir=self._config.assets_dir,
        )

        # Initialize hotkey manager
        self._hotkey_manager = HotkeyManager(self._config)
        self._hotkey_manager.start(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

        logger.info("Application ready. Press %s to record.", self._config.hotkey)
        notify("Arch Whisper", f"Ready. Hold {self._config.hotkey} to record.")

        # Start GTK main loop
        Gtk.main()

    def stop(self) -> None:
        """Stop the application gracefully."""
        logger.info("Stopping arch-whisper")

        # Stop hotkey listener
        if self._hotkey_manager is not None:
            self._hotkey_manager.stop()

        # Stop any active recording
        if self._recorder is not None and self._recorder.is_recording:
            self._recorder.stop()

        # Quit GTK
        GLib.idle_add(Gtk.main_quit)
