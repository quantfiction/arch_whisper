"""X11 hotkey backend using pynput."""

from __future__ import annotations

import logging
from typing import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class X11HotkeyBackend:
    """Global hotkey listener for X11 using pynput."""

    def __init__(self, hotkey: str = "ctrl+space") -> None:
        """Initialize the backend.

        Args:
            hotkey: Hotkey combination (currently only ctrl+space supported)
        """
        self._hotkey = hotkey
        self._listener: keyboard.Listener | None = None
        self._on_press: Callable[[], None] | None = None
        self._on_release: Callable[[], None] | None = None

        # Track key states to detect combo and filter repeats
        self._ctrl_pressed = False
        self._space_pressed = False
        self._combo_active = False

    def _handle_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key press events."""
        # Track Ctrl
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = True

        # Track Space
        if key == keyboard.Key.space:
            if self._space_pressed:
                # Key repeat - ignore
                return
            self._space_pressed = True

        # Check if combo just became active
        if self._ctrl_pressed and self._space_pressed and not self._combo_active:
            self._combo_active = True
            logger.debug("Hotkey pressed: %s", self._hotkey)
            if self._on_press:
                self._on_press()

    def _handle_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Handle key release events."""
        released_ctrl = key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        released_space = key == keyboard.Key.space

        if released_ctrl:
            self._ctrl_pressed = False
        if released_space:
            self._space_pressed = False

        # Check if combo was active and now broken
        if self._combo_active and (released_ctrl or released_space):
            self._combo_active = False
            logger.debug("Hotkey released: %s", self._hotkey)
            if self._on_release:
                self._on_release()

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
        self._on_press = on_press
        self._on_release = on_release

        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()
        logger.info("X11 hotkey listener started")

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            logger.info("X11 hotkey listener stopped")
