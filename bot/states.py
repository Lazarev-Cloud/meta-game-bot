#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Conversation states and handlers for the Meta Game bot.
"""

import logging

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from bot.callbacks import join_collective_action_callback
# Import constants instead of defining states here (breaking circular import)
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
from bot.context import get_user_context, clear_user_context
from bot.keyboards import (
    get_ideology_keyboard,
    get_districts_keyboard,
    get_resource_type_keyboard,
    get_resource_amount_keyboard,
    get_physical_presence_keyboard,
    get_confirmation_keyboard,
    get_language_keyboard,
    get_collective_action_keyboard
)
from db import (
    register_player,
    player_exists,
    submit_action,
    exchange_resources,
    initiate_collective_action,
    join_collective_action
)
from db.error_handling import db_retry, DatabaseError
from utils.i18n import _, get_user_language, set_user_language

# Initialize logger
logger = logging.getLogger(__name__)


# Registration conversation handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation to register a new player."""
    user = update.effective_user
    telegram_id = str(user.id)

    # Check if player already exists
    try:
        exists = await player_exists(telegram_id)
    except Exception as e:
        logger.error(f"Error checking if player exists: {e}")
        await update.message.reply_text(
            "Sorry, we're experiencing technical difficulties. Please try again later."
        )
        return ConversationHandler.END

    if exists:
        # Redirect to welcome handler for existing players
        from bot.commands import start_command as welcome_command
        return await welcome_command(update, context)

    # Language selection first
    await update.message.reply_text(
        "Welcome to Novi-Sad, a city at the crossroads of Yugoslavia's future! "
        "Please select your preferred language:\n\n"
        "Добро пожаловать в Нови-Сад, город на перекрестке будущего Югославии! "
        "Пожалуйста, выберите предпочитаемый язык:",
        reply_markup=get_language_keyboard()
    )

    return NAME_ENTRY


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection."""
    query = update.callback_query
    await query.answer()

    language = query.data.split(":", 1)[1]
    telegram_id = str(update.effective_user.id)

    # Store language preference
    # (will be properly saved after registration)
    await set_user_language(telegram_id, language)

    # Continue with name entry
    await query.edit_message_text(
        _("Great! Now, tell me your character's name:", language)
    )

    return NAME_ENTRY


async def name_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name entry."""
    user_input = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Store the name in context
    context.user_data["player_name"] = user_input

    # Prompt for ideology selection
    await update.message.reply_text(
        _("Welcome, {name}! In this game, your ideological leaning will affect your interactions with politicians and districts.\n\n"
          "Please choose your character's ideological position:", language).format(name=user_input),
        reply_markup=get_ideology_keyboard(language)
    )

    return IDEOLOGY_CHOICE


@db_retry
async def ideology_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ideology choice."""
    query = update.callback_query
    await query.answer()

    # Extract ideology value
    ideology_value = int(query.data.split(":", 1)[1])
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Register the new player
    player_name = context.user_data.get("player_name", update.effective_user.first_name)

    try:
        # Call the registration function with proper error handling
        result = await register_player(telegram_id, player_name, ideology_value)

        # Better error handling
        if not result:
            await query.edit_message_text(
                _("Error during registration: Database connection issue", language)
            )
            return ConversationHandler.END

        # Save the language preference permanently
        await set_user_language(telegram_id, language)

        # Welcome message
        ideology_text = _("Strong Reformist", language) if ideology_value == -5 else \
            _("Moderate Reformist", language) if ideology_value == -3 else \
                _("Slight Reformist", language) if ideology_value == -1 else \
                    _("Neutral", language) if ideology_value == 0 else \
                        _("Slight Conservative", language) if ideology_value == 1 else \
                            _("Moderate Conservative", language) if ideology_value == 3 else \
                                _("Strong Conservative", language)

        await query.edit_message_text(
            _("Registration complete! Welcome to Novi-Sad, {name}.\n\n"
              "You have chosen an ideology of {ideology_value} ({ideology_text}).\n\n"
              "You have been granted initial resources to begin your journey. "
              "Use /help to learn about available commands, or /status to see your current situation.",
              language).format(
                name=player_name,
                ideology_value=ideology_value,
                ideology_text=ideology_text
            )
        )

        # Clean up context
        clear_user_context(telegram_id)

        # End the conversation
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error registering player: {str(e)}")
        await query.edit_message_text(
            _("There was an error registering your account. Please try again later or contact support.", language)
        )
        return ConversationHandler.END


# Action conversation handlers

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
            user_data = get_user_context(telegram_id)
            user_data["action_type"] = action_type
            user_data["is_quick_action"] = is_quick

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

        # Store district in user context
        user_data = get_user_context(telegram_id)
        user_data["district_name"] = district_name

        # Check if action needs a target
        action_type = user_data.get("action_type")

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


async def target_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target entry for an action."""
    user_input = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Store target in user context
    user_data = get_user_context(telegram_id)
    action_type = user_data.get("action_type")

    if action_type in ["politician_reputation_attack", "politician_displacement"]:
        # Target is a politician
        user_data["target_politician_name"] = user_input
    else:
        # Target is a player
        user_data["target_player_name"] = user_input

    # Prompt for resource selection
    await update.message.reply_text(
        _("Please select a resource type to use for this action:", language),
        reply_markup=get_resource_type_keyboard(language)
    )

    return ACTION_SELECT_RESOURCE


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

        # Store resource type in user context
        user_data = get_user_context(telegram_id)
        user_data["resource_type"] = resource_type

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

        # Store amount in user context
        user_data = get_user_context(telegram_id)
        user_data["resource_amount"] = resource_amount

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

        # Store physical presence in user context
        user_data = get_user_context(telegram_id)
        user_data["physical_presence"] = physical_presence

        # Collect all action details for confirmation
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
async def action_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle action confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Submit the action
        user_data = get_user_context(telegram_id)

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
    clear_user_context(telegram_id)

    return ConversationHandler.END


