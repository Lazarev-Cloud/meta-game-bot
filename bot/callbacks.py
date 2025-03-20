import logging
import sqlite3

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ContextTypes
from languages import get_text, get_player_language, set_player_language, get_action_name, get_resource_name
from db.queries import (
    get_player_resources, update_player_resources,
    get_remaining_actions, use_action, add_action,
    update_district_control, create_coordinated_action
)
from game.actions import (
    ACTION_INFLUENCE, ACTION_ATTACK, ACTION_DEFENSE,
    QUICK_ACTION_RECON, QUICK_ACTION_INFO, QUICK_ACTION_SUPPORT
)
from game.districts import format_district_info
from game.politicians import format_politician_info

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


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

        # Determine resource type based on action
        if action_type == QUICK_ACTION_RECON:
            resource_type = "information"
            resource_amount = 1
        elif action_type == QUICK_ACTION_SUPPORT:
            resource_type = "influence"
            resource_amount = 1
        else:
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

        # Use one quick action
        use_action(user.id, False)  # False means it's a quick action

        # Add the action to the database
        if resource_type:
            resources_used = {resource_type: resource_amount}
        else:
            resources_used = {}
            
        add_action(user.id, action_type, target_type, target_id, resources_used)

        # Show confirmation message
        await query.edit_message_text(
            get_text("action_success", lang,
                    type=get_text(f"action_{action_type}", lang),
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

        # Use one main action
        use_action(user.id, True)  # True means it's a main action

        # If it's a coordinated action, create it
        if is_coordinated:
            from db.queries import create_coordinated_action
            action_id = create_coordinated_action(
                user.id, action_type, target_type, target_id, resources_dict
            )
            message = get_text("action_coordinated_created", lang,
                             type=get_text(f"action_{action_type}", lang),
                             target=target_name,
                             id=action_id)
        else:
            # Otherwise, add a regular action
            add_action(user.id, action_type, target_type, target_id, resources_dict)
            message = get_text("action_success", lang,
                             type=get_text(f"action_{action_type}", lang),
                             target=target_name)

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
    """Register callback query handlers."""
    # Language callback
    application.add_handler(CallbackQueryHandler(language_selection_callback, pattern="^language:"))
    
    # Action callbacks
    application.add_handler(CallbackQueryHandler(select_action_type_callback, pattern="^action_type:"))
    application.add_handler(CallbackQueryHandler(handle_action_mode_selection, pattern="^action_(regular|coordinated):"))
    application.add_handler(CallbackQueryHandler(district_selection_callback, pattern="^district_select:"))
    application.add_handler(CallbackQueryHandler(resource_selection_callback, pattern="^resource:"))
    application.add_handler(CallbackQueryHandler(submit_action_callback, pattern="^submit:"))
    application.add_handler(CallbackQueryHandler(cancel_action_callback, pattern="^action_cancel$"))
    
    # District view callbacks
    application.add_handler(CallbackQueryHandler(view_district_callback, pattern="^view_district:"))
    application.add_handler(CallbackQueryHandler(view_politician_callback, pattern="^view_politician:"))
    
    # Direct actions from district view
    application.add_handler(CallbackQueryHandler(district_action_callback, pattern="^action_(influence|attack|defend):"))
    application.add_handler(CallbackQueryHandler(district_action_callback, pattern="^quick_(recon|support):"))
    
    # Quick action callbacks
    application.add_handler(CallbackQueryHandler(quick_action_type_callback, pattern="^quick_action_type:"))
    application.add_handler(CallbackQueryHandler(quick_district_selection_callback, pattern="^quick_district:"))
    
    # Politician callbacks
    application.add_handler(CallbackQueryHandler(pol_influence_callback, pattern="^pol_influence:"))
    application.add_handler(CallbackQueryHandler(pol_info_callback, pattern="^pol_info:"))
    application.add_handler(CallbackQueryHandler(pol_undermine_callback, pattern="^pol_undermine:"))
    
    logger.info("Callback handlers registered")


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


async def language_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    user = query.from_user

    await query.answer()

    # Extract language choice from callback data
    language = query.data.split(":")[1]
    set_player_language(user.id, language)

    # Confirm language change in the selected language
    response_text = get_text("language_changed", language)
    await query.edit_message_text(response_text)


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
        await query.edit_message_text(
            get_text("enter_info_content", lang)
        )
        return


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
    """Handle view district action."""
    query = update.callback_query
    await query.answer()
    
    district_id = query.data.split(":")[1]
    await show_district_info(query, district_id)


async def view_politician_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view politician action."""
    query = update.callback_query
    await query.answer()
    
    politician_id = int(query.data.split(":")[1])
    await show_politician_info(query, politician_id)


async def district_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct actions from district view."""
    query = update.callback_query
    user = query.from_user
    lang = get_player_language(user.id)

    await query.answer()

    parts = query.data.split(":")
    action_id = parts[0]
    district_id = parts[1]
    
    # Initialize user data if needed
    if not hasattr(context, 'user_data'):
        context.user_data = {}
    
    if user.id not in context.user_data:
        context.user_data[user.id] = {}
    
    if action_id.startswith("action_"):
        # Main action (influence, attack, defend)
        action_type = action_id.replace("action_", "")
        context.user_data[user.id]['action_type'] = action_type
        await show_resource_selection(query, action_type, district_id)
    
    elif action_id.startswith("quick_"):
        # Quick action (recon, support)
        action_type = action_id.replace("quick_", "")
        context.user_data[user.id]['quick_action_type'] = action_type
        await process_quick_action(query, action_type, "district", district_id)
    
    else:
        await query.edit_message_text(get_text("action_error", lang))