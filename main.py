import logging
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
import sqlite3
import json
import random
import asyncio
from config import TOKEN, ADMIN_IDS

# Import the language support module
from languages import get_text, get_cycle_name, get_resource_name, format_ideology, get_action_name

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Game constants
MORNING_CYCLE_START = datetime.time(6, 0)  # 6:00 AM
MORNING_CYCLE_DEADLINE = datetime.time(12, 0)  # 12:00 PM
MORNING_CYCLE_RESULTS = datetime.time(13, 0)  # 1:00 PM
EVENING_CYCLE_START = datetime.time(13, 1)  # 1:01 PM
EVENING_CYCLE_DEADLINE = datetime.time(18, 0)  # 6:00 PM
EVENING_CYCLE_RESULTS = datetime.time(19, 0)  # 7:00 PM

# Constants for action types
ACTION_INFLUENCE = "influence"
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defense"
QUICK_ACTION_RECON = "recon"
QUICK_ACTION_INFO = "info"
QUICK_ACTION_SUPPORT = "support"

# Resource types
RESOURCE_INFLUENCE = "influence"
RESOURCE_RESOURCES = "resources"
RESOURCE_INFORMATION = "information"
RESOURCE_FORCE = "force"

# Database setup
def setup_database():
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
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
        (1, 'Slobodan Milošević', 'President of Yugoslavia', 5, 'stari_grad', 6, 50, 0, 'Supporter of centralized power and opponent of radical reforms'),
        (2, 'Milan Milutinović', 'Administration, regional influence', 3, 'stari_grad', 4, 50, 0, 'Can slow down reforms but helps with bureaucracy'),
        (3, 'Zoran Đinđić', 'Leader of the Democratic Party', -5, 'novi_beograd', 7, 50, 0, 'Promoting democratization and economic reforms'),
        (4, 'Željko "Arkan" Ražnatović', 'Criminal networks, black market', -2, 'zemun', 5, 50, 0, 'Influential figure in criminal circles and politics'),
        (5, 'Borislav Milošević', 'International diplomats', 3, 'savski_venac', 4, 50, 0, 'Ambassador of Yugoslavia to Russia'),
        (6, 'Nebojša Pavković', 'Military command', -4, 'vozdovac', 6, 50, 0, 'Supporter of hardline security policies'),
        (7, 'Miroljub Labus', 'Union leaders', 2, 'cukarica', 4, 50, 0, 'Advocated for economic reforms and integration with Europe'),
        (8, 'Čedomir "Čeda" Jovanović', 'Student movement leader', -4, 'palilula', 5, 50, 0, 'Active participant in protests against the Milošević regime'),
        (9, 'Patriarch Pavle', 'Religious leaders', -1, 'vracar', 5, 50, 0, 'Supports traditional values and status quo')
    ]
    
    # International politicians
    international_politicians = [
        (10, 'Bill Clinton', 'USA', -5, None, 0, 50, 1, 'Sanctions against conservatives, support for opposition'),
        (11, 'Tony Blair', 'UK', -4, None, 0, 50, 1, 'Influence on economic reforms, criticizes dictatorship'),
        (12, 'Jacques Chirac', 'France', -3, None, 0, 50, 1, 'Supports diplomacy but does not intervene radically'),
        (13, 'Joschka Fischer', 'Germany', -2, None, 0, 50, 1, 'Support for democratic activists'),
        (14, 'Javier Solana', 'NATO', -3, None, 0, 50, 1, 'Political pressure, threat of military intervention'),
        (15, 'Vladimir Zhirinovsky', 'Russia', 4, None, 0, 50, 1, 'Support for chaos and destabilization'),
        (16, 'Yevgeny Primakov', 'Russia', 2, None, 0, 50, 1, 'Diplomatic support for the regime, help in bypassing sanctions'),
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
    conn.close()

# Database helper functions
def get_player(player_id):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    player = cursor.fetchone()
    conn.close()
    return player

def register_player(player_id, username, language="en"):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    # Check if player already exists
    cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    if cursor.fetchone() is None:
        # Insert new player
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO players (player_id, username, last_action_refresh, language) VALUES (?, ?, ?, ?)",
            (player_id, username, now, language)
        )
        
        # Initialize resources
        cursor.execute(
            "INSERT INTO resources (player_id, influence, resources, information, force) VALUES (?, 5, 5, 5, 5)",
            (player_id,)
        )
        
        conn.commit()
    
    conn.close()

def set_player_name(player_id, character_name):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET character_name = ? WHERE player_id = ?",
        (character_name, player_id)
    )
    conn.commit()
    conn.close()

def get_player_resources(player_id):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources WHERE player_id = ?", (player_id,))
    resources = cursor.fetchone()
    conn.close()
    
    if resources:
        return {
            "influence": resources[1],
            "resources": resources[2],
            "information": resources[3],
            "force": resources[4]
        }
    return None

def update_player_resources(player_id, resource_type, amount):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    # Get current resource amount
    cursor.execute(f"SELECT {resource_type} FROM resources WHERE player_id = ?", (player_id,))
    current = cursor.fetchone()[0]
    
    # Update resource
    new_amount = current + amount
    if new_amount < 0:
        new_amount = 0
    
    cursor.execute(
        f"UPDATE resources SET {resource_type} = ? WHERE player_id = ?",
        (new_amount, player_id)
    )
    
    conn.commit()
    conn.close()
    return new_amount

