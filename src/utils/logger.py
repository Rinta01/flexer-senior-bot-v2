"""Logging configuration for the application."""

import logging

# import logging.config
from typing import Optional

# from pythonjsonlogger import jsonlogger

from src.config import settings


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """
    Configure logging with both console and JSON output.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))

        # Console handler with detailed format
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "[%(asctime)s] %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Optional: JSON logging for structured logs
        # json_handler = logging.StreamHandler()
        # json_handler.setFormatter(jsonlogger.JsonFormatter())
        # logger.addHandler(json_handler)

    return logger


# Create root logger
logger = setup_logging("flexer_senior")
