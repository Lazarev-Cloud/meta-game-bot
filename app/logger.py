"""
Logging configuration module.

Initializes global logging settings based on the current environment configuration.
"""

import logging
from app.config import settings


def configure_logging():
    """
    Configure the root logger using the log level specified in the settings.

    Sets a standardized format for log messages, including timestamp, logger name,
    log level, and the actual message.
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
