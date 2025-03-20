import sqlite3
import logging
import datetime
import json
from functools import wraps
import time

from game.actions import ACTION_ATTACK, ACTION_DEFENSE

logger = logging.getLogger(__name__)


def db_transaction(func):
    """
    Decorator to handle database transactions with proper error handling and concurrency management.
    Implements connection pooling, retries, and transaction isolation.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        max_retries = 5
        retry_delay = 0.5  # seconds

        for attempt in range(max_retries):
            try:
                # Use WAL mode and set a timeout to handle concurrency better
                conn = sqlite3.connect('belgrade_game.db', timeout=20.0)
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')  # Faster with reasonable safety
                conn.execute('PRAGMA busy_timeout=5000')  # Wait up to 5 seconds when db is locked

                # Set isolation level - needed for concurrent writes
                conn.isolation_level = None  # This allows explicit transaction control
                conn.execute('BEGIN IMMEDIATE')  # Acquire write lock immediately

                # Call the function with the connection as first arg
                result = func(conn, *args, **kwargs)

                # Commit changes
                conn.execute('COMMIT')
                return result

            except sqlite3.OperationalError as e:
                if conn:
                    try:
                        conn.execute('ROLLBACK')
                    except:
                        pass  # Ignore rollback errors

                error_msg = str(e).lower()
                if ("database is locked" in error_msg or "busy" in error_msg) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue

                logger.error(f"Database operational error in {func.__name__}: {e}")
                return None

            except sqlite3.Error as e:
                if conn:
                    try:
                        conn.execute('ROLLBACK')
                    except:
                        pass

                logger.error(f"Database error in {func.__name__}: {e}")
                return None

            except Exception as e:
                if conn:
                    try:
                        conn.execute('ROLLBACK')
                    except:
                        pass

                logger.error(f"Unexpected error in {func.__name__}: {e}")
                return None

            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass

    return wrapper


# Player-related queries
@db_transaction
def get_player(conn, player_id):
    """Get player information by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
    player = cursor.fetchone()
    return player


def register_player(player_id, username, language="en"):
    """Register a new player."""
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
    """Set player's character name."""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE players SET character_name = ? WHERE player_id = ?",
        (character_name, player_id)
    )
    conn.commit()
    conn.close()



@db_transaction
def get_player_language(conn, player_id):
    """Get player's preferred language."""
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    return result[0] if result else "en"


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

    field = "main_actions_left" if is_main_action else "quick_actions_left"

    # Check if player has actions left
    cursor.execute(
        f"SELECT {field} FROM players WHERE player_id = ?",
        (player_id,)
    )
    actions_left = cursor.fetchone()

    if not actions_left or actions_left[0] <= 0:
        logger.warning(f"Player {player_id} has no {'main' if is_main_action else 'quick'} actions left")
        return False

    # Update the appropriate action count
    cursor.execute(
        f"UPDATE players SET {field} = {field} - 1 WHERE player_id = ? AND {field} > 0",
        (player_id,)
    )

    result = cursor.rowcount > 0
    logger.info(f"{'Main' if is_main_action else 'Quick'} action usage result for player {player_id}: {result}")

    return result


@db_transaction
def refresh_player_actions(conn, player_id):
    """Reset action counts and update refresh timestamp."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()

    # Check current action counts first
    cursor.execute(
        "SELECT main_actions_left, quick_actions_left, last_action_refresh FROM players WHERE player_id = ?",
        (player_id,)
    )
    result = cursor.fetchone()

    if not result:
        return False

    current_main, current_quick, last_refresh = result

    # If already at max, don't refresh
    if current_main >= 1 and current_quick >= 2:
        return False

    # Update to max values
    cursor.execute(
        "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
        (now, player_id)
    )

    # Return True only if values were actually updated
    return cursor.rowcount > 0


@db_transaction
def update_action_counts(conn, player_id):
    """Reset action counts if it's been more than 3 hours since last refresh."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT last_action_refresh FROM players WHERE player_id = ?",
        (player_id,)
    )
    last_refresh = cursor.fetchone()

    if not last_refresh:
        return False

    last_refresh_time = datetime.datetime.fromisoformat(last_refresh[0])
    now = datetime.datetime.now()

    # If it's been more than 3 hours
    if (now - last_refresh_time).total_seconds() > 3 * 60 * 60:
        cursor.execute(
            "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
            (now.isoformat(), player_id)
        )
        return True
    return False


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
        SELECT action_id, expires_at, status, initiator_id
        FROM coordinated_actions 
        WHERE action_id = ?
        """,
        (action_id,)
    )
    action = cursor.fetchone()

    if not action:
        return False, "Action not found"

    action_id, expires_at_str, status, initiator_id = action

    # Don't allow initiator to join their own action
    if player_id == initiator_id:
        return False, "You cannot join your own action"

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
        return False, "You have already joined this action"

    if status != 'open':
        return False, "Action is no longer open"

    expires_at = datetime.datetime.fromisoformat(expires_at_str)
    if datetime.datetime.now() > expires_at:
        return False, "Action has expired"

    # Add participant
    cursor.execute(
        """
        INSERT INTO coordinated_action_participants 
        (action_id, player_id, resources_used, joined_at)
        VALUES (?, ?, ?, ?)
        """,
        (action_id, player_id, json.dumps(resources_used), datetime.datetime.now().isoformat())
    )

    return True, "Successfully joined action"


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
