"""Configuration dataclass for arch_whisper."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration with sensible defaults."""

    hotkey: str = "ctrl+space"
    whisper_model: str = "base"
    whisper_threads: int = 4
    whisper_language: str | None = "en"
    claude_enabled: bool = True
    claude_model: str = "claude-sonnet-4-20250514"
    ding_enabled: bool = True
    assets_dir: Path | None = None
