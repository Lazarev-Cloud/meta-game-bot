import sqlite3
import logging
import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from config import ADMIN_IDS
from languages import get_text, get_cycle_name, get_resource_name
from db.queries import (
    register_player, set_player_name, get_player,
    get_player_language, get_player_resources, update_player_resources,
    get_remaining_actions, update_action_counts, get_news,
    get_player_districts, add_news, use_action, get_district_info
)
from game.districts import (
    generate_text_map, format_district_info, get_district_by_name
)
from game.politicians import (
    format_politicians_list, format_politician_info, get_politician_by_name
)
from game.actions import (
    process_game_cycle, get_current_cycle, get_cycle_deadline, get_cycle_results_time
)

logger = logging.getLogger(__name__)

# Chat states for conversation handlers
WAITING_NAME = "WAITING_NAME"
WAITING_INFO_CONTENT = "WAITING_INFO_CONTENT"


# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation and ask for player name."""
    user = update.effective_user
    register_player(user.id, user.username)

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

    set_player_name(user.id, character_name)

    await update.message.reply_text(
        get_text("name_set", lang, character_name=character_name)
    )

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user = update.effective_user
    lang = get_player_language(user.id)

    await update.message.reply_text(get_text("operation_cancelled", lang))
    return ConversationHandler.END


