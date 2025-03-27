# bot/states.py - Improved conversation handling with better error handling

import logging
import functools
from typing import Dict, Any, Optional, Callable, Awaitable, List

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CommandHandler
from telegram.ext import (
    ContextTypes,
)

# Import constants from constants.py for state definitions
from bot.constants import (
    NAME_ENTRY,
    IDEOLOGY_CHOICE,
    ACTION_SELECT_DISTRICT,
    ACTION_SELECT_TARGET,
    ACTION_SELECT_RESOURCE,
    ACTION_SELECT_AMOUNT,
    ACTION_PHYSICAL_PRESENCE,
    ACTION_CONFIRM,
    CONVERT_FROM_RESOURCE,
    CONVERT_TO_RESOURCE,
    CONVERT_AMOUNT,
    CONVERT_CONFIRM,
    COLLECTIVE_ACTION_TYPE,
    COLLECTIVE_ACTION_DISTRICT,
    COLLECTIVE_ACTION_TARGET,
    COLLECTIVE_ACTION_RESOURCE,
    COLLECTIVE_ACTION_AMOUNT,
    COLLECTIVE_ACTION_PHYSICAL,
    COLLECTIVE_ACTION_CONFIRM,
    JOIN_ACTION_RESOURCE,
    JOIN_ACTION_AMOUNT,
    JOIN_ACTION_PHYSICAL,
    JOIN_ACTION_CONFIRM,
)

# Import keyboard factories
from bot.keyboards import (
    get_ideology_keyboard,
    get_districts_keyboard,
    get_resource_type_keyboard,
    get_resource_amount_keyboard,
    get_physical_presence_keyboard,
    get_confirmation_keyboard,
    get_language_keyboard,
    get_collective_action_keyboard,
    get_politicians_keyboard,
    get_start_keyboard,
    get_back_keyboard,
    get_yes_no_keyboard
)

# Import database functionality
from db import (
    register_player,
    player_exists,
    submit_action,
    exchange_resources,
    initiate_collective_action,
    join_collective_action,
    get_player,
    get_active_collective_actions,
    get_collective_action
)

# Import utilities
from utils.context_manager import get_user_data, set_user_data, clear_user_data
from utils.error_handling import conversation_step, db_retry, DatabaseError
from utils.i18n import _, get_user_language, set_user_language
from utils.message_utils import send_message, edit_or_reply

# Initialize logger
logger = logging.getLogger(__name__)


