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

    # Start the Bot
    logger.info("Bot starting up - Press Ctrl+C to stop")
    application.run_polling(allowed_updates=Update.ALL_TYPES)



def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")

    # Send message to developer
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, something went wrong. The error has been reported."
        )




if __name__ == "__main__":
    main()
    # Add to your application
    # application.add_error_handler(error_handler)