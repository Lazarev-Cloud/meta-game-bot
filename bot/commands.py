#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete command handlers implementation for the Meta Game bot.
"""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from bot.keyboards import (
    get_start_keyboard,
    get_help_keyboard,
    get_status_keyboard,
    get_map_keyboard,
    get_action_keyboard,
    get_quick_action_keyboard,
    get_districts_keyboard,
    get_resources_keyboard,
    get_politicians_keyboard, get_politician_interaction_keyboard
)
from bot.states import NAME_ENTRY
from db import (
    player_exists,
    get_player,
    get_cycle_info,
    get_latest_news,
    cancel_latest_action,
    get_map_data,
    check_income,
    get_politicians,
    get_politician_status, get_active_collective_actions, get_district_info
)
from utils.formatting import (
    format_player_status,
    format_time,
    format_cycle_info,
    format_news,
    format_district_info,
    format_income_info,
    format_politicians_list,
    format_politician_info
)
from utils.i18n import _, get_user_language

# Initialize logger
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Handle the /start command - register new player or welcome existing one."""
    user = update.effective_user
    telegram_id = str(user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if exists:
        player_data = await get_player(telegram_id)
        if player_data:
            # Welcome back message for existing player
            await update.message.reply_text(
                _("Welcome back to Novi-Sad, {name}! What would you like to do?", language).format(
                    name=player_data.get("player_name", user.first_name)
                ),
                reply_markup=get_start_keyboard(language)
            )
            return None

    # For new players, start registration process
    await update.message.reply_text(
        _("Welcome to Novi-Sad, a city at the crossroads of Yugoslavia's future! "
          "You're about to enter a political game set in September 1999.\n\n"
          "First, tell me your character's name:", language)
    )
    return NAME_ENTRY


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command - display available commands."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    help_text = _(
        "Here are the available commands:\n\n"
        "*Basic Commands*\n"
        "/start - Start the game, register as a player\n"
        "/help - Show this help message\n"
        "/status - Show your current status (resources, districts)\n"
        "/map - Show the current map of district control\n"
        "/time - Show current game cycle information\n"
        "/news - Show the latest news\n\n"

        "*Action Commands*\n"
        "/action - Submit a main action\n"
        "/quick_action - Submit a quick action\n"
        "/cancel_action - Cancel your last action\n"
        "/actions_left - Check remaining actions\n"
        "/view_district [district] - View district information\n\n"

        "*Resource Commands*\n"
        "/resources - View your current resources\n"
        "/convert_resource [type] [amount] - Convert resources\n"
        "/check_income - Check expected resource income\n\n"

        "*Politicians Commands*\n"
        "/politicians - List available politicians\n"
        "/politician_status [name] - Information about a politician\n"
        "/international - Information about international politicians\n\n"

        "*Collective Action Commands*\n"
        "/collective - Initiate a collective action\n"
        "/join [action_id] - Join a collective action\n"
        "/active_actions - View all active collective actions",
        language
    )

    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_help_keyboard(language)
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /status command - show player status."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get player status
    player_status = await get_player(telegram_id)

    if not player_status:
        await update.message.reply_text(
            _("Error retrieving your status. Please try again later.", language)
        )
        return

    # Format and send status message
    status_text = await format_player_status(player_status, language)

    await update.message.reply_text(
        status_text,
        parse_mode="Markdown",
        reply_markup=get_status_keyboard(language)
    )


async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /map command - show the map of district control."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get map data
    map_data = await get_map_data(language)

    if not map_data:
        await update.message.reply_text(
            _("Error retrieving map data. Please try again later.", language)
        )
        return

    # Format and build map message
    districts = map_data.get("districts", [])
    game_date = map_data.get("game_date", "Unknown")
    cycle = map_data.get("cycle", "Unknown")

    map_text = _(
        "*Current Map of Novi-Sad*\n"
        "Date: {date}, {cycle} cycle\n\n"
        "District Control:\n",
        language
    ).format(date=game_date, cycle=cycle)

    for district in districts:
        name = district.get("name", "Unknown")
        controlling_player = district.get("controlling_player", _("None", language))
        control_level = district.get("control_level", "neutral")

        control_symbol = "🔴" if control_level == "strong" else "🟠" if control_level == "controlled" else "🟡" if control_level == "contested" else "⚪"

        map_text += f"{control_symbol} *{name}*: "
        if controlling_player != _("None", language):
            map_text += _("Controlled by {player}", language).format(player=controlling_player)
        else:
            map_text += _("No clear control", language)
        map_text += "\n"

    # Add map link if available
    map_text += "\n" + _("For a visual map, use the button below:", language)

    await update.message.reply_text(
        map_text,
        parse_mode="Markdown",
        reply_markup=get_map_keyboard(language)
    )


