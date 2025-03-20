import datetime
import json
import logging
import random
import sqlite3
from typing import Dict, Any, List, Optional, Literal

from db.queries import (
    distribute_district_resources,
    add_news, get_news, get_player_resources, get_player_language,
    get_player_districts, refresh_player_actions, db_transaction, db_connection_pool
)
from game.news import create_cycle_summary
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
CYCLE_DURATION = datetime.timedelta(hours=3)
CYCLE_STARTS = [
    datetime.time(0, 0),  # 00:00
    datetime.time(3, 0),  # 03:00
    datetime.time(6, 0),  # 06:00
    datetime.time(9, 0),  # 09:00
    datetime.time(12, 0),  # 12:00
    datetime.time(15, 0),  # 15:00
    datetime.time(18, 0),  # 18:00
    datetime.time(21, 0)  # 21:00
]


async def process_game_cycle(context):
    """Process actions and update game state at the end of a cycle."""
    now = datetime.datetime.now()
    current_time = now.time()

    # Determine current cycle
    if datetime.time(6, 0) <= current_time < datetime.time(18, 0):
        cycle = "morning"
    else:
        cycle = "evening"

    logger.info(f"Processing {cycle} cycle at {now}")

    try:
        # Process all actions for this cycle in a transaction
        await asyncio.get_event_loop().run_in_executor(
            executor,
            process_all_cycle_actions,
            cycle
        )

        # Process joint actions
        await asyncio.get_event_loop().run_in_executor(
            executor,
            process_expired_joint_actions
        )

        # Apply district decay
        await asyncio.get_event_loop().run_in_executor(
            executor,
            apply_district_decay
        )

        # Distribute resources
        await asyncio.get_event_loop().run_in_executor(
            executor,
            distribute_district_resources
        )

        # Process international politicians
        active_politicians = await asyncio.get_event_loop().run_in_executor(
            executor,
            get_random_international_politicians,
            1, 3  # min_count, max_count
        )

        for politician_id in active_politicians:
            await asyncio.get_event_loop().run_in_executor(
                executor,
                process_international_politician_action,
                politician_id
            )

        # Create cycle summary
        cycle_number = current_time.hour // 3
        await asyncio.get_event_loop().run_in_executor(
            executor,
            create_cycle_summary,
            cycle_number
        )

        # Notify players of results
        await notify_players_of_results(context, cycle)

        logger.info(f"Completed processing {cycle} cycle")

    except Exception as e:
        logger.error(f"Error processing game cycle: {e}")
        import traceback
        tb_list = traceback.format_exception(None, e, e.__traceback__)
        tb_string = ''.join(tb_list)
        logger.error(f"Exception traceback:\n{tb_string}")


# Add this function to properly handle all cycle actions in a transaction
@db_transaction
def process_all_cycle_actions(conn, cycle: str):
    """Process all actions for a cycle in a single transaction."""
    cursor = conn.cursor()

    # Get all pending actions for this cycle
    cursor.execute(
        "SELECT action_id, player_id, action_type, target_type, target_id FROM actions WHERE status = 'pending' AND cycle = ?",
        (cycle,)
    )
    actions = cursor.fetchall()

    for action in actions:
        try:
            action_id, player_id, action_type, target_type, target_id = action
            process_single_action_in_transaction(conn, action_id, player_id, action_type, target_type, target_id)
        except Exception as e:
            logger.error(f"Error processing action {action[0]}: {e}")
            # Continue to next action


def process_single_action_in_transaction(conn, action_id, player_id, action_type, target_type, target_id):
    """Process a single action within an existing transaction."""
    try:
        result = process_action_in_transaction(conn, player_id, action_type, target_type, target_id)

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE actions SET status = 'completed', result = ? WHERE action_id = ?",
            (json.dumps(result), action_id)
        )
        return True
    except Exception as e:
        logger.error(f"Error processing single action {action_id}: {e}")
        return False


