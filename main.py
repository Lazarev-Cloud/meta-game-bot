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
import sqlite3
from config import TOKEN, ADMIN_IDS
from db.schema import setup_database

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
        # Perform startup checks
        if not perform_startup_checks():
            logger.warning("Some startup checks failed, but continuing anyway")

        # Create the Application
        logger.info("Initializing Telegram bot...")
        application = Application.builder().token(TOKEN).build()

        # Import handlers here to avoid circular imports
        from bot.commands import register_commands
        from bot.callbacks import register_callbacks

        # Register command handlers
        logger.info("Registering command handlers...")
        register_commands(application)

        # Register callback handlers
        logger.info("Registering callback handlers...")
        register_callbacks(application)

        # Set up scheduled jobs
        logger.info("Setting up scheduled jobs...")
        from game.actions import schedule_jobs
        application.job_queue.run_once(lambda ctx: schedule_jobs(application), 1)

        # Add error handler
        logger.info("Setting up error handler...")
        application.add_error_handler(error_handler)

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


def validate_and_fix_database_schema():
    """Check database schema and fix any issues."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check for all required tables
        required_tables = [
            'players', 'resources', 'districts', 'district_control',
            'politicians', 'actions', 'news', 'politician_relationships',
            'coordinated_actions', 'coordinated_action_participants'
        ]

        missing_tables = []
        for table in required_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                missing_tables.append(table)

        if missing_tables:
            logger.warning(f"Missing tables found: {missing_tables}")

            # If there are missing tables, run the full setup
            from db.schema import setup_database
            setup_database()
            logger.info("Database schema has been fixed")

        # Check for newer tables that might be missing
        newer_tables = ['player_presence', 'district_defense']

        for table in newer_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                # Create the missing tables
                if table == 'player_presence':
                    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS player_presence (
                        player_id INTEGER,
                        district_id TEXT,
                        timestamp TEXT,
                        is_present BOOLEAN DEFAULT 1,
                        PRIMARY KEY (player_id, district_id),
                        FOREIGN KEY (player_id) REFERENCES players (player_id),
                        FOREIGN KEY (district_id) REFERENCES districts (district_id)
                    )
                    ''')
                elif table == 'district_defense':
                    cursor.execute('''
                    CREATE TABLE IF NOT EXISTS district_defense (
                        district_id TEXT,
                        player_id INTEGER,
                        defense_bonus INTEGER DEFAULT 0,
                        expires_at TEXT,
                        PRIMARY KEY (district_id, player_id),
                        FOREIGN KEY (district_id) REFERENCES districts (district_id),
                        FOREIGN KEY (player_id) REFERENCES players (player_id)
                    )
                    ''')
                logger.info(f"Created missing table: {table}")

        # Check and fix columns in tables
        # Example: Check if the 'coordinated_actions' table has the 'expires_at' column
        try:
            cursor.execute("SELECT expires_at FROM coordinated_actions LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            cursor.execute("ALTER TABLE coordinated_actions ADD COLUMN expires_at TEXT")
            logger.info("Added missing 'expires_at' column to coordinated_actions table")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error validating database schema: {e}")
        return False


def perform_startup_checks():
    """Perform various checks and fixes at application startup."""
    logger.info("Performing startup checks...")

    # Validate and fix database schema
    if not validate_and_fix_database_schema():
        logger.error("Failed to validate/fix database schema")
        return False

    # Check for expired coordinated actions and close them
    try:
        from db.queries import cleanup_expired_actions
        cleaned_count = cleanup_expired_actions()
        logger.info(f"Cleaned up {cleaned_count} expired coordinated actions")
    except Exception as e:
        logger.error(f"Error cleaning up expired actions: {e}")

    # Check if all player resources are initialized
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Find players without resources
        cursor.execute('''
        SELECT p.player_id FROM players p
        LEFT JOIN resources r ON p.player_id = r.player_id
        WHERE r.player_id IS NULL
        ''')

        players_without_resources = cursor.fetchall()

        for (player_id,) in players_without_resources:
            # Initialize resources for this player
            cursor.execute(
                "INSERT INTO resources (player_id, influence, resources, information, force) VALUES (?, 5, 5, 5, 5)",
                (player_id,)
            )
            logger.info(f"Initialized resources for player {player_id}")

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error checking player resources: {e}")

    logger.info("Startup checks completed")
    return True


if __name__ == "__main__":
    main()