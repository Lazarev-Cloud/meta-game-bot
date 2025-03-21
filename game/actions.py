import datetime
import json
import logging
import random
import sqlite3
from telegram.ext import ContextTypes
from db.queries import (
    update_district_control, distribute_district_resources,
    get_district_control, get_district_info, add_news, get_news, get_player_resources, get_player_language,
    get_player_districts, refresh_player_actions, db_transaction
)
from db.utils import get_db_connection, release_db_connection
from languages import get_text, get_cycle_name, get_action_name, get_resource_name

logger = logging.getLogger(__name__)

# Main actions (strategic, major impact)
ACTION_INFLUENCE = "influence"
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defense"

# Quick actions (tactical, minor impact)
QUICK_ACTION_RECON = "recon"
QUICK_ACTION_INFO = "info"
QUICK_ACTION_SUPPORT = "support"

# Group actions by type for validation
MAIN_ACTIONS = [ACTION_INFLUENCE, ACTION_ATTACK, ACTION_DEFENSE]
QUICK_ACTIONS = [QUICK_ACTION_RECON, QUICK_ACTION_INFO, QUICK_ACTION_SUPPORT]

# Action cost definitions - Map each action type to its typical resource costs
ACTION_COSTS = {
    # Main actions typically cost 2-3 resources
    ACTION_INFLUENCE: {
        "default": {"influence": 2},
        "alternatives": [
            {"influence": 1, "resources": 1},
            {"influence": 1, "information": 1}
        ]
    },
    ACTION_ATTACK: {
        "default": {"force": 2},
        "alternatives": [
            {"force": 1, "influence": 1},
            {"force": 1, "information": 1}
        ]
    },
    ACTION_DEFENSE: {
        "default": {"force": 2},
        "alternatives": [
            {"force": 1, "resources": 1},
            {"influence": 1, "force": 1}
        ]
    },

    # Quick actions typically cost 1 resource
    QUICK_ACTION_RECON: {
        "default": {"information": 1},
        "alternatives": []
    },
    QUICK_ACTION_INFO: {
        "default": {"information": 1},
        "alternatives": []
    },
    QUICK_ACTION_SUPPORT: {
        "default": {"influence": 1},
        "alternatives": []
    }
}

# Action effects - Define the possible outcomes for each action type
ACTION_EFFECTS = {
    # Main actions have significant effects
    ACTION_INFLUENCE: {
        "success": {"control_change": 10, "message": "influence_success"},
        "partial": {"control_change": 5, "message": "influence_partial"},
        "failure": {"control_change": 0, "message": "influence_failure"}
    },
    ACTION_ATTACK: {
        "success": {"target_control_change": -10, "attacker_control_change": 10, "message": "attack_success"},
        "partial": {"target_control_change": -5, "attacker_control_change": 5, "message": "attack_partial"},
        "failure": {"target_control_change": 0, "attacker_control_change": 0, "message": "attack_failure"}
    },
    ACTION_DEFENSE: {
        "success": {"defense_bonus": 10, "message": "defense_success"},
        "partial": {"defense_bonus": 5, "message": "defense_partial"},
        "failure": {"defense_bonus": 0, "message": "defense_failure"}
    },

    # Quick actions have limited effects
    QUICK_ACTION_RECON: {
        "success": {"message": "recon_success", "reveals_control": True, "reveals_plans": True}
    },
    QUICK_ACTION_INFO: {
        "success": {"message": "info_success", "news_published": True}
    },
    QUICK_ACTION_SUPPORT: {
        "success": {"control_change": 5, "message": "support_success"}
    }
}

# Game cycle times
MORNING_CYCLE_START = datetime.time(6, 0)  # 6:00 AM
MORNING_CYCLE_DEADLINE = datetime.time(12, 0)  # 12:00 PM
MORNING_CYCLE_RESULTS = datetime.time(13, 0)  # 1:00 PM
EVENING_CYCLE_START = datetime.time(13, 1)  # 1:01 PM
EVENING_CYCLE_DEADLINE = datetime.time(18, 0)  # 6:00 PM
EVENING_CYCLE_RESULTS = datetime.time(19, 0)  # 7:00 PM


async def process_game_cycle(context):
    """Process actions and update game state at the end of a cycle."""
    now = datetime.datetime.now().time()

    # Determine which cycle just ended
    if now.hour == MORNING_CYCLE_RESULTS.hour and now.minute == MORNING_CYCLE_RESULTS.minute:
        cycle = "morning"
    elif now.hour == EVENING_CYCLE_RESULTS.hour and now.minute == EVENING_CYCLE_RESULTS.minute:
        cycle = "evening"
    else:
        # If called at an unexpected time (e.g., manual admin trigger), use current cycle
        if MORNING_CYCLE_START <= now < EVENING_CYCLE_START:
            cycle = "morning"
        else:
            cycle = "evening"

    logger.info(f"Processing {cycle} cycle")

    try:
        # Process each action separately with its own connection to avoid long transactions
        actions = get_pending_actions(cycle)

        for action in actions:
            try:
                # Process action with its own connection
                process_single_action(action[0], action[1], action[2], action[3], action[4])
            except Exception as e:
                logger.error(f"Error processing action {action[0]}: {e}")

        # Apply decay to district control
        apply_district_decay()

        # Distribute resources - use existing function with its own connection
        distribute_district_resources()

        # Process international politicians one by one
        for politician_id in get_random_international_politicians(1, 3):
            try:
                process_international_politician_action(politician_id)
            except Exception as e:
                logger.error(f"Error processing international politician {politician_id}: {e}")

        # Notify all players of results
        await notify_players_of_results(context, cycle)

        logger.info(f"Completed processing {cycle} cycle")
    except Exception as e:
        logger.error(f"Error processing game cycle: {e}")
        import traceback
        tb_list = traceback.format_exception(None, e, e.__traceback__)
        tb_string = ''.join(tb_list)
        logger.error(f"Exception traceback:\n{tb_string}")