# Registration conversation handlers
@conversation_step
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation to register a new player."""
    user = update.effective_user
    telegram_id = str(user.id)
    language = await get_user_language(telegram_id)

    # Check if player already exists
    try:
        exists = await player_exists(telegram_id)

        if exists:
            # Player exists, welcome them back
            try:
                player_data = await get_player(telegram_id)
                player_name = player_data.get("player_name", user.first_name) if player_data else user.first_name

                welcome_text = _("Welcome back to Novi-Sad, {name}! What would you like to do?", language).format(
                    name=player_name
                )

                await update.message.reply_text(
                    welcome_text,
                    reply_markup=get_start_keyboard(language)
                )
                return ConversationHandler.END


# Helper function for registration checks
async def require_registration(update: Update, language: str) -> bool:
    """Check player registration."""
    telegram_id = str(update.effective_user.id)

    try:
        exists = await player_exists(telegram_id)

        if exists:
            return True

        # User not registered
        message = _("You are not registered yet. Use /start to register.", language)

        if update.callback_query:
            await update.callback_query.answer(_("You need to register first.", language))
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return False
    except Exception as e:
        logger.error(f"Registration check error: {e}")
        # Fall through and allow access if we can't check
        return True


# Create conversation handlers
registration_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        NAME_ENTRY: [
            CallbackQueryHandler(language_callback, pattern=r"^language:"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, name_entry)
        ],
        IDEOLOGY_CHOICE: [
            CallbackQueryHandler(ideology_choice, pattern=r"^ideology:")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_registration),
        MessageHandler(filters.COMMAND, cancel_registration)
    ]
)

action_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(action_select_district, pattern=r"^action:"),
        CallbackQueryHandler(action_select_district, pattern=r"^quick_action:")
    ],
    states={
        ACTION_SELECT_DISTRICT: [
            CallbackQueryHandler(district_selected, pattern=r"^district:")
        ],
        ACTION_SELECT_TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, target_entry)
        ],
        ACTION_SELECT_RESOURCE: [
            CallbackQueryHandler(resource_selected, pattern=r"^resource:")
        ],
        ACTION_SELECT_AMOUNT: [
            CallbackQueryHandler(amount_selected, pattern=r"^amount:")
        ],
        ACTION_PHYSICAL_PRESENCE: [
            CallbackQueryHandler(physical_presence_selected, pattern=r"^physical:")
        ],
        ACTION_CONFIRM: [
            CallbackQueryHandler(action_confirm, pattern=r"^confirm$"),
            CallbackQueryHandler(action_confirm, pattern=r"^cancel_selection$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_registration, pattern=r"^cancel_selection$")
    ]
)

resource_conversion_handler = ConversationHandler(
    entry_points=[
        CommandHandler("convert_resource", resource_conversion_start),
        CallbackQueryHandler(resource_conversion_start, pattern=r"^exchange_resources$")
    ],
    states={
        CONVERT_FROM_RESOURCE: [
            CallbackQueryHandler(convert_from_selected, pattern=r"^resource:")
        ],
        CONVERT_AMOUNT: [
            CallbackQueryHandler(convert_amount_selected, pattern=r"^amount:"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, convert_amount_text_handler)
        ],
        CONVERT_TO_RESOURCE: [
            CallbackQueryHandler(convert_to_selected, pattern=r"^resource:")
        ],
        CONVERT_CONFIRM: [
            CallbackQueryHandler(convert_confirm, pattern=r"^confirm$"),
            CallbackQueryHandler(convert_confirm, pattern=r"^cancel_selection$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_registration, pattern=r"^cancel_selection$")
    ]
)

collective_action_handler = ConversationHandler(
    entry_points=[CommandHandler("collective", collective_action_start)],
    states={
        COLLECTIVE_ACTION_TYPE: [
            CallbackQueryHandler(collective_action_type_selected, pattern=r"^collective:")
        ],
        COLLECTIVE_ACTION_DISTRICT: [
            CallbackQueryHandler(collective_action_district_selected, pattern=r"^district:")
        ],
        COLLECTIVE_ACTION_TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, collective_action_target_entry)
        ],
        COLLECTIVE_ACTION_RESOURCE: [
            CallbackQueryHandler(collective_action_resource_selected, pattern=r"^resource:")
        ],
        COLLECTIVE_ACTION_AMOUNT: [
            CallbackQueryHandler(collective_action_amount_selected, pattern=r"^amount:")
        ],
        COLLECTIVE_ACTION_PHYSICAL: [
            CallbackQueryHandler(collective_action_physical_presence_selected, pattern=r"^physical:")
        ],
        COLLECTIVE_ACTION_CONFIRM: [
            CallbackQueryHandler(collective_action_confirm, pattern=r"^confirm$"),
            CallbackQueryHandler(collective_action_confirm, pattern=r"^cancel_selection$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_registration, pattern=r"^cancel_selection$")
    ]
)

join_action_handler = ConversationHandler(
    entry_points=[
        CommandHandler("join", join_collective_action_start),
        CallbackQueryHandler(join_collective_action_start, pattern=r"^join_collective_action:")
    ],
    states={
        JOIN_ACTION_RESOURCE: [
            CallbackQueryHandler(join_action_resource_selected, pattern=r"^resource:")
        ],
        JOIN_ACTION_AMOUNT: [
            CallbackQueryHandler(join_action_amount_selected, pattern=r"^amount:")
        ],
        JOIN_ACTION_PHYSICAL: [
            CallbackQueryHandler(join_action_physical_presence_selected, pattern=r"^physical:")
        ],
        JOIN_ACTION_CONFIRM: [
            CallbackQueryHandler(join_action_confirm, pattern=r"^confirm$"),
            CallbackQueryHandler(join_action_confirm, pattern=r"^cancel_selection$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_registration, pattern=r"^cancel_selection$")
    ]
)

# Export conversation handlers
conversation_handlers = [
    registration_handler,
    action_handler,
    resource_conversion_handler,
    collective_action_handler,
    join_action_handler
]


@conversation_step
async def join_action_resource_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resource selection for joining collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract resource type
    resource_data = query.data.split(":", 1)
    if len(resource_data) > 1:
        resource_type = resource_data[1]

        # Store resource type in user data
        set_user_data(telegram_id, "join_resource_type", resource_type, context)

        # Prompt for resource amount
        await query.edit_message_text(
            _("How much {resource_type} do you want to contribute to this collective action?", language).format(
                resource_type=_(resource_type, language)
            ),
            reply_markup=get_resource_amount_keyboard(language)
        )

        return JOIN_ACTION_AMOUNT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def join_action_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount selection for joining collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract amount
    amount_data = query.data.split(":", 1)
    if len(amount_data) > 1:
        resource_amount = int(amount_data[1])

        # Store amount in user data
        set_user_data(telegram_id, "join_resource_amount", resource_amount, context)

        # Prompt for physical presence
        await query.edit_message_text(
            _("Will you be physically present for this collective action? Being present gives +10 control points.",
              language),
            reply_markup=get_physical_presence_keyboard(language)
        )

        return JOIN_ACTION_PHYSICAL

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def join_action_physical_presence_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle physical presence selection for joining collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract physical presence choice
    presence_data = query.data.split(":", 1)
    if len(presence_data) > 1:
        physical_presence = presence_data[1] == "yes"

        # Store physical presence in user data
        set_user_data(telegram_id, "join_physical_presence", physical_presence, context)

        # Collect all action details for confirmation
        user_data = get_user_data(telegram_id, context)
        action_id = user_data.get("join_action_id", "unknown")
        action_info = user_data.get("join_action_info", {})
        resource_type = user_data.get("join_resource_type", "unknown")
        resource_amount = user_data.get("join_resource_amount", 0)
        physical = user_data.get("join_physical_presence", False)

        # Get action details for confirmation
        action_type = action_info.get("action_type", "unknown") if action_info else "unknown"
        district_name = "Unknown"
        if action_info and "district_id" in action_info and action_info["district_id"]:
            if isinstance(action_info["district_id"], dict):
                district_name = action_info["district_id"].get("name", "Unknown")

        # Create confirmation message
        confirmation_text = _(
            "Please confirm your participation in this collective action:\n\n"
            "Action ID: {action_id}\n"
            "Action Type: {action_type}\n"
            "District: {district}\n"
            "Your Contribution: {amount} {resource_type}\n"
            "Physical Presence: {physical}",
            language
        ).format(
            action_id=action_id,
            action_type=_(action_type, language),
            district=district_name,
            amount=resource_amount,
            resource_type=_(resource_type, language),
            physical=_("Yes", language) if physical else _("No", language)
        )

        await query.edit_message_text(
            confirmation_text,
            reply_markup=get_confirmation_keyboard(language)
        )

        return JOIN_ACTION_CONFIRM

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@db_retry
@conversation_step
async def join_action_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for joining collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Submit the join request
        user_data = get_user_data(telegram_id, context)

        try:
            result = await join_collective_action(
                telegram_id=telegram_id,
                collective_action_id=user_data.get("join_action_id"),
                resource_type=user_data.get("join_resource_type"),
                resource_amount=user_data.get("join_resource_amount"),
                physical_presence=user_data.get("join_physical_presence", False),
                language=language
            )

            if result and result.get("success"):
                # Success message
                success_message = result.get("message", _("Successfully joined collective action!", language))

                await query.edit_message_text(
                    _(
                        "You have successfully joined the collective action!\n\n"
                        "Your contribution: {amount} {resource_type}\n"
                        "Physical Presence: {physical}\n\n"
                        "The action will be processed at the end of the current cycle.",
                        language
                    ).format(
                        amount=user_data.get("join_resource_amount"),
                        resource_type=_(user_data.get("join_resource_type"), language),
                        physical=_("Yes", language) if user_data.get("join_physical_presence") else _("No", language)
                    ),
                    parse_mode="Markdown"
                )
            else:
                # Error message
                await query.edit_message_text(
                    _("There was an error joining the collective action. Please try again.", language)
                )
        except DatabaseError as e:
            logger.error(f"Database error joining collective action: {str(e)}")
            await query.edit_message_text(
                _("Database connection error. Please try again later.", language)
            )
        except Exception as e:
            logger.error(f"Error joining collective action: {str(e)}")
            await query.edit_message_text(
                _("There was an error processing your request: {error}", language).format(error=str(e))
            )
    else:
        # Canceled
        await query.edit_message_text(
            _("Join request canceled.", language)
        )

    # Clean up context
    clear_user_data(telegram_id, context)

    return ConversationHandler.END


# Join collective action handlers
@conversation_step
async def join_collective_action_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start joining a collective action."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return ConversationHandler.END

    # Check for action ID in arguments
    args = context.args if context else None

    if args and len(args) > 0:
        action_id = args[0]
        set_user_data(telegram_id, "join_action_id", action_id, context)

        try:
            # Check if action exists
            action_info = await get_collective_action(action_id)

            if not action_info:
                await update.message.reply_text(
                    _("Collective action with ID {action_id} not found.", language).format(action_id=action_id)
                )
                return ConversationHandler.END

            if action_info.get("status") != "active":
                await update.message.reply_text(
                    _("This collective action is no longer active.", language)
                )
                return ConversationHandler.END

            # Store action details
            set_user_data(telegram_id, "join_action_info", action_info, context)

            # Display action info and prompt for resource contribution
            action_type = action_info.get("action_type", "unknown")
            district_name = "Unknown"
            if "district_id" in action_info and action_info["district_id"]:
                if isinstance(action_info["district_id"], dict):
                    district_name = action_info["district_id"].get("name", "Unknown")

            await update.message.reply_text(
                _(
                    "You are joining a collective {action_type} in {district}.\n\n"
                    "What resource would you like to contribute?",
                    language
                ).format(
                    action_type=_(action_type, language),
                    district=district_name
                ),
                reply_markup=get_resource_type_keyboard(language)
            )

            return JOIN_ACTION_RESOURCE
        except Exception as e:
            logger.error(f"Error getting collective action info: {str(e)}")
            await update.message.reply_text(
                _("Error retrieving collective action information. Please try again.", language)
            )
            return ConversationHandler.END
    else:
        # No action ID provided, show list of active actions
        try:
            active_actions = await get_active_collective_actions()

            if not active_actions or len(active_actions) == 0:
                await update.message.reply_text(
                    _("There are no active collective actions to join at the moment.", language)
                )
                return ConversationHandler.END

            # Show list of actions to join
            actions_text = _("Active collective actions:\n\n", language)

            for action in active_actions:
                action_id = action.get("collective_action_id", "unknown")
                action_type = action.get("action_type", "unknown")
                district_name = "Unknown"
                if "district_id" in action and action["district_id"]:
                    if isinstance(action["district_id"], dict):
                        district_name = action["district_id"].get("name", "Unknown")

                actions_text += f"ID: {action_id}\n"
                actions_text += _("Type: {type}\n", language).format(type=_(action_type, language))
                actions_text += _("District: {district}\n\n", language).format(district=district_name)

            actions_text += _("To join an action, use the command /join [action_id]", language)

            await update.message.reply_text(actions_text)
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error getting active collective actions: {str(e)}")
            await update.message.reply_text(
                _("Error retrieving active collective actions. Please try again.", language)
            )
            return ConversationHandler.END

            except Exception as e:
            logger.error(f"Error getting player data: {e}")
            # Continue with registration if we can't get player data

    # New player, start registration
    await update.message.reply_text(
        "Welcome to Novi-Sad, a city at the crossroads of Yugoslavia's future! "
        "Please select your preferred language:",
        reply_markup=get_language_keyboard()
    )

    return NAME_ENTRY

except Exception as e:
logger.error(f"Error checking if player exists: {e}")

# Fallback to language selection
await update.message.reply_text(
    "Welcome to Novi-Sad! Let's start by selecting your language:",
    reply_markup=get_language_keyboard()
)

return NAME_ENTRY


@conversation_step
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection for registration."""
    query = update.callback_query
    await query.answer()

    language = query.data.split(":", 1)[1]
    telegram_id = str(update.effective_user.id)

    # Save the language selection
    await set_user_language(telegram_id, language)
    # Also store in context for this session
    set_user_data(telegram_id, "language", language, context)

    # Now prompt for name
    await query.edit_message_text(
        _("Great! Now, tell me your character's name:", language)
    )

    return NAME_ENTRY


