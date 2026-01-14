"""Application state and core for arch_whisper."""

from enum import Enum, auto


class AppState(Enum):
    """Application state for tray indicator."""

    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
