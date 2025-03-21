import sqlite3
import logging
import datetime
import json
from functools import wraps
import time
import os
import random
from db.utils import get_db_connection, release_db_connection
import uuid

# Define action constants locally to avoid circular import
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defense"

logger = logging.getLogger(__name__)

# Constants for database configuration
DB_PATH = os.environ.get('GAME_DB_PATH', 'novi_sad_game.db')
MAX_RETRIES = int(os.environ.get('DB_MAX_RETRIES', '5'))
RETRY_BASE_DELAY = float(os.environ.get('DB_RETRY_BASE_DELAY', '0.5'))
DB_BUSY_TIMEOUT = int(os.environ.get('DB_BUSY_TIMEOUT', '5000'))

def db_transaction(func):
    """
    Decorator to handle database transactions with proper error handling and concurrency management.
    Uses connection pooling, transaction isolation, and exponential backoff.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        
        # Get the function name for better logging
        func_name = func.__name__
        
        # If the connection is already provided as first arg, use it
        if args and isinstance(args[0], sqlite3.Connection):
            # Function already received a connection object, just use it
            return func(*args, **kwargs)
        
        # Get a connection from the pool
        conn = get_db_connection()
        transaction_started = False
        
        try:
            # Check if a transaction is already active
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM sqlite_master LIMIT 1")
                in_transaction = conn.in_transaction
            except Exception as e:
                logger.debug(f"Error checking transaction state: {e}")
                in_transaction = False
            
            # Begin transaction if not already in one
            if not in_transaction:
                try:
                    conn.execute('BEGIN IMMEDIATE')
                    transaction_started = True
                    logger.debug(f"Started new transaction in {func_name}")
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e).lower():
                        logger.warning(f"Database locked in {func_name}, retrying...")
                        time.sleep(0.1)  # Brief sleep before retry
                        conn.execute('BEGIN IMMEDIATE')
                        transaction_started = True
                    else:
                        raise
            else:
                logger.debug(f"Reusing existing transaction in {func_name}")
            
            # Call the function with the connection as first arg
            result = func(conn, *args, **kwargs)
            
            # Commit changes only if we started the transaction
            if transaction_started:
                try:
                    conn.commit()
                    logger.debug(f"Transaction committed in {func_name}")
                except sqlite3.OperationalError as e:
                    if "cannot commit" in str(e).lower():
                        logger.warning(f"Cannot commit in {func_name}: {e}")
                        # Transaction may have been auto-committed or rolled back
                        pass
                    else:
                        raise
            
            return result
            
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            logger.error(f"Database operational error in {func_name}: {e}")
            
            # Only rollback if we started a transaction
            if transaction_started:
                try:
                    conn.rollback()
                    logger.debug(f"Transaction rolled back in {func_name}")
                except Exception as rollback_error:
                    logger.warning(f"Rollback failed in {func_name}: {rollback_error}")
            
            raise
            
        except sqlite3.IntegrityError as e:
            # Only rollback if we started a transaction
            if transaction_started:
                try:
                    conn.rollback()
                    logger.debug(f"Transaction rolled back in {func_name} due to integrity error")
                except Exception:
                    pass
            
            # Log the integrity error with detailed information
            logger.error(f"Database integrity error in {func_name}: {e}")
            raise
            
        except Exception as e:
            # Only rollback if we started a transaction
            if transaction_started:
                try:
                    conn.rollback()
                    logger.debug(f"Transaction rolled back in {func_name} due to exception")
                except Exception:
                    pass
            
            logger.error(f"Unexpected error in {func_name}: {e}")
            raise
            
        finally:
            # Release the connection back to the pool
            if conn is not None and conn != args[0] if args else None:
                release_db_connection(conn)
    
    return wrapper


# Player-related queries
@db_transaction
def get_player(conn, player_id):
    """Get player information by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    player = cursor.fetchone()
    return player


