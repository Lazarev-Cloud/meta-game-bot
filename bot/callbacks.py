import logging
import sqlite3

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from bot.commands import register_commands, executor
from config import TOKEN
from db.queries import (
    get_player_resources, update_player_resources,
    get_remaining_actions, use_action, add_action,
    update_district_control
)
from db.schema import setup_database
from game.actions import (
    ACTION_INFLUENCE, ACTION_ATTACK, ACTION_DEFENSE,
    QUICK_ACTION_RECON, QUICK_ACTION_INFO, QUICK_ACTION_SUPPORT
)
from game.actions import schedule_jobs
from game.districts import format_district_info
from game.politicians import format_politician_info
from languages import get_text, get_player_language, set_player_language, get_action_name, get_resource_name

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    # Set up the database
    setup_database()

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    register_commands(application)

    # Register callback handlers
    register_callbacks(application)

    # Set up scheduled jobs
    application.job_queue.run_once(schedule_jobs, 1)

    # Start the Bot
    logger.info("Bot starting up...")
    application.run_polling()
    logger.info("Bot stopped")


async def show_district_selection(query, message_text):
    """Display a list of districts for selection."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT district_id, name FROM districts ORDER BY name")
        districts = cursor.fetchall()
        conn.close()

        keyboard = []
        for district_id, name in districts:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"district_select:{district_id}")])

        # Add cancel button
        keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing district selection: {e}")
        await query.edit_message_text(
            text=get_text("error_district_selection", lang, default="Error showing district selection.")
        )


async def show_resource_selection(query, action_type, district_id):
    """Display resource selection options for an action."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Get district name
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM districts WHERE district_id = ?", (district_id,))
        district_result = cursor.fetchone()
        district_name = district_result[0] if district_result else district_id

        # Get player's resources
        resources = get_player_resources(user.id)
        conn.close()

        if not resources:
            await query.edit_message_text(get_text("not_registered", lang))
            return

        # Create resource selection buttons
        keyboard = []

        # Common resource combinations
        if action_type == ACTION_INFLUENCE:
            resource_options = [
                (f"2 {get_text('influence', lang)}", "influence,influence"),
                (f"1 {get_text('influence', lang)}, 1 {get_text('resources', lang)}", "influence,resources"),
                (f"1 {get_text('influence', lang)}, 1 {get_text('information', lang)}", "influence,information")
            ]
        elif action_type == ACTION_ATTACK:
            resource_options = [
                (f"2 {get_text('force', lang)}", "force,force"),
                (f"1 {get_text('force', lang)}, 1 {get_text('influence', lang)}", "force,influence"),
                (f"1 {get_text('force', lang)}, 1 {get_text('information', lang)}", "force,information")
            ]
        elif action_type == ACTION_DEFENSE:
            resource_options = [
                (f"2 {get_text('force', lang)}", "force,force"),
                (f"1 {get_text('force', lang)}, 1 {get_text('resources', lang)}", "force,resources"),
                (f"1 {get_text('influence', lang)}, 1 {get_text('force', lang)}", "influence,force")
            ]
        else:
            resource_options = []

        for label, resources_str in resource_options:
            resources_list = resources_str.split(',')
            # Check if player has enough resources
            if all(resources.get(r, 0) >= 1 for r in resources_list):
                keyboard.append([
                    InlineKeyboardButton(
                        label,
                        callback_data=f"resources:{action_type}:district:{district_id}:{resources_str}"
                    )
                ])

        # Add cancel button
        keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=get_text("select_resources", lang, action_type=action_type, district_name=district_name),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error showing resource selection: {e}")
        await query.edit_message_text(
            text=get_text("error_resource_selection", lang, default="Error showing resource selection.")
        )


