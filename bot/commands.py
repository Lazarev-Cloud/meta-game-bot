import sqlite3
import logging
import datetime
import re
import random
import html
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from config import ADMIN_IDS
from languages import get_text, get_cycle_name, get_resource_name, get_action_name
from db.queries import (
    register_player, set_player_name, get_player,
    get_player_language, get_player_resources, update_player_resources,
    get_remaining_actions, update_action_counts, get_news,
    get_player_districts, add_news, use_action, get_district_info,
    join_coordinated_action, get_open_coordinated_actions,
    get_coordinated_action_participants, get_coordinated_action_details
)
from game.districts import (
    generate_text_map, format_district_info, get_district_by_name
)
from game.politicians import (
    format_politicians_list, format_politician_info, get_politician_by_name
)
from game.actions import (
    process_game_cycle, get_current_cycle, get_cycle_deadline, get_cycle_results_time,
    ACTION_ATTACK, ACTION_DEFENSE, register_player_presence, get_player_presence_status
)
from utils import format_resources

logger = logging.getLogger(__name__)

# Chat states for conversation handlers
WAITING_NAME = "WAITING_NAME"
WAITING_INFO_CONTENT = "WAITING_INFO_CONTENT"


# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the conversation and register the user if needed."""
    user = update.effective_user
    lang = get_player_language(user.id)

    # Check if player is already registered
    player = get_player(user.id)
    if player:
        # Player is already registered, show status and action buttons
        resources = get_player_resources(user.id)
        
        # Create a message with status info
        status_text = (
            f"<b>{get_text('welcome_back', lang, default='Welcome back')} {player['name']}!</b>\n\n"
            f"<b>{get_text('status_title', lang)}:</b>\n"
            f"{format_resources(resources, lang)}\n\n"
            f"{get_text('what_next', lang, default='What would you like to do?')}"
        )
        
        # Create main action buttons
        keyboard = [
            [
                InlineKeyboardButton(get_text('action_button', lang, default='🎯 Actions'), callback_data="main_menu:actions"),
                InlineKeyboardButton(get_text('status_button', lang, default='📊 Status'), callback_data="main_menu:status")
            ],
            [
                InlineKeyboardButton(get_text('districts_button', lang, default='🏙️ Districts'), callback_data="main_menu:districts"),
                InlineKeyboardButton(get_text('politicians_button', lang, default='👥 Politicians'), callback_data="main_menu:politicians")
            ],
            [
                InlineKeyboardButton(get_text('join_button', lang, default='🤝 Join Actions'), callback_data="main_menu:join"),
                InlineKeyboardButton(get_text('language_button', lang, default='🌐 Language'), callback_data="main_menu:language")
            ],
            [
                InlineKeyboardButton(get_text('news_button', lang, default='📰 News'), callback_data="main_menu:news"),
                InlineKeyboardButton(get_text('help_button', lang, default='❓ Help'), callback_data="main_menu:help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=status_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        # New player registration
        register_player(user.id, user.username or "", lang)
        
        # Send welcome message with language selection buttons
        welcome_text = get_text('welcome', lang)
        
        keyboard = [
            [
                InlineKeyboardButton(get_text('language_en', lang, default='English 🇺🇸'), callback_data="language:en"),
                InlineKeyboardButton(get_text('language_ru', lang, default='Русский 🇷🇺'), callback_data="language:ru")
            ],
            [
                InlineKeyboardButton(get_text('set_name_button', lang, default='Set your character name'), callback_data="set_name:start")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=reply_markup
        )


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

    # Define the strings outside the f-string
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

    # Get player information
    player = get_player(user.id)
    player_id = user.id if player else None

    # Determine if this is a new user
    is_new_user = player is None

    # Create a clear, user-friendly help text with emojis
    if is_new_user:
        # Quick start guide for new users
        help_text = (
            f"<b>🎮 {get_text('welcome', lang)}</b>\n\n"
            f"<b>🚀 {get_text('quick_start_guide', lang, default='Quick Start Guide:')}</b>\n"
            f"1️⃣ {get_text('quick_start_1', lang, default='Type /start to register and begin playing')}\n"
            f"2️⃣ {get_text('quick_start_2', lang, default='Choose your language using /language')}\n"
            f"3️⃣ {get_text('quick_start_3', lang, default='Set your character name when prompted')}\n"
            f"4️⃣ {get_text('quick_start_4', lang, default='Use /status to view your resources')}\n"
            f"5️⃣ {get_text('quick_start_5', lang, default='Start playing with /act to perform actions')}\n\n"
            f"<b>❓ {get_text('need_more_help', lang, default='Need more help?')}</b>\n"
            f"{get_text('contact_admin', lang, default='Contact the game administrator for assistance.')}\n\n"
        )
    else:
        # Help for registered users - organized by categories
        help_text = f"<b>🎮 {get_text('help_title', lang)}</b>\n\n"
        
        # Basic commands section
        help_text += (
            f"<b>📋 {get_text('basic_commands', lang, default='Basic Commands:')}</b>\n"
            f"• /start - {get_text('start_command_help', lang)}\n"
            f"• /help - {get_text('help_command_help', lang)}\n"
            f"• /status - {get_text('status_command_help', lang)}\n"
            f"• /language - {get_text('language_command_help', lang)}\n\n"
        )
        
        # Game actions section
        help_text += (
            f"<b>🎯 {get_text('game_actions', lang, default='Game Actions:')}</b>\n"
            f"• /act - {get_text('act_command_help', lang)}\n"
            f"• /join - {get_text('join_command_help', lang)}\n\n"
        )
        
        # Information section
        help_text += (
            f"<b>🔍 {get_text('information_commands', lang, default='Information Commands:')}</b>\n"
            f"• /districts - {get_text('districts_command_help', lang)}\n"
            f"• /politicians - {get_text('politicians_command_help', lang)}\n"
            f"• /news - {get_text('news_command_help', lang)}\n\n"
        )

        # Coordinated actions explanation
        help_text += (
            f"<b>🤝 {get_text('coordinated_actions_heading', lang, default='Coordinated Actions:')}</b>\n"
            f"{get_text('coordinated_actions_help_text', lang, default='• Use /join to see available coordinated actions\n• Create a coordinated action with the "Attack" or "Defense" option when using /act\n• The more players join, the stronger the action will be')}\n\n"
        )

        # Resources explanation
        help_text += (
            f"<b>💰 {get_text('resources_heading', lang, default='Resources:')}</b>\n"
            f"{get_text('resources_help_text', lang, default='• You get resources from districts you control\n• Different actions require different resources\n• Plan your resource usage carefully')}\n\n"
        )

        # Game cycles explanation
        help_text += (
            f"<b>🕒 {get_text('game_cycles_heading', lang, default='Game Cycles:')}</b>\n"
            f"{get_text('game_cycles_help_text', lang, default='• The game has morning and evening cycles\n• Your actions refresh at the start of each cycle\n• Resources are distributed at the start of each cycle')}\n\n"
        )

        # Add player ID information
        if player_id:
            help_text += f"<b>🆔 {get_text('player_id_title', lang, default='Your Player ID:')}</b> {player_id}\n\n"

    # Add admin hint for admins
    if is_admin:
        help_text += (
            f"<b>⚙️ {get_text('admin_commands', lang, default='Admin Commands:')}</b>\n"
            f"{get_text('admin_help_hint', lang, default='Use /admin_help to see all admin commands.')}\n\n"
        )

    # Add footer with tips
    help_text += (
        f"<b>💡 {get_text('tips_heading', lang, default='Helpful Tips:')}</b>\n"
        f"{get_text('help_tips', lang, default='• Form alliances with other players\n• Watch the news for important events\n• Balance your resource usage carefully')}\n\n"
    )

    # Add contact information
    help_text += get_text('help_footer', lang, default="If you need assistance, contact the game administrator.")

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


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display player's current status."""
    user = update.effective_user
    lang = get_player_language(user.id)
    player = get_player(user.id)

    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Check if actions should refresh
    update_action_counts(user.id)

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

        f"*{get_text('resources_title', lang)}*\n"
        f"🔵 {get_resource_name('influence', lang)}: {resources['influence']}\n"
        f"💰 {get_resource_name('resources', lang)}: {resources['resources']}\n"
        f"🔍 {get_resource_name('information', lang)}: {resources['information']}\n"
        f"👊 {get_resource_name('force', lang)}: {resources['force']}\n\n"

        f"*{get_text('remaining_actions', lang)}*\n"
        f"{get_text('main_actions_status', lang, count=actions['main'])}\n"
        f"{get_text('quick_actions_status', lang, count=actions['quick'])}\n\n"
    )

    if districts:
        status_text += f"*{get_text('status_districts', lang)}*\n"
        for district in districts:
            district_id, name, control = district

            # Determine control status based on control points
            from game.districts import get_control_status_text
            control_status = get_control_status_text(control, lang)

            status_text += f"{name}: {control} {get_text('control_points', lang, count=control)} - {control_status}\n"
    else:
        status_text += f"*{get_text('status_no_districts', lang)}*\n"

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
        [InlineKeyboardButton(get_text("action_join", lang, default="Join"), callback_data=f"action_type:join")],
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

    # Resource management
    resources_text = (
        f"*{get_text('resources_title', lang)}*\n\n"
        f"🔵 {get_resource_name('influence', lang)}: {resources['influence']}\n"
        f"💰 {get_resource_name('resources', lang)}: {resources['resources']}\n"
        f"🔍 {get_resource_name('information', lang)}: {resources['information']}\n"
        f"👊 {get_resource_name('force', lang)}: {resources['force']}\n\n"
        f"{get_text('resources_guide', lang)}\n\n"
        f"*{get_text('resources_exchange_help', lang, default='Resource Exchange')}*\n"
        f"{get_text('resources_exchange_info', lang, default='Use /exchange for an interactive resource exchange interface.')}"
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


async def set_name_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the command to set a player's character name."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return
    
    # If player already has a name, confirm they want to change it
    if player[2]:  # player[2] contains the character name
        keyboard = [
            [
                InlineKeyboardButton(get_text("yes", lang, default="Yes"), callback_data="set_name:start"),
                InlineKeyboardButton(get_text("no", lang, default="No"), callback_data="back_to_main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            get_text("name_change_confirm", lang, default="You already have a character name. Do you want to change it?"),
            reply_markup=reply_markup
        )
    else:
        # Start name setting process
        await update.message.reply_text(
            get_text("enter_character_name", lang, default="Please enter your character name:")
        )
        return WAITING_NAME


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


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Join a coordinated action with specified action ID and resources."""
    user = update.effective_user
    lang = get_player_language(user.id)
    args = context.args

    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Check if actions should refresh
    update_action_counts(user.id)

    # Check if player has main actions left (coordinated actions use main actions)
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        await update.message.reply_text(get_text("no_main_actions", lang))
        return

    # If no arguments provided, show available actions
    if not args:
        await list_coordinated_actions_command(update, context)
        return

    # Process with arguments (action_id, resource types...)
    try:
        action_id = int(args[0])

        # Get action details to show in confirmation
        action_details = get_coordinated_action_details(action_id)

        if not action_details:
            await update.message.reply_text(get_text("action_not_found", lang))
            return

        action_type = action_details['action_type']
        target_type = action_details['target_type']
        target_id = action_details['target_id']

        # Get target name
        if target_type == "district":
            from game.districts import get_district_by_id
            target_info = get_district_by_id(target_id)
            target_name = target_info['name'] if target_info else target_id
        elif target_type == "politician":
            from game.politicians import get_politician_by_id
            target_info = get_politician_by_id(target_id)
            target_name = target_info['name'] if target_info else target_id
        else:
            target_name = target_id

        # Parse resource arguments if provided
        resources_dict = {}
        if len(args) > 1:
            for resource_type in args[1:]:
                resource_type = resource_type.lower()
                if resource_type in ["influence", "resources", "information", "force"]:
                    if resource_type in resources_dict:
                        resources_dict[resource_type] += 1
                    else:
                        resources_dict[resource_type] = 1

        # If resources are provided, process the join directly
        if resources_dict:
            # Validate resources
            player_resources = get_player_resources(user.id)
            for resource_type, amount in resources_dict.items():
                if player_resources.get(resource_type, 0) < amount:
                    await update.message.reply_text(
                        get_text("insufficient_resources", lang, resource_type=get_resource_name(resource_type, lang))
                    )
                    return

            # Join the action
            success, message = join_coordinated_action(user.id, action_id, resources_dict)

            if success:
                # Deduct resources
                for resource_type, amount in resources_dict.items():
                    update_player_resources(user.id, resource_type, -amount)

                # Use a main action
                use_action(user.id, True)  # True for main action

                # Format resources for display
                resources_text = []
                for resource_type, amount in resources_dict.items():
                    resources_text.append(f"{amount} {get_resource_name(resource_type, lang)}")

                resources_display = ", ".join(resources_text)

                await update.message.reply_text(
                    get_text("joined_coordinated_action", lang,
                             action_type=get_action_name(action_type, lang),
                             target=target_name,
                             resources=resources_display)
                )
            else:
                await update.message.reply_text(message)

            return

        # Otherwise, show interactive resource selection
        # Create buttons to select resources
        keyboard = [
            [
                InlineKeyboardButton("1 Influence", callback_data=f"join_resource:{action_id}:influence:1"),
                InlineKeyboardButton("1 Resources", callback_data=f"join_resource:{action_id}:resources:1")
            ],
            [
                InlineKeyboardButton("1 Information", callback_data=f"join_resource:{action_id}:information:1"),
                InlineKeyboardButton("1 Force", callback_data=f"join_resource:{action_id}:force:1")
            ],
            [
                InlineKeyboardButton("2 Influence", callback_data=f"join_resource:{action_id}:influence:2"),
                InlineKeyboardButton("2 Force", callback_data=f"join_resource:{action_id}:force:2")
            ],
            [
                InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            get_text("select_resources_join", lang,
                     action_type=get_action_name(action_type, lang),
                     target_name=target_name),
            reply_markup=reply_markup
        )

    except ValueError:
        await update.message.reply_text(get_text("join_usage", lang))
    except Exception as e:
        logger.error(f"Error in join_command: {e}")
        await update.message.reply_text(get_text("action_error", lang))


async def exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive resource exchange system using buttons."""
    user = update.effective_user
    lang = get_player_language(user.id)

    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Get player's current resources
    resources = get_player_resources(user.id)
    if not resources:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Create buttons for resource exchange options
    keyboard = []
    
    # Create color indicators for resource amounts
    def get_resource_indicator(amount):
        if amount < 5:
            return "🔴"  # Red for low
        elif amount < 10:
            return "🟡"  # Yellow for medium
        else:
            return "🟢"  # Green for high

    # Resources → Influence (2:1)
    if resources['resources'] >= 2:
        keyboard.append([
            InlineKeyboardButton(
                f"2 {get_resource_name('resources', lang)} → 1 {get_resource_name('influence', lang)}",
                callback_data="exchange:resources:influence:1"
            )
        ])

    # Resources → Information (2:1)
    if resources['resources'] >= 2:
        keyboard.append([
            InlineKeyboardButton(
                f"2 {get_resource_name('resources', lang)} → 1 {get_resource_name('information', lang)}",
                callback_data="exchange:resources:information:1"
            )
        ])

    # Resources → Force (2:1)
    if resources['resources'] >= 2:
        keyboard.append([
            InlineKeyboardButton(
                f"2 {get_resource_name('resources', lang)} → 1 {get_resource_name('force', lang)}",
                callback_data="exchange:resources:force:1"
            )
        ])

    # Add larger exchanges if the player has enough resources
    if resources['resources'] >= 4:
        keyboard.append([
            InlineKeyboardButton(
                f"4 {get_resource_name('resources', lang)} → 2 {get_resource_name('influence', lang)}",
                callback_data="exchange:resources:influence:2"
            )
        ])

    if resources['resources'] >= 6:
        keyboard.append([
            InlineKeyboardButton(
                f"6 {get_resource_name('resources', lang)} → 3 {get_resource_name('force', lang)}",
                callback_data="exchange:resources:force:3"
            )
        ])

    # Add cancel button
    keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Add colored indicators to resource counts
    influence_indicator = get_resource_indicator(resources['influence'])
    resources_indicator = get_resource_indicator(resources['resources']) 
    information_indicator = get_resource_indicator(resources['information'])
    force_indicator = get_resource_indicator(resources['force'])

    resource_text = (
        f"*{get_text('resources_title', lang)}*\n\n"
        f"{influence_indicator} 🔵 {get_resource_name('influence', lang)}: {resources['influence']}\n"
        f"{resources_indicator} 💰 {get_resource_name('resources', lang)}: {resources['resources']}\n"
        f"{information_indicator} 🔍 {get_resource_name('information', lang)}: {resources['information']}\n"
        f"{force_indicator} 👊 {get_resource_name('force', lang)}: {resources['force']}\n\n"
        f"{get_text('exchange_instructions', lang, default='Select a resource exchange option:')}"
    )

    await update.message.reply_text(
        resource_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def list_coordinated_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all open coordinated actions that players can join."""
    user = update.effective_user
    lang = get_player_language(user.id)

    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return

    # Get all open coordinated actions
    open_actions = get_open_coordinated_actions()

    if not open_actions:
        await update.message.reply_text(get_text("no_coordinated_actions", lang))
        return

    # Format actions
    response = f"*{get_text('coordinated_actions_title', lang)}*\n\n"

    for action in open_actions:
        action_id = action[0]
        initiator_name = action[8] or get_text("unnamed", lang)
        action_type_raw = action[2]
        action_type = get_action_name(action_type_raw, lang)
        target_type = action[3]
        target_id = action[4]

        # Get target name based on type
        if target_type == "district":
            from game.districts import get_district_by_id
            target_info = get_district_by_id(target_id)
            target_name = target_info['name'] if target_info else target_id
        elif target_type == "politician":
            from game.politicians import get_politician_by_id
            target_info = get_politician_by_id(target_id)
            target_name = target_info['name'] if target_info else target_id
        else:
            target_name = target_id

        # Get participants
        participants = get_coordinated_action_participants(action_id)
        participant_count = len(participants)

        # Format action entry
        response += f"*{get_text('action_id', lang)}: {action_id}*\n"
        response += f"{get_text('action_type', lang)}: {action_type}\n"
        response += f"{get_text('target', lang)}: {target_name} ({target_type})\n"
        response += f"{get_text('initiator', lang)}: {initiator_name}\n"
        response += f"{get_text('participants', lang)}: {participant_count}\n"
        response += f"{get_text('join_command', lang)}: `/join {action_id} {action_type_raw} {target_type} {target_id}`\n\n"

    response += get_text("coordinated_actions_help", lang)

    await update.message.reply_text(response, parse_mode='Markdown')


def get_resource_indicator(amount):
    """Return a colored indicator emoji based on resource amount."""
    if amount < 5:
        return "🔴"  # Red for low
    elif amount < 10:
        return "🟡"  # Yellow for medium
    else:
        return "🟢"  # Green for high


def get_district_by_location(location_data):
    """
    Get the district ID for a given location.
    
    Args:
        location_data: Location data containing latitude/longitude
        
    Returns:
        str: District ID or None if no matching district
    """
    try:
        if not location_data or 'latitude' not in location_data or 'longitude' not in location_data:
            logger.error("Invalid location data provided")
            return None
            
        lat = location_data['latitude']
        lon = location_data['longitude']
        
        logger.info(f"Looking up district for location: {lat}, {lon}")
        
        # Sample geo boundaries for Belgrade districts (approximate)
        # In a production environment, these would be stored in the database with proper polygon data
        district_boundaries = {
            'stari_grad': {
                'center': (44.8184, 20.4586),
                'radius': 0.015,  # roughly 1.5km
                'name': 'Stari Grad'
            },
            'vracar': {
                'center': (44.7989, 20.4774),
                'radius': 0.012,
                'name': 'Vračar'
            },
            'savski_venac': {
                'center': (44.8020, 20.4555),
                'radius': 0.018,
                'name': 'Savski Venac'
            },
            'novi_beograd': {
                'center': (44.8152, 20.4115),
                'radius': 0.025,
                'name': 'Novi Beograd'
            },
            'zemun': {
                'center': (44.8430, 20.4011),
                'radius': 0.022,
                'name': 'Zemun'
            },
            'palilula': {
                'center': (44.8156, 20.4861),
                'radius': 0.020,
                'name': 'Palilula'
            },
            'vozdovac': {
                'center': (44.7784, 20.4791),
                'radius': 0.023,
                'name': 'Voždovac'
            },
            'cukarica': {
                'center': (44.7840, 20.4142),
                'radius': 0.025,
                'name': 'Čukarica'
            }
        }
        
        # Function to calculate distance between two coordinates (Haversine formula)
        def calculate_distance(lat1, lon1, lat2, lon2):
            from math import radians, sin, cos, sqrt, atan2
            
            # Convert latitude and longitude from degrees to radians
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            radius = 6371  # Radius of earth in kilometers
            distance = radius * c
            
            return distance
        
        # Find the closest district
        closest_district = None
        min_distance = float('inf')
        
        for district_id, boundary in district_boundaries.items():
            center_lat, center_lon = boundary['center']
            distance = calculate_distance(lat, lon, center_lat, center_lon)
            
            # If within radius, consider it a match
            if distance <= boundary['radius']:
                logger.info(f"Location is within {boundary['name']} district (distance: {distance:.3f}km)")
                
                # If multiple districts match, choose the closest one
                if distance < min_distance:
                    min_distance = distance
                    closest_district = district_id
        
        # If no district is within the specific radius constraints but we need to return something
        if not closest_district:
            logger.info("Location not within any district radius, finding nearest district")
            for district_id, boundary in district_boundaries.items():
                center_lat, center_lon = boundary['center']
                distance = calculate_distance(lat, lon, center_lat, center_lon)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_district = district_id
            
            # Only return if reasonably close (within 10km)
            if min_distance > 10.0:
                logger.warning(f"Location too far from any district (nearest: {min_distance:.3f}km)")
                closest_district = None
                
        if closest_district:
            logger.info(f"Matched location to district: {closest_district}")
            
        return closest_district
        
    except Exception as e:
        logger.error(f"Error finding district by location: {e}")
        return None


async def presence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register physical presence in a district using location sharing."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return
    
    # Check if any actions need to be refreshed
    update_action_counts(user.id)
    
    # Check if message contains location data
    if update.message.location:
        try:
            # Show processing message
            processing_message = await update.message.reply_text(
                get_text("processing_location", lang, default="📍 Processing your location...")
            )
            
            location_data = {
                "latitude": update.message.location.latitude,
                "longitude": update.message.location.longitude
            }
            
            # Log received location data
            logger.info(f"Received location data from user {user.id}: {location_data['latitude']}, {location_data['longitude']}")
            
            # Get nearest district
            district_id = get_district_by_location(location_data)
            
            if not district_id:
                await processing_message.edit_text(
                    get_text("location_not_in_district", lang, 
                            default="📍 Your location could not be matched to any district in Belgrade.")
                )
                return
            
            # Register presence in the district
            result = register_player_presence(user.id, district_id, location_data)
            
            # Get district name
            district_info = get_district_info(district_id)
            district_name = district_info[1] if district_info else district_id  # Index 1 should be the name
            
            if result["success"]:
                # Parse the expiry time for a more user-friendly message
                expires_at = datetime.datetime.fromisoformat(result["expires_at"])
                hours_remaining = int((expires_at - datetime.datetime.now()).total_seconds() / 3600)
                minutes_remaining = int(((expires_at - datetime.datetime.now()).total_seconds() % 3600) / 60)
                time_message = f"{hours_remaining}h {minutes_remaining}m"
                
                # Get presence benefits explanation
                benefits_message = get_text("presence_benefits", lang, 
                                          default="Being physically present gives +20 Control Points to main actions in this district.")
                
                # Create success message with district name and expiry time
                success_message = (
                    f"✅ {get_text('presence_registered_district', lang, default='You are now registered as present in {district}.', district=district_name)}\n\n"
                    f"⏱️ {get_text('presence_duration', lang, default='Duration: {time}', time=time_message)}\n\n"
                    f"📊 {benefits_message}"
                )
                
                # Edit the processing message with the success message
                await processing_message.edit_text(success_message)
                
                # Keyboard to check current presence
                keyboard = [
                    [InlineKeyboardButton(
                        get_text("check_presence_status", lang, default="📍 Check My Status"),
                        callback_data="check_presence"
                    )]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Send district info with reply markup
                await update.message.reply_text(
                    get_text("view_district_prompt", lang, 
                            default="Would you like to check your presence status?"),
                    reply_markup=reply_markup
                )
            else:
                # Edit the processing message with the error message
                await processing_message.edit_text(
                    f"❌ {get_text('presence_registration_failed', lang, default='Failed to register your presence: {reason}', reason=result['message'])}"
                )
                
                # Offer to try again
                keyboard = [
                    [KeyboardButton(
                        get_text("try_again", lang, default="📍 Try Again"),
                        request_location=True
                    )]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
                
                await update.message.reply_text(
                    get_text("location_try_again", lang, default="Would you like to try sharing your location again?"),
                    reply_markup=reply_markup
                )
        
        except Exception as e:
            logger.error(f"Error processing location for user {user.id}: {e}")
            await update.message.reply_text(
                get_text("error_processing_location", lang, 
                        default="An error occurred while processing your location. Please try again later.")
            )
    else:
        # Request location sharing with a better explanation
        explanation = get_text("location_explanation", lang, 
                              default="Physical presence in a district gives you a +20 Control Point bonus to all main actions there for 6 hours.")
        
        instruction = get_text("location_instruction", lang,
                              default="Please share your location to register your physical presence.")
        
        keyboard = [
            [KeyboardButton(
                get_text("share_location", lang, default="📍 Share my location"),
                request_location=True
            )]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Send explanation and request location
        await update.message.reply_text(f"ℹ️ {explanation}\n\n📱 {instruction}", reply_markup=reply_markup)


async def check_presence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current physical presence status."""
    user = update.effective_user
    lang = get_player_language(user.id)
    
    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await update.message.reply_text(get_text("not_registered", lang))
        return
    
    # Show loading message
    loading_message = await update.message.reply_text(
        get_text("checking_presence", lang, default="📍 Checking your presence status...")
    )
    
    try:
        # Get player's presence status
        from game.actions import get_player_presence_status
        presence_records = get_player_presence_status(user.id)
        
        if not presence_records:
            await loading_message.edit_text(
                get_text("no_active_presence", lang,
                        default="📍 You are not currently registered as physically present in any district.")
            )
            
            # Offer to register presence
            keyboard = [
                [KeyboardButton(
                    get_text("share_location", lang, default="📍 Share my location"),
                    request_location=True
                )]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                get_text("register_presence_prompt", lang,
                        default="Would you like to register your physical presence now?"),
                reply_markup=reply_markup
            )
            return
        
        # Format presence information
        presence_text = f"🗺️ *{get_text('active_presence_title', lang, default='Your Active Physical Presence')}*\n\n"
        
        for record in presence_records:
            district_name = record['district_name']
            district_id = record['district_id']
            time_remaining = record['time_remaining']
            control = record.get('control_points', 0)
            
            # Create resource info string
            resources = record['resources_available']
            resource_text = ""
            if any(resources.values()):
                resource_text = get_text("district_resources", lang, default="Resources:") + " "
                resource_icons = []
                
                if resources['influence'] > 0:
                    resource_icons.append(f"🔵×{resources['influence']}")
                if resources['resources'] > 0:
                    resource_icons.append(f"💰×{resources['resources']}")
                if resources['information'] > 0:
                    resource_icons.append(f"🔍×{resources['information']}")
                if resources['force'] > 0:
                    resource_icons.append(f"👊×{resources['force']}")
                    
                resource_text += ", ".join(resource_icons)
            
            # Format control level with icon
            if control >= 75:
                control_icon = "🟢"  # Green for high control
            elif control >= 40:
                control_icon = "🟡"  # Yellow for medium control
            elif control > 0:
                control_icon = "🟠"  # Orange for low control
            else:
                control_icon = "⚪"  # White for no control
                
            presence_text += (
                f"🏙️ *{district_name}*\n"
                f"⏱️ {get_text('expires_in', lang, default='Expires in')}: {time_remaining}\n"
                f"{control_icon} {get_text('control_level', lang, default='Control')}: {control}%\n"
            )
            
            if resource_text:
                presence_text += f"{resource_text}\n"
                
            presence_text += "\n"
        
        # Add explanation of benefits
        presence_text += (
            f"ℹ️ {get_text('presence_benefits', lang, default='Physical presence gives you a +20 Control Point bonus when performing main actions in these districts.')}"
        )
        
        # Create inline keyboard for district actions
        keyboard = []
        
        # Add button for each district
        for record in presence_records:
            district_id = record['district_id']
            district_name = record['district_name']
            keyboard.append([
                InlineKeyboardButton(
                    get_text("view_district_button", lang, default="View {district}", district=district_name),
                    callback_data=f"view_district:{district_id}"
                )
            ])
        
        # Add refresh button
        keyboard.append([
            InlineKeyboardButton(
                get_text("refresh_presence", lang, default="🔄 Refresh Status"), 
                callback_data="refresh_presence"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the presence status with interactive buttons
        await loading_message.edit_text(
            presence_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error checking presence status for user {user.id}: {e}")
        await loading_message.edit_text(
            get_text("presence_check_error", lang, 
                    default="An error occurred while checking your presence status. Please try again later.")
        )