import logging
import json
import sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes, ConversationHandler
from languages import get_text, get_resource_name
from db.queries import (
    get_player_language, set_player_language, get_player_resources,
    use_action, update_player_resources, add_action,
    get_district_info, get_politician_info
)
from game.districts import format_district_info
from game.politicians import format_politician_info

logger = logging.getLogger(__name__)

# Constants for action types
ACTION_INFLUENCE = "influence"
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defense"
QUICK_ACTION_RECON = "recon"
QUICK_ACTION_INFO = "info"
QUICK_ACTION_SUPPORT = "support"

# Waiting for info content state
WAITING_INFO_CONTENT = "WAITING_INFO_CONTENT"


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
            return WAITING_INFO_CONTENT

    # Handle district selection for main actions
    elif callback_data.startswith("district_select:"):
        district_id = callback_data.split(":")[1]

        if 'action_type' in context.user_data:
            # For main action
            action_type = context.user_data['action_type']
            await show_resource_selection(query, action_type, district_id, lang)
        elif 'quick_action_type' in context.user_data:
            # For quick action
            action_type = context.user_data['quick_action_type']
            await process_quick_action(query, action_type, "district", district_id, lang)

    # Direct action buttons from district view
    elif callback_data.startswith(("action_influence:", "action_attack:", "action_defend:")):
        parts = callback_data.split(":")
        action_type = parts[0].replace("action_", "")
        district_id = parts[1]

        context.user_data['action_type'] = action_type
        await show_resource_selection(query, action_type, district_id, lang)

    elif callback_data.startswith(("quick_recon:", "quick_support:")):
        parts = callback_data.split(":")
        action_type = parts[0].replace("quick_", "")
        district_id = parts[1]

        context.user_data['quick_action_type'] = action_type
        await process_quick_action(query, action_type, "district", district_id, lang)

    # Handle resource selection
    elif callback_data.startswith("resources:"):
        parts = callback_data.split(":")
        action_type = parts[1]
        target_type = parts[2]
        target_id = parts[3]
        resources = parts[4].split(",")

        await process_main_action(query, action_type, target_type, target_id, resources, lang)

    # Handle view district
    elif callback_data.startswith("view_district:"):
        district_id = callback_data.split(":")[1]
        await show_district_info(query, district_id, lang)

    # Handle view politician
    elif callback_data.startswith("view_politician:"):
        politician_id = int(callback_data.split(":")[1])
        await show_politician_info(query, politician_id, user.id, lang)

    # Handle politician actions
    elif callback_data.startswith("pol_influence:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_influence(query, politician_id, lang)

    elif callback_data.startswith("pol_info:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_info(query, politician_id, lang)

    elif callback_data.startswith("pol_undermine:"):
        politician_id = int(callback_data.split(":")[1])
        await process_politician_undermine(query, politician_id, lang)

    # Handle cancellation
    elif callback_data == "action_cancel":
        await query.edit_message_text(get_text("operation_cancelled", lang))

    else:
        await query.edit_message_text(f"Unrecognized callback: {callback_data}")


async def show_district_selection(query, message):
    """Show districts for selection."""
    user = query.from_user
    lang = get_player_language(user.id)

    # Get all districts
    try:
        import sqlite3
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT district_id, name FROM districts ORDER BY name")
        districts = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Error getting districts: {e}")
        districts = []

    keyboard = []

    for district_id, name in districts:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"district_select:{district_id}")])

    keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message,
        reply_markup=reply_markup
    )


