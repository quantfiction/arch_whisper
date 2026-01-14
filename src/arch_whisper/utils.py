"""Utility functions for arch_whisper."""

from __future__ import annotations

import os
from contextlib import contextmanager
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator, Literal


def get_session_type() -> Literal["x11", "wayland", "unknown"]:
    """Detect the current display session type."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session in ("x11", "wayland"):
        return session  # type: ignore
    return "unknown"


@contextmanager
def asset_path(name: str, assets_dir: Path | None = None) -> Iterator[Path]:
    """Yield a usable filesystem path to a bundled asset.

    This is safe for packaged resources because the returned `Path` is only
    valid for the lifetime of the context manager.

    Args:
        name: Asset filename (e.g., "icon_idle.svg", "ding.wav")
        assets_dir: Optional override directory for development

    Raises:
        FileNotFoundError: If the asset doesn't exist
    """
    if assets_dir is not None:
        override_path = assets_dir / name
        if override_path.exists():
            yield override_path
            return

    traversable = files("arch_whisper") / "assets" / name
    with as_file(traversable) as p:
        if not p.exists():
            raise FileNotFoundError(f"Asset not found: {name}")
        yield p
