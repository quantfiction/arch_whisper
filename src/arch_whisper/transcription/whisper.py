"""Whisper transcription for arch_whisper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from faster_whisper import WhisperModel

if TYPE_CHECKING:
    from arch_whisper.config import Config

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio using faster-whisper with lazy model loading."""

    def __init__(self, config: Config) -> None:
        """Initialize the transcriber.

        Args:
            config: Application configuration
        """
        self._config = config
        self._model: WhisperModel | None = None

    def _ensure_model(self) -> WhisperModel:
        """Lazy-load the Whisper model on first use."""
        if self._model is None:
            logger.info(
                "Loading Whisper model: %s (threads=%d)",
                self._config.whisper_model,
                self._config.whisper_threads,
            )
            self._model = WhisperModel(
                self._config.whisper_model,
                device="cpu",
                compute_type="int8",
                cpu_threads=self._config.whisper_threads,
            )
            logger.info("Whisper model loaded")
        return self._model
