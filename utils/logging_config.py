"""
Logging configuration for Google Chat Utils.

Provides structured logging across all modules and CLI commands.
Supports console output with configurable log level and optional file output.
"""

import logging
import sys
from typing import Optional, Union

# Base logger name for the project
PROJECT_LOGGER_NAME = "google_chat_utils"

# Default format string
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[str] = None,
    verbose: bool = False,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Configures and initializes logging for Google Chat Utils.

    Args:
        level: Log level (int or string name like "DEBUG", "INFO", "WARNING", "ERROR").
        log_file: Optional path to write logs to a file.
        verbose: If True, overrides level to DEBUG.
        format_string: Custom log format string.

    Returns:
        Configured root logger for the project.
    """
    if verbose:
        level = logging.DEBUG
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    fmt = format_string or DEFAULT_LOG_FORMAT
    formatter = logging.Formatter(fmt, datefmt=DEFAULT_DATE_FORMAT)

    logger = logging.getLogger(PROJECT_LOGGER_NAME)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if setup_logging is called multiple times
    logger.handlers.clear()

    # Stream (console) handler
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a child logger under the project logger namespace.

    Args:
        name: Name of module or component (e.g. __name__ or "parser").

    Returns:
        logging.Logger instance.
    """
    if not name:
        return logging.getLogger(PROJECT_LOGGER_NAME)
    if name.startswith(PROJECT_LOGGER_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{PROJECT_LOGGER_NAME}.{name}")

