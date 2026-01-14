"""Wayland hotkey backend using evdev."""

from __future__ import annotations

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import evdev
    from evdev import ecodes

    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False


class WaylandHotkeyBackend:
    """Global hotkey listener for Wayland using evdev.

    Requires user to be in 'input' group for /dev/input access.
    """

    def __init__(self, hotkey: str = "ctrl+space") -> None:
        """Initialize the backend.

        Args:
            hotkey: Hotkey combination (currently only ctrl+space supported)
        """
        self._hotkey = hotkey
        self._device: evdev.InputDevice | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._on_press: Callable[[], None] | None = None
        self._on_release: Callable[[], None] | None = None

        self._ctrl_pressed = False
        self._space_pressed = False
        self._combo_active = False

    def _find_keyboard(self) -> evdev.InputDevice | None:
        """Find a keyboard device that has KEY_SPACE."""
        if not EVDEV_AVAILABLE:
            return None

        for path in evdev.list_devices():
            try:
                device = evdev.InputDevice(path)
                capabilities = device.capabilities()
                if ecodes.EV_KEY in capabilities:
                    keys = capabilities[ecodes.EV_KEY]
                    if ecodes.KEY_SPACE in keys:
                        logger.info("Found keyboard: %s (%s)", device.name, path)
                        return device
            except (PermissionError, OSError) as e:
                logger.debug("Cannot access %s: %s", path, e)
                continue

        return None

    def _event_loop(self) -> None:
        """Main event loop running in separate thread."""
        if self._device is None:
            return

        try:
            for event in self._device.read_loop():
                if not self._running:
                    break

                if event.type != ecodes.EV_KEY:
                    continue

                # event.value: 0=release, 1=press, 2=repeat
                is_press = event.value == 1
                is_release = event.value == 0

                # Track Ctrl (left or right)
                if event.code in (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL):
                    if is_press:
                        self._ctrl_pressed = True
                    elif is_release:
                        self._ctrl_pressed = False

                # Track Space
                if event.code == ecodes.KEY_SPACE:
                    if is_press and not self._space_pressed:
                        self._space_pressed = True
                    elif is_release:
                        self._space_pressed = False

                # Check combo state changes
                combo_should_be_active = self._ctrl_pressed and self._space_pressed

                if combo_should_be_active and not self._combo_active:
                    self._combo_active = True
                    logger.debug("Hotkey pressed: %s", self._hotkey)
                    if self._on_press:
                        self._on_press()

                elif not combo_should_be_active and self._combo_active:
                    self._combo_active = False
                    logger.debug("Hotkey released: %s", self._hotkey)
                    if self._on_release:
                        self._on_release()

        except Exception as e:
            if self._running:
                logger.error("Event loop error: %s", e)

    def start(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        """Start listening for the hotkey.

        Args:
            on_press: Called when hotkey combo is pressed
            on_release: Called when hotkey combo is released
        """
        if not EVDEV_AVAILABLE:
            logger.error("evdev not available, Wayland hotkeys disabled")
            return

        self._device = self._find_keyboard()
        if self._device is None:
            logger.error(
                "No keyboard found. Ensure user is in 'input' group: "
                "sudo usermod -aG input $USER"
            )
            return

        self._on_press = on_press
        self._on_release = on_release
        self._running = True

        self._thread = threading.Thread(target=self._event_loop, daemon=True)
        self._thread.start()
        logger.info("Wayland hotkey listener started")

    def stop(self) -> None:
        """Stop the hotkey listener."""
        self._running = False

        if self._device is not None:
            try:
                self._device.close()
            except Exception:
                pass
            self._device = None

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        logger.info("Wayland hotkey listener stopped")