async def process_quick_action(query, action_type, target_type, target_id):
    """Process a quick action such as reconnaissance or support."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Check if player has quick actions left
        actions = get_remaining_actions(user.id)
        if actions['quick'] <= 0:
            await query.edit_message_text(get_text("no_quick_actions", lang))
            return

        # Get target name for display
        if target_type == "district":
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM districts WHERE district_id = ?", (target_id,))
            target_result = cursor.fetchone()
            target_name = target_result[0] if target_result else target_id
            conn.close()
        elif target_type == "politician":
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM politicians WHERE politician_id = ?", (target_id,))
            target_result = cursor.fetchone()
            target_name = target_result[0] if target_result else target_id
            conn.close()
        else:
            target_name = target_id

        # Different processing based on action type
        if action_type == QUICK_ACTION_RECON:
            # Reconnaissance requires 1 Information resource
            resources = get_player_resources(user.id)
            if resources['information'] < 1:
                await query.edit_message_text(
                    get_text("insufficient_resources", lang, resource_type=get_resource_name("information", lang))
                )
                return

            # Deduct resource
            update_player_resources(user.id, 'information', -1)

            # Use action
            if not use_action(user.id, False):
                await query.edit_message_text(get_text("no_quick_actions", lang))
                return

            # Add the action to the database
            resources_used = {"information": 1}
            add_action(user.id, "recon", target_type, target_id, resources_used)

            # Get district info for immediate display
            if target_type == "district":
                district_info = await asyncio.get_event_loop().run_in_executor(
                    executor,
                    format_district_info,
                    target_id,
                    lang
                )

                await query.edit_message_text(
                    text=district_info,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    get_text("action_submitted", lang,
                             action_type=get_action_name("recon", lang),
                             target_name=target_name,
                             resources="1 " + get_resource_name("information", lang))
                )

        elif action_type == QUICK_ACTION_SUPPORT:
            # Support requires 1 Influence resource
            resources = get_player_resources(user.id)
            if resources['influence'] < 1:
                await query.edit_message_text(
                    get_text("insufficient_resources", lang, resource_type=get_resource_name("influence", lang))
                )
                return

            # Deduct resource
            update_player_resources(user.id, 'influence', -1)

            # Use action
            if not use_action(user.id, False):
                await query.edit_message_text(get_text("no_quick_actions", lang))
                return

            # Add the action to the database
            resources_used = {"influence": 1}
            add_action(user.id, "support", target_type, target_id, resources_used)

            await query.edit_message_text(
                get_text("action_submitted", lang,
                         action_type=get_action_name("support", lang),
                         target_name=target_name,
                         resources="1 " + get_resource_name("influence", lang))
            )

            # Apply support immediately for districts
            if target_type == "district":
                update_district_control(user.id, target_id, 5)

        else:
            await query.edit_message_text(get_text("action_error", lang))
            return

    except Exception as e:
        logger.error(f"Error processing quick action: {e}")
        await query.edit_message_text(get_text("action_error", lang))


async def process_main_action(query, action_type, target_type, target_id, resources_list):
    """Process a main action such as influence, attack, or defense."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Check if player has main actions left
        actions = get_remaining_actions(user.id)
        if actions['main'] <= 0:
            await query.edit_message_text(get_text("no_main_actions", lang))
            return

        # Get target name for display
        if target_type == "district":
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM districts WHERE district_id = ?", (target_id,))
            target_result = cursor.fetchone()
            target_name = target_result[0] if target_result else target_id
            conn.close()
        else:
            target_name = target_id

        # Parse resources
        resource_types = resources_list
        resources_dict = {}

        for resource_type in resource_types:
            if resource_type in resources_dict:
                resources_dict[resource_type] += 1
            else:
                resources_dict[resource_type] = 1

        # Check if player has the resources
        player_resources = get_player_resources(user.id)
        for resource_type, amount in resources_dict.items():
            if player_resources.get(resource_type, 0) < amount:
                await query.edit_message_text(
                    get_text("insufficient_resources", lang, resource_type=get_resource_name(resource_type, lang))
                )
                return

        # Deduct resources
        for resource_type, amount in resources_dict.items():
            update_player_resources(user.id, resource_type, -amount)

        # Use action
        if not use_action(user.id, True):
            await query.edit_message_text(get_text("no_main_actions", lang))
            return

        # Add the action to the database
        add_action(user.id, action_type, target_type, target_id, resources_dict)

        # Format resources for display
        resources_display = []
        for resource_type, amount in resources_dict.items():
            resources_display.append(f"{amount} {get_resource_name(resource_type, lang)}")

        resources_text = ", ".join(resources_display)

        await query.edit_message_text(
            get_text("action_submitted", lang,
                     action_type=get_action_name(action_type, lang),
                     target_name=target_name,
                     resources=resources_text)
        )

    except Exception as e:
        logger.error(f"Error processing main action: {e}")
        await query.edit_message_text(get_text("action_error", lang))