# Use database connection pool with the db_transaction decorator
@db_transaction
def get_pending_actions(conn, cycle: str) -> List[tuple]:
    """Get all pending actions for a cycle using the connection pool."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action_id, player_id, action_type, target_type, target_id FROM actions WHERE status = 'pending' AND cycle = ?",
            (cycle,)
        )
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting pending actions: {e}")
        return []



@db_transaction
def process_single_action(conn, action_id: int, player_id: int, action_type: str, target_type: str, target_id: str) -> bool:
    """Process a single action using the connection pool."""
    try:
        # Process the action
        result = process_action(conn, player_id, action_type, target_type, target_id)

        # Update status
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE actions SET status = 'completed', result = ? WHERE action_id = ?",
            (json.dumps(result), action_id)
        )
        return True
    except Exception as e:
        logger.error(f"Error processing single action {action_id}: {e}")
        return False


@db_transaction
def apply_district_decay(conn) -> bool:
    """Apply decay to district control using the connection pool."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE district_control SET control_points = MAX(0, control_points - 5) WHERE control_points > 0"
        )
        return True
    except Exception as e:
        logger.error(f"Error applying district decay: {e}")
        return False


def get_random_international_politicians(min_count: int, max_count: int) -> List[int]:
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


def calculate_action_success(
        action_type: Literal["influence", "attack", "defense"],
        player_id: int,
        target_id: str,
        power_multiplier: float = 1.0
) -> Dict[str, Any]:
    """
    Calculate success chance and result of an action.

    Args:
        action_type: Type of action (influence, attack, defense)
        player_id: ID of the player performing the action
        target_id: ID of the target district
        power_multiplier: Optional power multiplier for joint actions

    Returns:
        Dict containing success result information
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        base_success = {
            'influence': 70,  # 70% базовый шанс для влияния
            'attack': 60,  # 60% базовый шанс для атаки
            'defense': 80  # 80% базовый шанс для обороны
        }

        # Получаем базовый шанс успеха
        success_chance = base_success.get(action_type, 50)

        # Получаем контроль игрока в районе
        cursor.execute("""
            SELECT control_points 
            FROM district_control 
            WHERE district_id = ? AND player_id = ?
        """, (target_id, player_id))

        player_control = cursor.fetchone()
        player_control = player_control[0] if player_control else 0

        # Модификаторы от контроля района
        if player_control >= 75:
            success_chance += 20  # +20% за абсолютный контроль
        elif player_control >= 50:
            success_chance += 15  # +15% за полный контроль
        elif player_control >= 35:
            success_chance += 10  # +10% за уверенный контроль
        elif player_control >= 20:
            success_chance += 5  # +5% за частичный контроль

        # Применяем множитель силы (для совместных действий)
        success_chance = min(95, int(success_chance * power_multiplier))

        # Генерируем результат
        roll = random.randint(1, 100)

        result = {
            'roll': roll,
            'chance': success_chance,
            'power_multiplier': power_multiplier,
            'control_bonus': success_chance - base_success[action_type],
            'base_chance': base_success[action_type]
        }

        if roll <= success_chance:
            if roll <= success_chance - 20:
                result['status'] = 'critical'  # Критический успех
                result['effect_multiplier'] = 1.5
            else:
                result['status'] = 'success'  # Обычный успех
                result['effect_multiplier'] = 1.0
        else:
            if roll >= success_chance + 20:
                result['status'] = 'failure'  # Полный провал
                result['effect_multiplier'] = 0
            else:
                result['status'] = 'partial'  # Частичный успех
                result['effect_multiplier'] = 0.5

        conn.close()
        return result

    except Exception as e:
        logger.error(f"Error calculating action success: {e}")
        return {'status': 'failure', 'effect_multiplier': 0}


def process_action(action_id: int, player_id: int, action_type: str, target_type: str, target_id: str,
                   power_multiplier: float = 1.0) -> Dict[str, Any]:
    """Process an action with optional power multiplier for joint actions"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Get player's language
        lang = get_player_language(player_id)
        
        # Initialize result dictionary
        result = {
            'success': True,
            'messages': [],
            'effects': {}
        }

        # Calculate success chance and roll
        success_result = calculate_action_success(action_type, player_id, target_id, power_multiplier)
        
        # Get location bonus
        location_bonus = get_location_bonus(player_id, target_id)
        
        # Base effects for different action types
        base_effects = {
            'influence': {'control_points': 10},
            'attack': {'control_points': 15},
            'support': {'control_points': 8},
            'defend': {'control_points': 12}
        }

        if action_type in base_effects:
            effect = base_effects[action_type]
            # Apply multipliers to control points including location bonus
            base_control_points = effect['control_points']
            location_multiplier = 1.0 + (location_bonus / base_control_points)  # Convert bonus to multiplier
            total_control_points = int(base_control_points * power_multiplier * success_result['effect_multiplier'] * location_multiplier)

            if target_type == 'district':
                # Update district control
                cursor.execute("""
                    UPDATE district_control 
                    SET control_points = control_points + ?
                    WHERE district_id = ? AND player_id = ?
                """, (total_control_points, target_id, player_id))

                # If no rows affected, create new record
                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO district_control (district_id, player_id, control_points)
                        VALUES (?, ?, ?)
                    """, (target_id, player_id, total_control_points))

                result['effects']['control_points'] = total_control_points

                # Add result message
                result['messages'].append(
                    get_text(f"action_result_{success_result['status']}", lang,
                             action=get_text(f"action_type_{action_type}", lang),
                             target=target_id,
                             roll=success_result['roll'],
                             chance=success_result['chance'])
                )

                # If there was a power multiplier, add message
                if power_multiplier != 1.0:
                    result['messages'].append(
                        get_text("joint_action_power_increase", lang,
                                 percent=f"{(power_multiplier - 1) * 100:.0f}")
                    )
                
                # If there was a location bonus, add message
                if location_bonus > 0:
                    result['messages'].append(
                        get_text("location_bonus_applied", lang,
                                 bonus=location_bonus)
                    )

        conn.commit()
        conn.close()
        return result

    except Exception as e:
        logger.error(f"Error processing action: {e}")
        return {
            'success': False,
            'messages': [str(e)],
            'effects': {}
        }


def process_international_politician_action(politician_id: int) -> Optional[Dict[str, Any]]:
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


async def schedule_jobs(context):
    """Set up scheduled jobs for game cycle processing."""
    job_queue = context.job_queue

    # Schedule morning cycle results
    morning_time = datetime.time(hour=CYCLE_STARTS[4].hour, minute=CYCLE_STARTS[4].minute)
    job_queue.run_daily(process_game_cycle, time=morning_time)

    # Schedule evening cycle results
    evening_time = datetime.time(hour=CYCLE_STARTS[6].hour, minute=CYCLE_STARTS[6].minute)
    job_queue.run_daily(process_game_cycle, time=evening_time)

    # Schedule periodic action refreshes every 3 hours
    job_queue.run_repeating(refresh_actions_job, interval=3 * 60 * 60)

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
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT player_id FROM players")
            players = cursor.fetchall()

        for player_id_tuple in players:
            player_id = player_id_tuple[0]

            try:
                # Refresh their actions using the decorator
                await asyncio.get_event_loop().run_in_executor(
                    executor,
                    refresh_player_actions,
                    player_id
                )

                # Notify the player
                try:
                    lang = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        get_player_language,
                        player_id
                    )

                    await context.bot.send_message(
                        chat_id=player_id,
                        text=get_text("actions_refreshed_notification", lang)
                    )
                except Exception as e:
                    logger.error(f"Failed to notify player {player_id} about action refresh: {e}")

            except Exception as e:
                logger.error(f"Failed to refresh actions for player {player_id}: {e}")

        logger.info("Actions refreshed for all players")
    except Exception as e:
        logger.error(f"Error in refresh_actions_job: {e}")


def get_current_cycle():
    """Return the current game cycle (morning or evening)."""
    now = datetime.datetime.now().time()

    # Morning cycle: 06:00 to 17:59
    if datetime.time(6, 0) <= now < datetime.time(18, 0):
        return "morning"
    # Evening cycle: 18:00 to 05:59
    else:
        return "evening"


def get_cycle_deadline():
    """Return the submission deadline for the current cycle."""
    now = datetime.datetime.now().time()

    # Morning cycle deadline: 12:00
    if datetime.time(6, 0) <= now < datetime.time(18, 0):
        return datetime.time(12, 0)
    # Evening cycle deadline: 24:00
    else:
        return datetime.time(0, 0)


def get_cycle_results_time():
    """Return the results time for the current cycle."""
    now = datetime.datetime.now().time()

    # Morning cycle results: 13:00
    if datetime.time(6, 0) <= now < datetime.time(18, 0):
        return datetime.time(13, 0)
    # Evening cycle results: 19:00
    else:
        return datetime.time(19, 0)


def calculate_cycles_between(start_time: str, end_time: str) -> int:
    """
    Calculate the number of game cycles between two timestamps.

    Args:
        start_time: ISO format timestamp
        end_time: ISO format timestamp

    Returns:
        int: Number of cycles
    """
    try:
        start = datetime.datetime.fromisoformat(start_time)
        end = datetime.datetime.fromisoformat(end_time)

        # Calculate days difference
        days_diff = (end.date() - start.date()).days

        # Calculate cycles in the day
        start_cycle = 0 if start.time() < datetime.time(18, 0) else 1
        end_cycle = 0 if end.time() < datetime.time(18, 0) else 1

        # Total cycles
        return days_diff * 2 + end_cycle - start_cycle
    except Exception as e:
        logger.error(f"Error calculating cycles between: {e}")
        return 0

def calculate_quick_action_success(action_type: str, player_id: int, target_id: str) -> dict:
    """Calculate success chance and result of a quick action."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Базовые шансы для быстрых действий
        base_success = {
            'scout': 85,  # Разведка - высокий шанс успеха
            'info': 75,  # Сбор информации
            'support': 70  # Поддержка
        }

        # Получаем базовый шанс успеха
        success_chance = base_success.get(action_type, 50)

        # Получаем контроль игрока в районе
        cursor.execute("""
            SELECT control_points 
            FROM district_control 
            WHERE district_id = ? AND player_id = ?
        """, (target_id, player_id))

        player_control = cursor.fetchone()
        player_control = player_control[0] if player_control else 0

        # Модификаторы от контроля района (меньше влияют на быстрые действия)
        if player_control >= 75:
            success_chance += 10  # +10% за абсолютный контроль
        elif player_control >= 50:
            success_chance += 7  # +7% за полный контроль
        elif player_control >= 35:
            success_chance += 5  # +5% за уверенный контроль
        elif player_control >= 20:
            success_chance += 3  # +3% за частичный контроль

        # Максимальный шанс 95%
        success_chance = min(95, success_chance)

        # Генерируем результат
        roll = random.randint(1, 100)

        result = {
            'roll': roll,
            'chance': success_chance,
            'control_bonus': success_chance - base_success[action_type],
            'base_chance': base_success[action_type]
        }

        # Для быстрых действий - упрощённая система успеха
        if roll <= success_chance:
            result['status'] = 'success'
            result['effect_multiplier'] = 1.0
        else:
            result['status'] = 'failure'
            result['effect_multiplier'] = 0

        conn.close()
        return result

    except Exception as e:
        logger.error(f"Error calculating quick action success: {e}")
        return {'status': 'failure', 'effect_multiplier': 0}


