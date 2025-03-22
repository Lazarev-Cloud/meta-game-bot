#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Callback query handlers for the Meta Game bot.
"""

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler

from bot.constants import ACTION_SELECT_RESOURCE, JOIN_ACTION_RESOURCE
from bot.context import get_user_context, user_context
from bot.keyboards import (
    get_start_keyboard,
    get_help_keyboard,
    get_status_keyboard,
    get_map_keyboard,
    get_action_keyboard,
    get_quick_action_keyboard,
    get_districts_keyboard,
    get_politicians_keyboard,
    get_politician_interaction_keyboard,
    get_resource_type_keyboard,
    get_back_keyboard
)
from db import (
    get_player,
    get_district_info,
    get_map_data,
    check_income,
    get_politicians,
    get_politician_status,
    submit_action, get_latest_news, get_active_collective_actions
)
from utils.formatting import (
    format_player_status,
    format_district_info,
    format_income_info,
    format_politicians_list,
    format_politician_info
)
from utils.i18n import _, get_user_language

# Initialize logger
logger = logging.getLogger(__name__)


async def general_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general callbacks that don't need specific processing."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)
    callback_data = query.data

    if callback_data == "back_to_menu":
        # Return to main menu
        await query.edit_message_text(
            _("Main Menu", language),
            reply_markup=get_start_keyboard(language)
        )
    elif callback_data == "help":
        # Show help menu
        help_text = _(
            "Welcome to Novi-Sad! What would you like to learn about?",
            language
        )
        await query.edit_message_text(
            help_text,
            reply_markup=get_help_keyboard(language)
        )
    elif callback_data.startswith("help:"):
        # Show specific help section
        section = callback_data.split(":", 1)[1]
        await help_section_callback(update, context, section)


async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle status callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get player status
    player_status = await get_player(telegram_id)

    if not player_status:
        await query.edit_message_text(
            _("Error retrieving your status. Please try again later.", language)
        )
        return

    # Format and send status message
    status_text = await format_player_status(player_status, language)

    await query.edit_message_text(
        status_text,
        parse_mode="Markdown",
        reply_markup=get_status_keyboard(language)
    )


async def map_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle map callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get map data
    map_data = await get_map_data(language)

    if not map_data:
        await query.edit_message_text(
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

    await query.edit_message_text(
        map_text,
        parse_mode="Markdown",
        reply_markup=get_map_keyboard(language)
    )


async def news_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle news callback with improved interactivity."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get page number from context or initialize
    page = context.user_data.get("news_page", 0)

    # Extract page action if there is one
    if query.data.startswith("news_page:"):
        action = query.data.split(":", 1)[1]
        if action == "next":
            page += 1
        elif action == "prev" and page > 0:
            page -= 1
        context.user_data["news_page"] = page

    # Get news with pagination (5 per page)
    news_count = 5
    news_offset = page * news_count

    news_data = await get_latest_news(telegram_id, count=news_count + 1,
                                      language=language)  # +1 to check if there's more

    if not news_data:
        await query.edit_message_text(
            _("Error retrieving news. Please try again later.", language)
        )
        return

    # Format and build news message
    news_text = _("*Latest News*\n\n", language)

    # Add public news
    public_news = news_data.get("public", [])
    if public_news:
        news_text += _("📰 *Public News*\n", language)

        for i, news in enumerate(public_news[:news_count]):  # Show news_count items per page
            title = news.get("title", "")
            content = news.get("content", "")
            cycle_type = news.get("cycle_type", "")
            cycle_date = news.get("cycle_date", "")

            news_text += f"*{title}*\n"
            news_text += f"{content}\n"
            news_text += _("({cycle_type} cycle, {date})\n\n", language).format(
                cycle_type=cycle_type,
                date=cycle_date
            )
    else:
        news_text += _("📰 *Public News*\n", language)
        news_text += _("No recent public news.\n\n", language)

    # Add faction news
    faction_news = news_data.get("faction", [])
    if faction_news:
        news_text += _("🔒 *Faction Intel*\n", language)

        for i, news in enumerate(faction_news[:news_count]):  # Show news_count items per page
            title = news.get("title", "")
            content = news.get("content", "")
            cycle_type = news.get("cycle_type", "")
            cycle_date = news.get("cycle_date", "")
            district = news.get("district", "")

            news_text += f"*{title}*\n"
            news_text += f"{content}\n"

            location_info = ""
            if district:
                location_info = f" - {district}"

            news_text += _("({cycle_type} cycle, {date}{location})\n\n", language).format(
                cycle_type=cycle_type,
                date=cycle_date,
                location=location_info
            )
    else:
        news_text += _("🔒 *Faction Intel*\n", language)
        news_text += _("No recent intelligence reports.\n\n", language)

    # Create pagination buttons
    buttons = []

    # Add navigation row
    navigation_row = []

    # Previous page button if not on first page
    if page > 0:
        navigation_row.append(InlineKeyboardButton("◀️ " + _("Previous", language), callback_data="news_page:prev"))

    # Next page button if there are more news
    if len(public_news) > news_count or len(faction_news) > news_count:
        navigation_row.append(InlineKeyboardButton(_("Next", language) + " ▶️", callback_data="news_page:next"))

    if navigation_row:
        buttons.append(navigation_row)

    # Add back to menu button
    buttons.append([InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")])

    # Create keyboard
    keyboard = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(
        news_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def district_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, district_name: str = None) -> None:
    """Handle district info callback."""
    query = None
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        # Extract district name if not provided
        if not district_name and query.data.startswith("district:"):
            district_name = query.data.split(":", 1)[1]

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get district info
    district_data = await get_district_info(telegram_id, district_name, language)

    if not district_data:
        message = _("Error retrieving district information for {district}. Please try again later.", language).format(
            district=district_name
        )
        if query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    # Format district info
    district_text = await format_district_info(district_data, language)

    # Create back button keyboard
    keyboard = get_back_keyboard(language, "select_district")

    if query:
        await query.edit_message_text(
            district_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            district_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def select_district_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle district selection callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Show district selection keyboard
    await query.edit_message_text(
        _("Please select a district to view:", language),
        reply_markup=await get_districts_keyboard(language)
    )


async def resources_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle resources callback."""
    query = update.callback_query
    await query.answer()

    # Forward to resources command handler
    from bot.commands import resources_command

    # Create a message that resources_command can respond to
    context._message = query.message
    update.message = query.message

    # Call the resources command handler
    await resources_command(update, context)

    # Restore update.message
    update.message = None


