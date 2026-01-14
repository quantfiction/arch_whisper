"""Entry point for arch-whisper."""

from __future__ import annotations

import logging
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
        logger.info(
            "Feature %s: %s", feature, "available" if available else "unavailable"
        )

    # Create and run application
    app = App(config)

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted")
        app.stop()
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        notify("Error", f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