def get_district_info(district_id):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM districts WHERE district_id = ?", (district_id,))
    district = cursor.fetchone()
    conn.close()
    return district

def get_all_districts():
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM districts")
    districts = cursor.fetchall()
    conn.close()
    return districts

def get_district_control(district_id):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dc.player_id, dc.control_points, p.character_name 
        FROM district_control dc
        JOIN players p ON dc.player_id = p.player_id
        WHERE dc.district_id = ?
        ORDER BY dc.control_points DESC
        """, 
        (district_id,)
    )
    control_data = cursor.fetchall()
    conn.close()
    return control_data

def get_player_districts(player_id):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT d.district_id, d.name, dc.control_points 
        FROM district_control dc
        JOIN districts d ON dc.district_id = d.district_id
        WHERE dc.player_id = ?
        ORDER BY dc.control_points DESC
        """, 
        (player_id,)
    )
    districts = cursor.fetchall()
    conn.close()
    return districts

def update_district_control(player_id, district_id, points_change):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    # Check if player already has control points in this district
    cursor.execute(
        "SELECT control_points FROM district_control WHERE player_id = ? AND district_id = ?", 
        (player_id, district_id)
    )
    existing = cursor.fetchone()
    
    if existing:
        # Update existing control points
        new_points = max(0, existing[0] + points_change)  # Ensure points don't go below 0
        cursor.execute(
            "UPDATE district_control SET control_points = ?, last_action = ? WHERE player_id = ? AND district_id = ?",
            (new_points, datetime.datetime.now().isoformat(), player_id, district_id)
        )
    else:
        # Insert new control record
        points = max(0, points_change)  # Ensure points don't go below 0
        cursor.execute(
            "INSERT INTO district_control (district_id, player_id, control_points, last_action) VALUES (?, ?, ?, ?)",
            (district_id, player_id, points, datetime.datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()

def get_politician_info(politician_id=None, name=None):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    if politician_id:
        cursor.execute("SELECT * FROM politicians WHERE politician_id = ?", (politician_id,))
    elif name:
        cursor.execute("SELECT * FROM politicians WHERE name LIKE ?", (f"%{name}%",))
    else:
        conn.close()
        return None
    
    politician = cursor.fetchone()
    conn.close()
    return politician

def get_all_politicians(is_international=False):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM politicians WHERE is_international = ? ORDER BY name",
        (1 if is_international else 0,)
    )
    politicians = cursor.fetchall()
    conn.close()
    return politicians

def update_politician_friendliness(politician_id, player_id, change):
    # Todo: implement relationship tracking between players and politicians
    pass

def add_action(player_id, action_type, target_type, target_id, resources_used):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    
    # Determine current cycle
    current_time = now.time()
    if current_time >= MORNING_CYCLE_START and current_time < EVENING_CYCLE_START:
        cycle = "morning"
    else:
        cycle = "evening"
    
    cursor.execute(
        """
        INSERT INTO actions (player_id, action_type, target_type, target_id, resources_used, timestamp, cycle, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (player_id, action_type, target_type, target_id, json.dumps(resources_used), now.isoformat(), cycle)
    )
    
    action_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return action_id

def cancel_last_action(player_id):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    # Get the last pending action
    cursor.execute(
        """
        SELECT action_id, action_type, resources_used 
        FROM actions 
        WHERE player_id = ? AND status = 'pending' 
        ORDER BY timestamp DESC LIMIT 1
        """,
        (player_id,)
    )
    
    last_action = cursor.fetchone()
    
    if last_action:
        action_id, action_type, resources_used = last_action
        resources_used = json.loads(resources_used)
        
        # Delete the action
        cursor.execute("DELETE FROM actions WHERE action_id = ?", (action_id,))
        
        # Refund resources
        for resource_type, amount in resources_used.items():
            update_player_resources(player_id, resource_type, amount)  # Refund the resources
        
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def add_news(title, content, is_public=True, target_player_id=None, is_fake=False):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO news (title, content, timestamp, is_public, target_player_id, is_fake)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, content, now, is_public, target_player_id, is_fake)
    )
    
    news_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return news_id

def get_news(limit=5, player_id=None):
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    if player_id:
        cursor.execute(
            """
            SELECT * FROM news 
            WHERE is_public = 1 OR target_player_id = ? 
            ORDER BY timestamp DESC LIMIT ?
            """,
            (player_id, limit)
        )
    else:
        cursor.execute(
            "SELECT * FROM news WHERE is_public = 1 ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
    
    news = cursor.fetchall()
    conn.close()
    return news

def update_action_counts(player_id):
    """Reset action counts if it's been more than 3 hours since last refresh"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT last_action_refresh FROM players WHERE player_id = ?",
        (player_id,)
    )
    
    last_refresh = cursor.fetchone()[0]
    last_refresh_time = datetime.datetime.fromisoformat(last_refresh)
    now = datetime.datetime.now()
    
    # If it's been more than 3 hours
    if (now - last_refresh_time).total_seconds() > 3 * 60 * 60:
        cursor.execute(
            "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
            (now.isoformat(), player_id)
        )
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def use_action(player_id, is_main_action):
    """Decrement action count when player uses an action"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    if is_main_action:
        cursor.execute(
            "UPDATE players SET main_actions_left = main_actions_left - 1 WHERE player_id = ? AND main_actions_left > 0",
            (player_id,)
        )
    else:
        cursor.execute(
            "UPDATE players SET quick_actions_left = quick_actions_left - 1 WHERE player_id = ? AND quick_actions_left > 0",
            (player_id,)
        )
    
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return rows_affected > 0

def get_remaining_actions(player_id):
    """Get remaining actions for player"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT main_actions_left, quick_actions_left FROM players WHERE player_id = ?",
        (player_id,)
    )
    
    actions = cursor.fetchone()
    conn.close()
    
    if actions:
        return {"main": actions[0], "quick": actions[1]}
    return {"main": 0, "quick": 0}