@db_transaction
def register_player(conn, player_id, username, language="en"):
    """Register a new player."""
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

        return True
    return False


@db_transaction
def set_player_name(conn, player_id, character_name):
    """Set player's character name."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET character_name = ? WHERE player_id = ?",
        (character_name, player_id)
    )
    return cursor.rowcount > 0


@db_transaction
def get_player_language(conn, player_id):
    """Get player's preferred language."""
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    return result[0] if result else "en"


@db_transaction
def get_player_name(conn, player_id):
    """Get player's character name."""
    cursor = conn.cursor()
    cursor.execute("SELECT character_name, username FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    if not result:
        return None
    # Return character_name if it exists, otherwise return username
    return result[0] if result[0] else result[1]


@db_transaction
def set_player_language(conn, player_id, language):
    """Set player's preferred language."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET language = ? WHERE player_id = ?",
        (language, player_id)
    )
    return cursor.rowcount > 0


@db_transaction
def update_player_resources(conn, player_id, resource_type, amount):
    """Update player's resources."""
    cursor = conn.cursor()

    # Get current resource amount
    cursor.execute(f"SELECT {resource_type} FROM resources WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()

    if result is None:
        # Player doesn't exist in resources table
        logger.error(f"Player {player_id} not found in resources table")
        return 0

    current = result[0]

    # Update resource
    new_amount = current + amount
    if new_amount < 0:
        new_amount = 0

    cursor.execute(
        f"UPDATE resources SET {resource_type} = ? WHERE player_id = ?",
        (new_amount, player_id)
    )

    # Make sure the change is committed
    conn.commit()

    return new_amount


@db_transaction
def get_player_resources(conn, player_id):
    """Get player's current resources."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources WHERE player_id = ?", (player_id,))
    resources = cursor.fetchone()

    if resources:
        return {
            "influence": resources[1],
            "resources": resources[2],
            "information": resources[3],
            "force": resources[4]
        }
    return None


@db_transaction
def exchange_resources(conn, player_id, from_resource, to_resource, amount):
    """
    Exchange resources from one type to another.
    
    Args:
        conn: Database connection
        player_id: Player ID
        from_resource: Source resource type
        to_resource: Target resource type
        amount: Amount to convert to target resource
        
    Returns:
        dict: Updated resources or None if exchange failed
    """
    # Get current resources
    resources = get_player_resources(conn, player_id)
    if not resources:
        return None
    
    # Calculate required amount (2:1 ratio by default)
    required_amount = amount * 2
    
    # Check if player has enough resources
    if resources[from_resource] < required_amount:
        return None
    
    # Update resources
    update_player_resources(conn, player_id, from_resource, -required_amount)
    update_player_resources(conn, player_id, to_resource, amount)
    
    # Return updated resources
    return get_player_resources(conn, player_id)


# District-related queries
@db_transaction
def get_district_info(conn, district_id):
    """Get district information by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM districts WHERE district_id = ?", (district_id,))
    return cursor.fetchone()


@db_transaction
def get_all_districts(conn):
    """Get all districts."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM districts")
    return cursor.fetchall()


@db_transaction
def get_district_control(conn, district_id):
    """Get control information for a district."""
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
    return cursor.fetchall()


@db_transaction
def get_player_districts(conn, player_id):
    """Get districts controlled by a player."""
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
    return cursor.fetchall()


@db_transaction
def update_district_control(conn, player_id, district_id, points_change):
    """Update district control points."""
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
    return True


# Politician-related queries
@db_transaction
def get_politician_info(conn, politician_id=None, name=None):
    """Get politician information by ID or name."""
    cursor = conn.cursor()

    if politician_id:
        cursor.execute("SELECT * FROM politicians WHERE politician_id = ?", (politician_id,))
    elif name:
        cursor.execute("SELECT * FROM politicians WHERE name LIKE ?", (f"%{name}%",))
    else:
        return None

    return cursor.fetchone()


@db_transaction
def get_all_politicians(conn, is_international=False):
    """Get all politicians (local or international)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM politicians WHERE is_international = ? ORDER BY name",
        (1 if is_international else 0,)
    )
    return cursor.fetchall()


@db_transaction
def update_politician_friendliness(conn, politician_id, player_id, change):
    """Update the friendliness level between a player and a politician."""
    cursor = conn.cursor()

    # Check if the relationship exists, if not, create it
    cursor.execute(
        """
        INSERT OR IGNORE INTO politician_relationships 
        (politician_id, player_id, friendliness, last_interaction, interaction_count) 
        VALUES (?, ?, 50, ?, 0)
        """,
        (politician_id, player_id, datetime.datetime.now().isoformat())
    )

    # Update the relationship
    cursor.execute(
        """
        UPDATE politician_relationships
        SET 
            friendliness = MAX(0, MIN(100, friendliness + ?)),
            last_interaction = ?,
            interaction_count = interaction_count + 1
        WHERE politician_id = ? AND player_id = ?
        """,
        (change, datetime.datetime.now().isoformat(), politician_id, player_id)
    )

    # Get the updated relationship
    cursor.execute(
        """
        SELECT friendliness, interaction_count, last_interaction
        FROM politician_relationships
        WHERE politician_id = ? AND player_id = ?
        """,
        (politician_id, player_id)
    )
    relationship = cursor.fetchone()

    # Update the global politician friendliness
    cursor.execute(
        """
        UPDATE politicians
        SET friendliness = (
            SELECT AVG(friendliness) 
            FROM politician_relationships 
            WHERE politician_id = ?
        )
        WHERE politician_id = ?
        """,
        (politician_id, politician_id)
    )

    # Return detailed relationship information
    if relationship:
        friendliness, interaction_count, last_interaction = relationship
        return {
            "politician_id": politician_id,
            "player_id": player_id,
            "friendliness": friendliness,
            "interaction_count": interaction_count,
            "last_interaction": last_interaction,
            "change": change
        }
    return None


# Action-related queries
@db_transaction
def add_action(conn, player_id, action_type, target_type, target_id, resources_used):
    """Add a new action."""
    cursor = conn.cursor()

    now = datetime.datetime.now()

    # Determine current cycle
    current_time = now.time()
    if datetime.time(6, 0) <= current_time < datetime.time(13, 1):
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
    return cursor.lastrowid


@db_transaction
def cancel_last_action(conn, player_id):
    """Cancel the last pending action and refund resources."""
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
            # The resources_used has negative values (e.g., -1), so we negate it to refund
            update_player_resources_internal(conn, player_id, resource_type, -amount)
        return True
    return False


# Helper function for internal use within the module
def update_player_resources_internal(conn, player_id, resource_type, amount):
    """Update player resources (internal function without transaction)."""
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
    return new_amount


@db_transaction
def get_remaining_actions(conn, player_id):
    """Get remaining actions for player."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT main_actions_left, quick_actions_left FROM players WHERE player_id = ?",
        (player_id,)
    )
    actions = cursor.fetchone()
    if actions:
        return {"main": actions[0], "quick": actions[1]}
    return {"main": 0, "quick": 0}


@db_transaction
def use_action(conn, player_id, is_main_action):
    """Decrement action count when player uses an action."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()

    field = "main_actions_left" if is_main_action else "quick_actions_left"
    timestamp_field = "last_main_action_refresh" if is_main_action else "last_quick_action_refresh"

    # Check for last_main_action_refresh and last_quick_action_refresh columns
    cursor.execute("PRAGMA table_info(players)")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Use legacy field if new columns don't exist
    if 'last_main_action_refresh' not in columns or 'last_quick_action_refresh' not in columns:
        timestamp_field = "last_action_refresh"

    # Check if player has actions left
    cursor.execute(
        f"SELECT {field} FROM players WHERE player_id = ?",
        (player_id,)
    )
    actions_left = cursor.fetchone()

    if not actions_left or actions_left[0] <= 0:
        logger.warning(f"Player {player_id} has no {'main' if is_main_action else 'quick'} actions left")
        return False

    # Update the appropriate action count and timestamp
    cursor.execute(
        f"UPDATE players SET {field} = {field} - 1, {timestamp_field} = ? WHERE player_id = ? AND {field} > 0",
        (now, player_id)
    )

    result = cursor.rowcount > 0
    logger.info(f"{'Main' if is_main_action else 'Quick'} action usage result for player {player_id}: {result}")

    return result


@db_transaction
def refresh_player_actions(conn, player_id):
    """Reset action counts and update refresh timestamp."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    
    # Check for last_main_action_refresh and last_quick_action_refresh columns
    cursor.execute("PRAGMA table_info(players)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'last_main_action_refresh' not in columns or 'last_quick_action_refresh' not in columns:
        # Old schema - check current action counts first
        cursor.execute(
            "SELECT main_actions_left, quick_actions_left, last_action_refresh FROM players WHERE player_id = ?",
            (player_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return False
        
        current_main, current_quick, last_refresh = result
        
        # If already at max, don't refresh
        if current_main >= 3 and current_quick >= 5:
            return False
        
        # Update to max values
        cursor.execute(
            "UPDATE players SET main_actions_left = 3, quick_actions_left = 5, last_action_refresh = ? WHERE player_id = ?",
            (now, player_id)
        )
        
        # Return True only if values were actually updated
        return cursor.rowcount > 0
    
    # New schema with separate refresh timestamps
    updated = False
    
    # Check and update main actions
    cursor.execute(
        "SELECT main_actions_left FROM players WHERE player_id = ?",
        (player_id,)
    )
    main_result = cursor.fetchone()
    
    if main_result and main_result[0] < 3:
        cursor.execute(
            "UPDATE players SET main_actions_left = 3, last_main_action_refresh = ? WHERE player_id = ?",
            (now, player_id)
        )
        updated = True
    
    # Check and update quick actions
    cursor.execute(
        "SELECT quick_actions_left FROM players WHERE player_id = ?",
        (player_id,)
    )
    quick_result = cursor.fetchone()
    
    if quick_result and quick_result[0] < 5:
        cursor.execute(
            "UPDATE players SET quick_actions_left = 5, last_quick_action_refresh = ? WHERE player_id = ?",
            (now, player_id)
        )
        updated = True
    
    return updated


@db_transaction
def update_action_counts(conn, player_id, main_action=True, quick_action=True):
    """
    Reset action counts if it's been more than 3 hours since last refresh.
    
    Args:
        conn: Database connection
        player_id: Player ID
        main_action: Whether to check/update main actions
        quick_action: Whether to check/update quick actions
    
    Returns:
        bool: True if actions were refreshed, False otherwise
    """
    cursor = conn.cursor()
    now = datetime.datetime.now()
    now_str = now.isoformat()
    refresh_threshold = 3 * 60 * 60  # 3 hours in seconds
    
    # Check for last_main_action_refresh and last_quick_action_refresh columns
    cursor.execute("PRAGMA table_info(players)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'last_main_action_refresh' not in columns or 'last_quick_action_refresh' not in columns:
        # Old schema with only last_action_refresh
        cursor.execute(
            "SELECT last_action_refresh FROM players WHERE player_id = ?",
            (player_id,)
        )
        last_refresh = cursor.fetchone()
        
        if not last_refresh:
            return False
        
        last_refresh_time = datetime.datetime.fromisoformat(last_refresh[0])
        
        # If it's been more than 3 hours
        if (now - last_refresh_time).total_seconds() > refresh_threshold:
            cursor.execute(
                "UPDATE players SET main_actions_left = 3, quick_actions_left = 5, last_action_refresh = ? WHERE player_id = ?",
                (now_str, player_id)
            )
            return True
        return False
    
    # New schema with separate refresh timestamps
    refreshed = False
    
    if main_action:
        cursor.execute(
            "SELECT main_actions_left, last_main_action_refresh FROM players WHERE player_id = ?",
            (player_id,)
        )
        main_result = cursor.fetchone()
        
        if main_result and main_result[1]:  # If we have a last_main_action_refresh value
            last_main_refresh = datetime.datetime.fromisoformat(main_result[1])
            
            # If it's been more than 3 hours and not at max actions
            if (now - last_main_refresh).total_seconds() > refresh_threshold and main_result[0] < 3:
                cursor.execute(
                    "UPDATE players SET main_actions_left = 3, last_main_action_refresh = ? WHERE player_id = ?",
                    (now_str, player_id)
                )
                refreshed = True
    
    if quick_action:
        cursor.execute(
            "SELECT quick_actions_left, last_quick_action_refresh FROM players WHERE player_id = ?",
            (player_id,)
        )
        quick_result = cursor.fetchone()
        
        if quick_result and quick_result[1]:  # If we have a last_quick_action_refresh value
            last_quick_refresh = datetime.datetime.fromisoformat(quick_result[1])
            
            # If it's been more than 3 hours and not at max actions
            if (now - last_quick_refresh).total_seconds() > refresh_threshold and quick_result[0] < 5:
                cursor.execute(
                    "UPDATE players SET quick_actions_left = 5, last_quick_action_refresh = ? WHERE player_id = ?",
                    (now_str, player_id)
                )
                refreshed = True
    
    return refreshed


@db_transaction
def cleanup_expired_actions(conn):
    """Clean up expired actions and handle any orphaned data."""
    cursor = conn.cursor()
    now = datetime.datetime.now()

    # Clean up expired coordinated actions
    cursor.execute(
        "SELECT action_id FROM coordinated_actions WHERE status = 'open' AND expires_at < ?",
        (now.isoformat(),)
    )
    expired_actions = cursor.fetchall()

    # Process each expired action
    for (action_id,) in expired_actions:
        # Close the action
        cursor.execute(
            "UPDATE coordinated_actions SET status = 'expired' WHERE action_id = ?",
            (action_id,)
        )

        # Optionally refund resources for expired actions
        # (Uncomment if you want to implement this feature)
        """
        cursor.execute(
            "SELECT player_id, resources_used FROM coordinated_action_participants WHERE action_id = ?",
            (action_id,)
        )
        participants = cursor.fetchall()

        for player_id, resources_json in participants:
            resources = json.loads(resources_json)
            for resource_type, amount in resources.items():
                cursor.execute(
                    f"UPDATE resources SET {resource_type} = {resource_type} + ? WHERE player_id = ?",
                    (amount, player_id)
                )
        """

    # Add a cleanup for really old actions to prevent database bloat
    one_week_ago = (now - datetime.timedelta(days=7)).isoformat()

    # Archive or delete very old actions
    cursor.execute(
        "DELETE FROM coordinated_action_participants WHERE action_id IN (SELECT action_id FROM coordinated_actions WHERE timestamp < ?)",
        (one_week_ago,)
    )
    cursor.execute(
        "DELETE FROM coordinated_actions WHERE timestamp < ?",
        (one_week_ago,)
    )

    return len(expired_actions)


# News-related queries
@db_transaction
def add_news(conn, title, content, is_public=True, target_player_id=None, is_fake=False):
    """Add a news item."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO news (title, content, timestamp, is_public, target_player_id, is_fake)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, content, now, is_public, target_player_id, is_fake)
    )
    return cursor.lastrowid