async def admin_add_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to add resources to a player."""
    user = update.effective_user
    lang = get_player_language(user.id)

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

    player = get_player(player_id)
    if not player:
        await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
        return

    # Directly update resources in the database to ensure consistency
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get current amount
        cursor.execute(f"SELECT {resource_type} FROM resources WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()

        if result:
            current_amount = result[0]
            new_amount = current_amount + amount
            if new_amount < 0:
                new_amount = 0

            # Update resource
            cursor.execute(
                f"UPDATE resources SET {resource_type} = ? WHERE player_id = ?",
                (new_amount, player_id)
            )
            conn.commit()

            await update.message.reply_text(
                get_text("admin_resources_added", lang,
                         amount=amount,
                         resource_type=get_resource_name(resource_type, lang),
                         player_id=player_id,
                         new_amount=new_amount)
            )
        else:
            await update.message.reply_text(get_text("admin_player_resources_not_found", lang, player_id=player_id))
    except Exception as e:
        logger.error(f"Error in admin_add_resources: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))
    finally:
        conn.close()


async def admin_set_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to set district control points."""
    user = update.effective_user
    lang = get_player_language(user.id)

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

    player = get_player(player_id)
    if not player:
        await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
        return

    # Verify district exists
    district = None
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT district_id, name FROM districts WHERE district_id = ?", (district_id,))
        district = cursor.fetchone()
        conn.close()
    except Exception as e:
        logger.error(f"Error checking district: {e}")

    if not district:
        await update.message.reply_text(get_text("admin_district_not_found", lang, district_id=district_id))
        return

    # Update control directly in the database
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT control_points FROM district_control WHERE player_id = ? AND district_id = ?",
            (player_id, district_id)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE district_control SET control_points = ?, last_action = ? WHERE player_id = ? AND district_id = ?",
                (control_points, datetime.datetime.now().isoformat(), player_id, district_id)
            )
        else:
            cursor.execute(
                "INSERT INTO district_control (district_id, player_id, control_points, last_action) VALUES (?, ?, ?, ?)",
                (district_id, player_id, control_points, datetime.datetime.now().isoformat())
            )

        conn.commit()
        conn.close()

        district_name = district[1] if district else district_id
        await update.message.reply_text(
            get_text("admin_control_updated", lang,
                     player_id=player_id,
                     district_id=district_name,
                     control_points=control_points)
        )
    except Exception as e:
        logger.error(f"Error in admin_set_control: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to show admin-specific help."""
    user = update.effective_user
    lang = get_player_language(user.id)

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    # Define the strings with apostrophes outside the f-string
    reset_player_actions_text = "Reset a player's available actions"
    reset_all_actions_text = "Reset all players' available actions"

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display help message with available commands."""
    user = update.effective_user
    lang = get_player_language(user.id)

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
            f"<b>Admin Commands:</b>\n"
            f"Use /admin_help to see all admin commands.\n\n"
        )

    help_text += get_text('help_footer', lang)

    await update.message.reply_text(help_text, parse_mode='HTML')


async def admin_list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all registered players."""
    user = update.effective_user
    lang = get_player_language(user.id)

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.player_id, p.character_name, p.username, p.ideology_score, 
                   r.influence, r.resources, r.information, r.force
            FROM players p
            LEFT JOIN resources r ON p.player_id = r.player_id
            ORDER BY p.player_id
        """)

        players = cursor.fetchall()
        conn.close()

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


async def admin_reset_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to reset a player's available actions."""
    user = update.effective_user
    lang = get_player_language(user.id)

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    args = context.args

    if not args:
        await update.message.reply_text(get_text("admin_reset_actions_usage", lang))
        return

    try:
        player_id = int(args[0])

        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check if player exists
        cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
        if not cursor.fetchone():
            conn.close()
            await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
            return

        # Reset actions
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
            (now, player_id)
        )

        conn.commit()
        conn.close()

        await update.message.reply_text(get_text("admin_reset_actions_success", lang, player_id=player_id))

    except ValueError:
        await update.message.reply_text(get_text("admin_invalid_args", lang))
    except Exception as e:
        logger.error(f"Error in admin_reset_actions: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))


async def admin_reset_all_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to reset all players' available actions."""
    user = update.effective_user
    lang = get_player_language(user.id)

    if user.id not in ADMIN_IDS:
        await update.message.reply_text(get_text("admin_only", lang))
        return

    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Reset actions for all players
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ?",
            (now,)
        )

        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()

        await update.message.reply_text(get_text("admin_reset_all_actions_success", lang, count=affected_rows))

    except Exception as e:
        logger.error(f"Error in admin_reset_all_actions: {e}")
        await update.message.reply_text(get_text("admin_error", lang, error=str(e)))
    async def admin_list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to list all registered players."""
        user = update.effective_user
        lang = get_player_language(user.id)

        if user.id not in ADMIN_IDS:
            await update.message.reply_text(get_text("admin_only", lang))
            return

        try:
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()

            cursor.execute("""
                SELECT p.player_id, p.character_name, p.username, p.ideology_score, 
                       r.influence, r.resources, r.information, r.force
                FROM players p
                LEFT JOIN resources r ON p.player_id = r.player_id
                ORDER BY p.player_id
            """)

            players = cursor.fetchall()
            conn.close()

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

    async def admin_reset_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to reset a player's available actions."""
        user = update.effective_user
        lang = get_player_language(user.id)

        if user.id not in ADMIN_IDS:
            await update.message.reply_text(get_text("admin_only", lang))
            return

        args = context.args

        if not args:
            await update.message.reply_text(get_text("admin_reset_actions_usage", lang))
            return

        try:
            player_id = int(args[0])

            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()

            # Check if player exists
            cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
            if not cursor.fetchone():
                conn.close()
                await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
                return

            # Reset actions
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ? WHERE player_id = ?",
                (now, player_id)
            )

            conn.commit()
            conn.close()

            await update.message.reply_text(get_text("admin_reset_actions_success", lang, player_id=player_id))

        except ValueError:
            await update.message.reply_text(get_text("admin_invalid_args", lang))
        except Exception as e:
            logger.error(f"Error in admin_reset_actions: {e}")
            await update.message.reply_text(get_text("admin_error", lang, error=str(e)))

    async def admin_reset_all_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to reset all players' available actions."""
        user = update.effective_user
        lang = get_player_language(user.id)

        if user.id not in ADMIN_IDS:
            await update.message.reply_text(get_text("admin_only", lang))
            return

        try:
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()

            # Reset actions for all players
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                "UPDATE players SET main_actions_left = 1, quick_actions_left = 2, last_action_refresh = ?",
                (now,)
            )

            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()

            await update.message.reply_text(get_text("admin_reset_all_actions_success", lang, count=affected_rows))

        except Exception as e:
            logger.error(f"Error in admin_reset_all_actions: {e}")
            await update.message.reply_text(get_text("admin_error", lang, error=str(e)))

    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display player's current status."""
        user = update.effective_user
        lang = get_player_language(user.id)
        player = get_player(user.id)

        if not player:
            await update.message.reply_text(get_text("not_registered", lang))
            return

        character_name = player[2] or get_text("unnamed", lang, default="Unnamed")
        ideology_score = player[3]

        resources = get_player_resources(user.id)
        districts = get_player_districts(user.id)
        actions = get_remaining_actions(user.id)

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

    async def admin_set_ideology(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to set a player's ideology score."""
        user = update.effective_user
        lang = get_player_language(user.id)

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

            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()

            # Check if player exists
            cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
            if not cursor.fetchone():
                conn.close()
                await update.message.reply_text(get_text("admin_player_not_found", lang, player_id=player_id))
                return

            # Update ideology score
            cursor.execute(
                "UPDATE players SET ideology_score = ? WHERE player_id = ?",
                (ideology_score, player_id)
            )

            conn.commit()
            conn.close()

            await update.message.reply_text(get_text("admin_set_ideology_success", lang,
                                                     player_id=player_id, score=ideology_score,
                                                     default=f"Ideology score for player {player_id} set to {ideology_score}."))

        except ValueError:
            await update.message.reply_text(get_text("admin_invalid_args", lang))
        except Exception as e:
            logger.error(f"Error in admin_set_ideology: {e}")
            await update.message.reply_text(get_text("admin_error", lang, error=str(e)))

    async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the current game map."""
        user = update.effective_user
        lang = get_player_language(user.id)

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
        lang = get_player_language(user.id)

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
                from game.actions import EVENING_CYCLE_DEADLINE, EVENING_CYCLE_RESULTS
                next_deadline = datetime.datetime.combine(now.date(), EVENING_CYCLE_DEADLINE)
                next_results = datetime.datetime.combine(now.date(), EVENING_CYCLE_RESULTS)

        # Format time remaining
        if now > next_deadline:
            time_to_deadline = get_text("deadline_passed", lang)
            time_to_results = str(int((next_results - now).total_seconds() / 60)) + " " + get_text("minutes", lang)
        else:
            time_to_deadline = str(int((next_deadline - now).total_seconds() / 60)) + " " + get_text("minutes", lang)
            time_to_results = str(int((next_results - now).total_seconds() / 60)) + " " + get_text("minutes", lang)

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

        # Check if player is registered
        player = get_player(user.id)
        if not player:
            await update.message.reply_text(get_text("not_registered", lang))
            return

        # Check if actions should refresh
        update_action_counts(user.id)

        # Check if player has actions left
        actions = get_remaining_actions(user.id)
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
        lang = get_player_language(user.id)

        # Check if player is registered
        player = get_player(user.id)
        if not player:
            await update.message.reply_text(get_text("not_registered", lang))
            return

        # Check if actions should refresh
        update_action_counts(user.id)

        # Check if player has actions left
        actions = get_remaining_actions(user.id)
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
        lang = get_player_language(user.id)

        from db.queries import cancel_last_action
        if cancel_last_action(user.id):
            await update.message.reply_text(get_text("action_cancelled", lang))
        else:
            await update.message.reply_text(get_text("no_pending_actions", lang))

    async def actions_left_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show remaining actions."""
        user = update.effective_user
        lang = get_player_language(user.id)

        # Check if player is registered
        player = get_player(user.id)
        if not player:
            await update.message.reply_text(get_text("not_registered", lang))
            return

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
        user = update.effective_user
        lang = get_player_language(user.id)
        args = context.args

        if not args:
            # Show list of districts to select from
            districts = get_districts_for_selection(lang)
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
        district = get_district_by_name(district_name)

        if district:
            district_id = district[0]
            district_info = format_district_info(district_id, lang)

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

    def get_districts_for_selection(lang="en"):
        """Get list of districts for selection menu."""
        try:
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()
            cursor.execute("SELECT district_id, name FROM districts ORDER BY name")
            districts = cursor.fetchall()
            conn.close()
            return districts
        except Exception as e:
            logger.error(f"Error getting districts: {e}")
            return []

    async def politicians_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show list of local politicians."""
        user = update.effective_user
        lang = get_player_language(user.id)

        politicians_text = format_politicians_list(is_international=False, lang=lang)

        # Get list of politicians for buttons
        import sqlite3
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT politician_id, name FROM politicians WHERE is_international = 0 ORDER BY name")
        politicians = cursor.fetchall()
        conn.close()

        if not politicians:
            await update.message.reply_text(get_text("no_politicians", lang))
            return

        # Show list of politicians to choose from
        keyboard = []
        for politician in politicians:
            pol_id, name = politician
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
        lang = get_player_language(user.id)
        args = context.args

        if not args:
            # Call the politicians_command to show the list
            await politicians_command(update, context)
            return

        politician_name = ' '.join(args)
        politician = get_politician_by_name(politician_name)

        if politician:
            politician_info = format_politician_info(politician[0], user.id, lang)

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
        lang = get_player_language(user.id)

        international_text = format_politicians_list(is_international=True, lang=lang)

        await update.message.reply_text(international_text, parse_mode='Markdown')

    async def resources_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show player's resources and information about resource usage."""
        user = update.effective_user
        lang = get_player_language(user.id)

        resources = get_player_resources(user.id)

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
        lang = get_player_language(user.id)
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
        resources = get_player_resources(user.id)
        resources_needed = amount * 2  # 2 resources = 1 of any other type

        if resources['resources'] < resources_needed:
            await update.message.reply_text(
                get_text("not_enough_resources", lang, needed=resources_needed, available=resources['resources'])
            )
            return

        # Perform the conversion
        update_player_resources(user.id, 'resources', -resources_needed)
        update_player_resources(user.id, resource_type, amount)

        await update.message.reply_text(
            get_text("conversion_success", lang,
                     resources_used=resources_needed,
                     amount=amount,
                     resource_type=get_resource_name(resource_type, lang))
        )

    async def check_income_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check player's expected resource income."""
        user = update.effective_user
        lang = get_player_language(user.id)

        # Get districts controlled by the player (60+ control points)
        districts = get_player_districts(user.id)
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

                if control_points >= 60:
                    district = get_district_info(district_id)
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
        """Change the interface language."""
        user = update.effective_user
        lang = get_player_language(user.id)

        keyboard = [
            [
                InlineKeyboardButton(get_text("language_button_en", lang), callback_data="lang:en"),
                InlineKeyboardButton(get_text("language_button_ru", lang), callback_data="lang:ru")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            get_text("language_current", lang, language=lang) + "\n\n" +
            get_text("language_select", lang),
            reply_markup=reply_markup
        )

    async def receive_info_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle receiving information content for quick info action."""
        user = update.effective_user
        lang = get_player_language(user.id)
        content = update.message.text.strip()

        if not content:
            await update.message.reply_text(get_text("invalid_info_content", lang))
            return ConversationHandler.END

        # Check if player has quick actions left
        actions = get_remaining_actions(user.id)
        if actions['quick'] <= 0:
            await update.message.reply_text(get_text("no_quick_actions", lang))
            return ConversationHandler.END

        # Spread information requires 1 Information resource
        resources = get_player_resources(user.id)
        if resources['information'] < 1:
            await update.message.reply_text(
                get_text("insufficient_resources", lang, resource_type=get_resource_name("information", lang))
            )
            return ConversationHandler.END

        # Deduct resource
        update_player_resources(user.id, 'information', -1)

        # Use action
        if not use_action(user.id, False):
            await update.message.reply_text(get_text("no_quick_actions", lang))
            return ConversationHandler.END

        # Add news item
        title = get_text("info_from_user", lang, user=user.first_name)
        add_news(title, content, is_public=True, is_fake=False)

        # Add the action to the database
        from db.queries import add_action
        resources_used = {"information": 1}
        add_action(user.id, "info", "news", "public", resources_used)

        await update.message.reply_text(get_text("info_spreading", lang))
        return ConversationHandler.END

    # Admin commands
    async def admin_add_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to add a news item."""
        user = update.effective_user
        lang = get_player_language(user.id)

        if user.id not in ADMIN_IDS:
            await update.message.reply_text(get_text("admin_only", lang))
            return

        args = context.args

        if len(args) < 2:
            await update.message.reply_text(get_text("admin_news_usage", lang))
            return

        title = args[0]
        content = ' '.join(args[1:])

        news_id = add_news(title, content)

        await update.message.reply_text(get_text("admin_news_added", lang, news_id=news_id))

    async def admin_process_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin command to manually process a game cycle."""
        user = update.effective_user
        lang = get_player_language(user.id)

        if user.id not in ADMIN_IDS:
            await update.message.reply_text(get_text("admin_only", lang))
            return

        await process_game_cycle(context)

        await update.message.reply_text(get_text("admin_cycle_processed", lang))

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
        application.add_handler(conv_handler)

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

        logger.info("Command handlers registered")