async def actions_left_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle actions left callback."""
    query = update.callback_query
    await query.answer()

    # Forward to actions_left command handler
    from bot.commands import actions_left_command

    # Create a message that actions_left_command can respond to
    context._message = query.message
    update.message = query.message

    # Call the actions_left command handler
    await actions_left_command(update, context)

    # Restore update.message
    update.message = None


async def controlled_districts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle controlled districts callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get player status
    player_status = await get_player(telegram_id)

    if not player_status:
        await query.edit_message_text(
            _("Error retrieving your status. Please try again later.", language)
        )
        return

    # Get controlled districts
    controlled_districts = player_status.get("controlled_districts", [])

    if not controlled_districts:
        await query.edit_message_text(
            _("You don't control any districts yet.\n\nDistricts are considered controlled when you have 60 or more control points.",
              language),
            reply_markup=get_back_keyboard(language)
        )
        return

    # Format controlled districts message
    districts_text = _("*Your Controlled Districts*\n\n", language)

    for district in controlled_districts:
        name = district.get("district_name", "Unknown")
        control_points = district.get("control_points", 0)
        influence = district.get("resource_influence", 0)
        money = district.get("resource_money", 0)
        information = district.get("resource_information", 0)
        force = district.get("resource_force", 0)

        control_level = "🔴 " if control_points >= 80 else "🟠 "

        districts_text += f"{control_level}*{name}*: {control_points} CP\n"
        districts_text += _("Resources per cycle: ", language)

        resources = []
        if influence > 0:
            resources.append(f"{influence} {_('Influence', language)}")
        if money > 0:
            resources.append(f"{money} {_('Money', language)}")
        if information > 0:
            resources.append(f"{information} {_('Information', language)}")
        if force > 0:
            resources.append(f"{force} {_('Force', language)}")

        districts_text += ", ".join(resources)
        districts_text += "\n\n"

    await query.edit_message_text(
        districts_text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard(language)
    )


async def politician_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle politician action buttons."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract action details
    action_data = query.data.split(":", 2)
    if len(action_data) < 3:
        await query.edit_message_text(
            _("Invalid action format. Please try again.", language)
        )
        return

    action_type = action_data[1]
    politician_name = action_data[2]

    # Initialize user context for action
    if telegram_id not in user_context:
        user_context[telegram_id] = {}

    # Get politician info to verify
    politician_data = await get_politician_status(telegram_id, politician_name, language)

    if not politician_data:
        await query.edit_message_text(
            _("Politician not found. Please try again.", language)
        )
        return

    # Map button action type to actual action type
    action_map = {
        "influence": "politician_influence",
        "attack": "politician_reputation_attack",
        "displace": "politician_displacement",
        "request": "politician_request_resources"
    }

    actual_action_type = action_map.get(action_type)

    if not actual_action_type:
        await query.edit_message_text(
            _("Invalid action type. Please try again.", language)
        )
        return

    # Store action info in user context
    user_context[telegram_id]["action_type"] = actual_action_type
    user_context[telegram_id]["is_quick_action"] = False
    user_context[telegram_id]["target_politician_name"] = politician_name

    # For request resources, handle differently
    if actual_action_type == "politician_request_resources":
        # This is a special case that doesn't use the normal action flow
        try:
            result = await submit_action(
                telegram_id=telegram_id,
                action_type=actual_action_type,
                is_quick_action=False,
                target_politician_name=politician_name,
                resource_type="influence",  # Default resource type
                resource_amount=1,  # Default resource amount
                language=language
            )

            if result and result.get("success"):
                # Success message
                await query.edit_message_text(
                    _("Resource request submitted to {politician_name}. You will receive resources soon if they approve your request.",
                      language).format(
                        politician_name=politician_name
                    )
                )
            else:
                await query.edit_message_text(
                    _("Failed to submit resource request. Please try again.", language)
                )
        except Exception as e:
            logger.error(f"Error requesting resources: {str(e)}")
            await query.edit_message_text(
                _("An error occurred: {error}", language).format(error=str(e))
            )
        return

    # For other actions, proceed with normal action flow
    # Ask for resource type
    await query.edit_message_text(
        _("What resource would you like to use for this action?", language),
        reply_markup=get_resource_type_keyboard(language)
    )

    # This will continue the action flow in states.py from ACTION_SELECT_RESOURCE state
    return ACTION_SELECT_RESOURCE


async def exchange_resources_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resource exchange initiation."""
    query = update.callback_query
    await query.answer()

    # This is the entry point for resource conversion from a button click
    from bot.states import resource_conversion_start
    return await resource_conversion_start(update, context)