async def show_district_info(query, district_id):
    """Display information about a district with action buttons."""
    user = query.from_user
    lang = get_player_language(user.id)

    # Get district info formatted for display via context.application.create_task
    try:
        district_info = await context.application.create_task(
            format_district_info,
            district_id,
            lang
        )
    except Exception as e:
        logger.error(f"Error getting district info: {e}")
        await query.edit_message_text(
            text=get_text("error_district_info", lang, default="Error retrieving district information.")
        )
        return

    if district_info:
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton(get_text("action_influence", lang),
                                     callback_data=f"action_influence:{district_id}"),
                InlineKeyboardButton(get_text("action_attack", lang), callback_data=f"action_attack:{district_id}")
            ],
            [
                InlineKeyboardButton(get_text("action_defense", lang),
                                     callback_data=f"action_defend:{district_id}"),
                InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"quick_recon:{district_id}")
            ],
            [
                InlineKeyboardButton(get_text("action_support", lang), callback_data=f"quick_support:{district_id}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=district_info,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            text=get_text("error_district_info", lang, default="Error retrieving district information.")
        )


async def show_politician_info(query, politician_id):
    """Display information about a politician with action buttons."""
    user = query.from_user
    lang = get_player_language(user.id)

    # Get politician info formatted for display via context.application.create_task
    try:
        politician_info = await context.application.create_task(
            format_politician_info,
            politician_id,
            user.id,
            lang
        )
    except Exception as e:
        logger.error(f"Error getting politician info: {e}")
        await query.edit_message_text(
            text=get_text("error_politician_info", lang, default="Error retrieving politician information.")
        )
        return

    if politician_info:
        # Add action buttons
        keyboard = [
            [
                InlineKeyboardButton(get_text("action_influence", lang),
                                     callback_data=f"pol_influence:{politician_id}"),
                InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"pol_info:{politician_id}")
            ],
            [
                InlineKeyboardButton(get_text("action_info", lang), callback_data=f"pol_undermine:{politician_id}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=politician_info,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            text=get_text("error_politician_info", lang, default="Error retrieving politician information.")
        )


async def process_politician_influence(query, politician_id):
    """Process an influence action on a politician."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Check if player has main actions left
        actions = get_remaining_actions(user.id)
        if actions['main'] <= 0:
            await query.edit_message_text(get_text("politician_influence_no_action", lang))
            return

        # Influence requires 2 Influence resources
        resources = get_player_resources(user.id)
        if resources['influence'] < 2:
            await query.edit_message_text(get_text("politician_influence_no_resources", lang))
            return

        # Get politician name
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM politicians WHERE politician_id = ?", (politician_id,))
        politician_result = cursor.fetchone()
        politician_name = politician_result[0] if politician_result else str(politician_id)
        conn.close()

        # Deduct resources
        update_player_resources(user.id, 'influence', -2)

        # Use action
        if not use_action(user.id, True):
            await query.edit_message_text(get_text("politician_influence_no_action", lang))
            return

        # Record the action (actual effect processed at cycle end)
        resources_used = {"influence": 2}
        add_action(user.id, "influence", "politician", str(politician_id), resources_used)

        await query.edit_message_text(
            get_text("politician_influence_success", lang, name=politician_name)
        )

    except Exception as e:
        logger.error(f"Error processing politician influence: {e}")
        await query.edit_message_text(get_text("action_error", lang))


async def process_politician_info(query, politician_id):
    """Process an information gathering action on a politician."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Check if player has quick actions left
        actions = get_remaining_actions(user.id)
        if actions['quick'] <= 0:
            await query.edit_message_text(get_text("politician_info_no_action", lang))
            return

        # Info requires 1 Information resource
        resources = get_player_resources(user.id)
        if resources['information'] < 1:
            await query.edit_message_text(get_text("politician_info_no_resources", lang))
            return

        # Get politician information
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.name, p.role, p.ideology_score, p.influence, p.district_id, p.is_international, d.name
            FROM politicians p
            LEFT JOIN districts d ON p.district_id = d.district_id
            WHERE p.politician_id = ?
            """,
            (politician_id,)
        )
        politician_result = cursor.fetchone()
        conn.close()

        if not politician_result:
            await query.edit_message_text(get_text("politician_not_found", lang, name=politician_id))
            return

        name, role, ideology, influence, district_id, is_intl, district_name = politician_result

        # Deduct resource
        update_player_resources(user.id, 'information', -1)

        # Use action
        if not use_action(user.id, False):
            await query.edit_message_text(get_text("politician_info_no_action", lang))
            return

        # Record the action
        resources_used = {"information": 1}
        add_action(user.id, "info", "politician", str(politician_id), resources_used)

        # Format politician information
        from languages import format_ideology
        ideology_desc = format_ideology(ideology, lang)

        info_text = (
            f"*{get_text('politician_info_title', lang, name=name)}*\n\n"
            f"*{get_text('role', lang, default='Role')}:* {role}\n"
            f"*{get_text('ideology', lang, default='Ideology')}:* {ideology_desc} ({ideology})\n"
            f"*{get_text('influence', lang, default='Influence')}:* {influence}\n"
        )

        if district_name:
            info_text += f"*{get_text('district', lang, default='District')}:* {district_name}\n"

        # Send the detailed information
        await query.edit_message_text(
            text=info_text,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error processing politician info: {e}")
        await query.edit_message_text(get_text("action_error", lang))


async def process_politician_undermine(query, politician_id):
    """Process an undermining action on a politician."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Check if player has main actions left
        actions = get_remaining_actions(user.id)
        if actions['main'] <= 0:
            await query.edit_message_text(get_text("politician_undermine_no_action", lang))
            return

        # Undermine requires 2 Information resources
        resources = get_player_resources(user.id)
        if resources['information'] < 2:
            await query.edit_message_text(get_text("politician_undermine_no_resources", lang))
            return

        # Get politician name
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM politicians WHERE politician_id = ?", (politician_id,))
        politician_result = cursor.fetchone()
        politician_name = politician_result[0] if politician_result else str(politician_id)
        conn.close()

        # Deduct resources
        update_player_resources(user.id, 'information', -2)

        # Use action
        if not use_action(user.id, True):
            await query.edit_message_text(get_text("politician_undermine_no_action", lang))
            return

        # Record the action (actual effect processed at cycle end)
        resources_used = {"information": 2}
        add_action(user.id, "undermine", "politician", str(politician_id), resources_used)

        await query.edit_message_text(
            get_text("politician_undermine_success", lang, name=politician_name)
        )

    except Exception as e:
        logger.error(f"Error processing politician undermine: {e}")
        await query.edit_message_text(get_text("action_error", lang))


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
                get_text("enter_info_content", lang,
                         default="What information do you want to spread? Please type your message:")
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

    # For viewing politicians and districts, pass the context
    elif callback_data.startswith("view_politician:"):
        politician_id = int(callback_data.split(":")[1])
        await show_politician_info(query, politician_id)

    elif callback_data.startswith("view_district:"):
        district_id = callback_data.split(":")[1]
        await show_district_info(query, district_id)

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


def register_callbacks(application):
    """Register callback handlers."""
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Callback handlers registered")


if __name__ == "__main__":
    main()
