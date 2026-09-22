"""Application entrypoint for ArUco Chess Tracker."""

import argparse
import logging
import sys

from src.app import App
from src.config import APP_NAME, __version__

logger = logging.getLogger("main")


def main() -> None:
    """Parse command line options and launch the application."""
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{__version__}")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Force synthetic chessboard camera feed (useful for testing without webcam).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override TCP API port (default: 5555).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging.",
    )
    args = parser.parse_args()

    # Logging configuration
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Starting %s v%s...", APP_NAME, __version__)

    app = App()

    # Apply CLI overrides if specified
    if args.synthetic:
        app.camera.synthetic_mode = True
        logger.info("Forced synthetic camera mode via CLI flag.")

    if args.port:
        app.tcp_manager.port = args.port
        logger.info("Overriding TCP server port to %d via CLI flag.", args.port)

    try:
        app.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
        app.shutdown()


if __name__ == "__main__":
    main()
