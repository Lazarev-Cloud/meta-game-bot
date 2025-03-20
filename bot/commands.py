import logging
import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any, Tuple

from telegram.constants import ParseMode

from db.queries import get_player_language as db_get_player_language, update_action_counts, get_player_language, \
    reset_player_actions, get_player_districts, get_all_districts, distribute_district_resources, update_base_resources
from languages import get_player_language as lang_get_player_language

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from config import ADMIN_IDS
from languages import get_text, get_cycle_name, get_resource_name
from db.queries import (
    register_player, get_player, get_player_resources, update_player_resources,
    get_district_info, get_district_control, update_district_control,
    get_politician_info, update_politician_friendliness,
    add_action, cancel_last_action, get_remaining_actions, use_action,
    add_news, get_news, create_trade_offer, accept_trade_offer,
    update_player_location, get_player_location, db_transaction
)
from db.schema import setup_database
from game.districts import (
    format_district_info, get_district_by_name
)
from game.politicians import (
    format_politicians_list, format_politician_info, get_politician_by_name,
    get_politician_abilities
)
from game.actions import (
    process_game_cycle, get_current_cycle, get_cycle_deadline, get_cycle_results_time
)

logger = logging.getLogger(__name__)

# Chat states for conversation handlers
WAITING_NAME = "WAITING_NAME"
WAITING_INFO_CONTENT = "WAITING_INFO_CONTENT"

# Thread pool for database operations
executor = ThreadPoolExecutor(max_workers=4)


# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation and ask for player name."""
    user = update.effective_user

    # Run database operation in thread pool
    await asyncio.get_event_loop().run_in_executor(
        executor,
        register_player,
        user.id,
        user.username
    )

    # Default to English for new users
    lang = "en"

    await update.message.reply_text(
        get_text("welcome", lang, user_name=user.first_name)
    )

    return WAITING_NAME


async def set_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the player's character name."""
    user = update.effective_user
    character_name = update.message.text.strip()

    # Default to English for new users
    lang = "en"

    if not character_name:
        await update.message.reply_text(get_text("invalid_name", lang))
        return WAITING_NAME

    # Run database operation in thread pool
    success = await asyncio.get_event_loop().run_in_executor(
        executor,
        register_player,
        user.id,
        character_name
    )

    if success:
        await update.message.reply_text(
            get_text("name_set", lang, character_name=character_name)
        )
    else:
        await update.message.reply_text(
            get_text("error_setting_name", lang, default="Error setting character name. Please try again.")
        )

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    await update.message.reply_text(get_text("operation_cancelled", lang))
    return ConversationHandler.END


async def admin_add_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to add resources to a player."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(get_text("admin_resources_usage", lang))
        return

    try:
        player_id = int(args[0])
        resource_type = args[1].lower()
        amount = int(args[2])
    except ValueError:
        await update.message.reply_text(get_text("admin_invalid_args", lang))
        return

    if resource_type not in ["influence", "resources", "information", "force"]:
        await update.message.reply_text(get_text("admin_invalid_resource", lang))
        return

    # Check if player exists
    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        player_id
    )

    if not player:
        await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
        return

    # Update resources
    try:
        new_amount = await asyncio.get_event_loop().run_in_executor(
            executor,
            update_player_resources,
            player_id,
            resource_type,
            amount
        )

        await update.message.reply_text(
            get_text("admin_resources_added", lang,
                     amount=amount,
                     resource_type=get_resource_name(resource_type, lang),
                     player_id=player_id,
                     new_amount=new_amount)
        )
    except Exception as e:
        logger.error(f"Error in admin_add_resources: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


@db_transaction
def get_districts_for_selection(conn, lang="en"):
    """Get list of districts for selection menu."""
    cursor = conn.cursor()
    cursor.execute("SELECT district_id, name FROM districts ORDER BY name")
    districts = cursor.fetchall()
    return districts


@db_transaction
def get_player_status(conn, player_id):
    """Get all player status data in a single transaction."""
    try:
        cursor = conn.cursor()

        # Get player info and all related data in efficient queries
        cursor.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
        player = cursor.fetchone()

        if not player:
            return None

        lang = player[7] if len(player) > 7 and player[7] else "en"

        # Get resources in one query
        cursor.execute("SELECT influence, resources, information, force FROM resources WHERE player_id = ?",
                       (player_id,))
        resources_data = cursor.fetchone()
        resources = {
            "influence": resources_data[0] if resources_data else 0,
            "resources": resources_data[1] if resources_data else 0,
            "information": resources_data[2] if resources_data else 0,
            "force": resources_data[3] if resources_data else 0
        }

        # Get districts in one query with JOIN
        cursor.execute("""
            SELECT d.district_id, d.name, dc.control_points 
            FROM district_control dc
            JOIN districts d ON dc.district_id = d.district_id
            WHERE dc.player_id = ?
            ORDER BY dc.control_points DESC
        """, (player_id,))
        districts = cursor.fetchall()

        return player, resources, districts, {"main": player[4], "quick": player[5]}, lang

    except Exception as e:
        logger.error(f"Error getting player status: {e}")
        return None

async def admin_set_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to set district control points."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(get_text("admin_control_usage", lang))
        return

    try:
        player_id = int(args[0])
        district_id = args[1]
        control_points = int(args[2])
    except ValueError:
        await update.message.reply_text(get_text("admin_invalid_args", lang))
        return

    # Check if player exists
    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        player_id
    )

    if not player:
        await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
        return

    # Get district info to verify it exists
    district_info = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_district_info,
        district_id
    )

    if not district_info:
        await update.message.reply_text(get_text("admin_district_not_found", lang, district_id=district_id))
        return

    # Update district control
    try:
        from db.queries import update_district_control
        success = await asyncio.get_event_loop().run_in_executor(
            executor,
            update_district_control,
            player_id,
            district_id,
            control_points
        )

        if success:
            district_name = district_info[1] if district_info else district_id
            await update.message.reply_text(
                get_text("admin_control_updated", lang,
                         player_id=player_id,
                         district_id=district_name,
                         control_points=control_points)
            )
        else:
            await update.message.reply_text(get_text("admin_control_update_failed", lang))
    except Exception as e:
        logger.error(f"Error in admin_set_control: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to show admin-specific help."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    # Define the strings with apostrophes outside the f-string
    reset_player_actions_text = get_text("admin_reset_desc", lang, default="Reset a player's available actions")
    reset_all_actions_text = get_text("admin_reset_all_desc", lang, default="Reset all players' available actions")

    # Now use these variables in the f-string
    admin_help_text = (
        f"*{get_text('admin_help_title', lang, default='Admin Commands')}*\n\n"
        f"*/admin_help* - {get_text('admin_help_desc', lang, default='Show this admin help message')}\n"
        f"*/admin_add_news [title] [content]* - {get_text('admin_news_desc', lang, default='Add a news item')}\n"
        f"*/admin_process_cycle* - {get_text('admin_cycle_desc', lang, default='Manually process a game cycle')}\n"
        f"*/admin_add_resources [player_id] [resource_type] [amount]* - {get_text('admin_resources_desc', lang, default='Add resources to a player')}\n"
        f"*/admin_set_control [player_id] [district_id] [control_points]* - {get_text('admin_control_desc', lang, default='Set district control')}\n"
        f"*/admin_set_ideology [player_id] [ideology_score]* - {get_text('admin_ideology_desc', lang, default='Set player ideology score (-5 to +5)')}\n"
        f"*/admin_list_players* - {get_text('admin_list_desc', lang, default='List all registered players')}\n"
        f"*/admin_reset_actions [player_id]* - {get_text('admin_reset_desc', lang, default=reset_player_actions_text)}\n"
        f"*/admin_reset_all_actions* - {get_text('admin_reset_all_desc', lang, default=reset_all_actions_text)}\n"
    )

    await update.message.reply_text(admin_help_text, parse_mode='Markdown')


@db_transaction
def list_all_players(conn):
    """List all registered players from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.player_id, p.character_name, p.username, p.ideology_score, 
               r.influence, r.resources, r.information, r.force
        FROM players p
        LEFT JOIN resources r ON p.player_id = r.player_id
        ORDER BY p.player_id
    """)
    return cursor.fetchall()