@conversation_step
async def name_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name entry during registration."""
    user_input = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Validate name (add any required validation)
    if not user_input or len(user_input.strip()) < 2:
        await update.message.reply_text(
            _("Please enter a valid name (at least 2 characters):", language)
        )
        return NAME_ENTRY

    # Store name in context
    set_user_data(telegram_id, "player_name", user_input, context)

    # Prompt for ideology selection
    await update.message.reply_text(
        _("Welcome, {name}! In this game, your ideological leaning will affect your interactions with politicians and districts.\n\n"
          "Please choose your character's ideological position:", language).format(name=user_input),
        reply_markup=get_ideology_keyboard(language)
    )

    return IDEOLOGY_CHOICE


@conversation_step
async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancellation of registration."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    await update.message.reply_text(
        _("Registration canceled. You can start again with /start when you're ready.", language)
    )

    # Clean up context data
    clear_user_data(telegram_id, context)

    return ConversationHandler.END


@conversation_step
async def ideology_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ideology selection with proper formatting."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    ideology_value = int(query.data.split(":", 1)[1])
    language = await get_user_language(telegram_id)

    # Get player name from context
    user_data = get_user_data(telegram_id, context)
    player_name = user_data.get("player_name", update.effective_user.first_name)

    try:
        # Register player
        result = await register_player(telegram_id, player_name, ideology_value, language)

        # Determine ideology description
        ideology_text = _("Neutral", language) if ideology_value == 0 else \
            _("Conservative", language) if ideology_value > 0 else \
                _("Reformist", language)

        # Format success message properly
        success_message = _(
            "Registration complete! Welcome to Novi-Sad, {name}.\n\n"
            "You have chosen an ideology of {ideology_value} ({ideology_text}).\n\n"
            "You have been granted initial resources to begin your journey. Use "
            "/help to learn about available commands, or /status to see your current situation.",
            language
        ).format(name=player_name, ideology_value=ideology_value, ideology_text=ideology_text)

        await query.edit_message_text(success_message)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await query.edit_message_text(_("Registration error. Please try again later.", language))
        return ConversationHandler.END


# Action conversation handlers
@conversation_step
async def action_select_district(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle district selection for an action."""
    query = update.callback_query
    if query:
        await query.answer()
        telegram_id = str(update.effective_user.id)
        language = await get_user_language(telegram_id)

        # Extract action type
        action_data = query.data.split(":", 1)
        if len(action_data) > 1:
            action_type = action_data[1]
            is_quick = action_data[0] == "quick_action"

            # Store action info in user context
            set_user_data(telegram_id, "action_type", action_type, context)
            set_user_data(telegram_id, "is_quick_action", is_quick, context)

            # Prompt for district selection
            await query.edit_message_text(
                _("Please select a district for your {action_type} action:", language).format(
                    action_type=_(action_type, language)
                ),
                reply_markup=await get_districts_keyboard(language)
            )

            return ACTION_SELECT_DISTRICT

    # If we get here, there was a problem
    return ConversationHandler.END


