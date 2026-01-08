"""Logging configuration for invoice extraction."""

import logging
import sys
from pathlib import Path

from config import Config


def setup_logging(log_file: str | None = None, log_level: str | None = None) -> None:
    """
    Configure application logging with console and file handlers.

    Args:
        log_file: Path to log file (defaults to Config.LOG_FILE)
        log_level: Logging level (defaults to Config.LOG_LEVEL)
    """
    log_file = log_file or Config.LOG_FILE
    log_level = log_level or Config.LOG_LEVEL

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler with detailed formatting
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    logger.info("Logging initialized")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
