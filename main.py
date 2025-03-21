#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Belgrade Game Telegram Bot
Main entry point for the bot application
"""

import logging
import sys
import traceback
import sqlite3
import os
import argparse
import time
from contextlib import contextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from languages import get_text, get_player_language
from languages_update import init_language_support
from config import TOKEN, ADMIN_IDS
from db.schema import setup_database
from error_handlers import error_handler
from game_jobs import schedule_jobs

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

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run the Belgrade Game Bot")
parser.add_argument("--instance-id", type=str, help="Unique instance ID to avoid conflicts")
args, unknown = parser.parse_known_args()

# Set or get instance ID
INSTANCE_ID = args.instance_id or os.environ.get('BOT_INSTANCE_ID') or str(int(time.time()))
logger.info(f"Running with instance ID: {INSTANCE_ID}")

@contextmanager
def get_db_connection():
    """
    Context manager for database connections to ensure proper closing
    even in case of exceptions.
    """
    conn = None
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def main():
    """Start the bot."""
    # Log startup message
    logging.info("Starting Belgrade Game Bot...")
    logging.info(f"Bot instance ID: {INSTANCE_ID}")
    
    # Check if this is the first run or a restart
    is_restart = os.environ.get('BOT_RESTART_COUNT', '0') != '0'
    if is_restart:
        logging.info(f"This is restart #{os.environ.get('BOT_RESTART_COUNT')}") 

    # Attempt to terminate any competing bot instances
    try:
        from error_handlers import find_and_kill_bot_processes
        killed_count = find_and_kill_bot_processes(except_instance_id=INSTANCE_ID)
        if killed_count > 0:
            logging.info(f"Terminated {killed_count} competing bot instances")
            # Wait to ensure clean termination
            time.sleep(3) 
    except Exception as e:
        logging.error(f"Error killing competing processes: {e}")
    
    # Reset any webhook connections from previous runs
    try:
        import requests
        logging.info("Resetting Telegram webhook...")
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/deleteWebhook",
            params={"drop_pending_updates": True}
        )
        if response.status_code == 200:
            logging.info("Webhook reset successful")
        else:
            logging.warning(f"Webhook reset returned status code {response.status_code}")
        # Give the Telegram API a moment
        time.sleep(2)
    except Exception as e:
        logging.error(f"Error resetting webhook: {e}")
    
    # First initialize language system
    try:
        from languages import initialize
        initialize()
        logging.info("Language system initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize language system: {e}")
        traceback.print_exc()
    
    # Check startup conditions
    if not perform_startup_checks():
        logging.warning("There were issues during startup checks.")
    
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()
    
    # Register command and callback handlers
    try:
        from bot.commands import register_commands
        from bot.callbacks import register_callbacks
        
        register_commands(application)
        register_callbacks(application)
        logging.info("Command and callback handlers registered successfully")
    except Exception as e:
        logging.error(f"Failed to register handlers: {e}")
        traceback.print_exc()
    
    # Add the error handler
    application.add_error_handler(error_handler)
    
    # Set up job queue for scheduled tasks and register all game jobs
    schedule_jobs(application.job_queue)
    
    # Log instance information
    logger.info(f"Bot instance {INSTANCE_ID} starting polling")
    
    # Run the bot until the user presses Ctrl-C or an error occurs
    # Use instance-specific parameters to avoid conflicts
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "chat_member"],
            pool_timeout=30.0,
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0
        )
    except Exception as e:
        if "terminated by other getUpdates request" in str(e).lower() or "conflict" in str(e).lower():
            logging.error(f"Telegram conflict detected: {e}")
            # Increment restart counter
            os.environ['BOT_RESTART_COUNT'] = str(int(os.environ.get('BOT_RESTART_COUNT', '0')) + 1)
            # Clean up connections
            from db.utils import close_all_connections
            close_all_connections()
            # Exit with error code to enable restart
            sys.exit(1)
        else:
            logging.error(f"Error in main application: {e}")
            raise
    
    logging.info(f"Bot instance {INSTANCE_ID} stopped gracefully.")
    
    # Clean up before exit
    from db.utils import close_all_connections
    close_all_connections()
    logging.info("Database connections closed.")


def validate_system():
    """Perform validation checks to ensure the system is properly configured."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Check essential tables
            essential_tables = ['players', 'resources', 'districts', 'politicians', 'actions']
            for table in essential_tables:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
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

        # Check if all required translations are present
        from languages import TRANSLATIONS
        essential_keys = ['welcome', 'help_title', 'status_title', 'resources_title']
        for lang in TRANSLATIONS:
            for key in essential_keys:
                if key not in TRANSLATIONS[lang]:
                    logger.warning(f"Essential translation key '{key}' is missing for language '{lang}'")

        # Check if admin IDs are configured
        if not ADMIN_IDS:
            logger.warning("No admin IDs configured - admin commands will not be available")

        logger.info("System validation complete")
        return True
    except Exception as e:
        logger.error(f"System validation error: {e}")
        return False