# Helper functions to break down the process
def get_pending_actions(cycle):
    """Get all pending actions for a cycle with a dedicated connection."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action_id, player_id, action_type, target_type, target_id FROM actions WHERE status = 'pending' AND cycle = ?",
            (cycle,)
        )
        actions = cursor.fetchall()
        conn.close()
        return actions
    except Exception as e:
        logger.error(f"Error getting pending actions: {e}")
        return []


def process_single_action(action_id, player_id, action_type, target_type, target_id):
    """Process a single action with its own connection."""
    try:
        # Process the action
        result = process_action(action_id, player_id, action_type, target_type, target_id)

        # Update status
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE actions SET status = 'completed', result = ? WHERE action_id = ?",
            (json.dumps(result), action_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error processing single action {action_id}: {e}")
        return False


def apply_district_decay():
    """Apply decay to district control with a dedicated connection."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE district_control SET control_points = MAX(0, control_points - 5) WHERE control_points > 0"
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error applying district decay: {e}")
        return False


def get_random_international_politicians(min_count, max_count):
    """Get random international politician IDs."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT politician_id FROM politicians WHERE is_international = 1")
        politicians = cursor.fetchall()
        conn.close()

        import random
        count = min(max_count, max(min_count, len(politicians)))
        return [p[0] for p in random.sample(politicians, count)]
    except Exception as e:
        logger.error(f"Error getting international politicians: {e}")
        return []


def process_action(action_id, player_id, action_type, target_type, target_id):
    """Process a single action and return the result"""
    result = {}

    try:
        # Determine if this is a main or quick action
        is_main_action = action_type in [ACTION_INFLUENCE, ACTION_ATTACK, ACTION_DEFENSE]

        if target_type == "district":
            if action_type == ACTION_INFLUENCE:
                # Process influence action on district
                success_roll = random.randint(1, 100)

                # Main actions have more significant outcomes with possible failures
                if success_roll > 70:  # Success (30% chance)
                    update_district_control(player_id, target_id, 10)
                    result = {
                        "status": "success",
                        "message": f"Successfully increased influence in {target_id}",
                        "control_change": 10
                    }
                elif success_roll > 30:  # Partial success (40% chance)
                    update_district_control(player_id, target_id, 5)
                    result = {
                        "status": "partial",
                        "message": f"Partially increased influence in {target_id}",
                        "control_change": 5
                    }
                else:  # Failure (30% chance)
                    result = {
                        "status": "failure",
                        "message": f"Failed to increase influence in {target_id}",
                        "control_change": 0
                    }

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
                # Process defense action - will block future attacks
                result = {"status": "active", "message": f"Defensive measures in place for {target_id}"}

                # Store the defense bonus in the district_control table or another appropriate place
                conn = sqlite3.connect('belgrade_game.db')
                cursor = conn.cursor()
                now = datetime.datetime.now().isoformat()

                # Add a defense bonus that expires at the end of the cycle
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO district_defense 
                    (district_id, player_id, defense_bonus, expires_at)
                    VALUES (?, ?, 10, ?)
                    """,
                    (target_id, player_id, now)  # Use appropriate expiration time based on cycle
                )
                conn.commit()
                conn.close()

            elif action_type == QUICK_ACTION_RECON:
                # Process reconnaissance action - always succeeds
                control_data = get_district_control(target_id)
                district_info = get_district_info(target_id)

                # Get pending actions targeting this district
                conn = sqlite3.connect('belgrade_game.db')
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT a.action_type, p.character_name
                    FROM actions a
                    JOIN players p ON a.player_id = p.player_id
                    WHERE a.target_type = 'district' AND a.target_id = ? AND a.status = 'pending'
                    """,
                    (target_id,)
                )
                pending_actions = cursor.fetchall()
                conn.close()

                result = {
                    "status": "success",
                    "message": f"Reconnaissance of {target_id} complete",
                    "control_data": control_data,
                    "district_info": district_info,
                    "pending_actions": pending_actions if pending_actions else []
                }

            elif action_type == QUICK_ACTION_SUPPORT:
                # Process support action (small influence gain) - always succeeds
                update_district_control(player_id, target_id, 5)
                result = {
                    "status": "success",
                    "message": f"Support action in {target_id} complete",
                    "control_change": 5
                }

            elif action_type == QUICK_ACTION_INFO:
                # Process information spreading - always succeeds
                result = {
                    "status": "success",
                    "message": f"Information has been spread about {target_id}",
                }

        elif target_type == "politician":
            if action_type == ACTION_INFLUENCE:
                # Process influence on politician
                from game.politicians import get_politician_by_id
                politician = get_politician_by_id(target_id)
                if politician:
                    # Update politician relationship in the results processing phase
                    result = {
                        "status": "success",
                        "message": f"Improved relationship with {politician['name']}",
                        "politician_id": politician['politician_id']
                    }
            elif action_type == "undermine":
                # Process undermining action on politician
                from game.politicians import get_politician_by_id
                politician = get_politician_by_id(target_id)
                if politician:
                    result = {
                        "status": "success",
                        "message": f"Started undermining {politician['name']}'s influence",
                        "politician_id": politician['politician_id']
                    }
            elif action_type == "info":
                # Process info gathering on politician - quick action
                from game.politicians import get_politician_by_id
                politician = get_politician_by_id(target_id)
                if politician:
                    result = {
                        "status": "success",
                        "message": f"Gathered intelligence on {politician['name']}",
                        "politician_id": politician['politician_id'],
                        "politician_data": politician
                    }

    except Exception as e:
        logger.error(f"Error in process_action: {e}")
        result = {"status": "error", "message": f"An error occurred: {str(e)}"}

    return result


def apply_physical_presence_bonus(player_id, district_id, action_type):
    """
    Apply a bonus for physically being present in a district during an action.
    This gives +20 Control Points to the action if it's a main action.

    Args:
        player_id: The player ID
        district_id: The district ID
        action_type: The type of action

    Returns:
        dict: Bonus information
    """
    # Check if this is a main action
    if action_type not in MAIN_ACTIONS:
        return {"applied": False, "bonus": 0, "message": "Bonus only applies to main actions"}

    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check for a valid and not expired record of physical presence
        # Presence expires after 6 hours
        expiry_time = (datetime.datetime.now() - datetime.timedelta(hours=6)).isoformat()
        
        cursor.execute(
            """
            SELECT is_present, timestamp FROM player_presence 
            WHERE player_id = ? AND district_id = ? AND timestamp > ?
            """,
            (player_id, district_id, expiry_time)
        )
        presence_record = cursor.fetchone()

        if presence_record and presence_record[0]:
            # Calculate time remaining on presence bonus
            timestamp = datetime.datetime.fromisoformat(presence_record[1])
            expires_at = timestamp + datetime.timedelta(hours=6)
            now = datetime.datetime.now()
            time_remaining = max(0, (expires_at - now).total_seconds() // 60)  # Minutes remaining
            
            # Apply +20 CP bonus
            return {
                "applied": True, 
                "bonus": 20,
                "message": f"Physical presence bonus applied (+20 CP). Expires in {int(time_remaining)} minutes.",
                "expires_at": expires_at.isoformat()
            }

        conn.close()
        return {"applied": False, "bonus": 0, "message": "No physical presence detected"}

    except Exception as e:
        logger.error(f"Error checking physical presence: {e}")
        return {"applied": False, "bonus": 0, "message": f"Error: {str(e)}"}


def register_player_presence(player_id, district_id, location_data=None):
    """
    Register a player as physically present in a district.
    
    Args:
        player_id: The player ID
        district_id: The district ID
        location_data: Optional location data from Telegram (latitude/longitude)
        
    Returns:
        dict: Result of the operation
    """
    if not player_id or not district_id:
        logger.error("Missing player_id or district_id for presence registration")
        return {
            "success": False,
            "message": "Missing required information for presence registration."
        }
    
    conn = None
    
    try:
        # Validate the location if provided
        if location_data:
            valid_location = verify_location_in_district(location_data, district_id)
            if not valid_location:
                return {
                    "success": False,
                    "message": "Your location is not within this district."
                }
        
        # Validate that district exists
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT district_id FROM districts WHERE district_id = ?", (district_id,))
        if not cursor.fetchone():
            return {
                "success": False,
                "message": "District not found."
            }
            
        # Validate that player exists
        cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
        if not cursor.fetchone():
            return {
                "success": False, 
                "message": "Player not registered."
            }
            
        # Begin transaction
        cursor.execute("BEGIN IMMEDIATE")
        
        now = datetime.datetime.now().isoformat()
        
        # Check if record already exists
        cursor.execute(
            "SELECT * FROM player_presence WHERE player_id = ? AND district_id = ?",
            (player_id, district_id)
        )
        
        if cursor.fetchone():
            # Update existing record
            cursor.execute(
                """
                UPDATE player_presence 
                SET is_present = 1, timestamp = ? 
                WHERE player_id = ? AND district_id = ?
                """,
                (now, player_id, district_id)
            )
            
            # Add log for refreshed presence
            logger.info(f"Refreshed player {player_id} presence in district {district_id}")
        else:
            # Create new record
            cursor.execute(
                """
                INSERT INTO player_presence (player_id, district_id, timestamp, is_present)
                VALUES (?, ?, ?, 1)
                """,
                (player_id, district_id, now)
            )
            
            # Log new presence registration
            logger.info(f"New player {player_id} presence registered in district {district_id}")
            
        # Commit transaction
        cursor.execute("COMMIT")
        
        # Calculate expiry time
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=6)
        formatted_time = expires_at.strftime("%H:%M:%S on %Y-%m-%d")
        
        return {
            "success": True,
            "message": f"Physical presence registered in district. Expires at {formatted_time}.",
            "expires_at": expires_at.isoformat()
        }
        
    except sqlite3.Error as e:
        # Handle database errors
        if conn:
            try:
                # Rollback transaction on error
                conn.execute("ROLLBACK")
                logger.warning(f"Rolled back transaction: {str(e)}")
            except Exception as rollback_e:
                logger.error(f"Error rolling back transaction: {str(rollback_e)}")
                
        error_msg = str(e).lower()
        user_friendly_msg = "Database error occurred while registering presence."
        
        if "database is locked" in error_msg:
            user_friendly_msg = "The system is busy. Please try again in a moment."
        elif "no such table" in error_msg:
            user_friendly_msg = "System error: Missing required database table."
        elif "constraint failed" in error_msg:
            user_friendly_msg = "Data validation error. Please try again."
            
        logger.error(f"Database error registering presence: {str(e)}")
        return {
            "success": False,
            "message": user_friendly_msg
        }
    except Exception as e:
        # Handle other errors
        logger.error(f"Error registering physical presence: {e}")
        return {
            "success": False,
            "message": "An error occurred while registering your presence. Please try again."
        }
    finally:
        # Ensure connection is returned to the pool
        if conn:
            release_db_connection(conn)


def verify_location_in_district(location_data, district_id):
    """
    Verify if the provided location is within the specified district.
    
    Args:
        location_data: Location data (latitude/longitude)
        district_id: District ID to check against
        
    Returns:
        bool: True if location is in district, False otherwise
    """
    if not location_data or not district_id:
        logger.warning("Missing location data or district ID for verification")
        return False
        
    try:
        # Validate location data format
        if 'latitude' not in location_data or 'longitude' not in location_data:
            logger.warning("Location data missing latitude or longitude")
            return False
            
        lat = location_data['latitude']
        lon = location_data['longitude']
        
        # Ensure coordinates are in valid ranges
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            logger.warning(f"Invalid coordinates: {lat}, {lon}")
            return False
            
        # Belgrade boundaries approximation (simplified for demo)
        belgrade_bounds = {
            'min_lat': 44.7,
            'max_lat': 44.9,
            'min_lon': 20.3,
            'max_lon': 20.6
        }
        
        # First verify within Belgrade
        if (belgrade_bounds['min_lat'] <= lat <= belgrade_bounds['max_lat'] and
            belgrade_bounds['min_lon'] <= lon <= belgrade_bounds['max_lon']):
            
            # District-specific bounds (approximate)
            district_bounds = {
                'stari_grad': {'min_lat': 44.8, 'max_lat': 44.83, 'min_lon': 20.45, 'max_lon': 20.48},
                'novi_beograd': {'min_lat': 44.8, 'max_lat': 44.84, 'min_lon': 20.38, 'max_lon': 20.43},
                'zemun': {'min_lat': 44.84, 'max_lat': 44.88, 'min_lon': 20.37, 'max_lon': 20.42},
                'savski_venac': {'min_lat': 44.78, 'max_lat': 44.81, 'min_lon': 20.44, 'max_lon': 20.47},
                'vozdovac': {'min_lat': 44.75, 'max_lat': 44.79, 'min_lon': 20.48, 'max_lon': 20.53},
                'cukarica': {'min_lat': 44.77, 'max_lat': 44.8, 'min_lon': 20.36, 'max_lon': 20.41},
                'palilula': {'min_lat': 44.81, 'max_lat': 44.85, 'min_lon': 20.47, 'max_lon': 20.52},
                'vracar': {'min_lat': 44.79, 'max_lat': 44.81, 'min_lon': 20.46, 'max_lon': 20.49}
            }
            
            # If we have bounds for this district, check against them
            if district_id in district_bounds:
                bounds = district_bounds[district_id]
                return (bounds['min_lat'] <= lat <= bounds['max_lat'] and
                        bounds['min_lon'] <= lon <= bounds['max_lon'])
            else:
                # If we don't have specific bounds, use the quadrant approach as fallback
                conn = sqlite3.connect('belgrade_game.db')
                cursor = conn.cursor()
                
                # Get district's area code to verify it matches the location quadrant
                cursor.execute("SELECT district_id FROM districts WHERE district_id = ?", (district_id,))
                result = cursor.fetchone()
                conn.close()
                
                if not result:
                    logger.warning(f"District {district_id} not found in database")
                    return False
                
                # Belgrade center coordinates (approximate)
                belgrade_center_lat = 44.8125
                belgrade_center_lon = 20.4612
                
                # Determine which quadrant the location is in
                quadrant_districts = {
                    "NE": ['palilula', 'vracar'],
                    "NW": ['zemun', 'novi_beograd'],
                    "SE": ['stari_grad', 'savski_venac'],
                    "SW": ['cukarica', 'vozdovac']
                }
                
                if lat > belgrade_center_lat and lon > belgrade_center_lon:
                    return district_id in quadrant_districts["NE"]
                elif lat > belgrade_center_lat and lon <= belgrade_center_lon:
                    return district_id in quadrant_districts["NW"]
                elif lat <= belgrade_center_lat and lon > belgrade_center_lon:
                    return district_id in quadrant_districts["SE"]
                else:
                    return district_id in quadrant_districts["SW"]
        else:
            logger.warning(f"Location {lat}, {lon} is outside Belgrade boundaries")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying location in district: {e}")
        return False


def get_player_presence_status(player_id):
    """
    Get the player's current physical presence status in districts.
    
    Args:
        player_id: Telegram user ID
        
    Returns:
        list: List of districts where player is physically present, 
              with expiry time and resources information
    """
    if not player_id:
        return []
        
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.datetime.now().isoformat()
        
        # Get active presence records for player
        cursor.execute("""
            SELECT district_id, expires_at, location_data 
            FROM player_presence 
            WHERE player_id = ? AND expires_at > ?
        """, (player_id, now))
        
        presence_records = cursor.fetchall()
        
        if not presence_records:
            return []
            
        # Format presence data for display
        formatted_records = []
        
        for record in presence_records:
            district_id, expires_at, location_data_str = record
            
            # Get district info
            district_info = get_district_info(district_id)
            
            if not district_info:
                continue
                
            # Extract district name from district info
            district_name = district_info[1]  # Index 1 is the name
            
            # Calculate time remaining
            expires_datetime = datetime.datetime.fromisoformat(expires_at)
            time_delta = expires_datetime - datetime.datetime.now()
            
            # Format time remaining
            hours, remainder = divmod(time_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            time_remaining = f"{hours}h {minutes}m"
            
            # Get player's control points in this district
            cursor.execute("""
                SELECT control_points FROM district_control 
                WHERE player_id = ? AND district_id = ?
            """, (player_id, district_id))
            control_row = cursor.fetchone()
            control_points = control_row[0] if control_row else 0
            
            # Calculate resources available for collection
            resources_available = {
                "influence": district_info[3] or 0,  # influence_resources
                "resources": district_info[4] or 0,  # economic_resources
                "information": district_info[5] or 0,  # information_resources
                "force": district_info[6] or 0   # force_resources
            }
            
            # Add to formatted records
            formatted_records.append({
                "district_id": district_id,
                "district_name": district_name,
                "time_remaining": time_remaining,
                "control_points": control_points,
                "resources_available": resources_available,
                "expires_at": expires_at,
                "location_data": json.loads(location_data_str) if location_data_str else None
            })
            
        return formatted_records
        
    except Exception as e:
        logger.error(f"Database error getting presence status: {e}")
        return []
    finally:
        if conn:
            release_db_connection(conn)


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


async def schedule_jobs(application):
    """Set up scheduled jobs for game cycle processing."""
    job_queue = application.job_queue

    # Schedule morning cycle results
    morning_time = datetime.time(hour=MORNING_CYCLE_RESULTS.hour, minute=MORNING_CYCLE_RESULTS.minute)
    job_queue.run_daily(process_game_cycle, time=morning_time)

    # Schedule evening cycle results
    evening_time = datetime.time(hour=EVENING_CYCLE_RESULTS.hour, minute=EVENING_CYCLE_RESULTS.minute)
    job_queue.run_daily(process_game_cycle, time=evening_time)

    # Schedule periodic action refreshes every 3 hours
    job_queue.run_repeating(refresh_actions, interval=3 * 60 * 60)

    logger.info("Scheduled jobs set up")


async def refresh_actions(context):
    """Refresh actions for all players every 3 hours."""
    try:
        # Get all active players
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT player_id FROM players")
        players = cursor.fetchall()
        conn.close()

        for player_id_tuple in players:
            player_id = player_id_tuple[0]

            # Refresh their actions
            refreshed = refresh_player_actions(player_id)

            # Only notify the player if actions were actually refreshed
            if refreshed:
                try:
                    lang = get_player_language(player_id)
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=get_text("actions_refreshed_notification", lang)
                    )
                except Exception as e:
                    logger.error(f"Failed to notify player {player_id} about action refresh: {e}")

        logger.info("Actions refreshed for all players")
    except Exception as e:
        logger.error(f"Error in refresh_actions: {e}")


def process_international_politician_action(politician_id):
    """
    Process an action by an international politician.

    This function determines what effect an international politician has on the
    game world based on their ideology and role. Effects can include sanctions,
    support for certain districts, or penalties to opposing ideologies.

    Args:
        politician_id (int): The ID of the politician to process

    Returns:
        dict: Details of the action taken, or None if no action was taken
    """
    try:
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
                    SELECT districts.district_id FROM districts 
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
                    SELECT districts.district_id FROM districts 
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
                        SELECT districts.district_id FROM districts 
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
    except Exception as e:
        logger.error(f"Error processing international politician {politician_id}: {e}")
        return None


def _escape_markdown(text):
    """
    Escape special characters for Markdown formatting.
    """
    if text is None:
        return ""
    return text.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[", "\\[")


async def notify_players_of_results(context, cycle):
    """Send notifications to all players about cycle results."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get all active players
        cursor.execute("SELECT player_id FROM players")
        players = cursor.fetchall()

        for player_id_tuple in players:
            player_id = player_id_tuple[0]

            try:
                # Get player's language preference
                lang = get_player_language(player_id)

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
                cycle_name = get_cycle_name(cycle, lang)
                message = get_text("cycle_results_title", lang, cycle=cycle_name)

                if actions:
                    message += "\n\n" + get_text("your_actions", lang) + "\n"
                    for action in actions:
                        action_type, target_type, target_id, result_json = action
                        result = json.loads(result_json)
                        status = result.get('status', 'unknown')
                        action_msg = _escape_markdown(result.get('message', get_text("no_details", lang)))

                        # Format based on status
                        if status == 'success':
                            status_emoji = get_text("status_success", lang)
                        elif status == 'partial':
                            status_emoji = get_text("status_partial", lang)
                        elif status == 'failure':
                            status_emoji = get_text("status_failure", lang)
                        else:
                            status_emoji = get_text("status_info", lang)

                        message += f"{status_emoji} {_escape_markdown(action_type.capitalize())} - {action_msg}\n"

                    message += "\n"

                # District control summary
                if player_districts:
                    message += get_text("your_districts", lang) + "\n"
                    for district in player_districts:
                        district_id, name, control = district

                        # Determine control status
                        if control >= 80:
                            control_status = get_text("control_strong", lang)
                        elif control >= 60:
                            control_status = get_text("control_full", lang)
                        elif control >= 20:
                            control_status = get_text("control_contested", lang)
                        else:
                            control_status = get_text("control_weak", lang)

                        message += f"{name}: {control} {get_text('control_points', lang, count=control)} - {control_status}\n"

                    message += "\n"

                # News summary
                if recent_news:
                    message += get_text("recent_news", lang) + "\n"
                    for news_item in recent_news:
                        news_id, title, content, timestamp, is_public, target_player, is_fake = news_item
                        news_time = datetime.datetime.fromisoformat(timestamp).strftime("%H:%M")

                        # Escape special Markdown characters in title and content
                        safe_title = title.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`").replace("[",
                                                                                                               "\\[")

                        message += f"📰 {news_time} - *{safe_title}*\n"
                        # Truncate long content and escape special characters
                        content_to_show = content[:100] + "..." if len(content) > 100 else content
                        safe_content = content_to_show.replace("*", "\\*").replace("_", "\\_").replace("`",
                                                                                                       "\\`").replace(
                            "[", "\\[")
                        message += f"{safe_content}\n"

                    message += "\n"

                # Resources update
                resources = get_player_resources(player_id)
                if resources:
                    message += get_text("current_resources", lang) + "\n"
                    message += f"🔵 {get_text('influence', lang)}: {resources['influence']}\n"
                    message += f"💰 {get_text('resources', lang)}: {resources['resources']}\n"
                    message += f"🔍 {get_text('information', lang)}: {resources['information']}\n"
                    message += f"👊 {get_text('force', lang)}: {resources['force']}\n"

                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification to player {player_id}: {e}")

            except Exception as e:
                logger.error(f"Error preparing notification for player {player_id}: {e}")

        conn.close()
    except Exception as e:
        logger.error(f"Error in notify_players_of_results: {e}")


