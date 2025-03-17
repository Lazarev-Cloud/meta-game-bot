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
from config import TOKEN, ADMIN_IDS
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

    # Initialize language support
    init_language_support()

    # Initialize admin language support
    from languages_update import init_admin_language_support
    init_admin_language_support()
    logger.info("Admin language support initialized")

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

    # Extract traceback info
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    logger.error(f"Exception traceback:\n{tb_string}")

    # Send message to user (if possible)
    if update and update.effective_chat:
        try:
            # Get user's language
            user_id = update.effective_chat.id
            lang = "en"  # Default to English
            if hasattr(update, 'effective_user') and update.effective_user:
                try:
                    lang = get_player_language(update.effective_user.id)
                except Exception:
                    pass  # Fall back to default language

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_text("error_message", lang,
                              default="Sorry, something went wrong. The error has been reported.")
            )
        except Exception as e:
            logger.error(f"Error in error handler while sending message: {e}")

    # You might want to add code to notify admins about critical errors
    # For example, sending a message to specified admin chat IDs
    try:
        for admin_id in ADMIN_IDS:
            if update:
                error_message = f"⚠️ Bot error:\n{str(context.error)}\n\nUpdate: {update.to_dict() if update else 'No update'}"
                # Truncate if too long
                if len(error_message) > 4000:
                    error_message = error_message[:3997] + "..."
                context.bot.send_message(chat_id=admin_id, text=error_message)
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")



if __name__ == "__main__":
    main()