# Resource conversion handlers

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

    # Initialize user context
    user_data = get_user_context(telegram_id)

    # If from_resource is provided (direct command usage)
    if from_resource:
        user_data["from_resource"] = from_resource

        if amount:
            user_data["convert_amount"] = amount

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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["from_resource"] = from_resource

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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["convert_amount"] = convert_amount
        from_resource = user_data.get("from_resource")

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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["to_resource"] = to_resource

        # Get conversion details
        from_resource = user_data.get("from_resource")
        convert_amount = user_data.get("convert_amount")

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


@db_retry
async def convert_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversion confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Execute conversion
        user_data = get_user_context(telegram_id)

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
    clear_user_context(telegram_id)

    return ConversationHandler.END


# Collective action handlers

async def collective_action_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start collective action setup."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Initialize user context
    get_user_context(telegram_id)

    # Ask for action type (attack or defense)
    await update.message.reply_text(
        _("You're initiating a collective action. What type of action?", language),
        reply_markup=get_collective_action_keyboard(language)
    )

    return COLLECTIVE_ACTION_TYPE


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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["collective_action_type"] = action_type

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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["collective_district_name"] = district_name

        # For attack, ask for target player
        if user_data.get("collective_action_type") == "attack":
            await query.edit_message_text(
                _("Please enter the name of the target player:", language)
            )
            return COLLECTIVE_ACTION_TARGET
        else:
            # For defense, go straight to resource selection
            await query.edit_message_text(
                _("What resource would you like to contribute to this collective action?", language),
                reply_markup=get_resource_type_keyboard(language)
            )
            return COLLECTIVE_ACTION_RESOURCE

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


