import sqlite3
import logging
import sys
import os

# Add parent directory to path to import bot modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot.politicians import LOCAL_POLITICIANS, INTERNATIONAL_POLITICIANS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_politicians():
    """Populate the politicians table with data from politicians.py definitions."""
    try:
        # Connect to the database
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if politicians table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='politicians'")
        if not cursor.fetchone():
            logger.error("Politicians table does not exist. Run db/update_schema.py first.")
            return False
        
        # Truncate politicians table to avoid duplicates
        logger.info("Clearing existing politicians...")
        cursor.execute("DELETE FROM politicians")
        
        # Insert local politicians
        for politician_id, politician in LOCAL_POLITICIANS.items():
            logger.info(f"Adding local politician: {politician['name']}")
            cursor.execute('''
            INSERT INTO politicians (
                politician_id, name, role, description, ideology_score, 
                district_id, influence, is_international
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                politician_id,
                politician['name'],
                politician['role'],
                politician['description'],
                politician['ideology'],
                politician['district'],
                politician['district_influence']
            ))
        
        # Insert international politicians
        for politician_id, politician in INTERNATIONAL_POLITICIANS.items():
            logger.info(f"Adding international politician: {politician['name']} ({politician['country']})")
            # For international politicians, we don't associate with a specific district
            cursor.execute('''
            INSERT INTO politicians (
                politician_id, name, role, description, ideology_score, 
                district_id, influence, is_international
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, 1)
            ''', (
                politician_id,
                politician['name'],
                politician['country'],  # Using country as role for internationals
                politician['description'] if 'description' in politician else politician.get('actions', [{}])[0].get('description', ''),
                politician['ideology'],
                0  # No direct district influence for international politicians
            ))
        
        # Commit and close the connection
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully added {len(LOCAL_POLITICIANS)} local and {len(INTERNATIONAL_POLITICIANS)} international politicians")
        return True
        
    except Exception as e:
        logger.error(f"Error populating politicians: {e}")
        return False

if __name__ == "__main__":
    success = populate_politicians()
    sys.exit(0 if success else 1) 