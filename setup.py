#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for Belgrade Game Bot
Creates necessary directory structure and initializes empty __init__.py files
"""

import os
import logging

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def ensure_directory(path):
    """Ensure a directory exists and create it if it doesn't."""
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Created directory: {path}")
    else:
        logger.info(f"Directory already exists: {path}")


def create_init_file(directory):
    """Create an empty __init__.py file in the specified directory if it doesn't exist."""
    init_file = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            pass  # Create empty file
        logger.info(f"Created {init_file}")
    else:
        logger.info(f"File already exists: {init_file}")


def setup():
    """Set up the project directory structure."""
    logger.info("Setting up project directory structure...")

    # Define main package directories
    directories = [
        "bot",
        "db",
        "game"
    ]

    # Create directories and __init__.py files
    for directory in directories:
        ensure_directory(directory)
        create_init_file(directory)

    logger.info("Project directory structure setup complete")


if __name__ == "__main__":
    setup()