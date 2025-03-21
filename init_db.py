#!/usr/bin/env python3
import sqlite3
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with all required tables"""
    try:
        # Use novi_sad_game.db as it appears in the error messages
        db_path = 'novi_sad_game.db'
        
        # Check if database exists and remove it if --force flag is provided
        if os.path.exists(db_path) and '--force' in sys.argv:
            logger.info(f"Removing existing database: {db_path}")
            os.remove(db_path)
            
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"Connected to database: {db_path}")
        
        # Create all necessary tables
        
        # Create Players table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            username TEXT,
            character_name TEXT,
            ideology_score INTEGER DEFAULT 0,
            main_actions_left INTEGER DEFAULT 3,
            quick_actions_left INTEGER DEFAULT 3,
            last_action_refresh TEXT,
            language TEXT DEFAULT 'en'
        )
        ''')
        logger.info("Created players table")

        # Create Resources table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            player_id INTEGER,
            influence INTEGER DEFAULT 10,
            resources INTEGER DEFAULT 10,
            information INTEGER DEFAULT 10,
            force INTEGER DEFAULT 10,
            PRIMARY KEY (player_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created resources table")

        # Create or ensure Districts table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS districts (
            district_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            influence_resource INTEGER DEFAULT 0,
            resources_resource INTEGER DEFAULT 0,
            information_resource INTEGER DEFAULT 0,
            force_resource INTEGER DEFAULT 0
        )
        ''')
        logger.info("Created districts table")

        # Create DistrictControl table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS district_control (
            district_id TEXT,
            player_id INTEGER,
            control_points INTEGER DEFAULT 0,
            last_action TEXT,
            PRIMARY KEY (district_id, player_id),
            FOREIGN KEY (district_id) REFERENCES districts (district_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created district_control table")
        
        # Create presence tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_presence (
            player_id INTEGER,
            district_id TEXT,
            last_presence TEXT,
            last_collected TEXT,
            PRIMARY KEY (player_id, district_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id),
            FOREIGN KEY (district_id) REFERENCES districts (district_id)
        )
        ''')
        logger.info("Created player_presence table")

        # Create district defense table
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
        logger.info("Created district_defense table")

        # Create Politicians table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS politicians (
            politician_id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            ideology_score INTEGER,
            district_id TEXT,
            influence INTEGER DEFAULT 0,
            friendliness INTEGER DEFAULT 50,
            is_international BOOLEAN DEFAULT 0,
            description TEXT,
            FOREIGN KEY (district_id) REFERENCES districts (district_id)
        )
        ''')
        logger.info("Created politicians table")

        # Create politician relationships table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS politician_friendliness (
            politician_id TEXT,
            player_id INTEGER,
            friendliness INTEGER DEFAULT 50,
            last_interaction TEXT,
            interaction_count INTEGER DEFAULT 0,
            PRIMARY KEY (politician_id, player_id),
            FOREIGN KEY (politician_id) REFERENCES politicians (politician_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created politician_friendliness table")

        # Create Actions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            action_type TEXT,
            target_type TEXT,
            target_id TEXT,
            resources_used TEXT,
            timestamp TEXT,
            cycle TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created actions table")

        # Create News table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            news_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            importance INTEGER DEFAULT 1,
            timestamp TEXT,
            is_hidden INTEGER DEFAULT 0,
            is_public INTEGER DEFAULT 1,
            target_player_id INTEGER,
            is_fake INTEGER DEFAULT 0,
            FOREIGN KEY (target_player_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created news table")

        # Create CoordinatedActions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coordinated_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiator_id INTEGER,
            action_type TEXT,
            target_type TEXT,
            target_id TEXT,
            resources_used TEXT,
            timestamp TEXT,
            cycle TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'open',
            result TEXT,
            FOREIGN KEY (initiator_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created coordinated_actions table")

        # Create CoordinatedActionParticipants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coordinated_action_participants (
            participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id INTEGER,
            player_id INTEGER,
            resources_used TEXT,
            joined_at TEXT,
            FOREIGN KEY (action_id) REFERENCES coordinated_actions (action_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')
        logger.info("Created coordinated_action_participants table")
        
        # Create schema_version table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        )
        ''')
        cursor.execute("INSERT OR REPLACE INTO schema_version VALUES (4)")
        logger.info("Created schema_version table (set to version 4)")
        
        conn.commit()
        logger.info("Database initialization complete!")
        
        # Close connection
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    print("===== Initializing Database =====")
    if init_database():
        print("✅ Database initialization successful!")
    else:
        print("❌ Database initialization failed!")
        sys.exit(1) 