@conversation_step
async def district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle selected district for an action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract district name
    district_data = query.data.split(":", 1)
    if len(district_data) > 1:
        district_name = district_data[1]

        # Store district in user data
        set_user_data(telegram_id, "district_name", district_name, context)

        # Check if action needs a target
        action_type = get_user_data(telegram_id, context).get("action_type")

        if action_type in ["attack", "politician_reputation_attack", "politician_displacement"]:
            # Needs a target
            await query.edit_message_text(
                _("Please enter the name of your target for this action:", language)
            )
            return ACTION_SELECT_TARGET
        else:
            # No target needed, go to resource selection
            await query.edit_message_text(
                _("Please select a resource type to use for this action:", language),
                reply_markup=get_resource_type_keyboard(language)
            )
            return ACTION_SELECT_RESOURCE

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def target_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target entry for an action."""
    user_input = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Store target in user data
    action_type = get_user_data(telegram_id, context).get("action_type")

    if action_type in ["politician_reputation_attack", "politician_displacement"]:
        # Target is a politician
        set_user_data(telegram_id, "target_politician_name", user_input, context)
    else:
        # Target is a player
        set_user_data(telegram_id, "target_player_name", user_input, context)

    # Prompt for resource selection
    await update.message.reply_text(
        _("Please select a resource type to use for this action:", language),
        reply_markup=get_resource_type_keyboard(language)
    )

    return ACTION_SELECT_RESOURCE


@conversation_step
async def resource_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resource selection for an action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract resource type
    resource_data = query.data.split(":", 1)
    if len(resource_data) > 1:
        resource_type = resource_data[1]

        # Store resource type in user data
        set_user_data(telegram_id, "resource_type", resource_type, context)

        # Prompt for resource amount
        await query.edit_message_text(
            _("How much {resource_type} do you want to use for this action?", language).format(
                resource_type=_(resource_type, language)
            ),
            reply_markup=get_resource_amount_keyboard(language)
        )

        return ACTION_SELECT_AMOUNT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount selection for an action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract amount
    amount_data = query.data.split(":", 1)
    if len(amount_data) > 1:
        resource_amount = int(amount_data[1])

        # Store amount in user data
        set_user_data(telegram_id, "resource_amount", resource_amount, context)

        # Prompt for physical presence
        await query.edit_message_text(
            _("Will you be physically present for this action? Being present gives +20 control points.", language),
            reply_markup=get_physical_presence_keyboard(language)
        )

        return ACTION_PHYSICAL_PRESENCE

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def physical_presence_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle physical presence selection for an action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract physical presence choice
    presence_data = query.data.split(":", 1)
    if len(presence_data) > 1:
        physical_presence = presence_data[1] == "yes"

        # Store physical presence in user data
        set_user_data(telegram_id, "physical_presence", physical_presence, context)

        # Collect all action details for confirmation
        user_data = get_user_data(telegram_id, context)
        action_type = user_data.get("action_type", "unknown")
        is_quick = user_data.get("is_quick_action", False)
        district_name = user_data.get("district_name", "unknown")
        resource_type = user_data.get("resource_type", "unknown")
        resource_amount = user_data.get("resource_amount", 0)
        physical = user_data.get("physical_presence", False)

        target_text = ""
        if "target_player_name" in user_data:
            target_text = _("\nTarget Player: {target}", language).format(target=user_data["target_player_name"])
        elif "target_politician_name" in user_data:
            target_text = _("\nTarget Politician: {target}", language).format(
                target=user_data["target_politician_name"])

        # Create confirmation message
        confirmation_text = _(
            "Please confirm your action:\n\n"
            "Action Type: {action_type}\n"
            "District: {district}\n"
            "Resource: {amount} {resource_type}{target_text}\n"
            "Physical Presence: {physical}",
            language
        ).format(
            action_type=_(action_type, language),
            district=district_name,
            amount=resource_amount,
            resource_type=_(resource_type, language),
            target_text=target_text,
            physical=_("Yes", language) if physical else _("No", language)
        )

        await query.edit_message_text(
            confirmation_text,
            reply_markup=get_confirmation_keyboard(language)
        )

        return ACTION_CONFIRM

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@db_retry
@conversation_step
async def action_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle action confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Submit the action
        user_data = get_user_data(telegram_id, context)

        try:
            result = await submit_action(
                telegram_id=telegram_id,
                action_type=user_data.get("action_type"),
                is_quick_action=user_data.get("is_quick_action", False),
                district_name=user_data.get("district_name"),
                target_player_name=user_data.get("target_player_name"),
                target_politician_name=user_data.get("target_politician_name"),
                resource_type=user_data.get("resource_type"),
                resource_amount=user_data.get("resource_amount"),
                physical_presence=user_data.get("physical_presence", False),
                language=language
            )

            if result and result.get("success"):
                # Success message
                success_message = result.get("message", _("Action submitted successfully!", language))
                title = result.get("title", _("Action Submitted", language))

                await query.edit_message_text(
                    f"*{title}*\n\n{success_message}",
                    parse_mode="Markdown"
                )
            else:
                # Error message
                await query.edit_message_text(
                    _("There was an error submitting your action. Please try again.", language)
                )
        except DatabaseError as e:
            logger.error(f"Database error submitting action: {str(e)}")
            await query.edit_message_text(
                _("Database connection error. Please try again later.", language)
            )
        except Exception as e:
            logger.error(f"Error submitting action: {str(e)}")
            await query.edit_message_text(
                _("There was an error processing your action: {error}", language).format(error=str(e))
            )
    else:
        # Canceled
        await query.edit_message_text(
            _("Action canceled.", language)
        )

    # Clean up context
    clear_user_data(telegram_id, context)

    return ConversationHandler.END


# Resource conversion handlers
@conversation_step
async def resource_conversion_start(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    from_resource: str = None, amount: int = None) -> int:
    """Start resource conversion process."""
    message = None
    query = None

    if update.callback_query:
        query = update.callback_query
        await query.answer()
    else:
        message = update.message

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Initialize user data
    user_data = get_user_data(telegram_id, context)

    # If from_resource is provided (direct command usage)
    if from_resource:
        set_user_data(telegram_id, "from_resource", from_resource, context)

        if amount:
            set_user_data(telegram_id, "convert_amount", amount, context)

            # Skip to selecting destination resource
            if message:
                await message.reply_text(
                    _("What type of resource do you want to convert to?", language),
                    reply_markup=get_resource_type_keyboard(language, exclude_type=from_resource)
                )
            elif query:
                await query.edit_message_text(
                    _("What type of resource do you want to convert to?", language),
                    reply_markup=get_resource_type_keyboard(language, exclude_type=from_resource)
                )

            return CONVERT_TO_RESOURCE
        else:
            # Need to get amount
            if message:
                await message.reply_text(
                    _("How much {resource} do you want to convert?", language).format(
                        resource=_(from_resource, language)
                    ),
                    reply_markup=get_resource_amount_keyboard(language)
                )
            elif query:
                await query.edit_message_text(
                    _("How much {resource} do you want to convert?", language).format(
                        resource=_(from_resource, language)
                    ),
                    reply_markup=get_resource_amount_keyboard(language)
                )

            return CONVERT_AMOUNT
    else:
        # Need to select source resource first
        if message:
            await message.reply_text(
                _("What type of resource do you want to convert from?", language),
                reply_markup=get_resource_type_keyboard(language)
            )
        elif query:
            await query.edit_message_text(
                _("What type of resource do you want to convert from?", language),
                reply_markup=get_resource_type_keyboard(language)
            )

        return CONVERT_FROM_RESOURCE


@conversation_step
async def convert_from_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle source resource selection for conversion."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract resource type
    resource_data = query.data.split(":", 1)
    if len(resource_data) > 1:
        from_resource = resource_data[1]

        # Store in user data
        set_user_data(telegram_id, "from_resource", from_resource, context)

        # Prompt for amount
        await query.edit_message_text(
            _("How much {resource} do you want to convert? Remember that the exchange rate is 2:1.", language).format(
                resource=_(from_resource, language)
            ),
            reply_markup=get_resource_amount_keyboard(language)
        )

        return CONVERT_AMOUNT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def convert_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount selection for conversion."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract amount
    amount_data = query.data.split(":", 1)
    if len(amount_data) > 1:
        convert_amount = int(amount_data[1])

        # Store in user data
        set_user_data(telegram_id, "convert_amount", convert_amount, context)
        from_resource = get_user_data(telegram_id, context).get("from_resource")

        # Prompt for destination resource
        await query.edit_message_text(
            _("What type of resource do you want to convert to?", language),
            reply_markup=get_resource_type_keyboard(language, exclude_type=from_resource)
        )

        return CONVERT_TO_RESOURCE

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def convert_to_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle destination resource selection for conversion."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract resource type
    resource_data = query.data.split(":", 1)
    if len(resource_data) > 1:
        to_resource = resource_data[1]

        # Store in user data
        set_user_data(telegram_id, "to_resource", to_resource, context)

        # Get conversion details
        from_resource = get_user_data(telegram_id, context).get("from_resource")
        convert_amount = get_user_data(telegram_id, context).get("convert_amount")

        # Confirm conversion
        confirmation_text = _(
            "Please confirm resource conversion:\n\n"
            "From: {from_amount} {from_resource}\n"
            "To: {to_amount} {to_resource}\n\n"
            "Exchange rate: 2:1",
            language
        ).format(
            from_amount=convert_amount * 2,
            from_resource=_(from_resource, language),
            to_amount=convert_amount,
            to_resource=_(to_resource, language)
        )

        await query.edit_message_text(
            confirmation_text,
            reply_markup=get_confirmation_keyboard(language)
        )

        return CONVERT_CONFIRM

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def convert_amount_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount entry as text input for resource conversion."""
    user_input = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    try:
        convert_amount = int(user_input)
        if convert_amount <= 0:
            await update.message.reply_text(
                _("Please enter a positive number.", language)
            )
            return CONVERT_AMOUNT

        # Store in user data
        set_user_data(telegram_id, "convert_amount", convert_amount, context)
        from_resource = get_user_data(telegram_id, context).get("from_resource")

        # Prompt for destination resource
        await update.message.reply_text(
            _("What type of resource do you want to convert to?", language),
            reply_markup=get_resource_type_keyboard(language, exclude_type=from_resource)
        )

        return CONVERT_TO_RESOURCE
    except ValueError:
        await update.message.reply_text(
            _("Invalid input. Please enter a number.", language)
        )
        return CONVERT_AMOUNT


