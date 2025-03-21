#!/usr/bin/env python3
# test_bot.py - Test the Belgrade Game Bot functionality

import os
import logging
import sys
from dotenv import load_dotenv
from telegram.ext import Application

from bot.commands import register_commands
from bot.callbacks import register_callbacks
from main import setup_logging, validate_and_fix_database_schema

# Enable more detailed logging for development
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Run the bot for testing."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Setup logger
    setup_logging()
    
    # Get bot token from environment variable
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No bot token found. Set the TELEGRAM_BOT_TOKEN environment variable.")
        sys.exit(1)
    
    # Validate database schema
    logger.info("Validating database schema...")
    validate_and_fix_database_schema()
    
    # Create application
    logger.info("Starting bot...")
    application = Application.builder().token(token).build()
    
    # Register commands and callbacks
    register_commands(application)
    register_callbacks(application)
    
    # Start the bot
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()