async def admin_list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all registered players."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    try:
        # Get players using transaction decorator
        players = await asyncio.get_event_loop().run_in_executor(
            executor,
            list_all_players
        )

        if not players:
            await update.message.reply_text(
                get_text("admin_list_players_none", lang, default="No players registered."))
            return

        response = f"<b>{get_text('admin_list_players_title', lang, default='Registered Players')}</b>\n\n"

        for player in players:
            player_id, character_name, username, ideology, influence, resources, information, force = player

            character_name = character_name or get_text("unnamed", lang, default="Unnamed")
            username = username or get_text("no_username", lang, default="No username")

            response += (
                f"<b>{get_text('id', lang, default='ID')}:</b> {player_id}\n"
                f"<b>{get_text('name', lang, default='Name')}:</b> {character_name}\n"
                f"<b>{get_text('username', lang, default='Username')}:</b> @{username}\n"
                f"<b>{get_text('ideology', lang, default='Ideology')}:</b> {ideology}\n"
                f"<b>{get_text('resources', lang, default='Resources')}:</b> {influence}/{resources}/{information}/{force}\n\n"
            )

        await update.message.reply_text(response, parse_mode='HTML')

    except Exception as e:
        logger.error(f"Error in admin_list_players: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


@db_transaction
def reset_all_player_actions(conn):
    """Reset all players' available actions."""
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()

    # Reset actions for all players
    cursor.execute(
        "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ?",
        (now,)
    )

    return cursor.rowcount


async def admin_reset_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to reset a player's available actions."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    args = context.args

    if not args:
        await update.message.reply_text(get_text("admin_reset_actions_usage", lang))
        return

    try:
        player_id = int(args[0])

        # Reset actions using transaction decorator
        success = await asyncio.get_event_loop().run_in_executor(
            executor,
            reset_player_actions,
            player_id
        )

        if success:
            await update.message.reply_text(get_text("admin_reset_actions_success", lang, player_id=player_id))
        else:
            await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))

    except ValueError:
        await update.message.reply_text(get_text("admin_invalid_args", lang))
    except Exception as e:
        logger.error(f"Error in admin_reset_actions: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


async def admin_reset_all_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to reset all players' available actions."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    try:
        # Reset all actions using transaction decorator
        affected_rows = await asyncio.get_event_loop().run_in_executor(
            executor,
            reset_all_player_actions
        )

        await update.message.reply_text(get_text("admin_reset_all_actions_success", lang, count=affected_rows))

    except Exception as e:
        logger.error(f"Error in admin_reset_all_actions: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display player's current status."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        user.id
    )

    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    character_name = player[2] or get_text("unnamed", lang, default="Unnamed")
    ideology_score = player[3]

    # Run more database operations in thread pool
    resources = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_resources,
        user.id
    )

    districts = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_districts,
        user.id
    )

    actions = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_remaining_actions,
        user.id
    )

    # Format ideology using helper function
    from languages import format_ideology
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
            from game.districts import get_control_status_text
            control_status = get_control_status_text(control, lang)

            status_text += f"{name}: {control} {get_text('control_points', lang, count=control)} - {control_status}\n"
    else:
        status_text += f"{get_text('status_no_districts', lang)}\n"

    await update.message.reply_text(status_text, parse_mode='Markdown')