def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    if context.error:
        logger.error(f"Exception while handling an update: {context.error}")
        
        # Extract traceback info
        tb_string = ''.join(traceback.format_exception(
            type(context.error), context.error, context.error.__traceback__
        ))
        logger.error(f"Exception traceback:\n{tb_string}")
    else:
        logger.error("Unknown error in handler")

    # Send message to user (if possible)
    if update and update.effective_chat:
        try:
            # Get user's language
            from languages import get_player_language, get_text
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

    # Notify admins about critical errors
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
    """Check the database schema and fix if necessary."""
    try:
        logging.info("Validating database schema...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()

        # Create a versions table if it doesn't exist to track schema versions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS db_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Check current version
        cursor.execute("SELECT MAX(version) FROM db_version")
        result = cursor.fetchone()
        current_version = result[0] if result[0] is not None else 0
        max_version = current_version
        logging.info(f"Current database schema version: {current_version}")

        # Define migrations as a sequence of version upgrades
        migrations = {
            1: [
                # Initial schema - ensure core tables exist
                '''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY, 
                    name TEXT,
                    influence INTEGER DEFAULT 0,
                    surveillance INTEGER DEFAULT 0, 
                    force INTEGER DEFAULT 0,
                    wealth INTEGER DEFAULT 0,
                    operations_left INTEGER DEFAULT 3,
                    lang TEXT DEFAULT 'en'
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS districts (
                    id INTEGER PRIMARY KEY,
                    name TEXT, 
                    controller_id INTEGER,
                    FOREIGN KEY (controller_id) REFERENCES players(id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS politicians (
                    id INTEGER PRIMARY KEY, 
                    name TEXT,
                    controller_id INTEGER,
                    FOREIGN KEY (controller_id) REFERENCES players(id)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS coordinated_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    initiator_id INTEGER, 
                    target_type TEXT,
                    target_id INTEGER,
                    action_type TEXT,
                    expires_at TIMESTAMP,
                    resource_type TEXT,
                    resource_amount INTEGER,
                    participants TEXT,
                    FOREIGN KEY (initiator_id) REFERENCES players(id)
                )
                '''
            ],
            2: [
                # Version 2 - Add player_presence table
                '''
                CREATE TABLE IF NOT EXISTS player_presence (
                    player_id INTEGER PRIMARY KEY,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players(id)
                )
                '''
            ],
            3: [
                # Version 3 - Add district_defense table
                '''
                CREATE TABLE IF NOT EXISTS district_defense (
                    district_id INTEGER PRIMARY KEY,
                    defense_level INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (district_id) REFERENCES districts(id)
                )
                '''
            ],
            4: [
                # Version 4 - Add logs table for game event history
                '''
                CREATE TABLE IF NOT EXISTS game_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    player_id INTEGER,
                    target_type TEXT,
                    target_id INTEGER,
                    action TEXT,
                    result TEXT,
                    details TEXT,
                    FOREIGN KEY (player_id) REFERENCES players(id)
                )
                '''
            ]
        }

        # Add a new migration for processed_at column
        if max_version is None or current_version < 5:
            migrations[5] = [
                '''
                ALTER TABLE coordinated_actions ADD COLUMN processed_at TEXT
                '''
            ]
            
            # Apply this migration
            if current_version < 5:
                logging.info("Applying migration to version 5...")
                try:
                    for query in migrations[5]:
                        logging.info(f"Executing: {query}")
                        cursor.execute(query)
                        logging.info(f"Successfully executed: {query[:40]}...")
                    
                    # Update version in database
                    cursor.execute("INSERT INTO db_version (version) VALUES (?)", (5,))
                    conn.commit()
                    logging.info("Database upgraded to version 5")
                    current_version = 5
                except Exception as e:
                    conn.rollback()
                    logging.error(f"Migration to version 5 failed: {e}")
                    # Continue with other checks

        # Apply migrations sequentially
        for version in sorted(migrations.keys()):
            if version > current_version:
                logging.info(f"Applying migration to version {version}...")
                for sql in migrations[version]:
                    try:
                        cursor.execute(sql)
                        logging.info(f"Successfully executed: {sql[:50]}...")
                    except sqlite3.Error as e:
                        logging.warning(f"Error during migration: {e} - SQL: {sql[:50]}...")
                
                # Record the new version
                cursor.execute("INSERT INTO db_version (version) VALUES (?)", (version,))
                logging.info(f"Database upgraded to version {version}")
        
        conn.commit()

        # Additional schema checks (for backwards compatibility)
        check_required_tables(cursor)
        check_required_columns(cursor)

        conn.close()
        logging.info("Database schema validation complete.")
        return True
    except Exception as e:
        logging.error(f"Error validating database schema: {e}")
        traceback.print_exc()
        return False

def check_required_tables(cursor):
    """Check if required tables exist and create them if they don't."""
    # This function remains for backwards compatibility
    required_tables = ["players", "districts", "politicians", "coordinated_actions"]
    for table in required_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            logging.warning(f"Required table {table} not found. Setting up database...")
            setup_database()
            return

    # Check for newer tables that might not be in older versions
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_presence'")
    if not cursor.fetchone():
        logging.info("Adding player_presence table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_presence (
            player_id INTEGER PRIMARY KEY,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players(id)
        )
        ''')
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='district_defense'")
    if not cursor.fetchone():
        logging.info("Adding district_defense table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS district_defense (
            district_id INTEGER PRIMARY KEY,
            defense_level INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (district_id) REFERENCES districts(id)
        )
        ''')

