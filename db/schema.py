import sqlite3
import logging
import datetime

logger = logging.getLogger(__name__)

def setup_database():
    """Initialize database schema for the Belgrade game."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check if database is already set up
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='districts'")
        if cursor.fetchone():
            logger.info("Database already exists, skipping setup")
            conn.close()
            return

        # Create Players table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            username TEXT,
            character_name TEXT,
            ideology_score INTEGER DEFAULT 0,
            main_actions_left INTEGER DEFAULT 1,
            quick_actions_left INTEGER DEFAULT 2,
            last_action_refresh TEXT,
            language TEXT DEFAULT 'en'
        )
        ''')

        # Create Resources table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            player_id INTEGER,
            influence INTEGER DEFAULT 0,
            resources INTEGER DEFAULT 0,
            information INTEGER DEFAULT 0,
            force INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')

        # Create Districts table
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

        # Create DistrictControl table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS district_control (
            district_id TEXT,
            player_id INTEGER,
            control_points INTEGER DEFAULT 0,
            last_action TEXT,
            FOREIGN KEY (district_id) REFERENCES districts (district_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')

        # Create Politicians table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS politicians (
            politician_id INTEGER PRIMARY KEY,
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

        # Create News table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            news_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            timestamp TEXT,
            is_public BOOLEAN DEFAULT 1,
            target_player_id INTEGER DEFAULT NULL,
            is_fake BOOLEAN DEFAULT 0,
            FOREIGN KEY (target_player_id) REFERENCES players (player_id)
        )
        ''')

        # Create table for politician relationships
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS politician_relationships (
            politician_id INTEGER,
            player_id INTEGER,
            friendliness INTEGER DEFAULT 50,
            last_interaction TEXT,
            interaction_count INTEGER DEFAULT 0,
            PRIMARY KEY (politician_id, player_id),
            FOREIGN KEY (politician_id) REFERENCES politicians (politician_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')

        # Initialize districts data
        districts = [
            ('stari_grad', 'Stari grad', 'Center of political power', 2, 0, 2, 0),
            ('liman', 'Liman', 'Economic and business center', 1, 3, 0, 0),
            ('petrovaradin', 'Petrovaradin', 'Criminal networks, smuggling', 0, 0, 1, 3),
            ('grbavica', 'Grbavica', 'Diplomatic ties and embassies', 2, 0, 2, 0),
            ('adamoviceva', 'Adamoviceva naselje', 'Military power and security', 1, 0, 0, 3),
            ('sajmiste', 'Sajmište', 'Industrial and working-class district', 0, 3, 0, 1),
            ('podbara', 'Podbara', 'Youth and protest movements', 2, 0, 2, 0),
            ('salajka', 'Salajka', 'Cultural and religious elite', 2, 1, 0, 0)
        ]

        cursor.execute("SELECT COUNT(*) FROM districts")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO districts VALUES (?, ?, ?, ?, ?, ?, ?)",
                districts
            )

        # Initialize politicians data
        politicians = [
            (1, 'Slobodan Milošević', 'President of Yugoslavia', 5, 'stari_grad', 6, 50, 0,
             'Supporter of centralized power and opponent of radical reforms'),
            (2, 'Milan Milutinović', 'Administration, regional influence', 3, 'stari_grad', 4, 50, 0,
             'Can slow down reforms but helps with bureaucracy'),
            (3, 'Zoran Đinđić', 'Leader of the Democratic Party', -5, 'novi_beograd', 7, 50, 0,
             'Promoting democratization and economic reforms'),
            (4, 'Željko "Arkan" Ražnatović', 'Criminal networks, black market', -2, 'zemun', 5, 50, 0,
             'Influential figure in criminal circles and politics'),
            (5, 'Borislav Milošević', 'International diplomats', 3, 'savski_venac', 4, 50, 0,
             'Ambassador of Yugoslavia to Russia'),
            (
                6, 'Nebojša Pavković', 'Military command', -4, 'vozdovac', 6, 50, 0,
                'Supporter of hardline security policies'),
            (7, 'Miroljub Labus', 'Union leaders', 2, 'cukarica', 4, 50, 0,
             'Advocated for economic reforms and integration with Europe'),
            (8, 'Čedomir "Čeda" Jovanović', 'Student movement leader', -4, 'palilula', 5, 50, 0,
             'Active participant in protests against the Milošević regime'),
            (
                9, 'Patriarch Pavle', 'Religious leaders', -1, 'vracar', 5, 50, 0,
                'Supports traditional values and status quo')
        ]

        # International politicians
        international_politicians = get_international_politicians_data()

        cursor.execute("SELECT COUNT(*) FROM politicians")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO politicians VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                politicians
            )
            cursor.executemany(
                "INSERT INTO politicians VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                international_politicians
            )

        conn.commit()
        logger.info("Database setup completed successfully")
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")
    finally:
        if conn:
            conn.close()

def use_action(player_id: int, is_main: bool = True) -> bool:
    """
    Use up one action for the player
    
    Args:
        player_id: Player ID
        is_main: If True, uses main action. If False, uses quick action.
        
    Returns:
        bool: True if action was used, False if no actions left
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Check remaining actions
        action_type = 'main_actions_left' if is_main else 'quick_actions_left'
        cursor.execute(f"SELECT {action_type} FROM players WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()
        
        if not result or result[0] <= 0:
            conn.close()
            return False
            
        # Decrease action count
        cursor.execute(
            f"UPDATE players SET {action_type} = {action_type} - 1 WHERE player_id = ?",
            (player_id,)
        )
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error using action: {e}")
        return False

def get_international_politicians_data():
    """Get initial international politicians data"""
    from game.data.international_politicians import INTERNATIONAL_POLITICIANS
    
    # Convert to database format
    return [(i+10, p["name"], p["role"], p["ideology_score"], 
             None, p["influence"], 50, 1, p["description"]) 
            for i, p in enumerate(INTERNATIONAL_POLITICIANS)]