@db_transaction
def set_player_ideology(conn, player_id, ideology_score):
    """Set a player's ideology score."""
    cursor = conn.cursor()

    # Check if player exists
    cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
    if not cursor.fetchone():
        return False

    # Update ideology score
    cursor.execute(
        "UPDATE players SET ideology_score = ? WHERE player_id = ?",
        (ideology_score, player_id)
    )

    return cursor.rowcount > 0


async def admin_set_ideology(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to set a player's ideology score."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    args = context.args

    if len(args) != 2:
        await update.message.reply_text(get_text("admin_set_ideology_usage", lang,
                                                 default="Usage: /admin_set_ideology [player_id] [ideology_score]"))
        return

    try:
        player_id = int(args[0])
        ideology_score = int(args[1])

        # Validate ideology score
        if ideology_score < -5 or ideology_score > 5:
            await update.message.reply_text(get_text("admin_set_ideology_invalid", lang,
                                                     default="Ideology score must be between -5 and +5."))
            return

        # Set ideology using transaction decorator
        success = await asyncio.get_event_loop().run_in_executor(
            executor,
            set_player_ideology,
            player_id,
            ideology_score
        )

        if success:
            await update.message.reply_text(get_text("admin_set_ideology_success", lang,
                                                     player_id=player_id, score=ideology_score,
                                                     default=f"Ideology score for player {player_id} set to {ideology_score}."))
        else:
            await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))

    except ValueError:
        await update.message.reply_text(get_text("admin_invalid_args", lang))
    except Exception as e:
        logger.error(f"Error in admin_set_ideology: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


async def generate_text_map():
    """Generate a text representation of the game map."""
    districts = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_all_districts
    )

    map_text = []

    map_text.append(f"*{get_text('map_title', 'en', default='Current Control Map of Novi Sad')}*\n")

    for district in districts:
        district_id, name, description, *_ = district

        # Get district control data
        from db.queries import get_district_control
        control_data = await asyncio.get_event_loop().run_in_executor(
            executor,
            get_district_control,
            district_id
        )

        map_text.append(f"*{name}* - {description}")

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

                    map_text.append(
                        f"  {control_status} {player_name}: {control_points} {get_text('points', 'en', default='points')}")
        else:
            map_text.append(f"  {get_text('map_no_control', 'en', default='No control established')}")

        map_text.append("")  # Add empty line between districts

    map_text.append(get_text('map_legend', 'en', default="Legend:"))
    map_text.append(get_text('map_strong_control', 'en', default="🔒 Strong control (80+ points)"))
    map_text.append(get_text('map_controlled', 'en', default="✅ Controlled (60-79 points)"))
    map_text.append(get_text('map_contested', 'en', default="⚠️ Contested (20-59 points)"))
    map_text.append(get_text('map_weak', 'en', default="❌ Weak presence (<20 points)"))

    return "\n".join(map_text)


