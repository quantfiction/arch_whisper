"""Entry point for arch-whisper."""

from __future__ import annotations

import logging
import signal
import sys

from arch_whisper.app import App
from arch_whisper.config import load_config
from arch_whisper.notifications import init_notifications, notify
from arch_whisper.preflight import check_dependencies, check_optional_dependencies


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Main entry point for arch-whisper."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting arch-whisper")

    # Load configuration
    config = load_config()

    # Initialize notifications early for preflight messages
    init_notifications("arch-whisper")

    # Run preflight checks
    missing = check_dependencies()
    if missing:
        msg = "Missing: " + ", ".join(missing)
        logger.warning(msg)
        notify("Missing dependencies", msg)

    # Log optional feature status
    optional = check_optional_dependencies()
    for feature, available in optional.items():
        status = "available" if available else "unavailable"
        logger.info("Feature %s: %s", feature, status)

    # Create application
    app = App(config)

    # Setup signal handlers for graceful shutdown
    def on_shutdown(signum: int, frame) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down", sig_name)
        app.stop()

    signal.signal(signal.SIGINT, on_shutdown)
    signal.signal(signal.SIGTERM, on_shutdown)

    # Run application
    try:
        app.run()
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        notify("Error", f"Fatal error: {e}")
        sys.exit(1)

    logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