# Define the join_collective_action_callback function
async def join_collective_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle joining collective actions from a button click."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract action ID
    action_data = query.data.split(":", 1)
    if len(action_data) < 2:
        await query.edit_message_text(
            _("Invalid action format. Please try again.", language)
        )
        return ConversationHandler.END

    action_id = action_data[1]

    # Initialize user context for joining action
    user_data = get_user_context(telegram_id)
    user_data["join_action_id"] = action_id

    # Prompt for resource selection
    await query.edit_message_text(
        _("You are joining collective action {action_id}.\n\nWhat resource would you like to contribute?",
          language).format(
            action_id=action_id
        ),
        reply_markup=get_resource_type_keyboard(language)
    )

    return JOIN_ACTION_RESOURCE

async def check_income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle income check callback."""
    query = None
    message = None

    if update.callback_query:
        query = update.callback_query
        await query.answer()
    else:
        message = update.message

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get income data
    income_data = await check_income(telegram_id, language)

    if not income_data:
        error_text = _("Error retrieving income information. Please try again later.", language)
        if query:
            await query.edit_message_text(error_text)
        else:
            await message.reply_text(error_text)
        return

    # Format income info
    income_text = await format_income_info(income_data, language)

    # Create back button keyboard
    keyboard = get_back_keyboard(language)

    if query:
        await query.edit_message_text(
            income_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await message.reply_text(
            income_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def help_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, section: str) -> None:
    """Handle specific help section callbacks."""
    query = update.callback_query
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    help_text = ""

    if section == "actions":
        help_text = _(
            "*Actions Guide*\n\n"
            "Each game cycle, you can submit:\n"
            "• 1 Main Action (ОЗ)\n"
            "• 2 Quick Actions (БЗ)\n\n"

            "*Main Actions*\n"
            "• *Influence* - Increase your control in a district (+10 CP)\n"
            "• *Attack* - Reduce enemy control and gain control points\n"
            "• *Defense* - Defend against attacks\n"
            "• *Politician Influence* - Improve relations with a politician\n"
            "• *Politician Attack* - Damage a politician's reputation\n"
            "• *Politician Displacement* - Reduce a politician's influence\n\n"

            "*Quick Actions*\n"
            "• *Reconnaissance* - Get information about a district\n"
            "• *Information Spread* - Publish news or propaganda\n"
            "• *Support* - Small control boost in a district (+5 CP)\n"
            "• *Kompromat Search* - Find compromising information\n\n"

            "*Physical Presence*\n"
            "Being physically present during an action gives +20 control points.",
            language
        )
    elif section == "resources":
        help_text = _(
            "*Resources Guide*\n\n"
            "There are 4 types of resources:\n\n"

            "• *Influence* - Political capital and soft power\n"
            "  - Used for political actions and diplomacy\n"
            "  - Can be converted to additional actions\n\n"

            "• *Money* - Financial resources\n"
            "  - Used for economic actions and bribes\n"
            "  - Can be converted to other resources (2:1 ratio)\n\n"

            "• *Information* - Intelligence and secrets\n"
            "  - Used for reconnaissance and propaganda\n"
            "  - Provides insights into districts and opponents\n\n"

            "• *Force* - Military and security capabilities\n"
            "  - Used for attacks and defense\n"
            "  - Provides protection and offensive capabilities\n\n"

            "*Resource Exchange*\n"
            "You can convert resources at a 2:1 ratio. Example:\n"
            "2 Money → 1 Influence",
            language
        )
    elif section == "districts":
        help_text = _(
            "*Districts Guide*\n\n"
            "Control Points (CP) determine district control:\n"
            "• 0-59 CP - No control\n"
            "• 60+ CP - District controlled\n"
            "• 80+ CP - Strong control (bonus resources)\n\n"

            "*Resource Income Breakdown*\n"
            "• 75-100 CP = 120% resources\n"
            "• 50-74 CP = 100% resources\n"
            "• 35-49 CP = 80% resources\n"
            "• 20-34 CP = 60% resources\n"
            "• <20 CP = 40% resources\n\n"

            "*District Decay*\n"
            "If you don't perform actions in a district, your control will decay by 5 CP per cycle.",
            language
        )
    elif section == "politicians":
        help_text = _(
            "*Politicians Guide*\n\n"
            "Politicians have influence in specific districts and ideological leanings from -5 (reformist) to +5 (conservative).\n\n"

            "*Politician Friendliness*\n"
            "• 0-30: Hostile - May work against you\n"
            "• 30-70: Neutral - Limited interaction\n"
            "• 70-100: Friendly - Provides resources and support\n\n"

            "*Ideological Compatibility*\n"
            "When your ideology aligns with a politician:\n"
            "• Small difference (0-2): +2 CP per cycle\n"
            "• Large alignment (3+): +5 CP per cycle\n"
            "• Opposition (3+ difference): -5 CP per cycle\n\n"

            "*International Politicians*\n"
            "International figures can impose sanctions, provide support, or influence the game in various ways.",
            language
        )
    elif section == "rules":
        help_text = _(
            "*Game Rules*\n\n"
            "The game takes place in Novi-Sad, Yugoslavia, in September 1999.\n\n"

            "*Game Cycles*\n"
            "• Each day has two cycles: Morning and Evening\n"
            "• Morning deadlines: 12:00, results at 13:00\n"
            "• Evening deadlines: 18:00, results at 19:00\n\n"

            "*Ideology*\n"
            "Your ideology ranges from -5 (reformist) to +5 (conservative) and affects your interactions with politicians and districts.\n\n"

            "*Winning Strategy*\n"
            "Control districts to gain resources, build alliances with politicians, and expand your influence across the city.\n\n"

            "*Cooperative Actions*\n"
            "Players can join forces for collective attacks or defense using the command /action Join.",
            language
        )
    else:
        help_text = _("Help section not found.", language)

    await query.edit_message_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=get_back_keyboard(language, "help")
    )


async def politicians_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle politician type selection callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Extract politician type
    data_parts = query.data.split(":", 1)
    if len(data_parts) < 2:
        await query.edit_message_text(
            _("Invalid selection. Please try again.", language)
        )
        return

    politician_type = data_parts[1]  # "local", "international", or "all"

    # Get politicians data
    politicians_data = await get_politicians(telegram_id, politician_type, language)

    if not politicians_data:
        await query.edit_message_text(
            _("Error retrieving politicians data. Please try again later.", language)
        )
        return

    # Format politicians list
    politicians_text = await format_politicians_list(politicians_data, language)

    # Create back button keyboard
    keyboard = get_back_keyboard(language, "back_to_politicians")

    await query.edit_message_text(
        politicians_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def politician_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   politician_name: str = None) -> None:
    """Handle politician info callback."""
    query = None
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        # Extract politician name if not provided
        if not politician_name and query.data.startswith("politician:"):
            politician_name = query.data.split(":", 1)[1]

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get politician info
    politician_data = await get_politician_status(telegram_id, politician_name, language)

    if not politician_data:
        message = _("Error retrieving information for {politician}. Please try again later.", language).format(
            politician=politician_name
        )
        if query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    # Format politician info
    politician_text = await format_politician_info(politician_data, language)

    # Create interaction keyboard
    keyboard = get_politician_interaction_keyboard(language, politician_data)

    if query:
        await query.edit_message_text(
            politician_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            politician_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def action_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the action button from main menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Show action options
    await query.edit_message_text(
        _("What type of main action would you like to take?", language),
        reply_markup=get_action_keyboard(language)
    )


async def quick_action_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the quick action button from main menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Show quick action options
    await query.edit_message_text(
        _("What type of quick action would you like to take?", language),
        reply_markup=get_quick_action_keyboard(language)
    )


async def politicians_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the politicians button from main menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Show politician options
    await query.edit_message_text(
        _("Which politicians would you like to see?", language),
        reply_markup=get_politicians_keyboard(language)
    )


async def view_collective_actions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view collective actions button."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Get active collective actions
    active_actions = await get_active_collective_actions()

    if not active_actions:
        await query.edit_message_text(
            _("There are no active collective actions at the moment.", language),
            reply_markup=get_back_keyboard(language)
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
            "*Initiated by:* {initiator}\n\n",
            language
        ).format(
            id=action_id,
            type=_(action_type, language),
            district=district,
            initiator=initiator
        )

    # Add button to join a collective action
    buttons = []
    for action in active_actions[:3]:  # Limit to first 3 for cleaner UI
        action_id = action.get("collective_action_id", "unknown")
        action_type = action.get("action_type", "unknown")
        district = action.get("district_id", {}).get("name", "unknown")

        button_text = f"{_(action_type, language)} in {district}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"join_collective_action:{action_id}")])

    # Add back button
    buttons.append([InlineKeyboardButton(_("Back", language), callback_data="back_to_menu")])

    # Create keyboard with join buttons
    keyboard = InlineKeyboardMarkup(buttons)

    # Send message with formatted text and join buttons
    await query.edit_message_text(
        actions_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def back_to_politicians_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back to politicians list callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    # Show politician options
    await query.edit_message_text(
        _("Which politicians would you like to see?", language),
        reply_markup=get_politicians_keyboard(language)
    )


async def international_politicians_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle international politicians callback."""
    query = None
    message = None

    if update.callback_query:
        query = update.callback_query
        await query.answer()
    else:
        message = update.message

    # Forward to politicians_type_callback with type "international"
    if query:
        # Modify query.data to simulate politicians:international
        query.data = "politicians:international"
        await politicians_type_callback(update, context)
    else:
        # Create a fake update with callback_query
        from telegram import CallbackQuery
        fake_query = CallbackQuery(
            id="0",
            from_user=update.effective_user,
            chat_instance="0",
            message=message,
            data="politicians:international"
        )
        fake_update = Update(0)
        fake_update._effective_user = update.effective_user
        fake_update._callback_query = fake_query

        await politicians_type_callback(fake_update, context)


