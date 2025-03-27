# Updated main.py with improved initialization and error handling

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

# Load environment variables first
load_dotenv()

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Setup logging before anything else
from utils.logger import setup_logger, configure_telegram_logger, configure_supabase_logger

logger = setup_logger(name="meta_game", level="INFO", log_file="logs/meta_log")
configure_telegram_logger()
configure_supabase_logger()

# Now import database components
from db.supabase_client import init_supabase, get_supabase
from db import initialize_db

# Import core components
from bot.handlers import register_all_handlers
from bot.middleware import setup_middleware
from utils.config import load_config
from utils.i18n import load_translations_safely, init_i18n
from utils.error_handling import handle_error
from utils.context_manager import context_manager


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the dispatcher with better user feedback."""
    telegram_id = None
    language = "en_US"

    # Try to get the user's language for error messages
    if update and update.effective_user:
        telegram_id = str(update.effective_user.id)
        try:
            from utils.i18n import get_user_language
            language = await get_user_language(telegram_id)
        except Exception as e:
            logger.error(f"Error getting user language: {e}")

    # Log the error
    logger.error(f"Exception while handling an update: {context.error}")

    # Get detailed error info for logging
    error_details = ''.join(traceback.format_exception(None, context.error, context.error.__traceback__))
    logger.debug(f"Detailed error trace: {error_details}")

    # Use the centralized error handler
    await handle_error(
        update,
        language,
        context.error,
        "global_error_handler"
    )

    # Return True to mark the error as handled
    return True


async def init_database_with_retry(max_attempts=3):
    """Initialize database with robust fallback."""
    logger.info("Initializing database...")

    for attempt in range(1, max_attempts + 1):
        try:
            # Try to initialize Supabase client
            client = init_supabase()
            logger.info("Supabase client initialized")

            # Check if tables exist by trying to access them
            try:
                response = client.table("players").select("count").limit(1).execute()
                logger.info("Database tables verified")
                return True
            except Exception as e:
                logger.warning(f"Tables access check failed: {e}")
                logger.info("Tables don't exist or are inaccessible. Will use memory fallbacks.")
                return True

        except Exception as e:
            logger.error(f"Database initialization attempt {attempt}/{max_attempts} failed: {e}")

            if attempt < max_attempts:
                delay = 2 ** (attempt - 1)
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.warning("All database initialization attempts failed. Using in-memory fallbacks.")
                return False


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
    admin_ids = [int(id_str) for id_str in admin_ids_str.split(",") if id_str.strip()]

    # Load configuration
    config = load_config()
    # Remove proxy setting from config if present to avoid errors
    if 'proxy' in config.get('bot', {}):
        del config['bot']['proxy']
        logger.info("Removed proxy configuration as it's not supported with this version")

    # Initialize the Application with better error handling
    application = Application.builder().token(token).build()

    # Register error handler first so it can catch initialization errors
    application.add_error_handler(error_handler)

    # Start initialization tasks
    logger.info("Initializing Supabase client and database...")
    db_init_success = await init_database_with_retry()
    if not db_init_success:
        logger.warning("Bot will continue but database functionality may be limited")

    # Initialize db module and get functions
    db_functions = initialize_db()

    # Initialize i18n with correct dependencies
    init_i18n(player_exists_func=db_functions['player_exists'], get_supabase_func=get_supabase)

    # Asynchronously load translations
    logger.info("Loading translations...")
    await load_translations_safely()

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