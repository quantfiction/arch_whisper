"""Whisper transcription for arch_whisper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
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

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio samples as float32 numpy array

        Returns:
            Transcribed text, or empty string if no speech detected
        """
        if audio.size == 0:
            logger.debug("Empty audio input, returning empty string")
            return ""

        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        model = self._ensure_model()

        try:
            segments, info = model.transcribe(
                audio,
                vad_filter=True,
                language=self._config.whisper_language,
            )

            # Concatenate all segment texts
            text = " ".join(seg.text.strip() for seg in segments)
            text = text.strip()

            if text:
                logger.debug("Transcribed %d chars", len(text))
            else:
                logger.debug("No speech detected in audio")

            return text

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return ""