async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current game map."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    try:
        map_text = await generate_text_map()

        # If this is too long for one message, you might need to split it
        if len(map_text) > 4000:
            await update.message.reply_text(get_text("map_too_large", lang))
        else:
            await update.message.reply_text(map_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error generating map: {e}")
        await update.message.reply_text(get_text("error_generating_map", lang, default="Error generating map."))


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current game cycle and time until next phase."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    now = datetime.datetime.now()
    current_time = now.time()

    # Determine current cycle
    current_cycle = get_current_cycle()
    cycle_name = get_cycle_name(current_cycle, lang)

    # Get deadline and results times
    deadline_time = get_cycle_deadline()
    results_time = get_cycle_results_time()

    # Calculate time remaining
    next_deadline = datetime.datetime.combine(now.date(), deadline_time)
    next_results = datetime.datetime.combine(now.date(), results_time)

    # If we're past the deadline for today
    if now.time() > deadline_time:
        if current_cycle == "evening":
            # Next deadline is morning of next day
            tomorrow = now.date() + datetime.timedelta(days=1)
            next_deadline = datetime.datetime.combine(tomorrow, get_cycle_deadline())
            next_results = datetime.datetime.combine(tomorrow, get_cycle_results_time())
        else:
            # Next deadline is evening of today
            from game.actions import CYCLE_STARTS
            next_deadline = datetime.datetime.combine(now.date(), CYCLE_STARTS[6])
            next_results = datetime.datetime.combine(now.date(), CYCLE_STARTS[6])

    # Format time remaining
    def format_time_remaining(minutes):
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if hours > 0:
            return f"{hours} {get_text('hours', lang)} {remaining_minutes} {get_text('minutes', lang)}"
        return f"{remaining_minutes} {get_text('minutes', lang)}"

    if now > next_deadline:
        time_to_deadline = get_text("deadline_passed", lang)
        minutes_to_results = int((next_results - now).total_seconds() / 60)
        time_to_results = format_time_remaining(minutes_to_results)
    else:
        minutes_to_deadline = int((next_deadline - now).total_seconds() / 60)
        minutes_to_results = int((next_results - now).total_seconds() / 60)
        time_to_deadline = format_time_remaining(minutes_to_deadline)
        time_to_results = format_time_remaining(minutes_to_results)

    time_text = (
        f"*{get_text('time_info', lang)}*\n\n"
        f"{get_text('time_current', lang, cycle=cycle_name)}\n\n"
        f"{get_text('time_deadlines', lang, deadline=time_to_deadline, results=time_to_results)}\n\n"
        f"{get_text('time_schedule', lang)}\n\n"
        f"{get_text('time_refresh', lang)}"
    )

    await update.message.reply_text(time_text, parse_mode='Markdown')


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent news."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    news_items = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_news,
        5,  # limit
        user.id  # player_id
    )

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

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        db_get_player_language,
        user.id
    )

    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        user.id
    )

    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Check if actions should refresh
    updated = await asyncio.get_event_loop().run_in_executor(
        executor,
        update_action_counts,
        user.id
    )

    # Check if player has actions left
    actions = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_remaining_actions,
        user.id
    )

    if actions['main'] <= 0:
        await update.message.reply_text(get_text("no_main_actions", lang))
        return

    # Show action types for selection
    keyboard = [
        [InlineKeyboardButton(get_text("action_influence", lang), callback_data=f"action_type:influence")],
        [InlineKeyboardButton(get_text("action_attack", lang), callback_data=f"action_type:attack")],
        [InlineKeyboardButton(get_text("action_defense", lang), callback_data=f"action_type:defense")],
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

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        user.id
    )

    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Check if actions should refresh
    updated = await asyncio.get_event_loop().run_in_executor(
        executor,
        update_action_counts,
        user.id
    )

    # Check if player has actions left
    actions = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_remaining_actions,
        user.id
    )

    if actions['quick'] <= 0:
        await update.message.reply_text(get_text("no_quick_actions", lang))
        return

    # Show action types for selection
    keyboard = [
        [InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"quick_action_type:recon")],
        [InlineKeyboardButton(get_text("action_info", lang), callback_data=f"quick_action_type:info")],
        [InlineKeyboardButton(get_text("action_support", lang), callback_data=f"quick_action_type:support")],
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

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    from db.queries import cancel_last_action
    success = await asyncio.get_event_loop().run_in_executor(
        executor,
        cancel_last_action,
        user.id
    )

    if success:
        await update.message.reply_text(get_text("action_cancelled", lang))
    else:
        await update.message.reply_text(get_text("no_pending_actions", lang))


async def actions_left_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show remaining actions."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        user.id
    )

    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Check if actions should refresh
    updated = await asyncio.get_event_loop().run_in_executor(
        executor,
        update_action_counts,
        user.id
    )

    actions = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_remaining_actions,
        user.id
    )

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
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    args = context.args

    if not args:
        # Show list of districts to select from
        districts = await asyncio.get_event_loop().run_in_executor(
            executor,
            get_districts_for_selection,
            lang
        )

        keyboard = []

        for district_id, name in districts:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"view_district:{district_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            get_text("select_district", lang),
            reply_markup=reply_markup
        )
        return

    district_name = ' '.join(args)
    district = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_district_by_name,
        district_name
    )

    if district:
        district_id = district[0]
        district_info = await asyncio.get_event_loop().run_in_executor(
            executor,
            format_district_info,
            district_id,
            lang
        )

        if district_info:
            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton(get_text("action_influence", lang),
                                         callback_data=f"action_influence:{district_id}"),
                    InlineKeyboardButton(get_text("action_attack", lang),
                                         callback_data=f"action_attack:{district_id}")
                ],
                [
                    InlineKeyboardButton(get_text("action_defense", lang),
                                         callback_data=f"action_defend:{district_id}"),
                    InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"quick_recon:{district_id}")
                ],
                [
                    InlineKeyboardButton(get_text("action_support", lang),
                                         callback_data=f"quick_support:{district_id}")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                district_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                get_text("error_district_info", lang, default="Error retrieving district information."))
    else:
        await update.message.reply_text(
            get_text("district_not_found", lang, district_name=district_name)
        )


async def politicians_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of local politicians."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    politicians_text = await asyncio.get_event_loop().run_in_executor(
        executor,
        format_politicians_list,
        False,  # is_international
        lang
    )

    # Get list of politicians for buttons
    from db.queries import get_all_politicians
    politicians = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_all_politicians,
        False  # is_international
    )

    if not politicians:
        await update.message.reply_text(get_text("no_politicians", lang))
        return

    # Show list of politicians to choose from
    keyboard = []
    for politician in politicians:
        pol_id, name = politician[0], politician[1]
        keyboard.append([InlineKeyboardButton(name, callback_data=f"view_politician:{pol_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        politicians_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def politician_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View information about a specific politician."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    args = context.args

    if not args:
        # Call the politicians_command to show the list
        await politicians_command(update, context)
        return

    politician_name = ' '.join(args)
    politician = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_politician_by_name,
        politician_name
    )

    if politician:
        politician_info = await asyncio.get_event_loop().run_in_executor(
            executor,
            format_politician_info,
            politician[0],  # politician_id
            user.id,
            lang
        )

        if politician_info:
            pol_id = politician[0]

            # Add action buttons
            keyboard = [
                [
                    InlineKeyboardButton(get_text("action_influence", lang),
                                         callback_data=f"pol_influence:{pol_id}"),
                    InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"pol_info:{pol_id}")
                ],
                [
                    InlineKeyboardButton(get_text("action_info", lang), callback_data=f"pol_undermine:{pol_id}")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                politician_info,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                get_text("error_politician_info", lang, default="Error retrieving politician information."))
    else:
        await update.message.reply_text(
            get_text("politician_not_found", lang, name=politician_name)
        )


async def international_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show information about international politicians."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    international_text = await asyncio.get_event_loop().run_in_executor(
        executor,
        format_politicians_list,
        True,  # is_international
        lang
    )

    await update.message.reply_text(international_text, parse_mode='Markdown')


async def resources_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show player's resources and information about resource usage."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    resources = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_resources,
        user.id
    )

    if not resources:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    resources_text = (
        f"*{get_text('resources_title', lang)}*\n\n"
        f"🔵 {get_resource_name('influence', lang)}: {resources['influence']}\n"
        f"💰 {get_resource_name('resources', lang)}: {resources['resources']}\n"
        f"🔍 {get_resource_name('information', lang)}: {resources['information']}\n"
        f"👊 {get_resource_name('force', lang)}: {resources['force']}\n\n"
        f"{get_text('resources_guide', lang)}"
    )

    await update.message.reply_text(resources_text, parse_mode='Markdown')