async def refresh_actions_job(context):
    """Refresh actions for all players every 3 hours."""
    try:
        # Get all active players
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT player_id FROM players")
        players = cursor.fetchall()
        conn.close()

        for player_id_tuple in players:
            player_id = player_id_tuple[0]

            try:
                # Refresh their actions
                refresh_player_actions(player_id)

                # Notify the player
                lang = get_player_language(player_id)
                await context.bot.send_message(
                    chat_id=player_id,
                    text=get_text("actions_refreshed_notification", lang)
                )
            except Exception as e:
                logger.error(f"Failed to refresh actions for player {player_id}: {e}")

        logger.info("Actions refreshed for all players")
    except Exception as e:
        logger.error(f"Error in refresh_actions_job: {e}")


def get_current_cycle():
    """Return the current game cycle (morning or evening)."""
    now = datetime.datetime.now().time()
    if MORNING_CYCLE_START <= now < EVENING_CYCLE_START:
        return "morning"
    else:
        return "evening"


def get_cycle_deadline():
    """Return the submission deadline for the current cycle."""
    now = datetime.datetime.now().time()
    if MORNING_CYCLE_START <= now < EVENING_CYCLE_START:
        return MORNING_CYCLE_DEADLINE
    else:
        return EVENING_CYCLE_DEADLINE


