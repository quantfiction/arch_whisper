"""Audio recording for arch_whisper."""

from __future__ import annotations

import logging
import threading

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Thread-safe audio recorder from the default microphone."""

    SAMPLE_RATE = 16000  # Whisper requirement
    CHANNELS = 1  # Mono

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        """Initialize the recorder.

        Args:
            sample_rate: Audio sample rate in Hz (default: 16000 for Whisper)
        """
        self._sample_rate = sample_rate
        self._buffer: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        with self._lock:
            return self._recording

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for audio stream - stores chunks in buffer."""
        if status:
            logger.warning("Audio callback status: %s", status)
        with self._lock:
            if self._recording:
                self._buffer.append(indata.copy())

    def start(self) -> None:
        """Start recording audio from the microphone."""
        with self._lock:
            if self._recording:
                logger.warning("Already recording, ignoring start()")
                return

            self._buffer = []
            self._recording = True

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self.CHANNELS,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.error("Failed to start recording: %s", e)
            with self._lock:
                self._recording = False
            raise

    def stop(self) -> np.ndarray:
        """Stop recording and return captured audio.

        Safe to call multiple times - subsequent calls return empty array.

        Returns:
            Numpy array of audio samples (float32, mono)
        """
        with self._lock:
            if not self._recording:
                return np.array([], dtype=np.float32)
            self._recording = False
            buffer_copy = self._buffer.copy()
            self._buffer = []

        # Close stream outside lock
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning("Error closing audio stream: %s", e)
            finally:
                self._stream = None

        if not buffer_copy:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(buffer_copy, axis=0)
        return audio.flatten()
