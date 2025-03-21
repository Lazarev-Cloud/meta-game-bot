import sqlite3
import logging
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_schema():
    """Update the database schema to match the latest requirements."""
    try:
        # Connect to the database
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if we need to update column names in districts table
        cursor.execute("PRAGMA table_info(districts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Update the column names if they have the old format
        if 'economic_resources' in columns and 'resources_resource' not in columns:
            logger.info("Updating district resource column names...")
            
            # Create a new table with correct column names
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS districts_new (
                district_id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                influence_resource INTEGER DEFAULT 0,
                resources_resource INTEGER DEFAULT 0,
                information_resource INTEGER DEFAULT 0,
                force_resource INTEGER DEFAULT 0
            )
            ''')
            
            # Copy data from old table to new table
            cursor.execute('''
            INSERT INTO districts_new (district_id, name, description, influence_resource, 
                resources_resource, information_resource, force_resource)
            SELECT district_id, name, description, influence_resources, 
                economic_resources, information_resources, force_resources
            FROM districts
            ''')
            
            # Drop old table and rename new table
            cursor.execute('DROP TABLE districts')
            cursor.execute('ALTER TABLE districts_new RENAME TO districts')
            
            logger.info("Successfully updated district table structure")
        
        # Update district resource values to match game rules
        logger.info("Updating district resources to match Novi Sad game rules...")
        
        # Stari Grad: +2 Influence, +2 Information
        cursor.execute('''
        UPDATE districts SET 
            influence_resource = 2,
            information_resource = 2,
            resources_resource = 0,
            force_resource = 0,
            description = 'Historical and administrative center'
        WHERE district_id = 'stari_grad'
        ''')
        
        # Liman: +2 Influence, +2 Information
        cursor.execute('''
        UPDATE districts SET 
            influence_resource = 2,
            information_resource = 2,
            resources_resource = 0,
            force_resource = 0,
            description = 'University and scientific center'
        WHERE district_id = 'liman' OR district_id = 'novi_beograd'
        ''')
        
        # Petrovaradin: +2 Influence, +1 Resource
        cursor.execute('''
        UPDATE districts SET 
            influence_resource = 2,
            resources_resource = 1,
            information_resource = 0,
            force_resource = 0,
            description = 'Cultural heritage, tourism'
        WHERE district_id = 'petrovaradin' OR district_id = 'zemun'
        ''')
        
        # Podbara: +3 Resources, +1 Force
        cursor.execute('''
        UPDATE districts SET 
            resources_resource = 3,
            force_resource = 1,
            influence_resource = 0, 
            information_resource = 0,
            description = 'Industrial district'
        WHERE district_id = 'podbara' OR district_id = 'savski_venac'
        ''')
        
        # Detelinara: +2 Resources, +2 Influence
        cursor.execute('''
        UPDATE districts SET 
            resources_resource = 2,
            influence_resource = 2,
            information_resource = 0,
            force_resource = 0,
            description = 'Residential area, working class'
        WHERE district_id = 'detelinara' OR district_id = 'vracar'
        ''')
        
        # Satelit: +3 Resources, +1 Influence
        cursor.execute('''
        UPDATE districts SET 
            resources_resource = 3,
            influence_resource = 1,
            information_resource = 0,
            force_resource = 0,
            description = 'New district, economic growth'
        WHERE district_id = 'satelit' OR district_id = 'cukarica'
        ''')
        
        # Adamovicevo: +3 Force, +1 Influence
        cursor.execute('''
        UPDATE districts SET 
            force_resource = 3,
            influence_resource = 1,
            information_resource = 0, 
            resources_resource = 0,
            description = 'Military installations, security'
        WHERE district_id = 'adamovicevo' OR district_id = 'vozdovac'
        ''')
        
        # Sremska Kamenica: +3 Force, +1 Information
        cursor.execute('''
        UPDATE districts SET 
            force_resource = 3,
            information_resource = 1,
            influence_resource = 0,
            resources_resource = 0,
            description = 'Suburb, shadow economy'
        WHERE district_id = 'sremska_kamenica' OR district_id = 'palilula'
        ''')
        
        # Check if we need to insert any missing districts
        cursor.execute("SELECT district_id FROM districts")
        existing_districts = [row[0] for row in cursor.fetchall()]
        
        districts_to_create = [
            ('stari_grad', 'Stari Grad', 'Historical and administrative center', 2, 0, 2, 0),
            ('liman', 'Liman', 'University and scientific center', 2, 0, 2, 0),
            ('petrovaradin', 'Petrovaradin', 'Cultural heritage, tourism', 2, 1, 0, 0),
            ('podbara', 'Podbara', 'Industrial district', 0, 3, 0, 1),
            ('detelinara', 'Detelinara', 'Residential area, working class', 2, 2, 0, 0),
            ('satelit', 'Satelit', 'New district, economic growth', 1, 3, 0, 0),
            ('adamovicevo', 'Adamovicevo', 'Military installations, security', 1, 0, 0, 3),
            ('sremska_kamenica', 'Sremska Kamenica', 'Suburb, shadow economy', 0, 0, 1, 3)
        ]
        
        for district in districts_to_create:
            district_id = district[0]
            if district_id not in existing_districts:
                logger.info(f"Creating missing district: {district_id}")
                cursor.execute('''
                INSERT INTO districts (district_id, name, description, influence_resource, 
                    resources_resource, information_resource, force_resource)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', district)
        
        # Update politician table or create it if it doesn't exist
        # First check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='politicians'")
        if not cursor.fetchone():
            logger.info("Creating politicians table...")
            cursor.execute('''
            CREATE TABLE politicians (
                politician_id TEXT PRIMARY KEY,
                name TEXT,
                role TEXT,
                description TEXT,
                ideology INTEGER DEFAULT 0,
                district_id TEXT,
                district_influence INTEGER DEFAULT 0,
                is_international INTEGER DEFAULT 0,
                FOREIGN KEY (district_id) REFERENCES districts(district_id)
            )
            ''')
        else:
            # Check if ideology column exists and add it if not
            cursor.execute("PRAGMA table_info(politicians)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'ideology' not in columns:
                logger.info("Adding ideology column to politicians table...")
                cursor.execute("ALTER TABLE politicians ADD COLUMN ideology INTEGER DEFAULT 0")
            
            if 'district_influence' not in columns:
                logger.info("Adding district_influence column to politicians table...")
                cursor.execute("ALTER TABLE politicians ADD COLUMN district_influence INTEGER DEFAULT 0")
        
        # Create politicians_friendliness table if it doesn't exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='politician_friendliness'")
        if not cursor.fetchone():
            logger.info("Creating politician_friendliness table...")
            cursor.execute('''
            CREATE TABLE politician_friendliness (
                politician_id TEXT,
                player_id INTEGER,
                friendliness INTEGER DEFAULT 0,
                PRIMARY KEY (politician_id, player_id),
                FOREIGN KEY (politician_id) REFERENCES politicians(politician_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
            ''')
        
        # Commit and close the connection
        conn.commit()
        conn.close()
        
        logger.info("Database schema updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error updating schema: {e}")
        return False

if __name__ == "__main__":
    success = update_schema()
    sys.exit(0 if success else 1) 