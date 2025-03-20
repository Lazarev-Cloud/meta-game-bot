import datetime
import json
import logging
import random
import sqlite3

from db.queries import (
    update_district_control, distribute_district_resources,
    get_district_control, get_district_info, add_news, get_news, get_player_resources, get_player_language,
    get_player_districts, refresh_player_actions
)
from languages import get_text, get_cycle_name

logger = logging.getLogger(__name__)

# Main actions (strategic, major impact)
ACTION_INFLUENCE = "influence"
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defense"

# Quick actions (tactical, minor impact)
QUICK_ACTION_RECON = "recon"
QUICK_ACTION_INFO = "info"
QUICK_ACTION_SUPPORT = "support"

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
    if action_type not in [ACTION_INFLUENCE, ACTION_ATTACK, ACTION_DEFENSE]:
        return {"applied": False, "bonus": 0}

    # In a real implementation, you would check if the player is physically present
    # For now, we'll use a placeholder check based on the player's recent activity
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check for a record of physical presence
        cursor.execute(
            """
            SELECT is_present FROM player_presence 
            WHERE player_id = ? AND district_id = ? AND timestamp > ?
            """,
            (player_id, district_id, (datetime.datetime.now() - datetime.timedelta(hours=6)).isoformat())
        )
        presence = cursor.fetchone()

        conn.close()

        if presence and presence[0]:
            # Apply +20 CP bonus
            return {"applied": True, "bonus": 20}

    except Exception as e:
        logger.error(f"Error checking physical presence: {e}")

    return {"applied": False, "bonus": 0}


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
