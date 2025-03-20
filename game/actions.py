import logging
import datetime
import json
import random
import sqlite3
from db.queries import (
    add_action, update_district_control, distribute_district_resources,
    get_district_control, get_district_info, get_politician_info,
    add_news, get_news, get_player_resources, get_player_districts,
    get_remaining_actions, update_player_resources, get_player_language,
    get_player_districts, refresh_player_actions
)
from languages import get_text, get_cycle_name

logger = logging.getLogger(__name__)

# Constants for action types
ACTION_INFLUENCE = "influence"
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defense"
QUICK_ACTION_RECON = "recon"
QUICK_ACTION_INFO = "info"
QUICK_ACTION_SUPPORT = "support"

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

    if target_type == "district":
        if action_type == ACTION_INFLUENCE:
            # Process influence action on district
            success_roll = random.randint(1, 100)

            if success_roll > 70:  # Success
                update_district_control(player_id, target_id, 10)
                result = {"status": "success", "message": f"Successfully increased influence in {target_id}",
                          "control_change": 10}
            elif success_roll > 30:  # Partial success
                update_district_control(player_id, target_id, 5)
                result = {"status": "partial", "message": f"Partially increased influence in {target_id}",
                          "control_change": 5}
            else:  # Failure
                result = {"status": "failure", "message": f"Failed to increase influence in {target_id}",
                          "control_change": 0}

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
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()

    # Get all active players
    cursor.execute("SELECT player_id FROM players")
    players = cursor.fetchall()

    for player_id_tuple in players:
        player_id = player_id_tuple[0]

        # Refresh their actions
        cursor.execute(
            "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
            (datetime.datetime.now().isoformat(), player_id)
        )

        # Notify the player
        try:
            lang = get_player_language(player_id)
            await context.bot.send_message(
                chat_id=player_id,
                text=get_text("actions_refreshed_notification", lang)
            )
        except Exception as e:
            logger.error(f"Failed to notify player {player_id} about action refresh: {e}")

    conn.commit()
    conn.close()

    logger.info("Actions refreshed for all players")


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
    except Exception as e:
        logger.error(f"Error processing international politician {politician_id}: {e}")
        return None


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
                        action_msg = result.get('message', get_text("no_details", lang))

                        # Format based on status
                        if status == 'success':
                            status_emoji = get_text("status_success", lang)
                        elif status == 'partial':
                            status_emoji = get_text("status_partial", lang)
                        elif status == 'failure':
                            status_emoji = get_text("status_failure", lang)
                        else:
                            status_emoji = get_text("status_info", lang)

                        message += f"{status_emoji} {action_type.capitalize()} - {action_msg}\n"

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