@db_retry
@conversation_step
async def convert_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversion confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Execute conversion
        user_data = get_user_data(telegram_id, context)

        try:
            result = await exchange_resources(
                telegram_id=telegram_id,
                from_resource=user_data.get("from_resource"),
                to_resource=user_data.get("to_resource"),
                amount=user_data.get("convert_amount"),
                language=language
            )

            if result and result.get("success"):
                # Success message
                from_resource = result.get("from_resource", {})
                to_resource = result.get("to_resource", {})

                success_text = _(
                    "Resource exchange successful!\n\n"
                    "Converted {from_amount} {from_name} to {to_amount} {to_name}.",
                    language
                ).format(
                    from_amount=from_resource.get("amount"),
                    from_name=from_resource.get("name"),
                    to_amount=to_resource.get("amount"),
                    to_name=to_resource.get("name")
                )

                await query.edit_message_text(success_text)
            else:
                # Error message
                await query.edit_message_text(
                    _("Resource exchange failed. You may not have enough resources.", language)
                )
        except DatabaseError as e:
            logger.error(f"Database error exchanging resources: {str(e)}")
            await query.edit_message_text(
                _("Database connection error. Please try again later.", language)
            )
        except Exception as e:
            logger.error(f"Error exchanging resources: {str(e)}")
            await query.edit_message_text(
                _("There was an error processing your conversion: {error}", language).format(error=str(e))
            )
    else:
        # Canceled
        await query.edit_message_text(
            _("Resource conversion canceled.", language)
        )

    # Clean up context
    clear_user_data(telegram_id, context)

    return ConversationHandler.END