async def collective_action_target_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target entry for collective attack."""
    target_name = update.message.text
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Store in user context
    user_data = get_user_context(telegram_id)
    user_data["collective_target_player"] = target_name

    # Prompt for resource selection
    await update.message.reply_text(
        _("What resource would you like to contribute to this collective action?", language),
        reply_markup=get_resource_type_keyboard(language)
    )

    return COLLECTIVE_ACTION_RESOURCE


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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["collective_resource_type"] = resource_type

        # Prompt for amount
        await query.edit_message_text(
            _("How much {resource} do you want to contribute?", language).format(
                resource=_(resource_type, language)
            ),
            reply_markup=get_resource_amount_keyboard(language)
        )

        return COLLECTIVE_ACTION_AMOUNT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


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

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["collective_resource_amount"] = resource_amount

        # Prompt for physical presence
        await query.edit_message_text(
            _("Will you be physically present for this action? Being present gives +10 control points.", language),
            reply_markup=get_physical_presence_keyboard(language)
        )

        return COLLECTIVE_ACTION_PHYSICAL

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


async def collective_action_physical_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle physical presence selection for collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract physical presence choice
    presence_data = query.data.split(":", 1)
    if len(presence_data) > 1:
        physical_presence = presence_data[1] == "yes"

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["collective_physical_presence"] = physical_presence

        # Collect all details for confirmation
        action_type = user_data.get("collective_action_type", "unknown")
        district_name = user_data.get("collective_district_name", "unknown")
        resource_type = user_data.get("collective_resource_type", "unknown")
        resource_amount = user_data.get("collective_resource_amount", 0)
        physical = user_data.get("collective_physical_presence", False)

        target_text = ""
        if "collective_target_player" in user_data:
            target_text = _("\nTarget Player: {target}", language).format(
                target=user_data["collective_target_player"])

        # Create confirmation message
        confirmation_text = _(
            "Please confirm your collective action:\n\n"
            "Action Type: {action_type}\n"
            "District: {district}\n"
            "Resource: {amount} {resource_type}{target_text}\n"
            "Physical Presence: {physical}\n\n"
            "Other players will be able to join this action.",
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

        return COLLECTIVE_ACTION_CONFIRM

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


@db_retry
async def collective_action_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle collective action confirmation."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Submit the collective action
        user_data = get_user_context(telegram_id)

        try:
            result = await initiate_collective_action(
                telegram_id=telegram_id,
                action_type=user_data.get("collective_action_type"),
                district_name=user_data.get("collective_district_name"),
                target_player_name=user_data.get("collective_target_player"),
                resource_type=user_data.get("collective_resource_type"),
                resource_amount=user_data.get("collective_resource_amount"),
                physical_presence=user_data.get("collective_physical_presence", False),
                language=language
            )

            if result and result.get("success"):
                # Success message
                join_command = result.get("join_command", "/join [id]")

                success_text = _(
                    "Collective action initiated successfully!\n\n"
                    "Other players can join using the command:\n{join_command}",
                    language
                ).format(join_command=join_command)

                await query.edit_message_text(success_text)
            else:
                # Error message
                await query.edit_message_text(
                    _("There was an error initiating the collective action. Please try again.", language)
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
    clear_user_context(telegram_id)

    return ConversationHandler.END


# Join collective action handlers

async def join_collective_action_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the process of joining a collective action."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract action ID from command
    action_id = None
    if context.args and len(context.args) > 0:
        action_id = context.args[0]

    # Initialize user context
    user_data = get_user_context(telegram_id)

    if action_id:
        user_data["join_action_id"] = action_id

        # Prompt for resource selection
        await update.message.reply_text(
            _("You are joining collective action {action_id}.\n\nWhat resource would you like to contribute?",
              language).format(
                action_id=action_id
            ),
            reply_markup=get_resource_type_keyboard(language)
        )

        return JOIN_ACTION_RESOURCE
    else:
        await update.message.reply_text(
            _("Please specify a collective action ID to join. Example: /join [action_id]", language)
        )
        return ConversationHandler.END


async def join_action_resource_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resource selection for joining a collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract resource type
    resource_data = query.data.split(":", 1)
    if len(resource_data) > 1:
        resource_type = resource_data[1]

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["join_resource_type"] = resource_type

        # Prompt for amount
        await query.edit_message_text(
            _("How much {resource} do you want to contribute?", language).format(
                resource=_(resource_type, language)
            ),
            reply_markup=get_resource_amount_keyboard(language)
        )

        return JOIN_ACTION_AMOUNT

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


async def join_action_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount selection for joining a collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract amount
    amount_data = query.data.split(":", 1)
    if len(amount_data) > 1:
        resource_amount = int(amount_data[1])

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["join_resource_amount"] = resource_amount

        # Prompt for physical presence
        await query.edit_message_text(
            _("Will you be physically present for this action? Being present gives +10 control points.", language),
            reply_markup=get_physical_presence_keyboard(language)
        )

        return JOIN_ACTION_PHYSICAL

    # If we get here, there was a problem
    await query.edit_message_text(
        _("There was an error processing your selection. Please try again.", language)
    )
    return ConversationHandler.END


async def join_action_physical_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle physical presence selection for joining a collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract physical presence choice
    presence_data = query.data.split(":", 1)
    if len(presence_data) > 1:
        physical_presence = presence_data[1] == "yes"

        # Store in user context
        user_data = get_user_context(telegram_id)
        user_data["join_physical_presence"] = physical_presence

        # Collect all details for confirmation
        action_id = user_data.get("join_action_id", "unknown")
        resource_type = user_data.get("join_resource_type", "unknown")
        resource_amount = user_data.get("join_resource_amount", 0)
        physical = user_data.get("join_physical_presence", False)

        # Create confirmation message
        confirmation_text = _(
            "Please confirm joining collective action:\n\n"
            "Action ID: {action_id}\n"
            "Resource: {amount} {resource_type}\n"
            "Physical Presence: {physical}",
            language
        ).format(
            action_id=action_id,
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
async def join_action_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation for joining a collective action."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if confirmed
    if query.data == "confirm":
        # Join the collective action
        user_data = get_user_context(telegram_id)

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
                success_text = _(
                    "You have successfully joined the collective action!\n\n"
                    "Your contribution: {amount} {resource_type}\n"
                    "Physical Presence: {physical}",
                    language
                ).format(
                    amount=user_data.get("join_resource_amount"),
                    resource_type=_(user_data.get("join_resource_type", "unknown"), language),
                    physical=_("Yes", language) if user_data.get("join_physical_presence") else _("No", language)
                )

                await query.edit_message_text(success_text)
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
            _("Joining collective action canceled.", language)
        )

    # Clean up context
    clear_user_context(telegram_id)

    return ConversationHandler.END


# Cancel handler for all conversations
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command in any conversation."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Clean up user context
    clear_user_context(telegram_id)

    await update.message.reply_text(
        _("Action canceled.", language)
    )

    return ConversationHandler.END


# Initialize conversation handlers
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
    fallbacks=[CommandHandler("cancel", cancel_handler)],
    # Remove the per_message=True parameter
)

action_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(action_select_district, pattern=r"^(action|quick_action):")
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
            CallbackQueryHandler(action_confirm, pattern=r"^(confirm|cancel_selection)$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern=r"^cancel_selection$"),
        CommandHandler("cancel", cancel_handler)
    ],
    per_message=True  # Add this parameter
)

resource_conversion_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(resource_conversion_start, pattern=r"^exchange_resources$")
    ],
    states={
        CONVERT_FROM_RESOURCE: [
            CallbackQueryHandler(convert_from_selected, pattern=r"^resource:")
        ],
        CONVERT_AMOUNT: [
            CallbackQueryHandler(convert_amount_selected, pattern=r"^amount:")
        ],
        CONVERT_TO_RESOURCE: [
            CallbackQueryHandler(convert_to_selected, pattern=r"^resource:")
        ],
        CONVERT_CONFIRM: [
            CallbackQueryHandler(convert_confirm, pattern=r"^(confirm|cancel_selection)$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern=r"^cancel_selection$"),
        CommandHandler("cancel", cancel_handler)
    ],
    per_message=True  # Add this parameter
)

collective_action_handler = ConversationHandler(
    entry_points=[
        CommandHandler("collective", collective_action_start)
    ],
    states={
        COLLECTIVE_ACTION_TYPE: [
            CallbackQueryHandler(collective_action_type_selected, pattern=r"^collective:")
        ],
        COLLECTIVE_ACTION_DISTRICT: [
            CallbackQueryHandler(collective_action_district_selected, pattern=r"^district:")
        ],
        COLLECTIVE_ACTION_TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, collective_action_target_entered)
        ],
        COLLECTIVE_ACTION_RESOURCE: [
            CallbackQueryHandler(collective_action_resource_selected, pattern=r"^resource:")
        ],
        COLLECTIVE_ACTION_AMOUNT: [
            CallbackQueryHandler(collective_action_amount_selected, pattern=r"^amount:")
        ],
        COLLECTIVE_ACTION_PHYSICAL: [
            CallbackQueryHandler(collective_action_physical_selected, pattern=r"^physical:")
        ],
        COLLECTIVE_ACTION_CONFIRM: [
            CallbackQueryHandler(collective_action_confirm, pattern=r"^(confirm|cancel_selection)$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern=r"^cancel_selection$"),
        CommandHandler("cancel", cancel_handler)
    ],
    per_message=True  # Add this parameter
)

join_command_handler = ConversationHandler(
    entry_points=[
        CommandHandler("join", join_collective_action_start)
    ],
    states={
        JOIN_ACTION_RESOURCE: [
            CallbackQueryHandler(join_action_resource_selected, pattern=r"^resource:")
        ],
        JOIN_ACTION_AMOUNT: [
            CallbackQueryHandler(join_action_amount_selected, pattern=r"^amount:")
        ],
        JOIN_ACTION_PHYSICAL: [
            CallbackQueryHandler(join_action_physical_selected, pattern=r"^physical:")
        ],
        JOIN_ACTION_CONFIRM: [
            CallbackQueryHandler(join_action_confirm, pattern=r"^(confirm|cancel_selection)$")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler)
    ],
    per_message=True  # Add this parameter to fix the warning
)

join_callback_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(join_collective_action_callback, pattern=r"^join_collective_action:")
    ],
    states={
        JOIN_ACTION_RESOURCE: [
            CallbackQueryHandler(join_action_resource_selected, pattern=r"^resource:")
        ],
        JOIN_ACTION_AMOUNT: [
            CallbackQueryHandler(join_action_amount_selected, pattern=r"^amount:")
        ],
        JOIN_ACTION_PHYSICAL: [
            CallbackQueryHandler(join_action_physical_selected, pattern=r"^physical:")
        ],
        JOIN_ACTION_CONFIRM: [
            CallbackQueryHandler(join_action_confirm, pattern=r"^(confirm|cancel_selection)$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern=r"^cancel_selection$")
    ],
    per_message=True
)

# List of all conversation handlers
conversation_handlers = [
    registration_handler,
    action_handler,
    resource_conversion_handler,
    collective_action_handler,
    join_command_handler,
    join_callback_handler
]