async def show_resource_selection(query, action_type, district_id, lang):
    """Show resource selection for an action."""
    user = query.from_user
    resources = get_player_resources(user.id)

    district = get_district_info(district_id)
    district_name = district[1] if district else district_id

    # Translate action type
    action_type_name = get_text(f"action_{action_type}", lang, default=action_type)

    message = get_text("select_resources", lang, action_type=action_type_name, district_name=district_name)

    # Create resource selection options based on action type
    keyboard = []

    if action_type == ACTION_INFLUENCE:
        # Influence action typically uses Influence and Resources
        if resources['influence'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('influence', lang)}",
                                                  callback_data=f"resources:{action_type}:district:{district_id}:influence")])
        if resources['resources'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('resources', lang)}",
                                                  callback_data=f"resources:{action_type}:district:{district_id}:resources")])
        if resources['influence'] >= 1 and resources['resources'] >= 1:
            keyboard.append([InlineKeyboardButton(
                f"1 {get_resource_name('influence', lang)} + 1 {get_resource_name('resources', lang)}",
                callback_data=f"resources:{action_type}:district:{district_id}:influence,resources")])

    elif action_type == ACTION_ATTACK:
        # Attack action typically uses Force and Information
        if resources['force'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('force', lang)}",
                                                  callback_data=f"resources:{action_type}:district:{district_id}:force")])
        if resources['information'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('information', lang)}",
                                                  callback_data=f"resources:{action_type}:district:{district_id}:information")])
        if resources['force'] >= 1 and resources['information'] >= 1:
            keyboard.append([InlineKeyboardButton(
                f"1 {get_resource_name('force', lang)} + 1 {get_resource_name('information', lang)}",
                callback_data=f"resources:{action_type}:district:{district_id}:force,information")])

    elif action_type == ACTION_DEFENSE or action_type == "defense" or action_type == "defend":
        # Defense action can use various resources
        if resources['force'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('force', lang)}",
                                                  callback_data=f"resources:defense:district:{district_id}:force")])
        if resources['influence'] >= 1:
            keyboard.append([InlineKeyboardButton(f"1 {get_resource_name('influence', lang)}",
                                                  callback_data=f"resources:defense:district:{district_id}:influence")])
        if resources['force'] >= 1 and resources['influence'] >= 1:
            keyboard.append([InlineKeyboardButton(
                f"1 {get_resource_name('force', lang)} + 1 {get_resource_name('influence', lang)}",
                callback_data=f"resources:defense:district:{district_id}:force,influence")])

    keyboard.append([InlineKeyboardButton(get_text("action_cancel", lang), callback_data="action_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup)


async def process_quick_action(query, action_type, target_type, target_id, lang):
    """Process a quick action."""
    user = query.from_user

    # Check if player has quick actions left
    from db.queries import get_remaining_actions
    actions = get_remaining_actions(user.id)
    if actions['quick'] <= 0:
        await query.edit_message_text(get_text("no_quick_actions", lang))
        return

    # Process based on action type
    if action_type == QUICK_ACTION_RECON:
        # Reconnaissance requires 1 Information
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
        resources_used = {"information": -1}
        add_action(user.id, QUICK_ACTION_RECON, target_type, target_id, resources_used)

        # Get district info for the response
        district = get_district_info(target_id)
        district_name = district[1] if district else target_id

        await query.edit_message_text(
            get_text(
                "action_submitted",
                lang,
                action_type=get_text("action_recon", lang),
                target_name=district_name,
                resources=f"1 {get_resource_name('information', lang)}"
            )
        )

    elif action_type == QUICK_ACTION_SUPPORT:
        # Support requires 1 Influence
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
        resources_used = {"influence": -1}
        add_action(user.id, QUICK_ACTION_SUPPORT, target_type, target_id, resources_used)

        # Get district info for the response
        district = get_district_info(target_id)
        district_name = district[1] if district else target_id

        await query.edit_message_text(
            get_text(
                "action_submitted",
                lang,
                action_type=get_text("action_support", lang),
                target_name=district_name,
                resources=f"1 {get_resource_name('influence', lang)}"
            )
        )

    else:
        await query.edit_message_text(get_text("action_error", lang))


async def process_main_action(query, action_type, target_type, target_id, resource_list, lang):
    """Process a main action with selected resources."""
    user = query.from_user

    # Check if player has main actions left
    from db.queries import get_remaining_actions
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        await query.edit_message_text(get_text("no_main_actions", lang))
        return

    # Parse resources
    resources_used = {}
    player_resources = get_player_resources(user.id)

    for resource in resource_list:
        if resource not in resources_used:
            resources_used[resource] = 0
        resources_used[resource] -= 1

    # Check if player has enough resources
    for resource, amount in resources_used.items():
        if player_resources[resource] < abs(amount):
            await query.edit_message_text(
                get_text("insufficient_resources", lang, resource_type=get_resource_name(resource, lang))
            )
            return

    # Deduct resources
    for resource, amount in resources_used.items():
        update_player_resources(user.id, resource, amount)

    # Use action
    if not use_action(user.id, True):
        await query.edit_message_text(get_text("no_main_actions", lang))
        return

    # Add the action to the database
    add_action(user.id, action_type, target_type, target_id, resources_used)

    # Format resources for display
    resources_display = []
    for resource, amount in resources_used.items():
        resources_display.append(f"{abs(amount)} {get_resource_name(resource, lang)}")

    resources_text = ", ".join(resources_display)

    # Get target name
    target_name = target_id
    if target_type == "district":
        district = get_district_info(target_id)
        if district:
            target_name = district[1]

    # Send confirmation message
    await query.edit_message_text(
        get_text(
            "action_submitted",
            lang,
            action_type=get_text(f"action_{action_type}", lang, default=action_type),
            target_name=target_name,
            resources=resources_text
        )
    )


async def show_district_info(query, district_id, lang):
    """Show detailed information about a district."""
    user = query.from_user

    district_info = format_district_info(district_id, lang)

    if not district_info:
        await query.edit_message_text(get_text("district_not_found", lang, district_name=district_id))
        return

    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton(get_text("action_influence", lang), callback_data=f"action_influence:{district_id}"),
            InlineKeyboardButton(get_text("action_attack", lang), callback_data=f"action_attack:{district_id}")
        ],
        [
            InlineKeyboardButton(get_text("action_defense", lang), callback_data=f"action_defend:{district_id}"),
            InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"quick_recon:{district_id}")
        ],
        [
            InlineKeyboardButton(get_text("action_support", lang), callback_data=f"quick_support:{district_id}")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        district_info,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def show_politician_info(query, politician_id, player_id, lang):
    """Show detailed information about a politician."""
    politician_info = format_politician_info(politician_id, player_id, lang)

    if not politician_info:
        await query.edit_message_text(get_text("politician_not_found", lang, name=str(politician_id)))
        return

    # Add action buttons
    keyboard = [
        [
            InlineKeyboardButton(get_text("action_influence", lang), callback_data=f"pol_influence:{politician_id}"),
            InlineKeyboardButton(get_text("action_recon", lang), callback_data=f"pol_info:{politician_id}")
        ],
        [
            InlineKeyboardButton(get_text("action_info", lang), callback_data=f"pol_undermine:{politician_id}")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        politician_info,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def process_politician_influence(query, politician_id, lang):
    """Process influence action on a politician."""
    user = query.from_user

    # Influencing a politician requires 2 Influence resources
    resources = get_player_resources(user.id)
    if resources['influence'] < 2:
        await query.edit_message_text(get_text("politician_influence_no_resources", lang))
        return

    # Check if player has main actions left
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        await query.edit_message_text(get_text("politician_influence_no_action", lang))
        return

    # Deduct resources
    update_player_resources(user.id, 'influence', -2)

    # Use action
    use_action(user.id, True)

    # Add the action to the database
    resources_used = {"influence": -2}
    add_action(user.id, "influence", "politician", politician_id, resources_used)

    # Get politician name for response
    politician = get_politician_info(politician_id=politician_id)
    name = politician[1] if politician else str(politician_id)

    await query.edit_message_text(get_text("politician_influence_success", lang, name=name))


async def process_politician_info(query, politician_id, lang):
    """Process information gathering on a politician."""
    user = query.from_user

    # Gathering info on a politician requires 1 Information resource
    resources = get_player_resources(user.id)
    if resources['information'] < 1:
        await query.edit_message_text(get_text("politician_info_no_resources", lang))
        return

    # Check if player has quick actions left
    actions = get_remaining_actions(user.id)
    if actions['quick'] <= 0:
        await query.edit_message_text(get_text("politician_info_no_action", lang))
        return

    # Deduct resources
    update_player_resources(user.id, 'information', -1)

    # Use action
    use_action(user.id, False)

    # Get detailed info about the politician
    politician = get_politician_info(politician_id=politician_id)
    if not politician:
        await query.edit_message_text(get_text("politician_not_found", lang, name=str(politician_id)))
        return

    pol_id, name, role, ideology, district_id, influence, friendliness, is_intl, description = politician

    # Create a more detailed intelligence report
    report_text = (
        f"*{get_text('politician_info_title', lang, name=name)}*\n\n"
        f"*{get_text('role', lang, default='Role')}:* {role}\n"
        f"*{get_text('ideology_score', lang, default='Ideology Score')}:* {ideology}\n"
        f"*{get_text('current_influence', lang, default='Current Influence')}:* {influence}\n"
        f"*{get_text('friendliness', lang, default='Friendliness')} ({get_text('general', lang, default='general')}):* {friendliness}%\n"
    )

    if district_id:
        district = get_district_info(district_id)
        district_name = district[1] if district else district_id

        # Get control info for the politician's district
        from db.queries import get_district_control
        control_data = get_district_control(district_id)

        report_text += f"\n*{get_text('home_district', lang, default='Home District')}:* {district_name}\n"

        if control_data:
            report_text += f"*{get_text('current_district_control', lang, default='Current District Control')}:*\n"
            for player_id, control_points, player_name in control_data:
                if control_points > 0:
                    report_text += f"• {player_name}: {control_points} {get_text('points', lang, default='points')}\n"

    report_text += f"\n*{get_text('description', lang, default='Description')}:* {description}\n"

    await query.edit_message_text(report_text, parse_mode='Markdown')


async def process_politician_undermine(query, politician_id, lang):
    """Process undermining a politician's influence."""
    user = query.from_user

    # Undermining a politician requires 2 Information resources
    resources = get_player_resources(user.id)
    if resources['information'] < 2:
        await query.edit_message_text(get_text("politician_undermine_no_resources", lang))
        return

    # Check if player has main actions left
    actions = get_remaining_actions(user.id)
    if actions['main'] <= 0:
        await query.edit_message_text(get_text("politician_undermine_no_action", lang))
        return

    # Deduct resources
    update_player_resources(user.id, 'information', -2)

    # Use action
    use_action(user.id, True)

    # Add the action to the database
    resources_used = {"information": -2}
    add_action(user.id, "undermine", "politician", politician_id, resources_used)

    # Get politician name for response
    politician = get_politician_info(politician_id=politician_id)
    name = politician[1] if politician else str(politician_id)

    await query.edit_message_text(get_text("politician_undermine_success", lang, name=name))


def register_callbacks(application):
    """Register callback handlers."""
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Callback handlers registered")