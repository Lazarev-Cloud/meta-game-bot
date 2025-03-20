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
        tables_exist = cursor.fetchone() is not None

        if tables_exist:
            # Check if coordinated_actions tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coordinated_actions'")
            if not cursor.fetchone():
                logger.info("Creating missing coordinated_actions tables")
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
                logger.info("Coordinated actions tables created")
            else:
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
            ('stari_grad', 'Stari Grad', 'Center of political power', 2, 0, 2, 0),
            ('novi_beograd', 'Novi Beograd', 'Economic and business center', 1, 3, 0, 0),
            ('zemun', 'Zemun', 'Criminal networks, smuggling', 0, 0, 1, 3),
            ('savski_venac', 'Savski Venac', 'Diplomatic ties and embassies', 2, 0, 2, 0),
            ('vozdovac', 'Vožovac', 'Military power and security', 1, 0, 0, 3),
            ('cukarica', 'Čukarica', 'Industrial and working-class district', 0, 3, 0, 1),
            ('palilula', 'Palilula', 'Youth and protest movements', 2, 0, 2, 0),
            ('vracar', 'Vračar', 'Cultural and religious elite', 2, 1, 0, 0)
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
        international_politicians = [
            (10, 'Bill Clinton', 'USA', -5, None, 0, 50, 1, 'Sanctions against conservatives, support for opposition'),
            (11, 'Tony Blair', 'UK', -4, None, 0, 50, 1, 'Influence on economic reforms, criticizes dictatorship'),
            (12, 'Jacques Chirac', 'France', -3, None, 0, 50, 1, 'Supports diplomacy but does not intervene radically'),
            (13, 'Joschka Fischer', 'Germany', -2, None, 0, 50, 1, 'Support for democratic activists'),
            (14, 'Javier Solana', 'NATO', -3, None, 0, 50, 1, 'Political pressure, threat of military intervention'),
            (15, 'Vladimir Zhirinovsky', 'Russia', 4, None, 0, 50, 1, 'Support for chaos and destabilization'),
            (16, 'Yevgeny Primakov', 'Russia', 2, None, 0, 50, 1,
             'Diplomatic support for the regime, help in bypassing sanctions'),
            (17, 'Václav Havel', 'Czech Republic', -5, None, 0, 50, 1, 'Strengthens opposition, support through NGOs'),
            (18, 'Madeleine Albright', 'USA', -4, None, 0, 50, 1, 'Advocates for tough sanctions against Milošević')
        ]

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

def ensure_player_has_base_resources(player_id):
    """Ensure that a player has the base starting resources."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Check if player has resources
        cursor.execute("SELECT player_id FROM resources WHERE player_id = ?", (player_id,))
        player_resources = cursor.fetchone()
        
        if not player_resources:
            # Initialize resources with base amounts
            cursor.execute(
                "INSERT INTO resources (player_id, influence, resources, information, force) VALUES (?, 5, 5, 5, 5)",
                (player_id,)
            )
            conn.commit()
            logger.info(f"Base resources added for player {player_id}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error ensuring base resources for player {player_id}: {e}")
        return False