def get_cycle_results_time():
    """Return the results time for the current cycle."""
    now = datetime.datetime.now().time()
    if MORNING_CYCLE_START <= now < EVENING_CYCLE_START:
        return MORNING_CYCLE_RESULTS
    else:
        return EVENING_CYCLE_RESULTS


def process_coordinated_action(action_id):
    """Process a coordinated action with combined resources from all participants."""
    try:
        # Get the coordinated action
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT action_type, target_type, target_id, initiator_id
            FROM coordinated_actions
            WHERE action_id = ?
            """,
            (action_id,)
        )

        action = cursor.fetchone()
        if not action:
            return False, "Action not found"

        action_type, target_type, target_id, initiator_id = action

        # Get all participants' resources
        cursor.execute(
            """
            SELECT player_id, resources_used
            FROM coordinated_action_participants
            WHERE action_id = ?
            """,
            (action_id,)
        )

        participants = cursor.fetchall()
        if not participants:
            return False, "No participants"

        # Calculate total resources
        total_resources = {}
        for player_id, resources_json in participants:
            resources = json.loads(resources_json)
            for resource_type, amount in resources.items():
                if resource_type in total_resources:
                    total_resources[resource_type] += amount
                else:
                    total_resources[resource_type] = amount

        # Calculate total power based on resources
        power = calculate_coordinated_power(total_resources, action_type)

        # Apply the coordinated action effect
        if action_type == ACTION_ATTACK:
            result = process_coordinated_attack(target_id, power, initiator_id, participants)
        elif action_type == ACTION_DEFENSE:
            result = process_coordinated_defense(target_id, power, initiator_id, participants)
        else:
            return False, "Invalid action type"

        # Close the coordinated action
        cursor.execute(
            "UPDATE coordinated_actions SET status = 'closed' WHERE action_id = ?",
            (action_id,)
        )

        conn.commit()
        conn.close()

        return True, result

    except Exception as e:
        logger.error(f"Error processing coordinated action {action_id}: {e}")
        return False, str(e)


def calculate_coordinated_power(resources_list, action_type):
    """
    Calculate the combined power of a coordinated action based on all participants' resources.

    Args:
        resources_list: List of resource dictionaries from all participants
        action_type: Type of action (attack, defense, etc.)

    Returns:
        int: Total power value
    """
    # Combine all resources
    total_resources = {}
    for resources in resources_list:
        for resource_type, amount in resources.items():
            if resource_type in total_resources:
                total_resources[resource_type] += amount
            else:
                total_resources[resource_type] = amount

    # Calculate base power from combined resources
    base_power = 0
    for resource_type, amount in total_resources.items():
        if action_type == ACTION_ATTACK:
            if resource_type == "force":
                base_power += amount * 2
            elif resource_type == "influence":
                base_power += amount * 1.5
            else:
                base_power += amount
        elif action_type == ACTION_DEFENSE:
            if resource_type == "influence":
                base_power += amount * 2
            elif resource_type == "force":
                base_power += amount * 1.5
            else:
                base_power += amount
        else:
            base_power += amount

    # Apply synergy bonus based on number of participants
    participant_count = len(resources_list)
    if participant_count >= 4:
        synergy_multiplier = 1.3  # 30% bonus for 4+ participants
    elif participant_count >= 3:
        synergy_multiplier = 1.2  # 20% bonus for 3 participants
    elif participant_count >= 2:
        synergy_multiplier = 1.1  # 10% bonus for 2 participants
    else:
        synergy_multiplier = 1.0  # No bonus for solo actions

    # Apply diversity bonus based on resource types
    resource_types_used = set()
    for resources in resources_list:
        resource_types_used.update(resources.keys())

    if len(resource_types_used) >= 4:
        diversity_multiplier = 1.2  # 20% bonus for using all 4 resource types
    elif len(resource_types_used) >= 3:
        diversity_multiplier = 1.1  # 10% bonus for using 3 resource types
    else:
        diversity_multiplier = 1.0  # No bonus for less diversity

    # Final power calculation
    final_power = round(base_power * synergy_multiplier * diversity_multiplier)

    # Log the calculation for debugging
    logger.info(
        f"Coordinated {action_type} power: {final_power} (base: {base_power}, participants: {participant_count}, resources: {total_resources})")

    return final_power


def process_join_with_resources(player_id, action_id, resources_dict):
    """
    Process a player joining a coordinated action with specified resources.

    Args:
        player_id: Player ID
        action_id: Coordinated action ID
        resources_dict: Dictionary of resources {resource_type: amount}

    Returns:
        tuple: (success, message)
    """
    try:
        # Get action details
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check if action exists and is still open
        cursor.execute(
            """
            SELECT action_id, action_type, target_type, target_id, expires_at, status, initiator_id
            FROM coordinated_actions 
            WHERE action_id = ?
            """,
            (action_id,)
        )
        action = cursor.fetchone()

        if not action:
            conn.close()
            return False, "Action not found"

        action_id, action_type, target_type, target_id, expires_at_str, status, initiator_id = action

        # Don't allow initiator to join their own action again
        if player_id == initiator_id:
            conn.close()
            return False, "You cannot join your own action again"

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
            conn.close()
            return False, "You have already joined this action"

        if status != 'open':
            conn.close()
            return False, "Action is no longer open"

        # Check if action has expired
        expires_at = datetime.datetime.fromisoformat(expires_at_str)
        if datetime.datetime.now() > expires_at:
            # Update status to expired
            cursor.execute("UPDATE coordinated_actions SET status = 'expired' WHERE action_id = ?", (action_id,))
            conn.commit()
            conn.close()
            return False, "Action has expired"

        # Check if player has sufficient resources
        cursor.execute(
            """
            SELECT influence, resources, information, force
            FROM resources
            WHERE player_id = ?
            """,
            (player_id,)
        )
        player_resources = cursor.fetchone()

        if not player_resources:
            conn.close()
            return False, "Player resources not found"

        # Convert tuple to dict for easier checks
        available_resources = {
            "influence": player_resources[0],
            "resources": player_resources[1],
            "information": player_resources[2],
            "force": player_resources[3]
        }

        # Verify resources are available
        for resource_type, amount in resources_dict.items():
            if available_resources.get(resource_type, 0) < amount:
                conn.close()
                return False, f"Insufficient {resource_type} resources"

        # Deduct resources
        for resource_type, amount in resources_dict.items():
            cursor.execute(
                f"UPDATE resources SET {resource_type} = {resource_type} - ? WHERE player_id = ?",
                (amount, player_id)
            )

        # Add participant
        cursor.execute(
            """
            INSERT INTO coordinated_action_participants 
            (action_id, player_id, resources_used, joined_at)
            VALUES (?, ?, ?, ?)
            """,
            (action_id, player_id, json.dumps(resources_dict), datetime.datetime.now().isoformat())
        )

        conn.commit()
        conn.close()

        return True, "Successfully joined action"

    except Exception as e:
        logger.error(f"Error processing join with resources: {e}")
        return False, f"Error: {str(e)}"


def calculate_participant_power(resources, action_type):
    """
    Calculate a participant's power contribution based on resources.

    Args:
        resources: Dictionary of resources {resource_type: amount}
        action_type: Type of action (attack, defense, etc.)

    Returns:
        int: Power contribution value
    """
    base_power = 0

    for resource_type, amount in resources.items():
        if action_type == ACTION_ATTACK:
            if resource_type == "force":
                base_power += amount * 2  # Force is most effective for attacks
            elif resource_type == "influence":
                base_power += amount * 1.5  # Influence is moderately effective
            else:
                base_power += amount  # Other resources contribute base value
        elif action_type == ACTION_DEFENSE:
            if resource_type == "influence":
                base_power += amount * 2  # Influence is most effective for defense
            elif resource_type == "force":
                base_power += amount * 1.5  # Force is moderately effective
            else:
                base_power += amount  # Other resources contribute base value
        else:
            # Default contribution for other action types
            base_power += amount

    return round(base_power)


def process_coordinated_attack(district_id, attack_power, initiator_id, participants):
    """Process a coordinated attack action on a district."""
    try:
        # Get current control data for the district
        from db.queries import get_district_control
        control_data = get_district_control(district_id)

        # Get the district name for messages
        from game.districts import get_district_by_id
        district = get_district_by_id(district_id)
        district_name = district['name'] if district else district_id

        # Get participant names for messages
        participant_names = []
        for p in participants:
            # Participant tuple structure: (player_id, resources_json, joined_at, character_name)
            if len(p) >= 4:
                participant_names.append(p[3])
            else:
                participant_names.append(f"Player {p[0]}")

        if not control_data:
            # No one controls the district, so attackers gain control
            # Distribute control points proportionally among participants
            for participant in participants:
                participant_id = participant[0]  # First element is player_id

                # Give each participant a share of the control points
                participant_share = round(attack_power / len(participants))
                from db.queries import update_district_control
                update_district_control(participant_id, district_id, participant_share)

            return {
                "success": True,
                "message": f"Coordinated attack successful on uncontrolled district {district_name}",
                "participants": participant_names,
                "control_gained": attack_power
            }

        # Find the player with the most control points (the defender)
        defender_id, defender_control, defender_name = max(control_data, key=lambda x: x[1])

        # Don't attack yourself or other participants
        participant_ids = [p[0] for p in participants]
        if defender_id in participant_ids:
            # Find the next highest controller not in participants
            filtered_control_data = [c for c in control_data if c[0] not in participant_ids]
            if not filtered_control_data:
                return {
                    "success": False,
                    "message": f"No suitable target found in {district_name}.",
                    "participants": participant_names
                }
            defender_id, defender_control, defender_name = max(filtered_control_data, key=lambda x: x[1])

        # Check if the defender has active defense
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT defense_bonus FROM district_defense 
            WHERE district_id = ? AND player_id = ? AND expires_at > ?
            """,
            (district_id, defender_id, datetime.datetime.now().isoformat())
        )
        defense_result = cursor.fetchone()
        conn.close()

        defense_bonus = defense_result[0] if defense_result else 0

        # Calculate effect of attack vs defense
        net_attack = max(0, attack_power - defense_bonus)

        # Reduce defender control
        defender_new_control = max(0, defender_control - net_attack)
        defender_loss = defender_control - defender_new_control

        # Update defender control
        from db.queries import update_district_control
        update_district_control(defender_id, district_id, -defender_loss)

        # If defense completely blocked the attack
        if defender_loss == 0:
            return {
                "success": False,
                "message": f"Attack on {district_name} was blocked by {defender_name}'s defenses.",
                "participants": participant_names,
                "target_player": defender_name,
                "defense_bonus": defense_bonus
            }

        # Distribute gained control among participants proportionally
        for participant in participants:
            participant_id = participant[0]

            # Calculate participant's contribution to the attack
            participant_resources = json.loads(participant[1])  # Parse resource JSON
            participant_power = calculate_participant_power(participant_resources, ACTION_ATTACK)

            # Share of gained control based on contribution
            contribution_ratio = participant_power / max(1, attack_power)
            participant_share = round(defender_loss * contribution_ratio)

            update_district_control(participant_id, district_id, participant_share)

        # Add a news item about the attack
        from db.queries import add_news
        news_title = f"Coordinated Attack on {district_name}"
        news_content = f"A coordinated attack led by {participant_names[0]} with {len(participants)} participants successfully reduced {defender_name}'s control by {defender_loss} points."
        add_news(news_title, news_content)

        return {
            "success": True,
            "message": f"Coordinated attack successful against {defender_name} in {district_name}",
            "participants": participant_names,
            "defender": defender_name,
            "control_taken": defender_loss,
            "defense_blocked": defense_bonus
        }

    except Exception as e:
        logger.error(f"Error processing coordinated attack: {e}")
        return {"success": False, "message": str(e)}