async def convert_resource_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert resources from one type to another."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    args = context.args

    if len(args) != 2:
        usage_text = get_text("convert_usage", lang)
        await update.message.reply_text(usage_text)
        return

    resource_type = args[0].lower()
    amount_str = args[1]

    # Validate amount
    try:
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text(get_text("amount_not_number", lang))
        return

    if amount <= 0:
        await update.message.reply_text(get_text("amount_not_positive", lang))
        return

    # Validate resource type
    valid_types = ["influence", "information", "force"]
    if resource_type not in valid_types:
        await update.message.reply_text(
            get_text("invalid_resource_type", lang, valid_types=", ".join(valid_types))
        )
        return

    # Check if player has enough resources
    resources = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_resources,
        user.id
    )

    resources_needed = amount * 2  # 2 resources = 1 of any other type

    if resources['resources'] < resources_needed:
        await update.message.reply_text(
            get_text("not_enough_resources", lang, needed=resources_needed, available=resources['resources'])
        )
        return

    # Perform the conversion
    await asyncio.get_event_loop().run_in_executor(
        executor,
        update_player_resources,
        user.id,
        'resources',
        -resources_needed
    )

    await asyncio.get_event_loop().run_in_executor(
        executor,
        update_player_resources,
        user.id,
        resource_type,
        amount
    )

    await update.message.reply_text(
        get_text("conversion_success", lang,
                 resources_used=resources_needed,
                 amount=amount,
                 resource_type=get_resource_name(resource_type, lang))
    )


async def check_income_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check player's expected resource income."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    # Get districts controlled by the player (25+ control points)
    districts = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_districts,
        user.id
    )

    controlled_districts = []

    total_income = {
        "influence": 0,
        "resources": 0,
        "information": 0,
        "force": 0
    }

    if districts:
        for district_data in districts:
            district_id, name, control_points = district_data

            if control_points >= 25:  # Changed from 60 to 25
                district = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    get_district_info,
                    district_id
                )

                if district:
                    _, district_name, _, influence, resources, information, force = district

                    controlled_districts.append((district_name, influence, resources, information, force))

                    total_income["influence"] += influence
                    total_income["resources"] += resources
                    total_income["information"] += information
                    total_income["force"] += force

    if controlled_districts:
        income_text = get_text("income_controlled_districts", lang) + "\n"

        for district_name, influence, resources, information, force in controlled_districts:
            income_text += f"• {district_name}: "

            resources_list = []
            if influence > 0:
                resources_list.append(f"+{influence} {get_resource_name('influence', lang)}")
            if resources > 0:
                resources_list.append(f"+{resources} {get_resource_name('resources', lang)}")
            if information > 0:
                resources_list.append(f"+{information} {get_resource_name('information', lang)}")
            if force > 0:
                resources_list.append(f"+{force} {get_resource_name('force', lang)}")

            income_text += ", ".join(resources_list) + "\n"

        income_text += "\n" + get_text("income_total", lang,
                                       influence=total_income["influence"],
                                       resources=total_income["resources"],
                                       information=total_income["information"],
                                       force=total_income["force"])

        income_text += "\n\n" + get_text("income_note", lang)

        await update.message.reply_text(income_text, parse_mode='Markdown')
    elif districts:
        # Has districts but none fully controlled
        await update.message.reply_text(get_text("income_no_full_control", lang), parse_mode='Markdown')
    else:
        # No districts at all
        await update.message.reply_text(get_text("no_districts_controlled", lang), parse_mode='Markdown')


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /language command to change interface language."""
    try:
        user = update.effective_user

        # Get player's current language from database
        @db_transaction
        def get_current_lang(conn, user_id):
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM players WHERE player_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else "en"

        # Check if player exists, if not register them
        @db_transaction
        def ensure_player_exists(conn, user_id, username):
            cursor = conn.cursor()
            cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (user_id,))
            if not cursor.fetchone():
                now = datetime.datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO players (player_id, username, last_action_refresh) VALUES (?, ?, ?)",
                    (user_id, username, now)
                )
                return False
            return True

        player_exists = ensure_player_exists(user.id, user.username)
        current_lang = get_current_lang(user.id)

        # Create language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton(get_text("language_button_en", current_lang),
                                     callback_data="lang:en"),
                InlineKeyboardButton(get_text("language_button_ru", current_lang),
                                     callback_data="lang:ru")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Show current language and prompt for selection
        await update.message.reply_text(
            get_text("language_current", current_lang, language=current_lang) + "\n\n" +
            get_text("language_select", current_lang),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in language command: {e}")
        await update.message.reply_text("Error processing language command. Please try again.")


async def receive_info_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle receiving information content for quick info action."""
    user = update.effective_user
    content = update.message.text.strip()

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if not content:
        await update.message.reply_text(get_text("invalid_info_content", lang))
        return ConversationHandler.END

    # Check if player has quick actions left
    actions = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_remaining_actions,
        user.id
    )

    if actions['quick'] <= 0:
        await update.message.reply_text(get_text("no_quick_actions", lang))
        return ConversationHandler.END

    # Spread information requires 1 Information resource
    resources = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_resources,
        user.id
    )

    if resources['information'] < 1:
        await update.message.reply_text(
            get_text("insufficient_resources", lang, resource_type=get_resource_name("information", lang))
        )
        return ConversationHandler.END

    # Deduct resource
    await asyncio.get_event_loop().run_in_executor(
        executor,
        update_player_resources,
        user.id,
        'information',
        -1
    )

    # Use action
    action_used = await asyncio.get_event_loop().run_in_executor(
        executor,
        use_action,
        user.id,
        False  # is_main_action
    )

    if not action_used:
        await update.message.reply_text(get_text("no_quick_actions", lang))
        return ConversationHandler.END

    # Add news item
    title = get_text("info_from_user", lang, user=user.first_name)

    await asyncio.get_event_loop().run_in_executor(
        executor,
        add_news,
        title,
        content,
        True,  # is_public
        None,  # target_player_id
        False  # is_fake
    )

    # Add the action to the database
    from db.queries import add_action
    resources_used = {"information": 1}

    await asyncio.get_event_loop().run_in_executor(
        executor,
        add_action,
        user.id,
        "info",
        "news",
        "public",
        resources_used
    )

    await update.message.reply_text(get_text("info_spreading", lang))
    return ConversationHandler.END