# Collective action handlers
@conversation_step
async def collective_action_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start collective action setup."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return ConversationHandler.END

    # Initialize user data
    await update.message.reply_text(
        _("You're initiating a collective action. What type of action?", language),
        reply_markup=get_collective_action_keyboard(language)
    )

    return COLLECTIVE_ACTION_TYPE


@conversation_step
async def collective_action_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle collective action type selection."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract action type
    action_data = query.data.split(":", 1)
    if len(action_data) > 1:
        action_type = action_data[1]

        # Store in user data
        set_user_data(telegram_id, "collective_action_type", action_type, context)

        # Prompt for district selection
        await query.edit_message_text(
            _("Please select a district for the collective {action_type}:", language).format(
                action_type=_(action_type, language)
            ),
            reply_markup=await get_districts_keyboard(language)
        )

        return COLLECTIVE_ACTION_DISTRICT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def collective_action_district_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle district selection for collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract district name
    district_data = query.data.split(":", 1)
    if len(district_data) > 1:
        district_name = district_data[1]

        # Store district in user data
        set_user_data(telegram_id, "collective_district_name", district_name, context)

        # Check if action needs a target
        action_type = get_user_data(telegram_id, context).get("collective_action_type")

        if action_type == "attack":
            # Needs a target
            await query.edit_message_text(
                _("Please enter the name of your target player for this collective attack:", language)
            )
            return COLLECTIVE_ACTION_TARGET
        else:
            # No target needed, go to resource selection
            await query.edit_message_text(
                _("Please select a resource type to contribute to this collective action:", language),
                reply_markup=get_resource_type_keyboard(language)
            )
            return COLLECTIVE_ACTION_RESOURCE

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def collective_action_target_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target entry for collective action."""
    user_input = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Store target in user data
    set_user_data(telegram_id, "collective_target_player_name", user_input, context)

    # Prompt for resource selection
    await update.message.reply_text(
        _("Please select a resource type to contribute to this collective action:", language),
        reply_markup=get_resource_type_keyboard(language)
    )

    return COLLECTIVE_ACTION_RESOURCE


@conversation_step
async def collective_action_resource_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resource selection for collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract resource type
    resource_data = query.data.split(":", 1)
    if len(resource_data) > 1:
        resource_type = resource_data[1]

        # Store resource type in user data
        set_user_data(telegram_id, "collective_resource_type", resource_type, context)

        # Prompt for resource amount
        await query.edit_message_text(
            _("How much {resource_type} do you want to contribute to this collective action?", language).format(
                resource_type=_(resource_type, language)
            ),
            reply_markup=get_resource_amount_keyboard(language)
        )

        return COLLECTIVE_ACTION_AMOUNT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def collective_action_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount selection for collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract amount
    amount_data = query.data.split(":", 1)
    if len(amount_data) > 1:
        resource_amount = int(amount_data[1])

        # Store amount in user data
        set_user_data(telegram_id, "collective_resource_amount", resource_amount, context)

        # Prompt for physical presence
        await query.edit_message_text(
            _("Will you be physically present for this collective action? Being present gives +20 control points.",
              language),
            reply_markup=get_physical_presence_keyboard(language)
        )

        return COLLECTIVE_ACTION_PHYSICAL

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@conversation_step
async def collective_action_physical_presence_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle physical presence selection for collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract physical presence choice
    presence_data = query.data.split(":", 1)
    if len(presence_data) > 1:
        physical_presence = presence_data[1] == "yes"

        # Store physical presence in user data
        set_user_data(telegram_id, "collective_physical_presence", physical_presence, context)

        # Collect all action details for confirmation
        user_data = get_user_data(telegram_id, context)
        action_type = user_data.get("collective_action_type", "unknown")
        district_name = user_data.get("collective_district_name", "unknown")
        resource_type = user_data.get("collective_resource_type", "unknown")
        resource_amount = user_data.get("collective_resource_amount", 0)
        physical = user_data.get("collective_physical_presence", False)

        target_text = ""
        if "collective_target_player_name" in user_data:
            target_text = _("\nTarget Player: {target}", language).format(
                target=user_data["collective_target_player_name"])

        # Create confirmation message
        confirmation_text = _(
            "Please confirm your collective action:\n\n"
            "Action Type: {action_type}\n"
            "District: {district}{target_text}\n"
            "Your Contribution: {amount} {resource_type}\n"
            "Physical Presence: {physical}",
            language
        ).format(
            action_type=_(action_type, language),
            district=district_name,
            target_text=target_text,
            amount=resource_amount,
            resource_type=_(resource_type, language),
            physical=_("Yes", language) if physical else _("No", language)
        )

        await query.edit_message_text(
            confirmation_text,
            reply_markup=get_confirmation_keyboard(language)
        )

        return COLLECTIVE_ACTION_CONFIRM

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@db_retry
@conversation_step
async def collective_action_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle collective action confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Submit the collective action
        user_data = get_user_data(telegram_id, context)

        try:
            result = await initiate_collective_action(
                telegram_id=telegram_id,
                action_type=user_data.get("collective_action_type"),
                district_name=user_data.get("collective_district_name"),
                target_player_name=user_data.get("collective_target_player_name"),
                resource_type=user_data.get("collective_resource_type"),
                resource_amount=user_data.get("collective_resource_amount"),
                physical_presence=user_data.get("collective_physical_presence", False),
                language=language
            )

            if result and result.get("success"):
                # Success message
                success_message = result.get("message", _("Collective action initiated successfully!", language))
                action_id = result.get("collective_action_id", "unknown")
                join_command = result.get("join_command", f"/join {action_id}")

                await query.edit_message_text(
                    _(
                        "Collective action initiated successfully!\n\n"
                        "Action ID: {action_id}\n\n"
                        "Other players can join using:\n{join_command}\n\n"
                        "The action will be processed at the end of the current cycle.",
                        language
                    ).format(
                        action_id=action_id,
                        join_command=join_command
                    ),
                    parse_mode="Markdown"
                )
            else:
                # Error message
                await query.edit_message_text(
                    _("There was an error initiating your collective action. Please try again.", language)
                )
        except DatabaseError as e:
            logger.error(f"Database error initiating collective action: {str(e)}")
            await query.edit_message_text(
                _("Database connection error. Please try again later.", language)
            )
        except Exception as e:
            logger.error(f"Error initiating collective action: {str(e)}")
            await query.edit_message_text(
                _("There was an error processing your collective action: {error}", language).format(error=str(e))
            )
    else:
        # Canceled
        await query.edit_message_text(
            _("Collective action canceled.", language)
        )

    # Clean up context
    clear_user_data(telegram_id, context)

    return ConversationHandler.END