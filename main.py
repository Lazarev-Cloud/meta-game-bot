#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Belgrade Game Telegram Bot
Main entry point for the bot application
"""

import logging
import sys
from telegram import Update
from telegram.ext import Application
from languages import get_text, get_player_language
from languages_update import init_language_support

from bot.callbacks import register_callbacks
from bot.commands import register_commands
from config import TOKEN
from db.schema import setup_database
from game.actions import schedule_jobs

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Display startup message
    logger.info("Starting Belgrade Game Bot...")

    init_language_support()

    # Set up the database
    logger.info("Setting up database...")
    setup_database()

    # Create the Application
    logger.info("Initializing Telegram bot...")
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    logger.info("Registering command handlers...")
    register_commands(application)

    # Register callback handlers
    logger.info("Registering callback handlers...")
    register_callbacks(application)

    # Set up scheduled jobs
    logger.info("Setting up scheduled jobs...")
    application.job_queue.run_once(schedule_jobs, 1)

    # Add error handler
    logger.info("Setting up error handler...")
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Bot starting up - Press Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")

    # Send message to developer
    if update and update.effective_chat:
        try:
            # Get user's language
            user_id = update.effective_chat.id
            lang = "en"  # Default to English
            if hasattr(update, 'effective_user') and update.effective_user:
                lang = get_player_language(update.effective_user.id)

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_text("error_message", lang,
                              default="Sorry, something went wrong. The error has been reported.")
            )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")


if __name__ == "__main__":
    main()