def check_required_columns(cursor):
    """Check if required columns exist in tables and add them if they don't."""
    # Check for expires_at column in coordinated_actions
    try:
        cursor.execute("SELECT expires_at FROM coordinated_actions LIMIT 1")
    except sqlite3.OperationalError:
        logging.info("Adding expires_at column to coordinated_actions table...")
        cursor.execute("ALTER TABLE coordinated_actions ADD COLUMN expires_at TIMESTAMP")

    # Check for lang column in players
    try:
        cursor.execute("SELECT lang FROM players LIMIT 1")
    except sqlite3.OperationalError:
        logging.info("Adding lang column to players table...")
        cursor.execute("ALTER TABLE players ADD COLUMN lang TEXT DEFAULT 'en'")


def perform_startup_checks():
    """Perform all startup checks and return True if all passed."""
    try:
        # Check and fix database schema
        db_check = validate_and_fix_database_schema()
        if not db_check:
            logger.warning("Database schema validation failed or had issues")
        else:
            logger.info("Database schema check completed successfully")
        
        # Validate system components
        sys_check = validate_system()
        if not sys_check:
            logger.warning("System validation failed")
        else:
            logger.info("System validation completed successfully")
        
        # All checks must pass
        return db_check and sys_check
    except Exception as e:
        logger.error(f"Error during startup checks: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    main()