# Admin commands
async def admin_add_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to add a news item."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    args = context.args

    if len(args) < 2:
        await update.message.reply_text(get_text("admin_news_usage", lang))
        return

    title = args[0]
    content = ' '.join(args[1:])

    news_id = await asyncio.get_event_loop().run_in_executor(
        executor,
        add_news,
        title,
        content
    )

    await update.message.reply_text(get_text("admin_news_added", lang, news_id=news_id))


async def accept_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accept a trade offer."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    args = context.args

    if not args:
        await update.message.reply_text(get_text("accept_trade_usage", lang))
        return

    try:
        offer_id = int(args[0])

        # Accept the trade offer
        success = await asyncio.get_event_loop().run_in_executor(
            executor,
            accept_trade_offer,
            offer_id,
            user.id
        )

        if success:
            # Get sender ID to notify them
            from db.queries import get_trade_offer_sender
            sender_id = await asyncio.get_event_loop().run_in_executor(
                executor,
                get_trade_offer_sender,
                offer_id
            )

            if sender_id:
                # Notify sender
                try:
                    await context.bot.send_message(
                        chat_id=sender_id,
                        text=get_text("trade_accepted_notification", lang, player_id=user.id, offer_id=offer_id)
                    )
                except Exception as e:
                    logger.error(f"Failed to notify sender {sender_id} about accepted trade: {e}")

            await update.message.reply_text(get_text("trade_accepted", lang))
        else:
            await update.message.reply_text(get_text("trade_accept_failed", lang))

    except ValueError:
        await update.message.reply_text(get_text("invalid_offer_id", lang))
    except Exception as e:
        logger.error(f"Error in accept_trade: {e}")
        await update.message.reply_text(get_text("error_accepting_trade", lang))


async def admin_process_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manually process a game cycle."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    await process_game_cycle(context)

    await update.message.reply_text(get_text("admin_cycle_processed", lang))