def calculate_action_power(action_type: str, resources: dict) -> dict:
    """Calculate action power based on resources used."""
    power = {
        'base_power': 10,  # Базовая сила действия
        'bonus_power': 0,  # Бонусная сила от комбинаций
        'special_effects': []  # Специальные эффекты
    }

    # Бонусы за основной ресурс
    primary_resources = {
        'influence': 'influence',
        'attack': 'force',
        'defense': 'force'
    }

    primary = primary_resources.get(action_type)
    if primary and resources.get(primary, 0) >= 2:
        power['bonus_power'] += 5  # +5 за использование двух основных ресурсов
        power['special_effects'].append('primary_boost')

    # Бонусы за комбинации
    if 'influence' in resources and 'information' in resources:
        power['bonus_power'] += 3  # +3 за комбинацию влияние + информация
        power['special_effects'].append('precision')

    if 'force' in resources and 'influence' in resources:
        power['bonus_power'] += 3  # +3 за комбинацию сила + влияние
        power['special_effects'].append('coordinated')

    if 'force' in resources and 'information' in resources:
        power['bonus_power'] += 3  # +3 за комбинацию сила + информация
        power['special_effects'].append('tactical')

    # Специальные эффекты от ресурсов
    if 'information' in resources:
        power['special_effects'].append('reveal')  # Раскрывает информацию о цели

    if 'resources' in resources:
        power['special_effects'].append('sustain')  # Продлевает эффект

    return power
