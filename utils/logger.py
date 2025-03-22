#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging setup for the Meta Game bot.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import Optional

def setup_logger(
    name: Optional[str] = None,
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    max_bytes: int = 10485760,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """Configure the logger with file and console handlers."""
    # Get the name of the calling module if not provided
    if name is None:
        name = "meta_game"
    
    # Get the logger for the module
    logger = logging.getLogger(name)
    
    # Only set up handlers if they haven't been set up already
    if not logger.handlers:
        # Convert level string to logging level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        
        # Default format if not provided
        if log_format is None:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        formatter = logging.Formatter(log_format)
        
        # Set up logging to file if a file is specified
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Set up console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a specific logger by name."""
    return logging.getLogger(name)

def configure_telegram_logger() -> None:
    """Configure the python-telegram-bot library's logger."""
    # Configure python-telegram-bot's logger
    telegram_logger = logging.getLogger("telegram")
    telegram_logger.setLevel(logging.WARNING)  # Only log warnings and errors
    
    # Set up handler if not already configured
    if not telegram_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        telegram_logger.addHandler(console_handler)

def configure_supabase_logger() -> None:
    """Configure the supabase client's logger."""
    # Configure supabase logger
    supabase_logger = logging.getLogger("supabase")
    supabase_logger.setLevel(logging.WARNING)  # Only log warnings and errors
    
    # Set up handler if not already configured
    if not supabase_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        supabase_logger.addHandler(console_handler)