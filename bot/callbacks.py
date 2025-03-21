import logging
import sqlite3
import json
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler

from languages import get_text, get_player_language, set_player_language, get_action_name, get_resource_name, get_cycle_name, get_district_name
from db.queries import (
    get_player, get_player_language, get_player_resources, set_player_language,
    set_player_name, update_player_resources, get_coordinated_action_details,
    join_coordinated_action, get_open_coordinated_actions, get_district_info,
    get_politician_info, get_coordinated_action_participants, exchange_resources,
    cancel_last_action, get_remaining_actions, update_action_counts,
    get_player_districts, get_news, add_news, add_action, use_action,
    get_district_control, update_politician_friendliness, is_player_in_action
)
from game.districts import (
    format_district_info, get_district_by_name, get_district_by_id, generate_text_map, get_all_districts
)
from game.politicians import (
    get_politician_by_name, format_politician_info, format_politicians_list, get_all_politicians
)
from game.actions import (
    ACTION_ATTACK, ACTION_DEFENSE, get_current_cycle, get_cycle_deadline, get_cycle_results_time,
    get_player_presence_status, calculate_participant_power, process_join_with_resources, join_coordinated_action
)
from utils import format_resources, notify_player, log_game_event
from bot.commands import get_districts_for_selection

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Resource indicator helper function
def get_resource_indicator(amount):
    """Return a colored indicator emoji based on resource amount."""
    if amount < 5:
        return "🔴"  # Red for low
    elif amount < 10:
        return "🟡"  # Yellow for medium
    else:
        return "🟢"  # Green for high


