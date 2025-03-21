import sqlite3
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_coordinated_tables():
    """Create the coordinated action tables if they don't exist."""
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()

        # Check if tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coordinated_actions'")
        if cursor.fetchone():
            logger.info("Coordinated actions tables already exist")
            conn.close()
            return

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
            status TEXT DEFAULT 'open',
            expires_at TEXT,
            FOREIGN KEY (initiator_id) REFERENCES players (player_id)
        )
        ''')

        # Create CoordinatedActionParticipants table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS coordinated_action_participants (
            action_id INTEGER,
            player_id INTEGER,
            resources_used TEXT,
            joined_at TEXT,
            FOREIGN KEY (action_id) REFERENCES coordinated_actions (action_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')

        conn.commit()
        logger.info("Coordinated actions tables created successfully")
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_coordinated_tables() 