def distribute_district_resources():
    """Distribute resources from controlled districts to players"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    # Get all districts that are controlled (60+ points)
    cursor.execute(
        """
        SELECT dc.district_id, dc.player_id, dc.control_points, 
               d.influence_resource, d.resources_resource, d.information_resource, d.force_resource
        FROM district_control dc
        JOIN districts d ON dc.district_id = d.district_id
        WHERE dc.control_points >= 60
        """
    )
    
    controlled_districts = cursor.fetchall()
    
    for district in controlled_districts:
        district_id, player_id, control_points, influence, resources, information, force = district
        
        # Update player resources
        if influence > 0:
            update_player_resources(player_id, "influence", influence)
        
        if resources > 0:
            update_player_resources(player_id, "resources", resources)
        
        if information > 0:
            update_player_resources(player_id, "information", information)
        
        if force > 0:
            update_player_resources(player_id, "force", force)
    
    conn.close()

# Game cycle management
async def process_game_cycle(context):
    """Process actions and update game state at the end of a cycle"""
    now = datetime.datetime.now().time()
    
    # Determine which cycle just ended
    if now.hour == MORNING_CYCLE_RESULTS.hour and now.minute == MORNING_CYCLE_RESULTS.minute:
        cycle = "morning"
    elif now.hour == EVENING_CYCLE_RESULTS.hour and now.minute == EVENING_CYCLE_RESULTS.minute:
        cycle = "evening"
    else:
        return
    
    # Process all pending actions for this cycle
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM actions WHERE status = 'pending' AND cycle = ?",
        (cycle,)
    )
    
    actions = cursor.fetchall()
    
    # Process each action
    for action in actions:
        action_id = action[0]
        player_id = action[1]
        action_type = action[2]
        target_type = action[3]
        target_id = action[4]
        
        # Process different action types
        result = process_action(action_id, player_id, action_type, target_type, target_id)
        
        # Update action status
        cursor.execute(
            "UPDATE actions SET status = 'completed', result = ? WHERE action_id = ?",
            (json.dumps(result), action_id)
        )
    
    # Apply decay to district control
    cursor.execute(
        "UPDATE district_control SET control_points = control_points - 5 WHERE control_points > 0"
    )
    
    # Distribute resources from controlled districts
    distribute_district_resources()
    
    # Process international politicians' actions
    process_international_politicians()
    
    conn.commit()
    conn.close()
    
    # Notify all players of results
    await notify_players_of_results(context, cycle)

def process_action(action_id, player_id, action_type, target_type, target_id):
    """Process a single action and return the result"""
    result = {}
    
    if target_type == "district":
        if action_type == ACTION_INFLUENCE:
            # Process influence action on district
            success_roll = random.randint(1, 100)
            
            if success_roll > 70:  # Success
                update_district_control(player_id, target_id, 10)
                result = {"status": "success", "message": f"Successfully increased influence in {target_id}", "control_change": 10}
            elif success_roll > 30:  # Partial success
                update_district_control(player_id, target_id, 5)
                result = {"status": "partial", "message": f"Partially increased influence in {target_id}", "control_change": 5}
            else:  # Failure
                result = {"status": "failure", "message": f"Failed to increase influence in {target_id}", "control_change": 0}
        
        elif action_type == ACTION_ATTACK:
            # Process attack action on district
            # Get current controlling player(s)
            control_data = get_district_control(target_id)
            
            if control_data:
                # Attack the player with the most control
                target_player_id = control_data[0][0]
                success_roll = random.randint(1, 100)
                
                if success_roll > 70:  # Success
                    # Reduce target player's control
                    update_district_control(target_player_id, target_id, -10)
                    # Increase attacking player's control
                    update_district_control(player_id, target_id, 10)
                    result = {
                        "status": "success", 
                        "message": f"Successfully attacked {target_id}", 
                        "target_player": target_player_id,
                        "target_control_change": -10,
                        "attacker_control_change": 10
                    }
                elif success_roll > 30:  # Partial success
                    update_district_control(target_player_id, target_id, -5)
                    update_district_control(player_id, target_id, 5)
                    result = {
                        "status": "partial", 
                        "message": f"Partially successful attack on {target_id}", 
                        "target_player": target_player_id,
                        "target_control_change": -5,
                        "attacker_control_change": 5
                    }
                else:  # Failure
                    result = {
                        "status": "failure", 
                        "message": f"Failed to attack {target_id}", 
                        "target_player": target_player_id,
                        "target_control_change": 0,
                        "attacker_control_change": 0
                    }
            else:
                # No one controls the district, so just add control points
                update_district_control(player_id, target_id, 10)
                result = {
                    "status": "success", 
                    "message": f"Claimed uncontrolled district {target_id}", 
                    "attacker_control_change": 10
                }
        
        elif action_type == ACTION_DEFENSE:
            # Process defense action - will be used to reduce impact of attacks
            result = {"status": "active", "message": f"Defensive measures in place for {target_id}"}
        
        elif action_type == QUICK_ACTION_RECON:
            # Process reconnaissance action
            control_data = get_district_control(target_id)
            district_info = get_district_info(target_id)
            
            result = {
                "status": "success",
                "message": f"Reconnaissance of {target_id} complete",
                "control_data": control_data,
                "district_info": district_info
            }
        
        elif action_type == QUICK_ACTION_SUPPORT:
            # Process support action (small influence gain)
            update_district_control(player_id, target_id, 5)
            result = {"status": "success", "message": f"Support action in {target_id} complete", "control_change": 5}
    
    elif target_type == "politician":
        if action_type == ACTION_INFLUENCE:
            # Process influence on politician
            politician = get_politician_info(politician_id=target_id)
            if politician:
                # Update friendliness
                # This is simplified - in a real game you'd track per-player relationships
                result = {
                    "status": "success",
                    "message": f"Improved relationship with {politician[1]}",
                    "politician": politician[1]
                }
    
    return result

def process_international_politicians():
    """Process actions by international politicians"""
    # Choose 1-3 random international politicians to activate
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT politician_id, name FROM politicians WHERE is_international = 1")
    international_politicians = cursor.fetchall()
    
    num_active = random.randint(1, 3)
    active_politicians = random.sample(international_politicians, min(num_active, len(international_politicians)))
    
    activated_events = []
    
    for politician_id, name in active_politicians:
        # Process this politician's action
        event = process_international_politician_action(politician_id)
        if event:
            activated_events.append(event)
    
    conn.close()
    return activated_events

def process_international_politician_action(politician_id):
    """Process a specific international politician's action"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM politicians WHERE politician_id = ?", (politician_id,))
    politician = cursor.fetchone()
    
    if not politician:
        conn.close()
        return None
    
    pol_id, name, role, ideology, district_id, influence, friendliness, is_intl, description = politician
    
    # Different effects based on politician's ideology
    news_title = f"International News: {name} Takes Action"
    
    # Track what action was performed
    event_details = {
        "politician_id": politician_id,
        "name": name,
        "role": role, 
        "ideology": ideology,
        "effect_type": "",
        "effect_description": ""
    }
    
    if ideology < -3:  # Strongly pro-reform
        # Apply sanctions or support opposition
        news_content = f"{name} ({role}) has announced sanctions against the current regime. Districts supporting conservative policies will receive a penalty to control."
        
        # Apply penalties to conservative districts
        cursor.execute(
            """
            UPDATE district_control 
            SET control_points = CASE WHEN control_points > 5 THEN control_points - 5 ELSE control_points END
            WHERE district_id IN (
                SELECT district_id FROM districts 
                JOIN politicians ON districts.district_id = politicians.district_id
                WHERE politicians.ideology_score > 3 AND politicians.is_international = 0
            )
            """
        )
        
        event_details["effect_type"] = "sanctions"
        event_details["effect_description"] = "Applied sanctions against conservative districts"
    
    elif ideology > 3:  # Strongly conservative
        # Support status quo or destabilize
        news_content = f"{name} ({role}) has pledged support for stability and traditional governance. Districts with reform movements will face challenges."
        
        # Apply penalties to reform districts
        cursor.execute(
            """
            UPDATE district_control 
            SET control_points = CASE WHEN control_points > 5 THEN control_points - 5 ELSE control_points END
            WHERE district_id IN (
                SELECT district_id FROM districts 
                JOIN politicians ON districts.district_id = politicians.district_id
                WHERE politicians.ideology_score < -3 AND politicians.is_international = 0
            )
            """
        )
        
        event_details["effect_type"] = "conservative_support"
        event_details["effect_description"] = "Applied pressure against reform districts"
    
    else:  # Moderate influence
        effect_type = random.choice(["economic", "diplomatic", "humanitarian"])
        
        if effect_type == "economic":
            news_content = f"{name} ({role}) has announced economic support for moderate districts in Yugoslavia."
            
            # Apply bonuses to moderate districts
            cursor.execute(
                """
                UPDATE district_control 
                SET control_points = control_points + 3
                WHERE district_id IN (
                    SELECT district_id FROM districts 
                    JOIN politicians ON districts.district_id = politicians.district_id
                    WHERE politicians.ideology_score BETWEEN -2 AND 2 AND politicians.is_international = 0
                )
                """
            )
            
            event_details["effect_type"] = "economic_support"
            event_details["effect_description"] = "Provided economic support to moderate districts"
            
        elif effect_type == "diplomatic":
            news_content = f"{name} ({role}) has applied diplomatic pressure for peaceful resolution of tensions in Yugoslavia."
            
            # Generate random diplomatic event
            event_details["effect_type"] = "diplomatic_pressure"
            event_details["effect_description"] = "Applied diplomatic pressure"
            
        else:  # humanitarian
            news_content = f"{name} ({role}) has announced humanitarian aid to affected regions in Yugoslavia."
            
            # Small bonus to all districts
            cursor.execute(
                """
                UPDATE district_control 
                SET control_points = control_points + 2
                """
            )
            
            event_details["effect_type"] = "humanitarian_aid"
            event_details["effect_description"] = "Provided humanitarian aid to all districts"
    
    # Add news about this action
    add_news(news_title, news_content)
    
    conn.commit()
    conn.close()
    
    return event_details

