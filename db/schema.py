from typing import Dict, List, Optional, Any
from db.queries import db_connection_pool, db_transaction
import logging
import datetime
import json

logger = logging.getLogger(__name__)

def initialize_database() -> None:
    """Initialize the database schema."""
    with db_connection_pool.get_connection() as conn:
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                ideology_score INTEGER DEFAULT 50,
                language TEXT DEFAULT 'en',
                influence INTEGER DEFAULT 0,
                last_action_time TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS districts (
                district_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                control_points INTEGER DEFAULT 0,
                controller_id INTEGER,
                FOREIGN KEY (controller_id) REFERENCES players(player_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS politicians (
                politician_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                ideology_score INTEGER DEFAULT 50,
                district_id INTEGER,
                influence INTEGER DEFAULT 0,
                friendliness INTEGER DEFAULT 50,
                is_international BOOLEAN DEFAULT FALSE,
                description TEXT,
                FOREIGN KEY (district_id) REFERENCES districts(district_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS politician_relationships (
                player_id INTEGER,
                politician_id INTEGER,
                friendliness INTEGER DEFAULT 50,
                interaction_count INTEGER DEFAULT 0,
                PRIMARY KEY (player_id, politician_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                FOREIGN KEY (politician_id) REFERENCES politicians(politician_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_types (
                resource_type TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_resources (
                player_id INTEGER,
                resource_type TEXT,
                amount INTEGER DEFAULT 0,
                PRIMARY KEY (player_id, resource_type),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                FOREIGN KEY (resource_type) REFERENCES resource_types(resource_type)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS district_resources (
                district_id INTEGER,
                resource_type TEXT,
                production_rate INTEGER DEFAULT 0,
                PRIMARY KEY (district_id, resource_type),
                FOREIGN KEY (district_id) REFERENCES districts(district_id),
                FOREIGN KEY (resource_type) REFERENCES resource_types(resource_type)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS languages (
                language_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                native_name TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                key TEXT,
                language_code TEXT,
                text TEXT NOT NULL,
                PRIMARY KEY (key, language_code),
                FOREIGN KEY (language_code) REFERENCES languages(language_code)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                cost INTEGER,
                cooldown_hours INTEGER DEFAULT 0,
                required_influence INTEGER DEFAULT 0,
                success_chance INTEGER DEFAULT 100
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_actions (
                player_id INTEGER,
                action_id INTEGER,
                last_used_timestamp TIMESTAMP,
                PRIMARY KEY (player_id, action_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                FOREIGN KEY (action_id) REFERENCES actions(action_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS politician_abilities (
                ability_id INTEGER PRIMARY KEY AUTOINCREMENT,
                politician_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                cooldown_hours INTEGER DEFAULT 0,
                cost INTEGER DEFAULT 0,
                FOREIGN KEY (politician_id) REFERENCES politicians(politician_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ability_history (
                ability_id INTEGER,
                player_id INTEGER,
                used_timestamp TIMESTAMP,
                PRIMARY KEY (ability_id, player_id),
                FOREIGN KEY (ability_id) REFERENCES politician_abilities(ability_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                news_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                offerer_id INTEGER,
                offered_resources TEXT NOT NULL,  -- JSON string
                requested_resources TEXT NOT NULL,  -- JSON string
                status TEXT DEFAULT 'pending',
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_timestamp TIMESTAMP,
                FOREIGN KEY (offerer_id) REFERENCES players(player_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS joint_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                initiator_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                required_participants INTEGER DEFAULT 2,
                status TEXT DEFAULT 'pending',
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline_timestamp TIMESTAMP,
                FOREIGN KEY (initiator_id) REFERENCES players(player_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS joint_action_participants (
                action_id INTEGER,
                player_id INTEGER,
                joined_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (action_id, player_id),
                FOREIGN KEY (action_id) REFERENCES joint_actions(action_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commands (
                command TEXT PRIMARY KEY,
                description TEXT NOT NULL
            )
        """)

        # Initialize basic data
        initialize_basic_data(conn)

def initialize_basic_data(conn: Any) -> None:
    """Initialize basic data in the database."""
    cursor = conn.cursor()

    # Initialize resource types
    resource_types = [
        ('money', 'Money', 'Basic currency'),
        ('influence', 'Influence', 'Political influence points'),
        ('support', 'Support', 'Public support points')
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO resource_types (resource_type, name, description)
        VALUES (?, ?, ?)
    """, resource_types)

    # Initialize languages
    languages = [
        ('en', 'English', 'English'),
        ('sr', 'Serbian', 'Српски'),
        ('ru', 'Russian', 'Русский')
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO languages (language_code, name, native_name)
        VALUES (?, ?, ?)
    """, languages)

    # Initialize commands
    commands = [
        ('start', 'Start the game'),
        ('help', 'Show available commands'),
        ('profile', 'View your profile'),
        ('language', 'Change language'),
        ('districts', 'View districts'),
        ('politicians', 'View politicians'),
        ('actions', 'View available actions'),
        ('resources', 'View your resources'),
        ('trades', 'View active trades'),
        ('news', 'View latest news')
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO commands (command, description)
        VALUES (?, ?)
    """, commands)

    conn.commit()

def update_database_schema() -> None:
    """Update the database schema if needed."""
    with db_connection_pool.get_connection() as conn:
        cursor = conn.cursor()
        
        # Add new columns or tables here
        try:
            # Example: Add a new column to the players table
            cursor.execute("""
                ALTER TABLE players
                ADD COLUMN last_login TIMESTAMP
            """)
        except Exception as e:
            # Column might already exist
            pass
            
        conn.commit()

def get_international_politicians_data():
    """Get initial international politicians data"""
    from game.data.international_politicians import INTERNATIONAL_POLITICIANS
    
    # Convert to database format
    return [(i+10, p["name"], p["role"], p["ideology_score"], 
             None, p["influence"], 50, 1, p["description"]) 
            for i, p in enumerate(INTERNATIONAL_POLITICIANS)]

def setup_database() -> None:
    """Set up the database by initializing schema and basic data."""
    try:
        initialize_database()
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database schema: {e}")
        raise