async def trade_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a trade offer with another player."""
    user = update.effective_user

    # Run database operations in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    args = context.args

    if len(args) < 4:
        usage_text = get_text("trade_offer_usage", lang)
        await update.message.reply_text(usage_text)
        return

    try:
        # Parse receiver ID
        receiver_id = int(args[0])

        # Parse offered resources
        offer = {}
        request = {}

        # Parse format: /trade <player_id> offer <resource> <amount> request <resource> <amount>
        i = 1
        current_dict = None

        while i < len(args):
            if args[i].lower() == 'offer':
                current_dict = offer
                i += 1
                continue
            elif args[i].lower() == 'request':
                current_dict = request
                i += 1
                continue

            if current_dict is None or i + 1 >= len(args):
                await update.message.reply_text(get_text("trade_offer_invalid_format", lang))
                return

            resource_type = args[i].lower()
            try:
                amount = int(args[i + 1])
            except ValueError:
                await update.message.reply_text(get_text("amount_not_number", lang))
                return

            if amount <= 0:
                await update.message.reply_text(get_text("amount_not_positive", lang))
                return

            if resource_type not in ['influence', 'force', 'information', 'resources']:
                await update.message.reply_text(get_text("invalid_resource_type", lang))
                return

            current_dict[resource_type] = amount
            i += 2

        # Create trade offer
        offer_id = await asyncio.get_event_loop().run_in_executor(
            executor,
            create_trade_offer,
            user.id,
            receiver_id,
            offer,
            request
        )

        if offer_id > 0:
            # Notify receiver
            try:
                offered_resources = ", ".join(
                    [f"{amount} {get_resource_name(res, lang)}" for res, amount in offer.items()])
                requested_resources = ", ".join(
                    [f"{amount} {get_resource_name(res, lang)}" for res, amount in request.items()])

                await context.bot.send_message(
                    chat_id=receiver_id,
                    text=get_text("trade_offer_received", lang,
                                  sender_id=user.id,
                                  offered=offered_resources,
                                  requested=requested_resources,
                                  offer_id=offer_id)
                )

                await update.message.reply_text(get_text("trade_offer_sent", lang, receiver_id=receiver_id))
            except Exception as e:
                logger.error(f"Failed to notify receiver about trade offer: {e}")
                await update.message.reply_text(get_text("trade_offer_sent_no_notify", lang))
        else:
            await update.message.reply_text(get_text("trade_offer_failed", lang))

    except ValueError:
        await update.message.reply_text(get_text("invalid_player_id", lang))
    except Exception as e:
        logger.error(f"Error in trade_offer: {e}")
        await update.message.reply_text(get_text("error_creating_trade", lang))


def register_commands(application):
    """Register all command handlers."""
    # Create conversation handler for /start command
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            "WAITING_NAME": [MessageHandler(filters.TEXT & ~filters.COMMAND, set_name_handler)],
            "WAITING_INFO_CONTENT": [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_info_content)]
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)]
    )
    application.add_handler(CommandHandler("language", language_command))

    # Add basic command handlers
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("news", news_command))

    # Action handlers
    application.add_handler(CommandHandler("action", action_command))
    application.add_handler(CommandHandler("quick_action", quick_action_command))
    application.add_handler(CommandHandler("cancel_action", cancel_action_command))
    application.add_handler(CommandHandler("actions_left", actions_left_command))

    # District and politician handlers
    application.add_handler(CommandHandler("view_district", view_district_command))
    application.add_handler(CommandHandler("politicians", politicians_command))
    application.add_handler(CommandHandler("politician_status", politician_status_command))
    application.add_handler(CommandHandler("international", international_command))

    # Resource handlers
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("convert_resource", convert_resource_command))
    application.add_handler(CommandHandler("check_income", check_income_command))

    # Language handler
    application.add_handler(CommandHandler("language", language_command))

    # Admin command handlers
    application.add_handler(CommandHandler("admin_help", admin_help_command))
    application.add_handler(CommandHandler("admin_add_news", admin_add_news))
    application.add_handler(CommandHandler("admin_process_cycle", admin_process_cycle))
    application.add_handler(CommandHandler("admin_add_resources", admin_add_resources))
    application.add_handler(CommandHandler("admin_set_control", admin_set_control))
    application.add_handler(CommandHandler("admin_list_players", admin_list_players))
    application.add_handler(CommandHandler("admin_reset_actions", admin_reset_actions))
    application.add_handler(CommandHandler("admin_reset_all_actions", admin_reset_all_actions))
    application.add_handler(CommandHandler("admin_set_ideology", admin_set_ideology))

    # Trading handlers
    application.add_handler(CommandHandler("trade", trade_offer))
    application.add_handler(CommandHandler("accept_trade", accept_trade))

    # New admin command for managing player resources with interactive menu
    application.add_handler(CommandHandler("admin_manage_resources", admin_manage_resources))

    logger.info("Command handlers registered")

async def process_cycle_results():
    """Process results for the current cycle."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get all players
        cursor.execute("SELECT player_id FROM players")
        players = cursor.fetchall()
        
        for player in players:
            player_id = player[0]
            
            # Update base resources for each player
            await asyncio.get_event_loop().run_in_executor(
                executor,
                update_base_resources,
                player_id
            )
            
            # Process district resources
            await asyncio.get_event_loop().run_in_executor(
                executor,
                distribute_district_resources,
                player_id
            )
            
            # Reset actions
            await asyncio.get_event_loop().run_in_executor(
                executor,
                reset_player_actions,
                player_id
            )
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error processing cycle results: {e}")
        conn.rollback()
    finally:
        conn.close()

async def admin_manage_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to manage player resources with interactive menu."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    # Get all players
    players = await asyncio.get_event_loop().run_in_executor(
        executor,
        list_all_players
    )

    if not players:
        await update.message.reply_text(get_text("admin_no_players", lang))
        return

    # Create inline keyboard with player buttons
    keyboard = []
    for player in players:
        player_id, username, character_name = player
        button_text = f"{character_name} (@{username})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_resources_{player_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text("admin_select_player", lang),
        reply_markup=reply_markup
    )

async def admin_resources_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback for admin resources management."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.message.reply_text(get_text("admin_only", "en"))
        return

    # Extract player_id from callback_data
    player_id = int(query.data.split('_')[2])
    
    # Get player resources
    resources = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_resources,
        player_id
    )

    # Create keyboard for resource management
    keyboard = []
    for resource_type in ["influence", "resources", "information", "force"]:
        current_amount = resources.get(resource_type, 0)
        keyboard.extend([
            [
                InlineKeyboardButton(f"-10 {resource_type}", callback_data=f"admin_resource_{player_id}_{resource_type}_-10"),
                InlineKeyboardButton(f"-1 {resource_type}", callback_data=f"admin_resource_{player_id}_{resource_type}_-1"),
                InlineKeyboardButton(f"{current_amount} {resource_type}", callback_data=f"admin_resource_{player_id}_{resource_type}_0"),
                InlineKeyboardButton(f"+1 {resource_type}", callback_data=f"admin_resource_{player_id}_{resource_type}_1"),
                InlineKeyboardButton(f"+10 {resource_type}", callback_data=f"admin_resource_{player_id}_{resource_type}_10")
            ]
        ])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("Back to player list", callback_data="admin_resources_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get player info
    player = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player,
        player_id
    )
    
    if player:
        username, character_name = player[1], player[2]
        await query.message.edit_text(
            f"Managing resources for {character_name} (@{username})\n"
            f"Current resources:\n"
            f"Influence: {resources.get('influence', 0)}\n"
            f"Resources: {resources.get('resources', 0)}\n"
            f"Information: {resources.get('information', 0)}\n"
            f"Force: {resources.get('force', 0)}",
            reply_markup=reply_markup
        )