async def show_district_selection(query, message_text):
    """Display a list of districts for selection."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        conn = sqlite3.connect('novi_sad_game.db')
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
        from game.districts import get_district_by_id
        district = get_district_by_id(district_id)
        district_name = district['name'] if district else district_id

        # Get player's resources
        resources = get_player_resources(user.id)

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


async def exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle resource exchange."""
    query = update.callback_query
    await query.answer()
    
    # Get user language
    user_id = query.from_user.id
    lang = get_player_language(user_id)
    
    # Parse callback data: exchange:from_resource:to_resource:amount
    data = query.data.split(":")
    if len(data) != 4:
        await query.edit_message_text(get_text("error_invalid_data", lang))
        return
    
    from_resource = data[1]
    to_resource = data[2]
    amount = int(data[3])
    
    # Calculate required resources (2:1 ratio)
    required_amount = amount * 2
    
    # Get player resources
    resources = get_player_resources(user_id)
    if not resources:
        await query.edit_message_text(get_text("resources_error", lang))
        return
    
    # Check if player has enough resources
    if resources[from_resource] < required_amount:
        await query.edit_message_text(get_text("not_enough_resources", lang))
        return
    
    # Update resources (subtract from_resource, add to_resource)
    update_player_resources(user_id, from_resource, -required_amount)
    update_player_resources(user_id, to_resource, amount)
    
    # Get updated resources
    updated_resources = get_player_resources(user_id)
    
    # Create resource indicators
    influence_indicator = get_resource_indicator(updated_resources['influence'])
    resources_indicator = get_resource_indicator(updated_resources['resources']) 
    information_indicator = get_resource_indicator(updated_resources['information'])
    force_indicator = get_resource_indicator(updated_resources['force'])

    # Format response
    exchange_text = get_text("conversion_success", lang,
                             resources_used=required_amount,
                             amount=amount,
                             resource_type=get_resource_name(to_resource, lang))

    resource_text = (
        f"*{get_text('resources_title', lang)}*\n\n"
        f"{influence_indicator} 🔵 {get_resource_name('influence', lang)}: {updated_resources['influence']}\n"
        f"{resources_indicator} 💰 {get_resource_name('resources', lang)}: {updated_resources['resources']}\n"
        f"{information_indicator} 🔍 {get_resource_name('information', lang)}: {updated_resources['information']}\n"
        f"{force_indicator} 👊 {get_resource_name('force', lang)}: {updated_resources['force']}\n\n"
        f"{exchange_text}"
    )

    # Create buttons for another exchange
    keyboard = []

    # Only show options that the player can afford
    if updated_resources['resources'] >= 2:
        keyboard.append([
            InlineKeyboardButton(
                f"{get_text('exchange_again', lang, default='Exchange Again')}",
                callback_data="exchange_again"
            )
        ])

    await query.edit_message_text(
        resource_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def exchange_again_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the exchange options menu again."""
    query = update.callback_query
    await query.answer()
    
    # Get user language
    user_id = query.from_user.id
    lang = get_player_language(user_id)
    
    # Get current resources
    resources = get_player_resources(user_id)
    if not resources:
        await query.edit_message_text(get_text("resources_error", lang))
        return
    
    # Create resource indicators
    influence_indicator = get_resource_indicator(resources['influence'])
    resources_indicator = get_resource_indicator(resources['resources']) 
    information_indicator = get_resource_indicator(resources['information'])
    force_indicator = get_resource_indicator(resources['force'])

    # Create buttons for resource exchange options
    keyboard = []

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

    resource_text = (
        f"*{get_text('resources_title', lang)}*\n\n"
        f"{influence_indicator} 🔵 {get_resource_name('influence', lang)}: {resources['influence']}\n"
        f"{resources_indicator} 💰 {get_resource_name('resources', lang)}: {resources['resources']}\n"
        f"{information_indicator} 🔍 {get_resource_name('information', lang)}: {resources['information']}\n"
        f"{force_indicator} 👊 {get_resource_name('force', lang)}: {resources['force']}\n\n"
        f"{get_text('exchange_instructions', lang, default='Select a resource exchange option:')}"
    )

    await query.edit_message_text(
        resource_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
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
            from game.districts import get_district_by_id
            district = get_district_by_id(target_id)
            target_name = district['name'] if district else target_id
        elif target_type == "politician":
            from game.politicians import get_politician_by_id
            politician = get_politician_by_id(target_id)
            target_name = politician['name'] if politician else target_id
        else:
            target_name = target_id

        # Determine resource type and amount based on action
        if action_type == QUICK_ACTION_RECON:
            resource_type = "information"
            resource_amount = 1
        elif action_type == QUICK_ACTION_SUPPORT:
            resource_type = "influence"
            resource_amount = 1
        elif action_type == QUICK_ACTION_INFO:
            resource_type = "information"
            resource_amount = 1
        else:
            logger.warning(f"Unknown quick action type: {action_type}")
            resource_type = None
            resource_amount = 0

        # Check and deduct resources if needed
        if resource_type and resource_amount > 0:
            player_resources = get_player_resources(user.id)
            if player_resources.get(resource_type, 0) < resource_amount:
                await query.edit_message_text(
                    get_text("insufficient_resources", lang, resource_type=get_resource_name(resource_type, lang))
                )
                return
            update_player_resources(user.id, resource_type, -resource_amount)

        # Use one quick action - IMPORTANT: Pass False for quick action
        if not use_action(user.id, False):  # False means it's a quick action, not a main action
            await query.edit_message_text(get_text("no_quick_actions", lang))
            return

        # Add the action to the database
        if resource_type:
            resources_used = {resource_type: resource_amount}
        else:
            resources_used = {}

        add_action(user.id, action_type, target_type, target_id, resources_used)

        # Show confirmation message
        await query.edit_message_text(
            get_text("action_success", lang,
                     type=get_action_name(action_type, lang),
                     target=target_name)
        )

    except Exception as e:
        logger.error(f"Error processing quick action: {e}")
        await query.edit_message_text(get_text("action_error", lang))


async def process_main_action(query, action_type, target_type, target_id, resources_list, is_coordinated=False):
    """Process a main action such as influence, attack, or defense."""
    user = query.from_user
    lang = get_player_language(user.id)

    try:
        # Check if player has main actions left
        actions = get_remaining_actions(user.id)
        if actions['main'] <= 0:
            await query.edit_message_text(get_text("no_main_actions", lang))
            return

        # Parse resources
        resources_dict = {}
        for resource_type in resources_list:
            if resource_type in resources_dict:
                resources_dict[resource_type] += 1
            else:
                resources_dict[resource_type] = 1

        # Ensure we have sufficient resources for a main action (minimum 2)
        total_resources = sum(resources_dict.values())
        if total_resources < 2:
            await query.edit_message_text(
                get_text("insufficient_resources_for_main_action", lang,
                         default="Main actions require at least 2 resources. Please select more resources.")
            )
            return

        # Check if player has the resources
        player_resources = get_player_resources(user.id)
        for resource_type, amount in resources_dict.items():
            if player_resources.get(resource_type, 0) < amount:
                await query.edit_message_text(
                    get_text("insufficient_resources", lang, resource_type=get_resource_name(resource_type, lang))
                )
                return

        # Get target name based on type
        if target_type == "district":
            from game.districts import get_district_by_id
            district = get_district_by_id(target_id)
            target_name = district['name'] if district else target_id
        elif target_type == "politician":
            from game.politicians import get_politician_by_id
            politician = get_politician_by_id(target_id)
            target_name = politician['name'] if politician else target_id
        else:
            target_name = target_id

        # Deduct resources
        for resource_type, amount in resources_dict.items():
            update_player_resources(user.id, resource_type, -amount)

        # Use one main action - IMPORTANT: True for main action
        if not use_action(user.id, True):  # True means it's a main action
            await query.edit_message_text(get_text("no_main_actions", lang))
            return

        # Format resources for display
        resources_text = []
        for resource_type, amount in resources_dict.items():
            resources_text.append(f"{amount} {get_resource_name(resource_type, lang)}")
        resources_display = ", ".join(resources_text)

        # If it's a coordinated action, create it
        if is_coordinated:
            action_id = create_coordinated_action(
                user.id, action_type, target_type, target_id, resources_dict
            )
            message = get_text("action_coordinated_created", lang,
                               type=get_text(f"action_{action_type}", lang),
                               target=target_name,
                               id=action_id,
                               resources=resources_display)
        else:
            # Otherwise, add a regular action
            add_action(user.id, action_type, target_type, target_id, resources_dict)
            message = get_text("action_submitted", lang,
                               action_type=get_text(f"action_{action_type}", lang),
                               target_name=target_name,
                               resources=resources_display)

        await query.edit_message_text(message)

    except Exception as e:
        logger.error(f"Error processing main action: {e}")
        await query.edit_message_text(get_text("action_error", lang))

async def show_district_info(query, district_id):
    """Display information about a district with action buttons."""
    user = query.from_user
    lang = get_player_language(user.id)

    district_info = format_district_info(district_id, lang)

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
            parse_mode=ParseMode.MARKDOWN,
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

    # Get politician info formatted for display
    politician_info = format_politician_info(politician_id, user.id, lang)

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
            parse_mode=ParseMode.MARKDOWN,
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
        from game.politicians import get_politician_by_id
        politician = get_politician_by_id(politician_id)
        politician_name = politician['name'] if politician else str(politician_id)

        # Deduct resources
        update_player_resources(user.id, 'influence', -2)

        # Use action
        use_action(user.id, True)  # True means it's a main action

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
        from game.politicians import get_politician_by_id
        politician = get_politician_by_id(politician_id)
        
        if not politician:
            await query.edit_message_text(get_text("politician_not_found", lang, name=politician_id))
            return

        name = politician['name']
        role = politician['role']
        ideology = politician['ideology_score']
        influence = politician['influence']
        district_id = politician['district_id']
        is_intl = politician['is_international']
        
        # Get district name if applicable
        district_name = None
        if district_id:
            from game.districts import get_district_by_id
            district = get_district_by_id(district_id)
            district_name = district['name'] if district else None

        # Deduct resource
        update_player_resources(user.id, 'information', -1)

        # Use action
        use_action(user.id, False)  # False means it's a quick action

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
            parse_mode=ParseMode.MARKDOWN
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
        from game.politicians import get_politician_by_id
        politician = get_politician_by_id(politician_id)
        politician_name = politician['name'] if politician else str(politician_id)

        # Deduct resources
        update_player_resources(user.id, 'information', -2)

        # Use action
        use_action(user.id, True)  # True means it's a main action

        # Record the action (actual effect processed at cycle end)
        resources_used = {"information": 2}
        add_action(user.id, "undermine", "politician", str(politician_id), resources_used)

        await query.edit_message_text(
            get_text("politician_undermine_success", lang, name=politician_name)
        )

    except Exception as e:
        logger.error(f"Error processing politician undermine: {e}")
        await query.edit_message_text(get_text("action_error", lang))


def register_callbacks(application):
    """Register all callback handlers with the application."""
    # Language and profile callbacks
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^language:"))
    application.add_handler(CallbackQueryHandler(set_name_callback, pattern="^set_name:"))
    
    # Action callbacks
    application.add_handler(CallbackQueryHandler(action_callback, pattern="^action_type:"))
    application.add_handler(CallbackQueryHandler(action_target_callback, pattern="^target:"))
    application.add_handler(CallbackQueryHandler(submit_action_callback, pattern="^submit:"))
    application.add_handler(CallbackQueryHandler(cancel_action_callback, pattern="^action_cancel$"))
    
    # Join action callbacks
    application.add_handler(CallbackQueryHandler(join_action_callback, pattern="^join_action:"))
    application.add_handler(CallbackQueryHandler(join_resource_callback, pattern="^join_resource:"))
    application.add_handler(CallbackQueryHandler(join_submit_callback, pattern="^join_submit$"))
    
    # Exchange callbacks
    application.add_handler(CallbackQueryHandler(exchange_callback, pattern="^exchange:"))
    application.add_handler(CallbackQueryHandler(exchange_again_callback, pattern="^exchange_again$"))
    application.add_handler(CallbackQueryHandler(resource_callback, pattern="^resource:"))
    application.add_handler(CallbackQueryHandler(confirm_action_callback, pattern="^confirm:"))
    
    # Quick action callbacks
    application.add_handler(CallbackQueryHandler(quick_action_type_callback, pattern="^quick_action_type:"))
    application.add_handler(CallbackQueryHandler(quick_district_selection_callback, pattern="^quick_district:"))
    
    # Politician callbacks
    application.add_handler(CallbackQueryHandler(pol_influence_callback, pattern="^pol_influence:"))
    application.add_handler(CallbackQueryHandler(pol_info_callback, pattern="^pol_info:"))
    application.add_handler(CallbackQueryHandler(pol_undermine_callback, pattern="^pol_undermine:"))
    
    # View callbacks
    application.add_handler(CallbackQueryHandler(view_district_callback, pattern="^view_district:"))
    application.add_handler(CallbackQueryHandler(view_politician_callback, pattern="^view_politician:"))
    
    # Action handlers
    application.add_handler(CallbackQueryHandler(handle_district_action, pattern="^district_action:"))
    application.add_handler(CallbackQueryHandler(handle_politician_action, pattern="^politician_action:"))
    
    # Menu callbacks
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu:"))
    application.add_handler(CallbackQueryHandler(back_to_main_menu_callback, pattern="^back_to_main_menu$"))
    
    # Presence callbacks
    application.add_handler(CallbackQueryHandler(refresh_presence_callback, pattern="^refresh_presence$"))
    application.add_handler(CallbackQueryHandler(check_presence_callback, pattern="^check_presence$"))
    
    # Other callbacks
    application.add_handler(CallbackQueryHandler(district_action_callback, pattern=r'^district_action:'))
    
    return application


async def select_action_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action type selection."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    action_type = query.data.split(":")[1]

    # Add option to create a coordinated action for attack and defense
    if action_type in [ACTION_ATTACK, ACTION_DEFENSE]:
        keyboard = [
            [InlineKeyboardButton(get_text("action_regular", lang), callback_data=f"action_regular:{action_type}")],
            [InlineKeyboardButton(get_text("action_coordinated", lang), callback_data=f"action_coordinated:{action_type}")],
            [InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("select_action_mode", lang, action_type=get_action_name(action_type, lang)),
            reply_markup=reply_markup
        )
        return
    
    # For influence, proceed as normal
    message_text = get_text("select_district", lang)
    await show_district_selection(query, message_text)


async def action_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of 'Join' action type."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    # Store the fact that the user chose the "Join" action
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    if user.id not in context.user_data:
        context.user_data[user.id] = {}

    context.user_data[user.id]['action_type'] = "join"

    # Show the list of available coordinated actions to join
    # Get all open coordinated actions
    open_actions = get_open_coordinated_actions()

    if not open_actions:
        await query.edit_message_text(get_text("no_coordinated_actions", lang))
        return

    # Create buttons for each coordinated action
    keyboard = []

    for action in open_actions:
        action_id = action[0]
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

        button_text = f"{action_type} - {target_name} (ID: {action_id})"
        callback_data = f"join_action:{action_id}:{action_type_raw}:{target_type}:{target_id}"

        # Limit the callback_data to avoid error (Telegram has 64-byte limit)
        if len(callback_data) > 60:
            callback_data = f"join_action:{action_id}"

        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # Add cancel button
    keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        get_text("coordinated_actions_title", lang),
        reply_markup=reply_markup
    )




async def submit_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action submission with selected resources."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    # Parse callback data
    parts = query.data.split(":")
    action_type = parts[1]
    target_type = parts[2]
    target_id = parts[3]
    
    # Check if this is a coordinated action
    is_coordinated = False
    if len(parts) > 4:
        is_coordinated = parts[4].lower() == "true"
    elif hasattr(context, 'user_data') and user.id in context.user_data:
        user_data = context.user_data[user.id]
        if user_data.get('action_mode') == 'action_coordinated':
            is_coordinated = True

    # Get selected resources
    selected_resources = []
    if hasattr(context, 'user_data') and user.id in context.user_data:
        if 'selected_resources' in context.user_data[user.id]:
            selected_resources = context.user_data[user.id]['selected_resources']

    # Make sure we have at least one resource
    if not selected_resources:
        await query.edit_message_text(
            get_text("no_resources_selected", lang)
        )
        return

    # Process the action
    await process_main_action(query, action_type, target_type, target_id, selected_resources, is_coordinated)


async def handle_action_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of regular or coordinated action mode."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    parts = query.data.split(":")
    mode = parts[0]
    action_type = parts[1]
    
    # Store the mode and action type in context
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    
    context.user_data[user.id] = {
        'action_mode': mode,
        'action_type': action_type
    }
    
    # Proceed to district selection
    message_text = get_text("select_district", lang)
    await show_district_selection(query, message_text)


async def district_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle district selection."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    district_id = query.data.split(":")[1]
    
    # Check if this is part of a coordinated action
    is_coordinated = False
    action_type = ACTION_ATTACK  # Default
    
    if hasattr(context, 'user_data') and user.id in context.user_data:
        user_data = context.user_data[user.id]
        if user_data.get('action_mode') == 'action_coordinated':
            is_coordinated = True
        action_type = user_data.get('action_type', ACTION_ATTACK)
    
    # Prepare resource selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("Influence", callback_data=f"resource:influence:{action_type}:district:{district_id}"),
            InlineKeyboardButton("Resources", callback_data=f"resource:resources:{action_type}:district:{district_id}")
        ],
        [
            InlineKeyboardButton("Information", callback_data=f"resource:information:{action_type}:district:{district_id}"),
            InlineKeyboardButton("Force", callback_data=f"resource:force:{action_type}:district:{district_id}")
        ],
        [
            InlineKeyboardButton(get_text("action_submit", lang), callback_data=f"submit:{action_type}:district:{district_id}:{is_coordinated}")
        ],
        [
            InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Show resource selection
    from game.districts import get_district_by_id
    district = get_district_by_id(district_id)
    district_name = district['name'] if district else district_id

    # Store selected resources in context
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    
    if user.id not in context.user_data:
        context.user_data[user.id] = {}
    
    context.user_data[user.id]['selected_resources'] = []
    
    await query.edit_message_text(
        get_text("select_resources", lang, 
                 action_type=get_action_name(action_type, lang),
                 district_name=district_name),
        reply_markup=reply_markup
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data.split(':')
    selected_lang = callback_data[1]
    
    # Update player's language preference
    set_player_language(user_id, selected_lang)
    
    # Check if player needs to set their name
    player = get_player(user_id)
    if player and not player['character_name']:
        await query.message.edit_text(
            get_text("enter_character_name", selected_lang, default="Enter your character name:"),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        # Parse the callback data
        callback_data = query.data.split(':')
        if len(callback_data) != 2:
            # Default to current language for error message
            current_lang = get_player_language(user_id)
            logger.warning(f"Invalid language callback data: {query.data}")
            await query.message.reply_text(get_text("error_occurred", current_lang))
            return
        
        lang_code = callback_data[1]
        
        # Check if language is supported
        supported_languages = {"en": "English 🇺🇸", "ru": "Русский 🇷🇺"}
        if lang_code not in supported_languages:
            current_lang = get_player_language(user_id)
            await query.message.edit_text(
                get_text("language_not_supported", current_lang, default="Sorry, this language is not supported yet."),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(get_text("back_button", current_lang, default="Back"), 
                                        callback_data="back_to_main_menu")]
                ])
            )
            return
        
        # Set the player's language
        set_player_language(user_id, lang_code)
        
        # Get player info
        player = get_player(user_id)
        
        # If the player is new and doesn't have a name yet, prompt to set name
        if player and not player['name']:
            # Display name selection options
            keyboard = []
            
            # Common names based on selected language
            if lang_code == "en":
                common_names = ["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey"]
            elif lang_code == "ru":
                common_names = ["Алексей", "Михаил", "Иван", "Анна", "Елена", "Мария"]
            else:
                common_names = ["Alex", "Sam", "Jordan", "Taylor", "Morgan", "Casey"]
            
            # Create rows of 2 names
            row = []
            for i, name in enumerate(common_names):
                row.append(InlineKeyboardButton(name, callback_data=f"set_name:name_{name}"))
                if (i + 1) % 2 == 0:
                    keyboard.append(row)
                    row = []
            
            # Add any remaining names
            if row:
                keyboard.append(row)
            
            # Add custom name option and back button
            keyboard.append([InlineKeyboardButton(
                get_text("custom_name", lang_code, default="Enter Custom Name"), 
                callback_data="set_name:start"
            )])
            
            await query.message.edit_text(
                get_text("language_set_select_name", lang_code, 
                        default="Language set! Please select or enter your character name:"),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        else:
            # Show confirmation and return to main menu
            await query.message.edit_text(
                get_text("language_set", lang_code, 
                        language=supported_languages[lang_code]),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        get_text("back_to_main_menu", lang_code, default="Back to Main Menu"), 
                        callback_data="back_to_main_menu"
                    )]
                ])
            )
        
    except Exception as e:
        logger.error(f"Error in language_callback: {e}", exc_info=True)
        # Try to use English as fallback for the error message
        await query.message.reply_text(
            get_text("error_occurred", "en", default="An error occurred. Please try again.")
        )


async def resource_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle resource selection for actions."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    # Parse callback data
    parts = query.data.split(":")
    resource_type = parts[1]
    action_type = parts[2]
    target_type = parts[3]
    target_id = parts[4]
    
    # Initialize user data if not present
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    
    if user.id not in context.user_data:
        context.user_data[user.id] = {}
    
    if 'selected_resources' not in context.user_data[user.id]:
        context.user_data[user.id]['selected_resources'] = []
    
    # Add the selected resource
    context.user_data[user.id]['selected_resources'].append(resource_type)
    
    # Limit to max 2 resources
    if len(context.user_data[user.id]['selected_resources']) > 2:
        context.user_data[user.id]['selected_resources'] = context.user_data[user.id]['selected_resources'][-2:]
    
    # Get resources count
    resource_counts = {}
    for res in context.user_data[user.id]['selected_resources']:
        if res in resource_counts:
            resource_counts[res] += 1
        else:
            resource_counts[res] = 1
    
    # Format selected resources for display
    selected_text = []
    for res_type, count in resource_counts.items():
        selected_text.append(f"{count} {get_resource_name(res_type, lang)}")
    
    selected_resources_text = ", ".join(selected_text)
    
    # Check if player has the resources
    player_resources = get_player_resources(user.id)
    can_submit = True
    
    for res_type, count in resource_counts.items():
        if player_resources.get(res_type, 0) < count:
            can_submit = False
            break
    
    # Prepare resource selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("Influence", callback_data=f"resource:influence:{action_type}:{target_type}:{target_id}"),
            InlineKeyboardButton("Resources", callback_data=f"resource:resources:{action_type}:{target_type}:{target_id}")
        ],
        [
            InlineKeyboardButton("Information", callback_data=f"resource:information:{action_type}:{target_type}:{target_id}"),
            InlineKeyboardButton("Force", callback_data=f"resource:force:{action_type}:{target_type}:{target_id}")
        ]
    ]
    
    # Add submit button if resources are selected and player has them
    if context.user_data[user.id]['selected_resources'] and can_submit:
        keyboard.append([
            InlineKeyboardButton(
                get_text("action_submit", lang), 
                callback_data=f"submit:{action_type}:{target_type}:{target_id}"
            )
        ])
    
    # Add cancel button
    keyboard.append([
        InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get target name
    target_name = target_id
    if target_type == "district":
        from game.districts import get_district_by_id
        district = get_district_by_id(target_id)
        target_name = district['name'] if district else target_id
    
    # Update message with selected resources
    message_text = get_text("select_resources", lang, 
                           action_type=get_action_name(action_type, lang),
                           district_name=target_name)
    
    if selected_resources_text:
        message_text += f"\n\n{get_text('selected', lang, default='Selected')}: {selected_resources_text}"
    
    await query.edit_message_text(
        text=message_text,
        reply_markup=reply_markup
    )


async def cancel_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle action cancellation."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()
    
    # Clear any stored action data
    if hasattr(context, 'user_data') and user.id in context.user_data:
        context.user_data[user.id] = {}
    
    await query.edit_message_text(get_text("operation_cancelled", lang))


async def quick_action_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quick action type selection."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    action_type = query.data.split(":")[1]

    # Initialize user data if not present
    if not hasattr(context, 'user_data'):
        context.user_data = {}

    if user.id not in context.user_data:
        context.user_data[user.id] = {}

    context.user_data[user.id]['quick_action_type'] = action_type

    # Different targets based on quick action type
    if action_type in [QUICK_ACTION_RECON, QUICK_ACTION_SUPPORT]:
        message_text = get_text("select_district", lang)
        await show_district_selection(query, message_text)
    elif action_type == QUICK_ACTION_INFO:
        # Enter conversation state for text input
        from telegram.ext import ConversationHandler
        context.user_data[user.id]['conversation_state'] = "WAITING_INFO_CONTENT"
        await query.edit_message_text(
            get_text("enter_info_content", lang)
        )
        return ConversationHandler.END  # Exit the callback to enter the conversation


async def quick_district_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle district selection for quick actions."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    district_id = query.data.split(":")[1]
    
    # Check if we have a quick action type stored
    action_type = None
    if hasattr(context, 'user_data') and user.id in context.user_data:
        action_type = context.user_data[user.id].get('quick_action_type')
    
    if not action_type:
        await query.edit_message_text(get_text("action_error", lang))
        return
    
    # Process the quick action
    await process_quick_action(query, action_type, "district", district_id)


async def pol_influence_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle politician influence action."""
    query = update.callback_query
    await query.answer()
    
    politician_id = int(query.data.split(":")[1])
    await process_politician_influence(query, politician_id)


async def pol_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle politician info action."""
    query = update.callback_query
    await query.answer()
    
    politician_id = int(query.data.split(":")[1])
    await process_politician_info(query, politician_id)


async def pol_undermine_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle politician undermine action."""
    query = update.callback_query
    await query.answer()
    
    politician_id = int(query.data.split(":")[1])
    await process_politician_undermine(query, politician_id)


async def view_district_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle viewing district details."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_player_language(user_id)
    
    try:
        # Parse the callback data
        callback_data = query.data.split(':')
        if len(callback_data) != 2:
            logger.warning(f"Invalid view_district callback data: {query.data}")
            await query.message.reply_text(get_text("error_occurred", lang))
            return
        
        district_id = callback_data[1]  # Don't convert to int, district_id is a string
        
        # Get district info
        district = get_district_by_id(district_id)
        if not district:
            await query.message.edit_text(get_text("district_not_found", lang))
            return
        
        district_name = district['name']
        
        # Format district info
        district_info = format_district_info(district_id, lang)
        if not district_info:
            await query.message.edit_text(get_text("error_retrieving_district", lang, default="Error retrieving district information."))
            return
        
        # Build action buttons for this district
        keyboard = [
            [
                InlineKeyboardButton(get_text("attack_button", lang), 
                                   callback_data=f"district_action:attack_{district_id}"),
                InlineKeyboardButton(get_text("defense_button", lang), 
                                   callback_data=f"district_action:defense_{district_id}")
            ],
            [
                InlineKeyboardButton(get_text("recon_button", lang, default="👁️ Reconnaissance"), 
                                   callback_data=f"district_action:recon_{district_id}"),
                InlineKeyboardButton(get_text("info_button", lang, default="ℹ️ Information"), 
                                   callback_data=f"district_action:info_{district_id}")
            ],
            [
                InlineKeyboardButton(get_text("back_to_districts", lang, default="Back to Districts"), 
                                   callback_data="main_menu:districts"),
                InlineKeyboardButton(get_text("back_to_main", lang, default="Main Menu"), 
                                   callback_data="back_to_main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Show district info with action buttons
        await query.message.edit_text(
            text=district_info,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in view_district_callback: {e}", exc_info=True)
        await query.message.reply_text(get_text("error_occurred", lang))


async def view_politician_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle viewing politician details."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_player_language(user_id)
    
    try:
        # Parse the callback data
        callback_data = query.data.split(':')
        if len(callback_data) != 2:
            logger.warning(f"Invalid view_politician callback data: {query.data}")
            await query.message.reply_text(get_text("error_occurred", lang))
            return
        
        politician_name = callback_data[1]
        
        # Get politician info
        politician = get_politician_by_name(politician_name)
        if not politician:
            await query.message.edit_text(get_text("politician_not_found", lang))
            return
        
        # Format politician info
        politician_info = format_politician_info(politician_name, lang)
        if not politician_info:
            await query.message.edit_text(get_text("error_retrieving_politician", lang, default="Error retrieving politician information."))
            return
        
        # Build action buttons for this politician
        keyboard = [
            [
                InlineKeyboardButton(get_text("influence_button", lang, default="🗣️ Influence"), 
                                   callback_data=f"pol_influence:{politician_name}"),
                InlineKeyboardButton(get_text("info_gathering_button", lang, default="🔍 Gather Intel"), 
                                   callback_data=f"pol_info:{politician_name}")
            ],
            [
                InlineKeyboardButton(get_text("undermine_button", lang, default="💥 Undermine"), 
                                   callback_data=f"pol_undermine:{politician_name}")
            ],
            [
                InlineKeyboardButton(get_text("back_to_politicians", lang, default="Back to Politicians"), 
                                   callback_data="main_menu:politicians"),
                InlineKeyboardButton(get_text("back_to_main", lang, default="Main Menu"), 
                                   callback_data="back_to_main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Show politician info with action buttons
        await query.message.edit_text(
            text=politician_info,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error in view_politician_callback: {e}", exc_info=True)
        await query.message.reply_text(get_text("error_occurred", lang))


# In bot/callbacks.py - Add these functions

async def join_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle joining a coordinated action after selecting from the list."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    # Parse callback data (format: join_action:action_id:action_type:target_type:target_id)
    parts = query.data.split(":")
    
    # Handle both formats for backward compatibility
    if len(parts) < 2:
        await query.edit_message_text(get_text("action_error", lang))
        return
    
    action_id = int(parts[1])
    
    # If we have the full data in the callback
    if len(parts) >= 5:
        action_type = parts[2]
        target_type = parts[3]
        target_id = parts[4]
        
        # Convert target_id to int if it's a number
        try:
            target_id = int(target_id)
        except ValueError:
            pass
    else:
        # Otherwise, get action details from the database
        action_details = get_coordinated_action_details(action_id)
        
        if not action_details:
            await query.edit_message_text(get_text("action_not_found", lang))
            return
        
        action_type = action_details['action_type']
        target_type = action_details['target_type']
        target_id = action_details['target_id']

    # Get target name
    if target_type == "district":
        from game.districts import get_district_by_id
        target_info = get_district_by_id(target_id)
        target_name = target_info['name'] if target_info else str(target_id)
    elif target_type == "politician":
        from game.politicians import get_politician_by_id
        target_info = get_politician_by_id(target_id)
        target_name = target_info['name'] if target_info else str(target_id)
    else:
        target_name = str(target_id)

    # Check if the player has actions left
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        keyboard = [
            [InlineKeyboardButton(get_text("back_to_menu", lang, default="Back to Menu"), callback_data="main_menu:back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("no_main_actions", lang),
            reply_markup=reply_markup
        )
        return

    # Check if the player is already participating
    if is_player_in_action(user.id, action_id):
        keyboard = [
            [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), callback_data="main_menu:join")],
            [InlineKeyboardButton(get_text("back_to_menu", lang, default="Back to Menu"), callback_data="main_menu:back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_text("already_participating", lang, default="You are already participating in this action."),
            reply_markup=reply_markup
        )
        return

    # Store the action ID and target info for later use
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    if user.id not in context.user_data:
        context.user_data[user.id] = {}
    
    context.user_data[user.id]['joining_action_id'] = action_id
    context.user_data[user.id]['joining_action_type'] = action_type
    context.user_data[user.id]['joining_target_type'] = target_type
    context.user_data[user.id]['joining_target_id'] = target_id
    context.user_data[user.id]['joining_target_name'] = target_name
    
    # Get player resources for UI display
    player_resources = get_player_resources(user.id)
    
    # Create keyboard for resource selection
    keyboard = []
    
    # First row: 1 of each resource
    row1 = []
    for resource_type in ["influence", "surveillance", "force", "wealth"]:
        amount = 1
        if player_resources.get(resource_type, 0) >= amount:
            button_text = f"{amount} {get_resource_name(resource_type, lang)}"
            callback_data = f"join_resource:{action_id}:{resource_type}:{amount}"
            row1.append(InlineKeyboardButton(button_text, callback_data=callback_data))
    
    # If row has buttons, add it to keyboard
    if row1:
        keyboard.append(row1[:2])  # Split into two rows if needed
        if len(row1) > 2:
            keyboard.append(row1[2:])
    
    # Second row: 2 of key resources
    row2 = []
    for resource_type in ["influence", "force"]:
        amount = 2
        if player_resources.get(resource_type, 0) >= amount:
            button_text = f"{amount} {get_resource_name(resource_type, lang)}"
            callback_data = f"join_resource:{action_id}:{resource_type}:{amount}"
            row2.append(InlineKeyboardButton(button_text, callback_data=callback_data))
    
    # If row has buttons, add it to keyboard
    if row2:
        keyboard.append(row2)
    
    # Add back button
    keyboard.append([
        InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), callback_data="main_menu:join"),
        InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Display the resource selection UI
    await query.edit_message_text(
        get_text("select_resources_join", lang,
                 action_type=get_action_name(action_type, lang),
                 target_name=target_name,
                 default=f"Select resources to use for joining {action_type} action on {target_name}:"),
        reply_markup=reply_markup
    )


async def show_join_resource_selection(query, action_type, target_name, lang):
    """Show resource selection buttons for joining an action."""
    # Prepare resource selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("Influence", callback_data=f"join_resource:influence"),
            InlineKeyboardButton("Resources", callback_data=f"join_resource:resources")
        ],
        [
            InlineKeyboardButton("Information", callback_data=f"join_resource:information"),
            InlineKeyboardButton("Force", callback_data=f"join_resource:force")
        ],
        [
            InlineKeyboardButton(get_text("action_submit", lang), callback_data=f"join_submit")
        ],
        [
            InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = get_text("select_resources_join", lang,
                            action_type=get_action_name(action_type, lang),
                            target_name=target_name,
                            default=f"Select resources to use for joining {action_type} action on {target_name}:")

    await query.edit_message_text(
        text=message_text,
        reply_markup=reply_markup
    )




async def join_submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle submission of joining a coordinated action."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    # Get user data
    if not hasattr(context, 'user_data') or user.id not in context.user_data:
        await query.edit_message_text(get_text("action_error", lang))
        return
    
    user_data = context.user_data[user.id]
    
    # Check required data exists
    if 'joining_action_id' not in user_data or 'selected_resources' not in user_data or not user_data.get('selected_resources'):
        await query.edit_message_text(
            get_text("must_select_resource", lang, 
                    default="You need to select at least one resource to join this action."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), 
                                      callback_data="main_menu:join")]
            ])
        )
        return
    
    action_id = user_data['joining_action_id']
    action_type = user_data['joining_action_type']
    target_name = user_data['joining_target_name']
    selected_resources = user_data.get('selected_resources', {})
    
    # Convert resources for DB storage
    resources_dict = {}
    resources_display = []
    for resource_type, amount in selected_resources.items():
        resources_dict[resource_type] = amount
        resource_name = get_resource_name(resource_type, lang)
        resources_display.append(f"{amount} {resource_name}")
    
    # Verify at least one resource is selected
    if not resources_dict:
        await query.edit_message_text(
            get_text("must_select_resource", lang, 
                    default="You need to select at least one resource to join this action."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), 
                                      callback_data="main_menu:join")]
            ])
        )
        return
    
    # Check if player has the required resources
    player_resources = get_player_resources(user.id)
    
    insufficient_resources = []
    for resource_type, amount in resources_dict.items():
        if player_resources.get(resource_type, 0) < amount:
            resource_name = get_resource_name(resource_type, lang)
            insufficient_resources.append(f"{resource_name} ({player_resources.get(resource_type, 0)}/{amount})")
    
    if insufficient_resources:
        await query.edit_message_text(
            get_text("insufficient_resources_detail", lang, 
                    resources=", ".join(insufficient_resources),
                    default=f"You don't have enough resources: {', '.join(insufficient_resources)}"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), 
                                     callback_data="main_menu:join")]
            ])
        )
        return
    
    # Check if player still has actions left
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        await query.edit_message_text(
            get_text("no_main_actions", lang),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("back_to_menu", lang, default="Back to Menu"), 
                                     callback_data="main_menu:back")]
            ])
        )
        return
    
    # Check if the coordinated action still exists
    conn = sqlite3.connect('novi_sad_game.db')
    action_details = get_coordinated_action_details(conn, action_id)
    conn.close()
    
    if not action_details:
        await query.edit_message_text(
            get_text("action_no_longer_exists", lang, 
                    default="This coordinated action no longer exists."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), 
                                     callback_data="main_menu:join")]
            ])
        )
        return
    
    # Check if player is already participating in this action
    if is_player_in_action(user.id, action_id):
        await query.edit_message_text(
            get_text("already_participating", lang,
                    default="You are already participating in this action."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), 
                                     callback_data="main_menu:join")]
            ])
        )
        return
    
    # Join the action
    from game.actions import process_join_with_resources
    success, message = await process_join_with_resources(user.id, action_id, resources_dict)
    
    if success:
        # Success message with return button
        action_name = get_action_name(action_type, lang)
        
        success_keyboard = [
            [InlineKeyboardButton(get_text("view_actions", lang, default="View All Actions"), 
                                 callback_data="main_menu:join")],
            [InlineKeyboardButton(get_text("back_to_menu", lang, default="Back to Menu"), 
                                 callback_data="main_menu:back")]
        ]
        
        await query.edit_message_text(
            get_text("joined_action_success", lang,
                    action_type=action_name,
                    target_name=target_name,
                    resources=", ".join(resources_display),
                    default=f"Successfully joined {action_name} action on {target_name} using {', '.join(resources_display)}!"),
            reply_markup=InlineKeyboardMarkup(success_keyboard)
        )
        
        # Clear the temporary data
        user_data.pop('selected_resources', None)
        user_data.pop('joining_action_id', None)
        user_data.pop('joining_action_type', None)
        user_data.pop('joining_target_type', None)
        user_data.pop('joining_target_id', None)
        user_data.pop('joining_target_name', None)
    else:
        # Error message with return button
        error_keyboard = [
            [InlineKeyboardButton(get_text("back_to_actions", lang, default="Back to Actions"), 
                                 callback_data="main_menu:join")]
        ]
        
        await query.edit_message_text(
            get_text("join_action_error", lang,
                    error=message,
                    default=f"Failed to join action: {message}"),
            reply_markup=InlineKeyboardMarkup(error_keyboard)
        )


async def back_to_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to the main menu."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)
    
    await query.answer()
    
    # Get player information
    player = get_player(user.id)
    if not player:
        await query.edit_message_text(get_text("not_registered", lang))
        return
    
    resources = get_player_resources(user.id)
    
    # Create main menu
    status_text = (
        f"<b>{get_text('welcome_back', lang, default='Welcome back')} {player[2]}!</b>\n\n"
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
    
    await query.edit_message_text(
        text=status_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def set_name_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting name callback."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)
    
    await query.answer()
    
    # Check if player is registered
    player = get_player(user.id)
    if not player:
        await query.edit_message_text(get_text("not_registered", lang))
        return
    
    # Ask for the new name
    await query.edit_message_text(
        get_text("enter_character_name", lang, default="Please enter your character name:")
    )
    
    # Set conversation state to wait for name input
    return "waiting_for_name"  # This state should be handled in your ConversationHandler