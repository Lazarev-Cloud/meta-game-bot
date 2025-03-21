import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate_action_timestamp_fields():
    """Add separate action refresh timestamp fields if they don't exist."""
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if the new columns already exist
        cursor.execute("PRAGMA table_info(players)")
        columns = [info[1] for info in cursor.fetchall()]
        
        # Add the missing columns if needed
        if "last_main_action_refresh" not in columns:
            logger.info("Adding last_main_action_refresh column to players table")
            cursor.execute("ALTER TABLE players ADD COLUMN last_main_action_refresh TEXT")
            cursor.execute("UPDATE players SET last_main_action_refresh = last_action_refresh")
        
        if "last_quick_action_refresh" not in columns:
            logger.info("Adding last_quick_action_refresh column to players table")
            cursor.execute("ALTER TABLE players ADD COLUMN last_quick_action_refresh TEXT")
            cursor.execute("UPDATE players SET last_quick_action_refresh = last_action_refresh")
        
        conn.commit()
        conn.close()
        logger.info("Action timestamp fields migration completed")
        return True
    
    except Exception as e:
        logger.error(f"Error migrating action timestamp fields: {e}")
        return False 

def run_migrations():
    """Run all necessary database migrations."""
    try:
        logger.info("Starting database migrations")
        
        # Run action timestamp migration
        migrate_action_timestamp_fields()
        
        # Add more migrations here as needed
        
        logger.info("All migrations completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False 