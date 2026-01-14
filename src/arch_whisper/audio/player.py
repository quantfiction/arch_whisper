"""Audio playback for arch_whisper."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import sounddevice as sd

from arch_whisper.utils import asset_path

logger = logging.getLogger(__name__)


def play_ding(assets_dir: Path | None = None) -> None:
    """Play recording start sound (non-blocking).

    Args:
        assets_dir: Optional override for asset directory
    """
    try:
        import soundfile as sf

        with asset_path("ding.wav", assets_dir) as ding_path:
            data, samplerate = sf.read(ding_path)

        sd.play(data, samplerate)
        # Don't wait - fire and forget
    except FileNotFoundError:
        logger.debug("Ding sound not found, playing generated tone")
        _play_generated_ding()
    except Exception as e:
        logger.warning("Failed to play ding: %s", e)


def _play_generated_ding() -> None:
    """Play a simple generated sine wave as fallback."""
    try:
        duration = 0.1  # seconds
        frequency = 880  # Hz (A5 note)
        sample_rate = 44100

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        # Sine wave with fade out
        tone = np.sin(2 * np.pi * frequency * t)
        fade = np.linspace(1, 0, len(tone))
        tone = tone * fade * 0.3  # Lower volume

        sd.play(tone.astype(np.float32), sample_rate)
    except Exception as e:
        logger.warning("Failed to play generated ding: %s", e)


def generate_ding_wav(output_path: Path) -> None:
    """Generate a ding.wav file for bundling.

    This is a utility for development - run once to create the asset.

    Args:
        output_path: Where to save the WAV file
    """
    import soundfile as sf

    duration = 0.15
    frequency = 880
    sample_rate = 44100

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Two-tone ding (880Hz + 1320Hz)
    tone = np.sin(2 * np.pi * frequency * t) + 0.5 * np.sin(2 * np.pi * 1320 * t)
    # Envelope: quick attack, smooth decay
    envelope = np.exp(-t * 15) * (1 - np.exp(-t * 100))
    tone = tone * envelope * 0.4

    sf.write(output_path, tone.astype(np.float32), sample_rate)
