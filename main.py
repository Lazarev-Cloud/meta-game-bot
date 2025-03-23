#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Meta Game - Telegram Bot
A political strategy game set in Novi-Sad, Yugoslavia in 1999.
"""

import os
import asyncio
import traceback

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
)

from bot import get_back_keyboard
from bot.callbacks import register_callbacks
# Import bot components
from bot.commands import register_commands
from bot.middleware import setup_middleware
from bot.states import conversation_handlers
# Import database client
from db.supabase_client import init_supabase
from utils.config import load_config
from utils.i18n import setup_i18n, _, get_user_language, load_translations_from_file, load_translations_from_db
# Import utility functions
from utils.logger import setup_logger, configure_telegram_logger, configure_supabase_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(name="meta_game", level="INFO", log_file="logs/meta_game.log")
configure_telegram_logger()
configure_supabase_logger()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the dispatcher with better user feedback."""
    telegram_id = None
    language = "en_US"

    # Try to get the user's language for error messages
    if update and update.effective_user:
        telegram_id = str(update.effective_user.id)
        try:
            language = await get_user_language(telegram_id)
        except:
            pass

    # Log the error
    logger.error(f"Exception while handling an update: {context.error}")

    # Get detailed error info for logging
    error_details = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.error(f"Detailed error: {error_details}")

    # Different error types need different responses
    if isinstance(context.error, Exception):
        error_type = type(context.error).__name__
        error_message = str(context.error)
    else:
        error_type = "Unknown Error"
        error_message = "An unexpected error occurred"

    # Create user-friendly message based on error type
    user_message = _("An error occurred while processing your request.", language)

    if "resource" in error_message.lower():
        user_message = _("You don't have enough resources for this action.", language)
    elif "permission" in error_message.lower():
        user_message = _("You don't have permission to perform this action.", language)
    elif "not found" in error_message.lower():
        user_message = _("The requested item was not found.", language)
    elif "deadline" in error_message.lower():
        user_message = _("The submission deadline for this cycle has passed.", language)

    # Send the error message to the user
    try:
        if update.callback_query:
            await update.callback_query.answer(
                user_message[:200]  # Callback answers have a character limit
            )
            # Try to edit the message if possible
            try:
                await update.callback_query.edit_message_text(
                    user_message,
                    reply_markup=get_back_keyboard(language)
                )
            except:
                pass
        elif update.message:
            await update.message.reply_text(
                user_message
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")

    # Return True to mark the error as handled
    return True


async def init_translations():
    """Initialize translations asynchronously."""
    try:
        # Load translations in the correct order
        await load_translations_from_file()
        await load_translations_from_db()
        logger.info("Translations initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing translations: {e}")


async def main():
    """Initialize and start the bot."""
    # Load bot token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No bot token found. Please set TELEGRAM_BOT_TOKEN in .env file.")
        return

    # Load admin IDs
    admin_ids_str = os.getenv("TELEGRAM_ADMIN_IDS", "")
    admin_ids = [int(id_str) for id_str in admin_ids_str.split(",") if id_str]

    # Load configuration
    config = load_config()

    # Initialize Supabase client
    init_supabase()

    # Set up internationalization (init default translations)
    setup_i18n()

    # Asynchronously load translations
    await init_translations()

    # Initialize the Application with better error handling
    application = Application.builder().token(token).build()

    # Register command handlers first
    register_commands(application)

    # Register callback query handlers
    register_callbacks(application)

    # Add conversation handlers
    for handler in conversation_handlers:
        application.add_handler(handler)

    # Set up middleware (AFTER all other handlers)
    setup_middleware(application, admin_ids)

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting Meta Game bot...")
    # Change this line to start and close the application properly
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    # Run until stopped
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

if __name__ == "__main__":
    # Properly run the main coroutine with asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