async def active_collective_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /active_actions command - list active collective actions."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get active collective actions
    active_actions = await get_active_collective_actions()

    if not active_actions:
        await update.message.reply_text(
            _("There are no active collective actions at the moment.", language)
        )
        return

    # Format and display active actions
    actions_text = _("*Active Collective Actions*\n\n", language)

    for action in active_actions:
        action_id = action.get("collective_action_id", "unknown")
        action_type = action.get("action_type", "unknown")
        district = action.get("district_id", {}).get("name", "unknown")
        initiator = action.get("initiator_player_id", {}).get("name", "unknown")

        actions_text += _(
            "*Action ID:* {id}\n"
            "*Type:* {type}\n"
            "*District:* {district}\n"
            "*Initiated by:* {initiator}\n"
            "*Join Command:* `/join {id}`\n\n",
            language
        ).format(
            id=action_id,
            type=_(action_type, language),
            district=district,
            initiator=initiator
        )

    # Send message with formatted text
    await update.message.reply_text(
        actions_text,
        parse_mode="Markdown"
    )


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /time command - show current cycle information."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get cycle information
    cycle_info = await get_cycle_info(language)

    if not cycle_info:
        await update.message.reply_text(
            _("Error retrieving cycle information. Please try again later.", language)
        )
        return

    # Format and send cycle information
    cycle_text = await format_cycle_info(cycle_info, language)

    await update.message.reply_text(
        cycle_text,
        parse_mode="Markdown"
    )


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /news command - show latest news."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get latest news
    news_data = await get_latest_news(telegram_id, language=language)

    if not news_data:
        await update.message.reply_text(
            _("Error retrieving news. Please try again later.", language)
        )
        return

    # Format and send news
    news_text = await format_news(news_data, language)

    await update.message.reply_text(
        news_text,
        parse_mode="Markdown"
    )


async def action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /action command - submit a main action."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get player information
    player_data = await get_player(telegram_id)

    # Check if player has actions left
    actions_remaining = player_data.get("actions_remaining", 0)

    if actions_remaining <= 0:
        await update.message.reply_text(
            _("You have no main actions remaining for this cycle.", language)
        )
        return

    # Show action options
    await update.message.reply_text(
        _("What type of main action would you like to take?", language),
        reply_markup=get_action_keyboard(language)
    )


async def quick_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /quick_action command - submit a quick action."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get player information
    player_data = await get_player(telegram_id)

    # Check if player has quick actions left
    quick_actions_remaining = player_data.get("quick_actions_remaining", 0)

    if quick_actions_remaining <= 0:
        await update.message.reply_text(
            _("You have no quick actions remaining for this cycle.", language)
        )
        return

    # Show quick action options
    await update.message.reply_text(
        _("What type of quick action would you like to take?", language),
        reply_markup=get_quick_action_keyboard(language)
    )


async def cancel_action_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /cancel_action command - cancel the last action."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    try:
        # Cancel the latest action
        result = await cancel_latest_action(telegram_id, language)

        if result and result.get("success"):
            action_id = result.get("action_id", "unknown")
            action_type = result.get("action_type", "unknown")
            resource_refunded = result.get("resource_refunded", {})
            resource_type = resource_refunded.get("type", "unknown")
            resource_amount = resource_refunded.get("amount", 0)

            # Success message
            await update.message.reply_text(
                _("Action canceled successfully!\n\n"
                  "Action type: {action_type}\n"
                  "Resources refunded: {amount} {resource_type}", language).format(
                    action_type=action_type,
                    amount=resource_amount,
                    resource_type=resource_type
                )
            )
        else:
            # Error message
            await update.message.reply_text(
                _("Failed to cancel action. You may not have any pending actions, or the action may already be processed.",
                  language)
            )
    except Exception as e:
        logger.error(f"Error canceling action: {str(e)}")
        await update.message.reply_text(
            _("An error occurred while canceling your action. Please try again later.", language)
        )