async def cancel_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancel selection callback."""
    query = update.callback_query
    await query.answer()

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    await query.edit_message_text(
        _("Action canceled.", language)
    )


def register_callbacks(application) -> None:
    """Register all callback query handlers."""
    # Main menu callbacks
    application.add_handler(CallbackQueryHandler(status_callback, pattern=r"^status$"))
    application.add_handler(CallbackQueryHandler(map_callback, pattern=r"^map$"))
    application.add_handler(CallbackQueryHandler(news_callback, pattern=r"^news$"))
    application.add_handler(CallbackQueryHandler(resources_callback, pattern=r"^resources$"))
    application.add_handler(CallbackQueryHandler(action_button_callback, pattern=r"^action$"))
    application.add_handler(CallbackQueryHandler(quick_action_button_callback, pattern=r"^quick_action$"))
    application.add_handler(CallbackQueryHandler(politicians_button_callback, pattern=r"^politicians$"))

    # Secondary menu callbacks
    application.add_handler(CallbackQueryHandler(actions_left_callback, pattern=r"^actions_left$"))
    application.add_handler(CallbackQueryHandler(controlled_districts_callback, pattern=r"^controlled_districts$"))
    application.add_handler(CallbackQueryHandler(check_income_callback, pattern=r"^check_income$"))
    application.add_handler(CallbackQueryHandler(select_district_callback, pattern=r"^select_district$"))
    application.add_handler(
        CallbackQueryHandler(view_collective_actions_callback, pattern=r"^view_collective_actions$"))

    # Information callbacks
    application.add_handler(CallbackQueryHandler(district_info_callback, pattern=r"^district:"))
    application.add_handler(CallbackQueryHandler(back_to_politicians_callback, pattern=r"^back_to_politicians$"))
    application.add_handler(CallbackQueryHandler(politicians_type_callback, pattern=r"^politicians:"))
    application.add_handler(CallbackQueryHandler(politician_info_callback, pattern=r"^politician:"))

    # Action callbacks
    application.add_handler(CallbackQueryHandler(exchange_resources_callback, pattern=r"^exchange_resources$"))
    application.add_handler(CallbackQueryHandler(politician_action_handler, pattern=r"^politician_action:"))
    application.add_handler(CallbackQueryHandler(join_collective_action_callback, pattern=r"^join_collective_action:"))
    application.add_handler(CallbackQueryHandler(cancel_selection_callback, pattern=r"^cancel_selection$"))

    # Help callbacks
    application.add_handler(CallbackQueryHandler(help_section_callback, pattern=r"^help:"))

    # Navigation callbacks
    application.add_handler(CallbackQueryHandler(general_callback, pattern=r"^(back_to_menu|help)$"))

    # Register catch-all handler for any remaining patterns
    application.add_handler(CallbackQueryHandler(general_callback))
