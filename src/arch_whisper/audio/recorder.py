"""Audio recording for arch_whisper."""

from __future__ import annotations

import logging

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from the default microphone."""

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
        self._buffer.append(indata.copy())

    def start(self) -> None:
        """Start recording audio from the microphone."""
        self._buffer = []
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=self.CHANNELS,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return captured audio.

        Returns:
            Numpy array of audio samples (float32, mono)
        """
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._buffer:
            return np.array([], dtype=np.float32)

        # Concatenate all chunks and flatten to 1D
        audio = np.concatenate(self._buffer, axis=0)
        return audio.flatten()
