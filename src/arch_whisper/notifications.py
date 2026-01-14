"""Desktop notification wrapper for arch_whisper."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_initialized = False


def init_notifications(app_name: str) -> bool:
    """Initialize the notification system.

    Returns:
        True if initialization succeeded, False otherwise.
    """
    global _initialized
    try:
        import gi

        gi.require_version("Notify", "0.7")
        from gi.repository import Notify

        Notify.init(app_name)
        _initialized = True
        return True
    except Exception as e:
        logger.warning("Failed to initialize notifications: %s", e)
        return False


def notify(summary: str, body: str = "", urgency: str = "normal") -> None:
    """Show a desktop notification.

    Thread-safe: schedules the GI call onto the GTK main loop.

    Args:
        summary: Notification title
        body: Notification body text
        urgency: One of "low", "normal", "critical"
    """
    if not _initialized:
        logger.debug("Notifications not initialized, skipping: %s", summary)
        return

    try:
        from gi.repository import GLib, Notify

        def _do_notify() -> bool:
            n = Notify.Notification.new(summary, body, "dialog-information")

            urgency_map = {
                "low": Notify.Urgency.LOW,
                "normal": Notify.Urgency.NORMAL,
                "critical": Notify.Urgency.CRITICAL,
            }
            n.set_urgency(urgency_map.get(urgency, Notify.Urgency.NORMAL))
            n.show()
            return False

        GLib.idle_add(_do_notify)

    except Exception as e:
        logger.warning("Failed to show notification: %s", e)