def process_coordinated_defense(district_id, defense_power, initiator_id, participants):
    """Process a coordinated defense action on a district."""
    try:
        # Get the district name for messages
        from game.districts import get_district_by_id
        district = get_district_by_id(district_id)
        district_name = district['name'] if district else district_id

        # Get participant names for messages
        participant_names = []
        for p in participants:
            if len(p) >= 4:
                participant_names.append(p[3])
            else:
                participant_names.append(f"Player {p[0]}")

        # Set up the defense to last until the end of the cycle
        now = datetime.datetime.now()

        # Determine cycle end time based on current time
        if now.hour < 13:  # Morning cycle
            expires_at = datetime.datetime.combine(now.date(), datetime.time(13, 0))
        else:  # Evening cycle
            if now.hour < 19:
                expires_at = datetime.datetime.combine(now.date(), datetime.time(19, 0))
            else:
                # If it's after 19:00, set to 13:00 next day
                tomorrow = now.date() + datetime.timedelta(days=1)
                expires_at = datetime.datetime.combine(tomorrow, datetime.time(13, 0))

        # Record defense bonuses for each participant
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        for participant in participants:
            participant_id = participant[0]

            # Calculate participant's individual defense contribution
            participant_resources = json.loads(participant[1])
            participant_power = calculate_participant_power(participant_resources, ACTION_DEFENSE)

            # Insert or update defense bonus
            cursor.execute(
                """
                INSERT OR REPLACE INTO district_defense
                (district_id, player_id, defense_bonus, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (district_id, participant_id, participant_power, expires_at.isoformat())
            )

            # Also increment control points for the district (reinforcement)
            from db.queries import update_district_control
            control_increase = round(participant_power / 2)  # Half of defense power translates to control
            update_district_control(participant_id, district_id, control_increase)

        conn.commit()
        conn.close()

        # Add a news item about the defense
        from db.queries import add_news
        news_title = f"Coordinated Defense of {district_name}"
        news_content = f"A coordinated defense led by {participant_names[0]} with {len(participants)} participants has fortified their positions in {district_name}."
        add_news(news_title, news_content)

        return {
            "success": True,
            "message": f"Coordinated defense successful in {district_name}",
            "participants": participant_names,
            "defense_power": defense_power,
            "expires_at": expires_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing coordinated defense: {e}")
        return {"success": False, "message": str(e)}


def process_attack(district_id, resources):
    """Process an attack action with combined resources."""
    try:
        # Get current control points
        current_control = get_district_control(district_id)

        # Calculate attack power
        attack_power = 0
        for resource_type, amount in resources.items():
            if resource_type == "force":
                attack_power += amount * 2  # Force is most effective for attacks
            elif resource_type == "influence":
                attack_power += amount * 1.5  # Influence is moderately effective
            else:
                attack_power += amount  # Other resources are less effective

        # Apply attack
        new_control = max(0, current_control - attack_power)
        update_district_control(district_id, new_control)

        return {
            "success": True,
            "message": f"Attack successful. District control reduced by {attack_power} points.",
            "new_control": new_control
        }
    except Exception as e:
        logger.error(f"Error processing attack: {e}")
        return {"success": False, "message": str(e)}


def process_defense(district_id, resources):
    """Process a defense action with combined resources."""
    try:
        # Get current control points
        current_control = get_district_control(district_id)

        # Calculate defense power
        defense_power = 0
        for resource_type, amount in resources.items():
            if resource_type == "influence":
                defense_power += amount * 2  # Influence is most effective for defense
            elif resource_type == "force":
                defense_power += amount * 1.5  # Force is moderately effective
            else:
                defense_power += amount  # Other resources are less effective

        # Apply defense
        new_control = min(100, current_control + defense_power)
        update_district_control(district_id, new_control)

        return {
            "success": True,
            "message": f"Defense successful. District control increased by {defense_power} points.",
            "new_control": new_control
        }
    except Exception as e:
        logger.error(f"Error processing defense: {e}")
        return {"success": False, "message": str(e)}


def get_next_cycle_time(is_morning=True):
    """Calculate the next time for a morning (8:00) or evening (20:00) cycle."""
    now = datetime.datetime.now()
    target_hour = 8 if is_morning else 20
    
    # Create a datetime for today at the target hour
    target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    
    # If that time has already passed today, move to tomorrow
    if now >= target_time:
        target_time += datetime.timedelta(days=1)
    
    # Calculate seconds until that time
    time_diff = (target_time - now).total_seconds()
    return time_diff


async def morning_cycle(context: ContextTypes.DEFAULT_TYPE):
    """Run the morning cycle tasks: distributing resources, resetting actions."""
    try:
        logger.info("Starting morning cycle...")
        
        # Notify users
        await send_cycle_notification(context, is_morning=True)
        
        # Reset player operations
        reset_player_operations()
        
        # Distribute resources
        distribute_resources()
        
        # Create news about the cycle
        create_cycle_news(is_morning=True)
        
        logger.info("Morning cycle completed successfully")
    except Exception as e:
        logger.error(f"Error during morning cycle: {e}", exc_info=True)


async def evening_cycle(context: ContextTypes.DEFAULT_TYPE):
    """Run the evening cycle tasks: distributing resources, resetting actions."""
    try:
        logger.info("Starting evening cycle...")
        
        # Notify users
        await send_cycle_notification(context, is_morning=False)
        
        # Reset player operations
        reset_player_operations()
        
        # Distribute resources
        distribute_resources()
        
        # Create news about the cycle
        create_cycle_news(is_morning=False)
        
        logger.info("Evening cycle completed successfully")
    except Exception as e:
        logger.error(f"Error during evening cycle: {e}", exc_info=True)


async def cleanup_expired_actions(context: ContextTypes.DEFAULT_TYPE):
    """Clean up expired coordinated actions."""
    try:
        logger.info("Cleaning up expired coordinated actions...")
        
        # Get expired actions and notify their initiators
        from db.queries import cleanup_expired_actions as db_cleanup
        expired_count = db_cleanup()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired coordinated actions")
        else:
            logger.info("No expired coordinated actions found")
            
    except Exception as e:
        logger.error(f"Error during cleanup of expired actions: {e}", exc_info=True)


@db_transaction
def reset_player_operations(cursor):
    """Reset the operations_left counter for all players."""
    cursor.execute("UPDATE players SET main_actions_left = 3, quick_actions_left = 3")
    logger.info("Reset actions for all players")


@db_transaction
def distribute_resources(cursor):
    """Distribute resources to players based on district control."""
    # Get all players
    cursor.execute("SELECT player_id FROM players")
    players = cursor.fetchall()
    
    for player_id in [p[0] for p in players]:
        # Count controlled districts
        cursor.execute("""
            SELECT COUNT(*) FROM district_control 
            WHERE player_id = ? AND control_points > 30
        """, (player_id,))
        district_count = cursor.fetchone()[0]
        
        # Base resource amount
        base_amount = 5
        
        # Calculate resource amounts based on district control
        # More districts = more resources
        influence = base_amount + (district_count * 3)
        information = base_amount + (district_count * 2)
        force = base_amount + (district_count * 2)
        
        # Update player resources
        cursor.execute(
            """
            UPDATE resources 
            SET influence = influence + ?, 
                information = information + ?, 
                force = force + ?
            WHERE player_id = ?
            """, 
            (influence, information, force, player_id)
        )
        
        logger.info(f"Distributed resources to player {player_id}: I:{influence} S:{information} F:{force}")


@db_transaction
def create_cycle_news(cursor, is_morning=True):
    """Create a news entry for the game cycle."""
    cycle_type = "Morning" if is_morning else "Evening"
    
    # Create news entry
    cursor.execute(
        """
        INSERT INTO news (content) 
        VALUES (?)
        """,
        (
            f"The {cycle_type.lower()} cycle has begun. All players have received resources and actions have been reset.",
        )
    )
    
    logger.info(f"Created news entry for {cycle_type.lower()} cycle")


async def send_cycle_notification(context: ContextTypes.DEFAULT_TYPE, is_morning=True):
    """Send notifications to all players about the new cycle."""
    try:
        # Connect to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all players
            cursor.execute("SELECT player_id, lang FROM players")
            players = cursor.fetchall()
            
            cycle_type = "cycle_morning" if is_morning else "cycle_evening"
            
            # Send notifications
            for player_id, lang in players:
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=get_text(cycle_type, lang)
                    )
                    logger.info(f"Sent cycle notification to player {player_id}")
                except Exception as e:
                    logger.error(f"Failed to send cycle notification to player {player_id}: {e}")
    except Exception as e:
        logger.error(f"Error during cycle notification: {e}", exc_info=True)
