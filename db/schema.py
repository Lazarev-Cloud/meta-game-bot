import sqlite3
import logging
import datetime
import json

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

        # Create politician_relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS politician_relationships (
                relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                politician_id INTEGER,
                player_id INTEGER,
                friendliness INTEGER NOT NULL DEFAULT 50,
                interaction_count INTEGER NOT NULL DEFAULT 0,
                last_interaction INTEGER,
                FOREIGN KEY (politician_id) REFERENCES politicians(politician_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        # Create politician_abilities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS politician_abilities (
                ability_id INTEGER PRIMARY KEY AUTOINCREMENT,
                politician_id INTEGER,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                cooldown INTEGER NOT NULL,  -- в циклах
                cost TEXT NOT NULL,  -- JSON строка с ресурсами
                effect_type TEXT NOT NULL,  -- тип эффекта
                effect_value TEXT NOT NULL,  -- значение эффекта в JSON
                required_friendliness INTEGER NOT NULL,
                FOREIGN KEY (politician_id) REFERENCES politicians(politician_id)
            )
        """)

        # Create politician_ability_usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS politician_ability_usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                politician_id INTEGER,
                player_id INTEGER,
                ability_id INTEGER,
                last_used_cycle INTEGER,
                FOREIGN KEY (politician_id) REFERENCES politicians(politician_id),
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                FOREIGN KEY (ability_id) REFERENCES politician_abilities(ability_id)
            )
        """)

        # Create tables for trading system
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_offers (
            offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (sender_id) REFERENCES players (player_id),
            FOREIGN KEY (receiver_id) REFERENCES players (player_id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER,
            resource_type TEXT,
            amount INTEGER,
            is_offer BOOLEAN,
            FOREIGN KEY (offer_id) REFERENCES trade_offers (offer_id)
        )
        ''')

        # Create table for joint actions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS joint_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            initiator_id INTEGER,
            district_id TEXT,
            action_type TEXT,
            created_at TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (initiator_id) REFERENCES players (player_id),
            FOREIGN KEY (district_id) REFERENCES districts (district_id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS joint_action_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id INTEGER,
            player_id INTEGER,
            join_time TEXT,
            resources TEXT,
            FOREIGN KEY (action_id) REFERENCES joint_actions (action_id),
            FOREIGN KEY (player_id) REFERENCES players (player_id)
        )
        ''')

        # Create table for district control history
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS district_control_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district_id TEXT,
            player_id INTEGER,
            cycle INTEGER,
            control_points_change INTEGER,
            timestamp TEXT,
            FOREIGN KEY (district_id) REFERENCES districts (district_id),
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
            (3, 'Zoran Đinđić', 'Leader of the Democratic Party', -5, 'liman', 7, 50, 0,
             'Promoting democratization and economic reforms'),
            (4, 'Željko "Arkan" Ražnatović', 'Criminal networks, black market', -2, 'petrovaradin', 5, 50, 0,
             'Influential figure in criminal circles and politics'),
            (5, 'Borislav Milošević', 'International diplomats', 3, 'grbavica', 4, 50, 0,
             'Ambassador of Yugoslavia to Russia'),
            (
                6, 'Nebojša Pavković', 'Military command', -4, 'adamoviceva', 6, 50, 0,
                'Supporter of hardline security policies'),
            (7, 'Miroljub Labus', 'Union leaders', 2, 'sajmiste', 4, 50, 0,
             'Advocated for economic reforms and integration with Europe'),
            (8, 'Čedomir "Čeda" Jovanović', 'Student movement leader', -4, 'podbara', 5, 50, 0,
             'Active participant in protests against the Milošević regime'),
            (
                9, 'Patriarch Pavle', 'Religious leaders', -1, 'salajka', 5, 50, 0,
                'Supports traditional values and status quo')
        ]

        # International politicians
        international_politicians = get_international_politicians_data()

        cursor.executemany(
            "INSERT INTO politicians VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            politicians
        )
        cursor.executemany(
            "INSERT INTO politicians VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            international_politicians
        )

        # Initialize politician abilities
        politician_abilities = [
            # Неманя Ковачевич
            (1, 1, "Административный ресурс", 
             "Позволяет заблокировать одну заявку противника в день в районе Стари Град",
             1,  # cooldown в циклах
             json.dumps({"influence": 2, "information": 1}),  # cost
             "block_action",  # effect_type
             json.dumps({"district_id": "stari_grad"}),  # effect_value
             80),  # required_friendliness

            # Профессор Драган Йович
            (2, 3, "Студенческий протест",
             "Можно организовать протест в любом районе (+15 ОК к атаке)",
             2,  # cooldown
             json.dumps({"influence": 2, "information": 2}),
             "attack_bonus",
             json.dumps({"bonus": 15}),
             75),

            # Зоран "Зоки" Новакович
            (3, 4, "Теневые связи",
             "Конвертирует 2 любых ресурса в 4 Силы раз в день",
             1,  # cooldown
             json.dumps({"influence": 1, "information": 1}),
             "resource_conversion",
             json.dumps({"force": 4}),
             70),

            # Полковник Бранко Петрович
            (4, 6, "Силовая зачистка",
             "Можно 'обнулить' контроль противника в одном районе раз в 3 цикла",
             3,  # cooldown
             json.dumps({"force": 3, "influence": 2}),
             "reset_control",
             json.dumps({"district_id": None}),  # district_id будет указан при использовании
             85)
        ]

        cursor.executemany(
            "INSERT INTO politician_abilities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            politician_abilities
        )

        conn.commit()
        logger.info("Database setup completed successfully")
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")
    finally:
        if conn:
            conn.close()

def update_database_schema():
    """
    Update database schema to resolve ambiguous column names and add missing columns
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Add fully qualified column names to tables
        cursor.execute("""
            ALTER TABLE politicians 
            ADD COLUMN politician_district_id TEXT 
            REFERENCES districts(district_id)
        """)

        # Ensure news table has created_at column
        cursor.execute("""
            ALTER TABLE news 
            ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        """)

        # Update existing queries to use fully qualified column names
        cursor.execute("""
            CREATE VIEW v_politician_districts AS
            SELECT 
                p.politician_id, 
                p.name, 
                p.politician_district_id AS district_id,
                d.name AS district_name
            FROM politicians p
            LEFT JOIN districts d ON p.politician_district_id = d.district_id
        """)

        conn.commit()
        conn.close()
        logger.info("Database schema updated successfully")
    except sqlite3.OperationalError as e:
        # Ignore error if column already exists
        if "duplicate column name" not in str(e) and "column created_at already exists" not in str(e):
            logger.error(f"Error updating database schema: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating database schema: {e}")



def get_international_politicians_data():
    """Get initial international politicians data"""
    from game.data.international_politicians import INTERNATIONAL_POLITICIANS
    
    # Convert to database format
    return [(i+10, p["name"], p["role"], p["ideology_score"], 
             None, p["influence"], 50, 1, p["description"]) 
            for i, p in enumerate(INTERNATIONAL_POLITICIANS)]