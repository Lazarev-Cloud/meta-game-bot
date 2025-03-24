#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Meta Game - Telegram Bot
A political strategy game set in Novi-Sad, Yugoslavia in 1999.
"""

import asyncio
import os
import traceback
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
)

# Import core components
from bot.handlers import register_all_handlers
from bot.middleware import setup_middleware
from db.supabase_client import init_supabase, check_schema_exists
from utils.config import load_config
from utils.i18n import load_translations, get_user_language
from utils.logger import setup_logger, configure_telegram_logger, configure_supabase_logger
from utils.error_handling import handle_error
from utils.context_manager import context_manager

# Load environment variables
load_dotenv()

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

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
        except Exception as e:
            logger.error(f"Error getting user language: {e}")

    # Log the error
    logger.error(f"Exception while handling an update: {context.error}")

    # Get detailed error info for logging
    error_details = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.error(f"Detailed error trace: {error_details}")

    # Use the centralized error handler
    await handle_error(
        update,
        language,
        context.error,
        "global_error_handler"
    )

    # Return True to mark the error as handled
    return True


async def init_translations():
    """Initialize translations asynchronously."""
    try:
        # Try up to 3 times with exponential backoff
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                # Load translations using the unified loading function
                await load_translations()
                logger.info("Translations initialized successfully")
                return
            except Exception as e:
                if attempt < max_attempts:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} to load translations failed: {e}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    raise
    except Exception as e:
        logger.error(f"All attempts to initialize translations failed: {e}")
        logger.info("Continuing with default translations only")


async def init_database():
    """Initialize the database if it hasn't been set up yet."""
    try:
        # Initialize Supabase client
        client = init_supabase()

        # Check if game schema exists
        schema_exists = False
        try:
            schema_exists = await check_schema_exists()
        except Exception as check_error:
            logger.error(f"Error checking schema existence: {check_error}")
            # Try a more direct approach
            try:
                from db.supabase_client import execute_sql
                check_result = await execute_sql(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'game';")
                schema_exists = check_result and len(check_result) > 0
                logger.info(f"Alternative schema check result: {schema_exists}")
            except Exception as direct_check_error:
                logger.error(f"Direct schema check also failed: {direct_check_error}")
                # Assume schema exists to avoid potential data loss
                schema_exists = True
                logger.warning("Assuming schema exists due to check failures")

        if not schema_exists:
            logger.info("Database schema 'game' doesn't exist. Running initialization...")

            try:
                # Execute basic SQL for schema and critical tables
                from db.supabase_client import execute_sql

                # Create the game schema
                await execute_sql("CREATE SCHEMA IF NOT EXISTS game;")

                # Create essential tables with proper schema reference
                await execute_sql("""
                CREATE TABLE IF NOT EXISTS game.players (
                    player_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    telegram_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    ideology_score INTEGER NOT NULL DEFAULT 0,
                    remaining_actions INTEGER NOT NULL DEFAULT 1,
                    remaining_quick_actions INTEGER NOT NULL DEFAULT 2,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    language TEXT DEFAULT 'en_US',
                    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );""")

                await execute_sql("""
                CREATE TABLE IF NOT EXISTS game.resources (
                    resource_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    player_id UUID NOT NULL,
                    influence_amount INTEGER NOT NULL DEFAULT 0,
                    money_amount INTEGER NOT NULL DEFAULT 0,
                    information_amount INTEGER NOT NULL DEFAULT 0,
                    force_amount INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );""")

                logger.info("Created minimal database schema and tables")
            except Exception as init_error:
                logger.error(f"Error during database initialization: {init_error}")
                logger.warning("Continuing without database initialization")
        else:
            logger.info("Database schema 'game' already exists")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.warning("Bot will continue but database functionality may be limited")


async def cleanup_task():
    """Periodically clean up expired user contexts."""
    while True:
        try:
            cleaned = context_manager.cleanup_expired()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired user contexts")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
        await asyncio.sleep(300)  # Run every 5 minutes


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

    # Initialize the Application with better error handling
    application = Application.builder().token(token).build()

    # Register error handler first so it can catch initialization errors
    application.add_error_handler(error_handler)

    # Start initialization tasks
    logger.info("Initializing Supabase client and database...")
    try:
        # Initialize Supabase client and database
        await init_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Bot will continue but database functionality may be limited")

    # Asynchronously load translations
    logger.info("Loading translations...")
    await init_translations()

    # Set up middleware FIRST
    logger.info("Setting up middleware...")
    setup_middleware(application, admin_ids)

    # Register all handlers using the unified handler registration system
    logger.info("Registering handlers...")
    try:
        register_all_handlers(application)
    except Exception as handler_error:
        logger.error(f"Error registering handlers: {handler_error}")
        logger.critical("Cannot continue without handlers")
        return

    # Start the bot
    logger.info("Starting Meta Game bot...")

    # Set up graceful shutdown
    import signal

    # Define shutdown handler
    async def shutdown(signal_number, frame):
        """Shut down the bot gracefully on receiving a signal."""
        logger.info(f"Received signal {signal_number}, shutting down...")

        # Make sure updater is stopped first
        if application.updater and application.updater.running:
            try:
                await application.updater.stop()
            except Exception as e:
                logger.error(f"Error stopping updater: {e}")

        # Then stop the application
        try:
            if application.running:
                await application.stop()
        except Exception as e:
            logger.error(f"Error stopping application: {e}")

        # Finally, shutdown the application
        try:
            await application.shutdown()
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")

    # Register signal handlers with proper error handling
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, lambda s, f: asyncio.create_task(shutdown(s, f)))
            except Exception as signal_error:
                logger.error(f"Error setting up signal handler for {sig}: {signal_error}")
    except Exception as e:
        logger.error(f"Error setting up signal handlers: {e}")

    # Start the bot with error handling
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot is running!")

        # Start cleanup task as a background task
        cleanup_job = asyncio.create_task(cleanup_task())

        # Run the bot until stopped
        try:
            # Use asyncio.Event() to keep the task running indefinitely
            stop_event = asyncio.Event()
            await stop_event.wait()
        except asyncio.CancelledError:
            # Bot is being shut down
            logger.info("Main task cancelled, shutting down...")
        finally:
            # Clean up
            if 'cleanup_job' in locals() and not cleanup_job.done():
                cleanup_job.cancel()

            # Ensure the bot is properly shut down
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

        logger.info("Bot stopped")

    except Exception as startup_error:
        logger.critical(f"Failed to start bot: {startup_error}")
        # Try to clean up if startup failed
        try:
            if 'application' in locals():
                if hasattr(application, 'updater') and application.updater:
                    await application.updater.stop()
                if hasattr(application, 'stop'):
                    await application.stop()
                if hasattr(application, 'shutdown'):
                    await application.shutdown()
        except Exception as cleanup_error:
            logger.error(f"Error during emergency cleanup: {cleanup_error}")


if __name__ == "__main__":
    # Properly run the main coroutine with asyncio
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
    except Exception as e:
        logger.critical(f"Critical error in main: {e}")
        traceback.print_exc()
        sys.exit(1)