@db_transaction
def get_news(conn, limit=5, player_id=None):
    """Get recent news items."""
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
    return cursor.fetchall()


# Game cycle management
@db_transaction
def distribute_district_resources(conn):
    """Distribute resources from controlled districts to players."""
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
            update_player_resources_internal(conn, player_id, "influence", influence)
        if resources > 0:
            update_player_resources_internal(conn, player_id, "resources", resources)
        if information > 0:
            update_player_resources_internal(conn, player_id, "information", information)
        if force > 0:
            update_player_resources_internal(conn, player_id, "force", force)


@db_transaction
def create_coordinated_action(conn, initiator_id, action_type, target_type, target_id, resources_used):
    """Create a new coordinated action."""
    cursor = conn.cursor()
    now = datetime.datetime.now()
    expires_at = now + datetime.timedelta(minutes=30)

    # Determine current cycle
    current_time = now.time()
    if datetime.time(6, 0) <= current_time < datetime.time(13, 1):
        cycle = "morning"
    else:
        cycle = "evening"

    # Only certain action types can be coordinated
    if action_type not in [ACTION_ATTACK, ACTION_DEFENSE]:
        logger.warning(f"Attempt to create coordinated action with invalid type: {action_type}")
        return None

    # Convert resources dictionary to JSON string
    resources_json = json.dumps(resources_used)

    cursor.execute(
        """
        INSERT INTO coordinated_actions 
        (initiator_id, action_type, target_type, target_id, resources_used, timestamp, cycle, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (initiator_id, action_type, target_type, target_id, resources_json,
         now.isoformat(), cycle, expires_at.isoformat())
    )
    action_id = cursor.lastrowid

    # Add initiator as first participant
    cursor.execute(
        """
        INSERT INTO coordinated_action_participants 
        (action_id, player_id, resources_used, joined_at)
        VALUES (?, ?, ?, ?)
        """,
        (action_id, initiator_id, resources_json, now.isoformat())
    )

    return action_id


@db_transaction
def join_coordinated_action(conn, player_id, action_id, resources_used):
    """Join an existing coordinated action."""
    cursor = conn.cursor()

    # Check if action exists and is still open
    cursor.execute(
        """
        SELECT action_id, expires_at, status, initiator_id, min_participants
        FROM coordinated_actions 
        WHERE action_id = ?
        """,
        (action_id,)
    )
    action = cursor.fetchone()

    if not action:
        return False, "Action not found", False

    action_id, expires_at_str, status, initiator_id, min_participants = action

    # Don't allow initiator to join their own action
    if player_id == initiator_id:
        return False, "You cannot join your own action", False

    # Check if player already joined this action
    cursor.execute(
        """
        SELECT player_id
        FROM coordinated_action_participants
        WHERE action_id = ? AND player_id = ?
        """,
        (action_id, player_id)
    )
    if cursor.fetchone():
        return False, "You have already joined this action", False

    if status != 'open':
        return False, "Action is no longer open", False

    expires_at = datetime.datetime.fromisoformat(expires_at_str)
    if datetime.datetime.now() > expires_at:
        return False, "Action has expired", False

    # Add participant
    cursor.execute(
        """
        INSERT INTO coordinated_action_participants 
        (action_id, player_id, resources_used, joined_at)
        VALUES (?, ?, ?, ?)
        """,
        (action_id, player_id, json.dumps(resources_used), datetime.datetime.now().isoformat())
    )

    # Count current participants to see if we've reached the minimum
    cursor.execute(
        """
        SELECT COUNT(*) 
        FROM coordinated_action_participants
        WHERE action_id = ?
        """,
        (action_id,)
    )
    participant_count = cursor.fetchone()[0]
    
    # Check if we have enough participants to complete the action
    action_completed = False
    if participant_count >= min_participants:
        # Close the action and convert it to regular actions
        close_coordinated_action(conn, action_id)
        action_completed = True
        
    return True, "Successfully joined action", action_completed


@db_transaction
def get_open_coordinated_actions(conn):
    """Get all open coordinated actions."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    
    cursor.execute(
        """
        SELECT ca.action_id, ca.initiator_id, ca.action_type, ca.target_type, 
               ca.target_id, ca.resources_used, ca.timestamp, ca.cycle,
               p.character_name as initiator_name
        FROM coordinated_actions ca
        JOIN players p ON ca.initiator_id = p.player_id
        WHERE ca.status = 'open' AND ca.expires_at > ?
        ORDER BY ca.timestamp DESC
        """,
        (now,)
    )
    
    return cursor.fetchall()

@db_transaction
def get_coordinated_action_participants(conn, action_id):
    """Get all participants of a coordinated action."""
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT cap.player_id, cap.resources_used, cap.joined_at,
               p.character_name
        FROM coordinated_action_participants cap
        JOIN players p ON cap.player_id = p.player_id
        WHERE cap.action_id = ?
        ORDER BY cap.joined_at ASC
        """,
        (action_id,)
    )
    
    return cursor.fetchall()

@db_transaction
def close_coordinated_action(conn, action_id):
    """Close a coordinated action and convert it to regular actions."""
    cursor = conn.cursor()
    
    # Get action details
    cursor.execute(
        """
        SELECT action_type, target_type, target_id, cycle
        FROM coordinated_actions
        WHERE action_id = ?
        """,
        (action_id,)
    )
    action = cursor.fetchone()
    
    if not action:
        return False
    
    action_type, target_type, target_id, cycle = action
    
    # Get all participants
    participants = get_coordinated_action_participants(conn, action_id)
    
    # Create regular actions for each participant
    for participant in participants:
        player_id, resources_used, _, _ = participant
        add_action(conn, player_id, action_type, target_type, target_id, json.loads(resources_used))
    
    # Mark action as closed
    cursor.execute(
        "UPDATE coordinated_actions SET status = 'closed' WHERE action_id = ?",
        (action_id,)
    )
    
    return True

@db_transaction
def cleanup_expired_coordinated_actions(conn):
    """Clean up expired coordinated actions."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    
    # Get expired actions
    cursor.execute(
        "SELECT action_id FROM coordinated_actions WHERE status = 'open' AND expires_at <= ?",
        (now,)
    )
    expired_actions = cursor.fetchall()
    
    # Close each expired action
    for action in expired_actions:
        close_coordinated_action(conn, action[0])
    
    return len(expired_actions)


@db_transaction
def get_coordinated_action_details(conn, action_id):
    """Get detailed information about a coordinated action."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()

    cursor.execute(
        """
        SELECT action_id, initiator_id, action_type, target_type, 
               target_id, resources_used, timestamp, cycle, status
        FROM coordinated_actions
        WHERE action_id = ? AND status = 'open' AND expires_at > ?
        """,
        (action_id, now)
    )

    action = cursor.fetchone()

    if not action:
        return None

    # Convert to dictionary
    return {
        'action_id': action[0],
        'initiator_id': action[1],
        'action_type': action[2],
        'target_type': action[3],
        'target_id': action[4],
        'resources_used': json.loads(action[5]),
        'timestamp': action[6],
        'cycle': action[7],
        'status': action[8]
    }

# Function to generate a unique ID for various database records
def generate_id():
    """Generate a unique ID for database records."""
    return str(uuid.uuid4())

def is_player_in_action(player_id, action_id):
    """
    Check if a player is already participating in a coordinated action.
    
    Args:
        player_id (int): The ID of the player
        action_id (int): The ID of the coordinated action
        
    Returns:
        bool: True if the player is already participating, False otherwise
    """
    conn = sqlite3.connect('novi_sad_game.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT player_id
            FROM coordinated_action_participants
            WHERE action_id = ? AND player_id = ?
            """,
            (action_id, player_id)
        )
        
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        logger.error(f"Error checking if player is in action: {e}")
        return False
    finally:
        conn.close()