async def actions_left_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /actions_left command - check remaining actions."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get player information
    player_data = await get_player(telegram_id)

    if not player_data:
        await update.message.reply_text(
            _("Error retrieving your information. Please try again later.", language)
        )
        return

    # Get remaining actions
    actions_remaining = player_data.get("actions_remaining", 0)
    quick_actions_remaining = player_data.get("quick_actions_remaining", 0)

    # Get cycle info for time remaining
    cycle_info = await get_cycle_info(language)
    time_to_deadline = cycle_info.get("time_to_deadline", "unknown")

    # Format and send actions remaining message
    await update.message.reply_text(
        _("*Actions Remaining*\n\n"
          "Main Actions: {main_actions}\n"
          "Quick Actions: {quick_actions}\n\n"
          "Time remaining in this cycle: {time_remaining}", language).format(
            main_actions=actions_remaining,
            quick_actions=quick_actions_remaining,
            time_remaining=await format_time(time_to_deadline, language)
        ),
        parse_mode="Markdown"
    )


async def view_district_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /view_district command - show district information."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Check if district name is provided
    if not context.args or not context.args[0]:
        # Show list of all districts to choose from
        await update.message.reply_text(
            _("Please select a district to view:", language),
            reply_markup=await get_districts_keyboard(language)
        )
        return

    # Get district name from args
    district_name = " ".join(context.args)

    # Get district info
    district_data = await get_district_info(telegram_id, district_name, language)

    if not district_data:
        await update.message.reply_text(
            _("Error retrieving district information for {district}. The district may not exist or there was a server error.",
              language).format(
                district=district_name
            )
        )
        return

    # Format district info
    district_text = await format_district_info(district_data, language)

    # Send district info
    await update.message.reply_text(
        district_text,
        parse_mode="Markdown",
        reply_markup=await get_districts_keyboard(language)
    )


async def resources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /resources command - show current resources."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get player information
    player_data = await get_player(telegram_id)

    if not player_data:
        await update.message.reply_text(
            _("Error retrieving your information. Please try again later.", language)
        )
        return

    # Get and format resources
    resources = player_data.get("resources", {})
    influence = resources.get("influence", 0)
    money = resources.get("money", 0)
    information = resources.get("information", 0)
    force = resources.get("force", 0)

    resources_text = _(
        "*Your Resources*\n\n"
        "🔵 *Influence:* {influence} - Used for political maneuvers\n"
        "💰 *Money:* {money} - Used for economic actions\n"
        "🔍 *Information:* {information} - Used for intelligence and research\n"
        "👊 *Force:* {force} - Used for military and security actions\n\n"
        "_Use the buttons below to exchange resources (2:1 ratio)_",
        language
    ).format(
        influence=influence,
        money=money,
        information=information,
        force=force
    )

    await update.message.reply_text(
        resources_text,
        parse_mode="Markdown",
        reply_markup=get_resources_keyboard(language)
    )


async def convert_resource_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /convert_resource command - convert between resource types."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Check if resource type and amount are provided
    if len(context.args) < 2:
        await update.message.reply_text(
            _("Please specify the resource type and amount. For example:\n"
              "/convert_resource money 5\n\n"
              "This would convert 10 money (2:1 ratio) into 5 of your chosen resource.", language)
        )
        return

    # Let the callback handle the conversion
    from bot.states import resource_conversion_start
    resource_type = context.args[0].lower()
    try:
        amount = int(context.args[1])
        await resource_conversion_start(update, context, resource_type, amount)
    except ValueError:
        await update.message.reply_text(
            _("Invalid amount. Please provide a number.", language)
        )


async def check_income_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /check_income command - show expected resource income."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get income data
    income_data = await check_income(telegram_id, language)

    if not income_data:
        await update.message.reply_text(
            _("Error retrieving income information. Please try again later.", language)
        )
        return

    # Format income info
    income_text = await format_income_info(income_data, language)

    # Send income info
    await update.message.reply_text(
        income_text,
        parse_mode="Markdown"
    )


async def politicians_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /politicians command - list available politicians."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Show politician options
    await update.message.reply_text(
        _("Which politicians would you like to see?", language),
        reply_markup=get_politicians_keyboard(language)
    )


async def politician_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /politician_status command - show politician information."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Check if politician name is provided
    if not context.args or not context.args[0]:
        await update.message.reply_text(
            _("Please specify a politician name. For example:\n"
              "/politician_status Nemanja Kovacevic", language)
        )
        return

    # Get politician name from args
    politician_name = " ".join(context.args)

    # Get politician info
    politician_data = await get_politician_status(telegram_id, politician_name, language)

    if not politician_data:
        await update.message.reply_text(
            _("Error retrieving information for politician {name}. The politician may not exist or there was a server error.",
              language).format(
                name=politician_name
            )
        )
        return

    # Format politician info
    politician_text = await format_politician_info(politician_data, language)

    # Send politician info
    await update.message.reply_text(
        politician_text,
        parse_mode="Markdown",
        reply_markup=get_politician_interaction_keyboard(language, politician_data)
    )


