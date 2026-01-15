"""Preflight dependency checks for arch_whisper."""

from __future__ import annotations

import logging
import shutil

from arch_whisper.utils import get_session_type

logger = logging.getLogger(__name__)


def check_dependencies() -> list[str]:
    """Check for required system dependencies.

    Returns:
        List of missing dependency descriptions
    """
    missing: list[str] = []
    session = get_session_type()

    # Check GTK/GI
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Notify", "0.7")
        from gi.repository import Gtk, Notify  # noqa: F401
    except (ImportError, ValueError) as e:
        missing.append(f"PyGObject/GTK ({e})")

    # Check AppIndicator
    try:
        import gi

        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3  # noqa: F401
    except (ImportError, ValueError):
        missing.append("gir1.2-ayatanaappindicator3-0.1")

    # Session-specific checks
    if session == "x11":
        if not shutil.which("xdotool"):
            missing.append("xdotool (sudo apt install xdotool)")

    elif session == "wayland":
        if not shutil.which("wl-copy"):
            missing.append("wl-clipboard (sudo apt install wl-clipboard)")

        has_paste_tool = (
            shutil.which("wtype") is not None or shutil.which("ydotool") is not None
        )
        if not has_paste_tool:
            missing.append("wtype or ydotool (for paste simulation)")

    return missing


def check_optional_dependencies() -> dict[str, bool]:
    """Check optional dependencies and their availability.

    Returns:
        Dict mapping feature names to availability
    """
    features: dict[str, bool] = {}

    # Claude CLI (used via Agent SDK for post-processing)
    features["claude_cli"] = shutil.which("claude") is not None

    # Wayland evdev access
    session = get_session_type()
    if session == "wayland":
        try:
            import evdev

            devices = list(evdev.list_devices())
            features["evdev_access"] = len(devices) > 0
        except Exception:
            features["evdev_access"] = False

    return features
