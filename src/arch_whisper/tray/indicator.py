"""System tray indicator for arch_whisper."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import gi

gi.require_version("Gtk", "3.0")

# Try AyatanaAppIndicator3, common on Ubuntu
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator

    INDICATOR_AVAILABLE = True
except (ValueError, ImportError):
    INDICATOR_AVAILABLE = False

from gi.repository import Gtk

if TYPE_CHECKING:
    from arch_whisper.app import AppState

from arch_whisper.utils import asset_path

logger = logging.getLogger(__name__)

# Icon filenames for each state
ICON_FILES = {
    "IDLE": "icon_idle.svg",
    "RECORDING": "icon_recording.svg",
    "PROCESSING": "icon_processing.svg",
}


class TrayIndicator:
    """System tray indicator showing application state."""

    def __init__(
        self,
        on_quit: Callable[[], None],
        assets_dir: Path | None = None,
    ) -> None:
        """Initialize the tray indicator.

        Args:
            on_quit: Callback when user selects Quit from menu
            assets_dir: Optional override for asset directory
        """
        self._on_quit = on_quit
        self._assets_dir = assets_dir
        self._indicator = None

        if not INDICATOR_AVAILABLE:
            logger.warning("AppIndicator not available, tray icon disabled")
            return

        # Set initial icon (keep resource path valid during call)
        with asset_path(ICON_FILES["IDLE"], self._assets_dir) as icon_path:
            self._indicator = AppIndicator.Indicator.new(
                "arch-whisper",
                str(icon_path),
                AppIndicator.IndicatorCategory.APPLICATION_STATUS,
            )

        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_menu(self._build_menu())

    def _build_menu(self) -> Gtk.Menu:
        """Build the right-click context menu."""
        menu = Gtk.Menu()

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self._on_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def set_state(self, state: AppState) -> None:
        """Update the tray icon to reflect current state.

        Args:
            state: Current application state
        """
        if self._indicator is None:
            return

        filename = ICON_FILES.get(state.name, ICON_FILES["IDLE"])
        with asset_path(filename, self._assets_dir) as icon_path:
            self._indicator.set_icon_full(str(icon_path), state.name)
