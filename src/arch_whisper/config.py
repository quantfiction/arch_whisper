"""Configuration dataclass for arch_whisper."""

import sys
from dataclasses import dataclass, fields
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

CONFIG_PATH = Path.home() / ".config" / "arch-whisper" / "config.toml"


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


def load_config() -> Config:
    """Load config from file, falling back to defaults."""
    if not CONFIG_PATH.exists():
        return Config()
    try:
        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        return Config(**{k: v for k, v in data.items() if hasattr(Config, k)})
    except Exception:
        return Config()


def save_config(config: Config) -> None:
    """Save config to file."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for field in fields(config):
        value = getattr(config, field.name)
        if value is None:
            continue
        if isinstance(value, str):
            lines.append(f'{field.name} = "{value}"')
        elif isinstance(value, bool):
            lines.append(f'{field.name} = {str(value).lower()}')
        elif isinstance(value, Path):
            lines.append(f'{field.name} = "{value}"')
        else:
            lines.append(f'{field.name} = {value}')
    CONFIG_PATH.write_text("\n".join(lines) + "\n")
