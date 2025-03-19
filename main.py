#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Belgrade Game Telegram Bot
Main entry point for the bot application
"""

import logging
import sys
import sqlite3
from telegram import Update
from telegram.ext import Application
from languages import get_text, get_player_language, init_language_support
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

    try:
        # Set up the database
        logger.info("Setting up database...")
        setup_database()

        # Initialize language support
        logger.info("Initializing language support...")
        init_language_support()

        # Create the Application
        logger.info("Initializing Telegram bot...")
        application = Application.builder().token(TOKEN).build()

        # Register command handlers
        logger.info("Registering command handlers...")
        register_commands(application)

        # Register callback handlers
        logger.info("Registering callback handlers...")
        register_callbacks(application)

        # Set up scheduled jobs - no await needed
        logger.info("Setting up scheduled jobs...")
        application.job_queue.run_once(schedule_jobs, 1)

        # Add error handler
        logger.info("Setting up error handler...")
        application.add_error_handler(error_handler)

        # Perform validation checks
        logger.info("Performing validation checks...")
        validate_system()

        # Start the Bot
        logger.info("Bot starting up - Press Ctrl+C to stop")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Failed to initialize bot: {e}")
        import traceback
        tb_list = traceback.format_exception(None, e, e.__traceback__)
        tb_string = ''.join(tb_list)
        logger.critical(f"Initialization error traceback:\n{tb_string}")
        sys.exit(1)


def validate_system():
    """Perform validation checks to ensure the system is properly configured."""
    try:
        # Check database connection
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check essential tables
        essential_tables = ['players', 'resources', 'districts', 'politicians', 'actions']
        for table in essential_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                logger.error(f"Essential table {table} is missing from the database!")

        # Check if districts and politicians are populated
        cursor.execute("SELECT COUNT(*) FROM districts")
        district_count = cursor.fetchone()[0]
        if district_count == 0:
            logger.warning("Districts table is empty. Initial data may be missing.")

        cursor.execute("SELECT COUNT(*) FROM politicians")
        politician_count = cursor.fetchone()[0]
        if politician_count == 0:
            logger.warning("Politicians table is empty. Initial data may be missing.")

        conn.close()

        # Check if all required translations are present
        from languages import TRANSLATIONS
        essential_keys = ['welcome', 'help_title', 'status_title', 'action_influence', 'resources_title']
        for lang in TRANSLATIONS:
            for key in essential_keys:
                if key not in TRANSLATIONS[lang]:
                    logger.warning(f"Essential translation key '{key}' is missing for language '{lang}'")

        # Check if admin IDs are configured
        if not ADMIN_IDS:
            logger.warning("No admin IDs configured - admin commands will not be available")

        logger.info("System validation complete")
    except Exception as e:
        logger.error(f"System validation error: {e}")


async def error_handler(update, context):
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
            lang = "en"  # Default to English
            if hasattr(update, 'effective_user') and update.effective_user:
                try:
                    lang = get_player_language(update.effective_user.id)
                except Exception:
                    pass  # Fall back to default language

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_text("error_message", lang,
                              default="Sorry, something went wrong. The error has been reported.")
            )
        except Exception as e:
            logger.error(f"Error in error handler while sending message: {e}")

    # Notify admins about critical errors
    try:
        for admin_id in ADMIN_IDS:
            if update:
                error_message = f"⚠️ Bot error:\n{str(context.error)}\n\nUpdate: {update.to_dict() if update else 'No update'}"
                # Truncate if too long
                if len(error_message) > 4000:
                    error_message = error_message[:3997] + "..."
                await context.bot.send_message(chat_id=admin_id, text=error_message)
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")


if __name__ == "__main__":
    main()