async def international_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /international command - show international politicians."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Check if player exists
    exists = await player_exists(telegram_id)

    if not exists:
        await update.message.reply_text(
            _("You are not registered yet. Use /start to register.", language)
        )
        return

    # Get international politicians
    politicians_data = await get_politicians(telegram_id, "international", language)

    if not politicians_data:
        await update.message.reply_text(
            _("Error retrieving international politicians. Please try again later.", language)
        )
        return

    # Format politicians list
    politicians_text = await format_politicians_list(politicians_data, language)

    # Send politicians info
    await update.message.reply_text(
        politicians_text,
        parse_mode="Markdown",
        reply_markup=get_politicians_keyboard(language)
    )


async def collective_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /collective command - initiate a collective action."""
    # This command is handled by the collective_action_handler ConversationHandler
    # from bot.states import collective_action_start
    # await collective_action_start(update, context)
    pass


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /join command - join a collective action."""
    # This command is handled by the join_action_handler ConversationHandler
    # from bot.states import join_collective_action_start
    # await join_collective_action_start(update, context)
    pass


# Admin commands
async def admin_process_actions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /admin_process command - process all pending actions (admin only)."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Import admin function
    from db import admin_process_actions

    try:
        result = await admin_process_actions(telegram_id)

        if result and result.get("success"):
            actions_processed = result.get("actions_processed", 0)
            collective_actions_processed = result.get("collective_actions_processed", 0)

            await update.message.reply_text(
                _("Actions processed successfully:\n\n"
                  "Regular actions: {actions}\n"
                  "Collective actions: {collective_actions}\n\n"
                  "New cycle has been created.", language).format(
                    actions=actions_processed,
                    collective_actions=collective_actions_processed
                )
            )
        else:
            await update.message.reply_text(
                _("Error processing actions. Make sure you have admin privileges.", language)
            )
    except Exception as e:
        logger.error(f"Error in admin_process_actions: {str(e)}")
        await update.message.reply_text(
            _("An error occurred while processing actions: {error}", language).format(error=str(e))
        )


async def admin_generate_effects_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /admin_generate command - generate international effects (admin only)."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Import admin function
    from db import admin_generate_international_effects

    # Get count parameter if provided
    count = 2
    if context.args and len(context.args) > 0:
        try:
            count = int(context.args[0])
        except ValueError:
            pass

    try:
        result = await admin_generate_international_effects(telegram_id, count)

        if result and result.get("success"):
            effects_generated = result.get("effects_generated", 0)
            effects = result.get("effects", [])

            effects_text = ""
            for effect in effects:
                politician = effect.get("politician", "Unknown")
                effect_type = effect.get("effect_type", "Unknown")
                description = effect.get("description", "No details")

                effects_text += f"• {politician}: {effect_type}\n  {description}\n\n"

            await update.message.reply_text(
                _("Generated {count} international effects:\n\n{effects}", language).format(
                    count=effects_generated,
                    effects=effects_text
                )
            )
        else:
            await update.message.reply_text(
                _("Error generating international effects. Make sure you have admin privileges.", language)
            )
    except Exception as e:
        logger.error(f"Error in admin_generate_effects: {str(e)}")
        await update.message.reply_text(
            _("An error occurred while generating effects: {error}", language).format(error=str(e))
        )


def register_commands(application) -> None:
    """Register all command handlers."""
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("action", action_command))
    application.add_handler(CommandHandler("quick_action", quick_action_command))
    application.add_handler(CommandHandler("cancel_action", cancel_action_command))
    application.add_handler(CommandHandler("actions_left", actions_left_command))
    application.add_handler(CommandHandler("view_district", view_district_command))
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("convert_resource", convert_resource_command))
    application.add_handler(CommandHandler("check_income", check_income_command))
    application.add_handler(CommandHandler("politicians", politicians_command))
    application.add_handler(CommandHandler("politician_status", politician_status_command))
    application.add_handler(CommandHandler("international", international_command))

    # Add the active collective actions command
    application.add_handler(CommandHandler("active_actions", active_collective_actions_command))

    # Admin commands
    application.add_handler(CommandHandler("admin_process", admin_process_actions_command))
    application.add_handler(CommandHandler("admin_generate", admin_generate_effects_command))