async def notify_players_of_results(context, cycle):
    """Send notifications to all players about cycle results"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    # Get all active players
    cursor.execute("SELECT player_id FROM players")
    players = cursor.fetchall()
    
    for player_id_tuple in players:
        player_id = player_id_tuple[0]
        
        # Get player's districts
        player_districts = get_player_districts(player_id)
        
        # Get news
        recent_news = get_news(limit=3, player_id=player_id)
        
        # Get player's completed actions in this cycle
        cursor.execute(
            """
            SELECT action_type, target_type, target_id, result
            FROM actions
            WHERE player_id = ? AND cycle = ? AND status = 'completed'
            """,
            (player_id, cycle)
        )
        actions = cursor.fetchall()
        
        # Create message
        message = f"📊 *{cycle.capitalize()} Cycle Results*\n\n"
        
        if actions:
            message += "*Your Actions:*\n"
            for action in actions:
                action_type, target_type, target_id, result_json = action
                result = json.loads(result_json)
                status = result.get('status', 'unknown')
                action_msg = result.get('message', 'No details available')
                
                # Format based on status
                if status == 'success':
                    status_emoji = "✅"
                elif status == 'partial':
                    status_emoji = "⚠️"
                elif status == 'failure':
                    status_emoji = "❌"
                else:
                    status_emoji = "ℹ️"
                
                message += f"{status_emoji} {action_type.capitalize()} - {action_msg}\n"
            
            message += "\n"
        
        # District control summary
        if player_districts:
            message += "*Your Districts:*\n"
            for district in player_districts:
                district_id, name, control = district
                
                # Determine control status
                if control >= 80:
                    control_status = "🔒 Strong control"
                elif control >= 60:
                    control_status = "✅ Controlled"
                elif control >= 20:
                    control_status = "⚠️ Contested"
                else:
                    control_status = "❌ Weak presence"
                
                message += f"{name}: {control} points - {control_status}\n"
            
            message += "\n"
        
        # News summary
        if recent_news:
            message += "*Recent News:*\n"
            for news_item in recent_news:
                news_id, title, content, timestamp, is_public, target_player, is_fake = news_item
                news_time = datetime.datetime.fromisoformat(timestamp).strftime("%H:%M")
                
                message += f"📰 {news_time} - *{title}*\n"
                # Truncate long content
                if len(content) > 100:
                    message += f"{content[:100]}...\n"
                else:
                    message += f"{content}\n"
            
            message += "\n"
        
        # Resources update
        resources = get_player_resources(player_id)
        if resources:
            message += "*Current Resources:*\n"
            message += f"🔵 Influence: {resources['influence']}\n"
            message += f"💰 Resources: {resources['resources']}\n"
            message += f"🔍 Information: {resources['information']}\n"
            message += f"👊 Force: {resources['force']}\n"
        
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send notification to player {player_id}: {e}")
    
    conn.close()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation and ask for player name."""
    user = update.effective_user
    register_player(user.id, user.username)
    
    # Default to English for new users
    lang = "en"
    
    await update.message.reply_text(
        get_text("welcome", lang, user_name=user.first_name)
    )
    
    return "WAITING_NAME"

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the player's character name."""
    user = update.effective_user
    character_name = update.message.text.strip()
    
    # Default to English for new users
    lang = "en"
    
    if not character_name:
        await update.message.reply_text(get_text("invalid_name", lang))
        return "WAITING_NAME"
    
    set_player_name(user.id, character_name)
    
    await update.message.reply_text(
        get_text("name_set", lang, character_name=character_name)
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    await update.message.reply_text(get_text("operation_cancelled", lang))
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display help message with available commands."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    help_text = (
        f"*{get_text('help_title', lang)}*\n\n"
        f"{get_text('help_basic', lang)}\n\n"
        f"{get_text('help_action', lang)}\n\n"
        f"{get_text('help_resource', lang)}\n\n"
        f"{get_text('help_political', lang)}\n\n"
        f"{get_text('help_footer', lang)}"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display player's current status."""
    user = update.effective_user
    lang = get_player_language(user.id)
    player = get_player(user.id)
    
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return
    
    character_name = player[2] or "Unnamed"
    ideology_score = player[3]
    
    resources = get_player_resources(user.id)
    districts = get_player_districts(user.id)
    actions = get_remaining_actions(user.id)
    
    # Format ideology using helper function
    ideology = format_ideology(ideology_score, lang)
    
    status_text = (
        f"*{get_text('status_title', lang, character_name=character_name)}*\n"
        f"{get_text('status_ideology', lang, ideology=ideology, score=ideology_score)}\n\n"
        
        f"{get_text('status_resources', lang, influence=resources['influence'], resources=resources['resources'], information=resources['information'], force=resources['force'])}\n\n"
        
        f"{get_text('status_actions', lang, main=actions['main'], quick=actions['quick'])}\n\n"
    )
    
    if districts:
        status_text += f"{get_text('status_districts', lang)}\n"
        for district in districts:
            district_id, name, control = district
            
            # Determine control status based on control points
            if control >= 80:
                control_status = get_text("control_strong", lang)
            elif control >= 60:
                control_status = get_text("control_full", lang)
            elif control >= 20:
                control_status = get_text("control_contested", lang)
            else:
                control_status = get_text("control_weak", lang)
            
            status_text += f"{name}: {control} {get_text('control_points', lang, count=control)} - {control_status}\n"
    else:
        status_text += f"{get_text('status_no_districts', lang)}\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current game map."""
    # In a real implementation, this would generate or link to a visual map
    # For now, just show a text summary of district control
    
    districts = get_all_districts()
    map_text = "*Current Control Map of Belgrade*\n\n"
    
    for district in districts:
        district_id, name, description, *_ = district
        control_data = get_district_control(district_id)
        
        map_text += f"*{name}* - {description}\n"
        
        if control_data:
            # Sort by control points (highest first)
            control_data.sort(key=lambda x: x[1], reverse=True)
            
            for player_id, control_points, player_name in control_data:
                if control_points > 0:
                    # Determine control status
                    if control_points >= 80:
                        control_status = "🔒"
                    elif control_points >= 60:
                        control_status = "✅"
                    elif control_points >= 20:
                        control_status = "⚠️"
                    else:
                        control_status = "❌"
                    
                    map_text += f"  {control_status} {player_name}: {control_points} points\n"
        else:
            map_text += "  No control established\n"
        
        map_text += "\n"
    
    map_text += "Legend:\n🔒 Strong control (80+ points)\n✅ Controlled (60-79 points)\n⚠️ Contested (20-59 points)\n❌ Weak presence (<20 points)"
    
    # If this is too long for one message, you might need to split it
    if len(map_text) > 4000:
        await update.message.reply_text("The map is being generated. Check the web UI for details.")
    else:
        await update.message.reply_text(map_text, parse_mode='Markdown')

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current game cycle and time until next phase."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    now = datetime.datetime.now()
    current_time = now.time()
    
    # Determine current cycle
    if current_time >= MORNING_CYCLE_START and current_time < EVENING_CYCLE_START:
        current_cycle = get_cycle_name("morning", lang)
        next_deadline = datetime.datetime.combine(now.date(), MORNING_CYCLE_DEADLINE)
        next_results = datetime.datetime.combine(now.date(), MORNING_CYCLE_RESULTS)
    else:
        current_cycle = get_cycle_name("evening", lang)
        next_deadline = datetime.datetime.combine(now.date(), EVENING_CYCLE_DEADLINE)
        next_results = datetime.datetime.combine(now.date(), EVENING_CYCLE_RESULTS)
    
    # If we're past the evening deadline, the next is morning of next day
    if current_time >= EVENING_CYCLE_DEADLINE:
        tomorrow = now.date() + datetime.timedelta(days=1)
        next_deadline = datetime.datetime.combine(tomorrow, MORNING_CYCLE_DEADLINE)
        next_results = datetime.datetime.combine(tomorrow, MORNING_CYCLE_RESULTS)
    
    # Calculate time remaining
    if now > next_deadline:
        time_to_deadline = get_text("deadline_passed", lang)
        time_to_results = str(int((next_results - now).total_seconds() / 60)) + " " + get_text("minutes", lang)
    else:
        time_to_deadline = str(int((next_deadline - now).total_seconds() / 60)) + " " + get_text("minutes", lang)
        time_to_results = str(int((next_results - now).total_seconds() / 60)) + " " + get_text("minutes", lang)
    
    time_text = (
        f"*{get_text('time_info', lang)}*\n\n"
        f"{get_text('time_current', lang, cycle=current_cycle)}\n\n"
        f"{get_text('time_deadlines', lang, deadline=time_to_deadline, results=time_to_results)}\n\n"
        f"{get_text('time_schedule', lang)}\n\n"
        f"{get_text('time_refresh', lang)}"
    )
    
    await update.message.reply_text(time_text, parse_mode='Markdown')

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent news."""
    user = update.effective_user
    lang = get_player_language(user.id)
    news_items = get_news(limit=5, player_id=user.id)
    
    if not news_items:
        await update.message.reply_text(get_text("no_news", lang))
        return
    
    news_text = f"*{get_text('news_title', lang)}*\n\n"
    
    for news_item in news_items:
        news_id, title, content, timestamp, is_public, target_player, is_fake = news_item
        news_time = datetime.datetime.fromisoformat(timestamp).strftime("%d/%m %H:%M")
        
        news_text += f"*{title}* - {news_time}\n"
        news_text += f"{content}\n\n"
    
    await update.message.reply_text(news_text, parse_mode='Markdown')

# Action submission handlers
async def action_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main action submission."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    # Check if player has actions left
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        await update.message.reply_text(get_text("no_main_actions", lang))
        return
    
    # Show action types for selection
    keyboard = [
        [InlineKeyboardButton(get_text("action_influence", lang), callback_data=f"action_type:{ACTION_INFLUENCE}")],
        [InlineKeyboardButton(get_text("action_attack", lang), callback_data=f"action_type:{ACTION_ATTACK}")],
        [InlineKeyboardButton(get_text("action_defense", lang), callback_data=f"action_type:{ACTION_DEFENSE}")],
        [InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text("select_action_type", lang),
        reply_markup=reply_markup
    )

async def quick_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quick action submission."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    # Check if player has actions left
    actions = get_remaining_actions(user.id)
    if actions['quick'] <= 0:
        await update.message.reply_text(get_text("no_quick_actions", lang))
        return
    
    # Show action types for selection
    keyboard = [
        [InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"quick_action_type:{QUICK_ACTION_RECON}")],
        [InlineKeyboardButton(get_text("action_info", lang), callback_data=f"quick_action_type:{QUICK_ACTION_INFO}")],
        [InlineKeyboardButton(get_text("action_support", lang), callback_data=f"quick_action_type:{QUICK_ACTION_SUPPORT}")],
        [InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        get_text("select_quick_action", lang),
        reply_markup=reply_markup
    )

async def cancel_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the last pending action."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    if cancel_last_action(user.id):
        await update.message.reply_text(get_text("action_cancelled", lang))
    else:
        await update.message.reply_text(get_text("no_pending_actions", lang))

async def actions_left_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show remaining actions."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    # Check if actions should refresh
    updated = update_action_counts(user.id)
    
    actions = get_remaining_actions(user.id)
    
    if updated:
        await update.message.reply_text(
            get_text("actions_refreshed", lang, main=actions['main'], quick=actions['quick'])
        )
    else:
        await update.message.reply_text(
            get_text("current_actions", lang, main=actions['main'], quick=actions['quick'])
        )

async def view_district_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View information about a district."""
    args = context.args
    
    if not args:
        # Show list of districts to select from
        districts = get_all_districts()
        keyboard = []
        
        for district in districts:
            district_id, name, *_ = district
            keyboard.append([InlineKeyboardButton(name, callback_data=f"view_district:{district_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Select a district to view:",
            reply_markup=reply_markup
        )
        return
    
    district_name = ' '.join(args)
    
    # Try to find the district by name
    districts = get_all_districts()
    district_id = None
    
    for district in districts:
        d_id, name, *_ = district
        if name.lower() == district_name.lower():
            district_id = d_id
            break
    
    if district_id:
        await show_district_info(update, district_id)
    else:
        await update.message.reply_text(
            f"District '{district_name}' not found. Use /view_district without arguments to see a list of districts."
        )

async def show_district_info(update, district_id):
    """Show detailed information about a district."""
    district = get_district_info(district_id)
    
    if not district:
        await update.message.reply_text("District not found.")
        return
    
    district_id, name, description, influence_res, resources_res, info_res, force_res = district
    
    # Get control information
    control_data = get_district_control(district_id)
    
    # Get politicians in the district
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, role, ideology_score, influence FROM politicians WHERE district_id = ?", 
        (district_id,)
    )
    politicians = cursor.fetchall()
    conn.close()
    
    district_text = (
        f"*{name}*\n"
        f"{description}\n\n"
        
        f"*Resources Provided (when controlled):*\n"
        f"🔵 Influence: {influence_res}\n"
        f"💰 Resources: {resources_res}\n"
        f"🔍 Information: {info_res}\n"
        f"👊 Force: {force_res}\n\n"
    )
    
    if politicians:
        district_text += "*Key Politicians:*\n"
        for politician in politicians:
            pol_name, role, ideology, influence = politician
            
            # Format ideology
            if ideology > 3:
                ideology_desc = "Strongly Conservative"
            elif ideology > 0:
                ideology_desc = "Conservative"
            elif ideology == 0:
                ideology_desc = "Neutral"
            elif ideology > -3:
                ideology_desc = "Reformist"
            else:
                ideology_desc = "Strongly Reformist"
            
            district_text += f"• {pol_name} - {role}\n"
            district_text += f"  Ideology: {ideology_desc} ({ideology}), Influence: {influence}\n"
        
        district_text += "\n"
    
    if control_data:
        district_text += "*Current Control:*\n"
        for player_id, control_points, player_name in control_data:
            if control_points > 0:
                # Determine control status
                if control_points >= 80:
                    control_status = "🔒 Strong control"
                elif control_points >= 60:
                    control_status = "✅ Controlled"
                elif control_points >= 20:
                    control_status = "⚠️ Contested"
                else:
                    control_status = "❌ Weak presence"
                
                district_text += f"• {player_name}: {control_points} points - {control_status}\n"
    else:
        district_text += "*Current Control:* No one has established control yet.\n"
    
    keyboard = [
        [
            InlineKeyboardButton("Influence", callback_data=f"action_influence:{district_id}"),
            InlineKeyboardButton("Attack", callback_data=f"action_attack:{district_id}")
        ],
        [
            InlineKeyboardButton("Defend", callback_data=f"action_defend:{district_id}"),
            InlineKeyboardButton("Recon", callback_data=f"quick_recon:{district_id}")
        ],
        [
            InlineKeyboardButton("Support", callback_data=f"quick_support:{district_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(district_text, parse_mode='Markdown', reply_markup=reply_markup)

# Callback query handler for inline keyboard buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user = query.from_user
    
    # Handle language selection
    if callback_data.startswith("lang:"):
        language = callback_data.split(":")[1]
        set_player_language(user.id, language)
        
        # Confirm language change in the selected language
        response_text = get_text("language_changed", language)
        await query.edit_message_text(response_text)
        return
    
    # Get player's language preference for all other callbacks
    lang = get_player_language(user.id)
    
    # Handle action type selection
    if callback_data.startswith("action_type:"):
        action_type = callback_data.split(":")[1]
        context.user_data['action_type'] = action_type
        
        # Now show districts to select as target
        await show_district_selection(query, get_text("select_district", lang))
    
    # Handle quick action type selection
    elif callback_data.startswith("quick_action_type:"):
        action_type = callback_data.split(":")[1]
        context.user_data['quick_action_type'] = action_type
        
        # Different targets based on quick action type
        if action_type in [QUICK_ACTION_RECON, QUICK_ACTION_SUPPORT]:
            await show_district_selection(query, get_text("select_district", lang))
        elif action_type == QUICK_ACTION_INFO:
            await query.edit_message_text(
                get_text("enter_info_content", lang, default="What information do you want to spread? Please type your message:")
            )
            return "WAITING_INFO_CONTENT"
    
    # Handle district selection for main actions
    elif callback_data.startswith("district_select:"):
        district_id = callback_data.split(":")[1]
        
        if 'action_type' in context.user_data:
            # For main action
            action_type = context.user_data['action_type']
            await show_resource_selection(query, action_type, district_id)
        elif 'quick_action_type' in context.user_data:
            # For quick action
            action_type = context.user_data['quick_action_type']
            await process_quick_action(query, action_type, "district", district_id)
    
    # Direct action buttons from district view
    elif callback_data.startswith(("action_influence:", "action_attack:", "action_defend:")):
        parts = callback_data.split(":")
        action_type = parts[0].replace("action_", "")
        district_id = parts[1]
        
        context.user_data['action_type'] = action_type
        await show_resource_selection(query, action_type, district_id)
    
    elif callback_data.startswith(("quick_recon:", "quick_support:")):
        parts = callback_data.split(":")
        action_type = parts[0].replace("quick_", "")
        district_id = parts[1]
        
        context.user_data['quick_action_type'] = action_type
        await process_quick_action(query, action_type, "district", district_id)
    
    # Handle resource selection
    elif callback_data.startswith("resources:"):
        parts = callback_data.split(":")
        action_type = parts[1]
        target_type = parts[2]
        target_id = parts[3]
        resources = parts[4].split(",")
        
        await process_main_action(query, action_type, target_type, target_id, resources)
    
    # Handle view district
    elif callback_data.startswith("view_district:"):
        district_id = callback_data.split(":")[1]
        await show_district_info(query, district_id)
    
    # Handle view politician
    elif callback_data.startswith("view_politician:"):
        politician_id = int(callback_data.split(":")[1])
        await show_politician_info(query, politician_id)
    
    # Handle politician actions
    elif callback_data.startswith("pol_influence:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_influence(query, politician_id)
    
    elif callback_data.startswith("pol_info:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_info(query, politician_id)
    
    elif callback_data.startswith("pol_undermine:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_undermine(query, politician_id)
    
    # Handle cancellation
    elif callback_data == "action_cancel":
        await query.edit_message_text("Action cancelled.")
    
    else:
        await query.edit_message_text(f"Unrecognized callback: {callback_data}")

async def show_district_selection(query, message):
    """Show districts for selection."""
    user = query.from_user
    lang = get_player_language(user.id)
    
    districts = get_all_districts()
    keyboard = []
    
    for district in districts:
        district_id, name, *_ = district
        keyboard.append([InlineKeyboardButton(name, callback_data=f"district_select:{district_id}")])
    
    keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup
    )

async def show_resource_selection(query, action_type, district_id):
    """Show resource selection for an action."""
    user = query.from_user
    lang = get_player_language(user.id)
    resources = get_player_resources(user.id)
    
    district = get_district_info(district_id)
    district_name = district[1] if district else district_id
    
    # Translate action type
    action_type_name = get_text(f"action_{action_type}", lang, default=action_type)
    
    message = get_text("select_resources", lang, action_type=action_type_name, district_name=district_name)
    
    # Create resource selection options based on action type
    keyboard = []
    
    if action_type == ACTION_INFLUENCE:
        # Influence action typically uses Influence and Resources
        if resources['influence'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('influence', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:influence")])
        if resources['resources'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('resources', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:resources")])
        if resources['influence'] >= 1 and resources['resources'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('influence', lang)} + 1 {get_resource_name('resources', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:influence,resources")])
    
    elif action_type == ACTION_ATTACK:
        # Attack action typically uses Force and Information
        if resources['force'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('force', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:force")])
        if resources['information'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('information', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:information")])
        if resources['force'] >= 1 and resources['information'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('force', lang)} + 1 {get_resource_name('information', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:force,information")])
    
    elif action_type == ACTION_DEFENSE:
        # Defense action can use various resources
        if resources['force'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('force', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:force")])
        if resources['influence'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('influence', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:influence")])
        if resources['force'] >= 1 and resources['influence'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('force', lang)} + 1 {get_resource_name('influence', lang)}", 
                                                callback_data=f"resources:{action_type}:district:{district_id}:force,influence")])
    
    keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)