async def admin_resource_change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback for changing resource amounts."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.message.reply_text(get_text("admin_only", "en"))
        return

    # Extract data from callback_data
    _, player_id, resource_type, amount = query.data.split('_')
    player_id = int(player_id)
    amount = int(amount)

    # Update resources
    success = await asyncio.get_event_loop().run_in_executor(
        executor,
        update_player_resources,
        player_id,
        resource_type,
        amount
    )

    if success:
        # Refresh the resource management menu
        await admin_resources_callback(update, context)
    else:
        await query.message.reply_text("Failed to update resources")

async def politician_abilities_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available abilities for a politician."""
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text(get_text("politician_abilities_no_args", get_player_language(user.id)))
        return

    politician_name = ' '.join(args)
    politician = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_politician_by_name,
        politician_name
    )

    if not politician:
        await update.message.reply_text(
            get_text("politician_not_found", get_player_language(user.id), name=politician_name)
        )
        return

    # Get available abilities
    abilities = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_politician_abilities,
        politician[0],  # politician_id
        user.id,
        get_player_language(user.id)
    )

    if not abilities:
        await update.message.reply_text(
            get_text("politician_no_abilities", get_player_language(user.id))
        )
        return

    # Format abilities list
    abilities_text = [f"*{politician[1]}'s Abilities:*\n"]
    for ability in abilities:
        status = "✅" if ability['is_available'] else f"⏳ ({ability['cycles_remaining']} cycles)"
        abilities_text.append(f"\n*{ability['name']}* {status}")
        abilities_text.append(f"_{ability['description']}_")
        
        # Show cost
        cost_text = []
        for resource, amount in ability['cost'].items():
            cost_text.append(f"{get_resource_name(resource, get_player_language(user.id))}: {amount}")
        abilities_text.append(f"Cost: {', '.join(cost_text)}")

    # Create buttons for available abilities
    keyboard = []
    for ability in abilities:
        if ability['is_available']:
            keyboard.append([
                InlineKeyboardButton(
                    ability['name'],
                    callback_data=f"use_ability:{politician[0]}:{ability['id']}"
                )
            ])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await update.message.reply_text(
        "\n".join(abilities_text),
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def set_location_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to set player's physical location in a district."""
    user = update.effective_user
    
    # Get player's language
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )
    
    if not context.args:
        # Show available districts
        districts = await asyncio.get_event_loop().run_in_executor(
            executor,
            get_all_districts
        )
        
        message = [get_text("available_districts", lang)]
        for district_id, name, description, *_ in districts:
            message.append(f"• {name} (`{district_id}`)")
        message.append("\n" + get_text("set_location_usage", lang))
        
        await update.message.reply_text("\n".join(message), parse_mode=ParseMode.MARKDOWN)
        return
    
    district_id = context.args[0].lower()
    
    # Verify district exists
    district = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_district_info,
        district_id
    )
    
    if not district:
        await update.message.reply_text(get_text("district_not_found", lang))
        return
    
    # Update player's location
    success = await asyncio.get_event_loop().run_in_executor(
        executor,
        update_player_location,
        user.id,
        district_id
    )
    
    if success:
        await update.message.reply_text(
            get_text("location_update_success", lang, district=district[1])
        )
    else:
        await update.message.reply_text(get_text("location_update_failed", lang))

async def get_location_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to check player's current location."""
    user = update.effective_user
    
    # Get player's language
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )
    
    # Get player's current location
    district_id = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_location,
        user.id
    )
    
    if district_id:
        district = await asyncio.get_event_loop().run_in_executor(
            executor,
            get_district_info,
            district_id
        )
        
        if district:
            await update.message.reply_text(
                get_text("current_location", lang, district=district[1]) + "\n" +
                get_text("location_bonus_info", lang)
            )
        else:
            await update.message.reply_text(get_text("no_location_set", lang))
    else:
        await update.message.reply_text(get_text("no_location_set", lang))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display help message with available commands."""
    user = update.effective_user

    # Run database operation in thread pool
    lang = await asyncio.get_event_loop().run_in_executor(
        executor,
        get_player_language,
        user.id
    )

    # Check if the user is an admin
    is_admin = user.id in ADMIN_IDS

    # Basic commands for all users
    help_text = (
        f"<b>{get_text('help_title', lang)}</b>\n\n"
        f"{get_text('help_basic', lang)}\n\n"
        f"{get_text('help_action', lang)}\n\n"
        f"{get_text('help_resource', lang)}\n\n"
        f"{get_text('help_political', lang)}\n\n"
    )

    # Add admin hint for admins
    if is_admin:
        help_text += (
            f"<b>{get_text('admin_commands', lang, default='Admin Commands')}:</b>\n"
            f"{get_text('admin_help_hint', lang, default='Use /admin_help to see all admin commands.')}\n\n"
        )

    help_text += get_text('help_footer', lang)

    await update.message.reply_text(help_text, parse_mode='HTML')