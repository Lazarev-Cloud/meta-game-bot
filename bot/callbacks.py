#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Callback query handlers for the Meta Game bot.
"""

import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler

from bot.constants import ACTION_SELECT_RESOURCE, JOIN_ACTION_RESOURCE
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
    get_back_keyboard,
    get_resources_keyboard,
    get_language_keyboard
)
from db import (
    get_player,
    get_district_info,
    get_map_data,
    check_income,
    get_politicians,
    get_politician_status,
    submit_action,
    get_latest_news,
    get_active_collective_actions,
    get_cycle_info
)
from utils.formatting import (
    format_player_status,
    format_district_info,
    format_income_info,
    format_politicians_list,
    format_politician_info,
    format_time,
    format_news
)
from utils.i18n import _, get_user_language, set_user_language
from utils.error_handling import require_registration, handle_error
from utils.message_utils import send_message, edit_or_reply, answer_callback
from utils.context_manager import get_user_data, set_user_data, clear_user_data

# Initialize logger
logger = logging.getLogger(__name__)


async def general_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general callbacks that don't need specific processing."""
    query = update.callback_query
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)
    callback_data = query.data

    if callback_data == "back_to_menu":
        # Return to main menu
        await edit_or_reply(
            update,
            _("Main Menu", language),
            keyboard=get_start_keyboard(language)
        )
    elif callback_data == "help":
        # Show help menu
        help_text = _(
            "Welcome to Novi-Sad! What would you like to learn about?",
            language
        )
        await edit_or_reply(
            update,
            help_text,
            keyboard=get_help_keyboard(language)
        )
    elif callback_data.startswith("help:"):
        # Show specific help section
        section = callback_data.split(":", 1)[1]
        await help_section_callback(update, context, section)


async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle status callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get player status
        player_status = await get_player(telegram_id)

        if not player_status:
            await edit_or_reply(
                update,
                _("Error retrieving your status. Please try again later.", language)
            )
            return

        # Format and send status message
        status_text = await format_player_status(player_status, language)

        await edit_or_reply(
            update,
            status_text,
            keyboard=get_status_keyboard(language),
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "status_callback")


async def map_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle map callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get map data
        map_data = await get_map_data(language)

        if not map_data:
            await edit_or_reply(
                update,
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

        await edit_or_reply(
            update,
            map_text,
            keyboard=get_map_keyboard(language),
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "map_callback")


async def news_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle news callback with improved interactivity."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get page number from context or initialize
        page = context.user_data.get("news_page", 0)

        # Extract page action if there is one
        if update.callback_query.data.startswith("news_page:"):
            action = update.callback_query.data.split(":", 1)[1]
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
            await edit_or_reply(
                update,
                _("Error retrieving news. Please try again later.", language)
            )
            return

        # Format and build news message
        news_text = await format_news(news_data, language)

        # Create pagination buttons
        buttons = []

        # Add navigation row
        navigation_row = []

        # Previous page button if not on first page
        if page > 0:
            navigation_row.append(InlineKeyboardButton("◀️ " + _("Previous", language), callback_data="news_page:prev"))

        # Next page button if there are more news
        public_news = news_data.get("public", [])
        faction_news = news_data.get("faction", [])
        has_more = (len(public_news) > news_count or len(faction_news) > news_count)

        if has_more:
            navigation_row.append(InlineKeyboardButton(_("Next", language) + " ▶️", callback_data="news_page:next"))

        if navigation_row:
            buttons.append(navigation_row)

        # Add back to menu button
        buttons.append([InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")])

        # Create keyboard
        keyboard = InlineKeyboardMarkup(buttons)

        await edit_or_reply(
            update,
            news_text,
            keyboard=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "news_callback")


async def district_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, district_name: str = None) -> None:
    """Handle district info callback."""
    query = None
    if update.callback_query:
        query = update.callback_query
        await answer_callback(update)

        # Extract district name if not provided
        if not district_name and query.data.startswith("district:"):
            district_name = query.data.split(":", 1)[1]

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if query and not await require_registration(update, language):
        return

    try:
        # Get district info
        district_data = await get_district_info(telegram_id, district_name, language)

        if not district_data:
            message = _("Error retrieving district information for {district}. Please try again later.",
                        language).format(
                district=district_name
            )
            await edit_or_reply(update, message)
            return

        # Format district info
        district_text = await format_district_info(district_data, language)

        # Create back button keyboard
        keyboard = get_back_keyboard(language, "select_district")

        await edit_or_reply(
            update,
            district_text,
            keyboard=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "district_info_callback")


async def select_district_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle district selection callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Show district selection keyboard
        await edit_or_reply(
            update,
            _("Please select a district to view:", language),
            keyboard=await get_districts_keyboard(language)
        )
    except Exception as e:
        await handle_error(update, language, e, "select_district_callback")


async def resources_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle resources callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get player information
        player_data = await get_player(telegram_id)

        if not player_data:
            await edit_or_reply(
                update,
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

        await edit_or_reply(
            update,
            resources_text,
            keyboard=get_resources_keyboard(language),
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "resources_callback")


async def actions_left_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle actions left callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get player information
        player_data = await get_player(telegram_id)

        if not player_data:
            await edit_or_reply(
                update,
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
        await edit_or_reply(
            update,
            _("*Actions Remaining*\n\n"
              "Main Actions: {main_actions}\n"
              "Quick Actions: {quick_actions}\n\n"
              "Time remaining in this cycle: {time_remaining}", language).format(
                main_actions=actions_remaining,
                quick_actions=quick_actions_remaining,
                time_remaining=await format_time(time_to_deadline, language)
            ),
            keyboard=get_back_keyboard(language),
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "actions_left_callback")


async def controlled_districts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle controlled districts callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get player status
        player_status = await get_player(telegram_id)

        if not player_status:
            await edit_or_reply(
                update,
                _("Error retrieving your status. Please try again later.", language)
            )
            return

        # Get controlled districts
        controlled_districts = player_status.get("controlled_districts", [])

        if not controlled_districts:
            await edit_or_reply(
                update,
                _("You don't control any districts yet.\n\nDistricts are considered controlled when you have 60 or more control points.",
                  language),
                keyboard=get_back_keyboard(language)
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

        await edit_or_reply(
            update,
            districts_text,
            keyboard=get_back_keyboard(language),
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "controlled_districts_callback")


async def politician_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle politician action buttons."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Extract action details
        action_data = update.callback_query.data.split(":", 2)
        if len(action_data) < 3:
            await edit_or_reply(
                update,
                _("Invalid action format. Please try again.", language)
            )
            return

        action_type = action_data[1]
        politician_name = action_data[2]

        # Store action info in user context
        user_data = get_user_data(telegram_id, context)
        set_user_data(telegram_id, "action_type", action_type, context)
        set_user_data(telegram_id, "is_quick_action", False, context)
        set_user_data(telegram_id, "target_politician_name", politician_name, context)

        # Get politician info to verify
        politician_data = await get_politician_status(telegram_id, politician_name, language)

        if not politician_data:
            await edit_or_reply(
                update,
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
            await edit_or_reply(
                update,
                _("Invalid action type. Please try again.", language)
            )
            return

        set_user_data(telegram_id, "action_type", actual_action_type, context)

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
                    await edit_or_reply(
                        update,
                        _("Resource request submitted to {politician_name}. You will receive resources soon if they approve your request.",
                          language).format(
                            politician_name=politician_name
                        )
                    )
                else:
                    await edit_or_reply(
                        update,
                        _("Failed to submit resource request. Please try again.", language)
                    )
            except Exception as e:
                logger.error(f"Error requesting resources: {str(e)}")
                await edit_or_reply(
                    update,
                    _("An error occurred: {error}", language).format(error=str(e))
                )
            return

        # For other actions, proceed with normal action flow
        # Ask for resource type
        await edit_or_reply(
            update,
            _("What resource would you like to use for this action?", language),
            keyboard=get_resource_type_keyboard(language)
        )

        # This will continue the action flow in states.py from ACTION_SELECT_RESOURCE state
        return ACTION_SELECT_RESOURCE
    except Exception as e:
        await handle_error(update, language, e, "politician_action_handler")


async def exchange_resources_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resource exchange initiation."""
    await answer_callback(update)

    # This is the entry point for resource conversion from a button click
    from bot.states import resource_conversion_start
    return await resource_conversion_start(update, context)


async def join_collective_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle joining collective actions from a button click."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return ConversationHandler.END

    try:
        # Extract action ID
        action_data = update.callback_query.data.split(":", 1)
        if len(action_data) < 2:
            await edit_or_reply(
                update,
                _("Invalid action format. Please try again.", language)
            )
            return ConversationHandler.END

        action_id = action_data[1]

        # Store action ID in user context
        set_user_data(telegram_id, "join_action_id", action_id, context)

        # Prompt for resource selection
        await edit_or_reply(
            update,
            _("You are joining collective action {action_id}.\n\nWhat resource would you like to contribute?",
              language).format(
                action_id=action_id
            ),
            keyboard=get_resource_type_keyboard(language)
        )

        return JOIN_ACTION_RESOURCE
    except Exception as e:
        await handle_error(update, language, e, "join_collective_action_callback")
        return ConversationHandler.END


async def check_income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle income check callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get income data
        income_data = await check_income(telegram_id, language)

        if not income_data:
            await edit_or_reply(
                update,
                _("Error retrieving income information. Please try again later.", language)
            )
            return

        # Format income info
        income_text = await format_income_info(income_data, language)

        # Create back button keyboard
        keyboard = get_back_keyboard(language)

        await edit_or_reply(
            update,
            income_text,
            keyboard=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "check_income_callback")


async def help_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, section: str) -> None:
    """Handle specific help section callbacks."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    try:
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
                "• Large alignment (3+ difference): -5 CP per cycle\n\n"

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
                "Players can join forces for collective attacks or defense using the command /collective.",
                language
            )
        else:
            help_text = _("Help section not found.", language)

        await edit_or_reply(
            update,
            help_text,
            keyboard=get_back_keyboard(language, "help"),
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "help_section_callback")


async def news_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle news pagination navigation."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Extract page action (next/prev)
        action = update.callback_query.data.split(":", 1)[1]

        # Get current page or initialize
        page = context.user_data.get("news_page", 0)

        # Update page based on action
        if action == "next":
            page += 1
        elif action == "prev" and page > 0:
            page -= 1

        # Store updated page
        context.user_data["news_page"] = page

        # Forward to main news handler with updated page
        await news_callback(update, context)
    except Exception as e:
        await handle_error(update, language, e, "news_page_callback")

async def language_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language setting callbacks."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)

    try:
        # Extract selected language
        selected_language = update.callback_query.data.split(":", 1)[1]

        # Update user's language preference
        success = await set_user_language(telegram_id, selected_language)
        language = await get_user_language(telegram_id)

        if success:
            await edit_or_reply(
                update,
                _("Language set to {language}. You can change it at any time from the settings menu.", language).format(
                    language=_("English", language) if selected_language == "en_US" else _("Russian", language)
                ),
                keyboard=get_back_keyboard(language)
            )
        else:
            await edit_or_reply(
                update,
                _("Failed to set language. Please try again later.", language),
                keyboard=get_back_keyboard(language)
            )
    except Exception as e:
        # Handle error with default language English since we don't know user's language
        logger.error(f"Error setting language: {str(e)}")
        await edit_or_reply(
            update,
            "Failed to set language. Please try again later.",
            keyboard=get_back_keyboard("en_US")
        )


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle settings menu."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    try:
        # Create settings menu
        settings_text = _("*Settings*\n\nHere you can change your preferences.", language)

        # Create settings keyboard
        keyboard = [
            [
                InlineKeyboardButton(_("Language", language), callback_data="settings:language")
            ],
            [
                InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await edit_or_reply(
            update,
            settings_text,
            keyboard=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "settings_menu_callback")


async def language_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show language selection menu."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    try:
        await edit_or_reply(
            update,
            _("Select your preferred language:", language),
            keyboard=get_language_keyboard()
        )
    except Exception as e:
        await handle_error(update, language, e, "language_menu_callback")


async def politicians_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle politician type selection callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Extract politician type
        data_parts = update.callback_query.data.split(":", 1)
        if len(data_parts) < 2:
            await edit_or_reply(
                update,
                _("Invalid selection. Please try again.", language)
            )
            return

        politician_type = data_parts[1]  # "local", "international", or "all"

        # Get politicians data
        politicians_data = await get_politicians(telegram_id, politician_type, language)

        if not politicians_data:
            await edit_or_reply(
                update,
                _("Error retrieving politicians data. Please try again later.", language)
            )
            return

        # Format politicians list
        politicians_text = await format_politicians_list(politicians_data, language)

        # Create back button keyboard
        keyboard = get_back_keyboard(language, "back_to_politicians")

        await edit_or_reply(
            update,
            politicians_text,
            keyboard=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "politicians_type_callback")


async def politician_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   politician_name: str = None) -> None:
    """Handle politician info callback."""
    query = None
    if update.callback_query:
        query = update.callback_query
        await answer_callback(update)

        # Extract politician name if not provided
        if not politician_name and query.data.startswith("politician:"):
            politician_name = query.data.split(":", 1)[1]

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if query and not await require_registration(update, language):
        return

    try:
        # Get politician info
        politician_data = await get_politician_status(telegram_id, politician_name, language)

        if not politician_data:
            message = _("Error retrieving information for {politician}. Please try again later.", language).format(
                politician=politician_name
            )
            await edit_or_reply(update, message)
            return

        # Format politician info
        politician_text = await format_politician_info(politician_data, language)

        # Create interaction keyboard
        keyboard = get_politician_interaction_keyboard(language, politician_data)

        await edit_or_reply(
            update,
            politician_text,
            keyboard=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "politician_info_callback")

async def help_section_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wrapper to extract section from callback data."""
    if update.callback_query and update.callback_query.data:
        section = update.callback_query.data.split(":", 1)[1]
        await help_section_callback(update, context, section)

async def action_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the action button from main menu."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get player information
        player_data = await get_player(telegram_id)

        # Check if submissions are open
        cycle_info = await get_cycle_info(language)
        if not cycle_info.get("is_accepting_submissions", False):
            await edit_or_reply(
                update,
                _("The submission deadline for this cycle has passed. "
                  "Wait until the next cycle to submit actions.", language)
            )
            return

        # Check if player has actions left
        actions_remaining = player_data.get("actions_remaining", 0)

        if actions_remaining <= 0:
            await edit_or_reply(
                update,
                _("You have no main actions remaining for this cycle.", language),
                keyboard=get_back_keyboard(language)
            )
            return

        # Show action options
        await edit_or_reply(
            update,
            _("What type of main action would you like to take?", language),
            keyboard=get_action_keyboard(language)
        )
    except Exception as e:
        await handle_error(update, language, e, "action_button_callback")


async def quick_action_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the quick action button from main menu."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get player information
        player_data = await get_player(telegram_id)

        # Check if submissions are open
        cycle_info = await get_cycle_info(language)
        if not cycle_info.get("is_accepting_submissions", False):
            await edit_or_reply(
                update,
                _("The submission deadline for this cycle has passed. "
                  "Wait until the next cycle to submit actions.", language)
            )
            return

        # Check if player has quick actions left
        quick_actions_remaining = player_data.get("quick_actions_remaining", 0)

        if quick_actions_remaining <= 0:
            await edit_or_reply(
                update,
                _("You have no quick actions remaining for this cycle.", language),
                keyboard=get_back_keyboard(language)
            )
            return

        # Show quick action options
        await edit_or_reply(
            update,
            _("What type of quick action would you like to take?", language),
            keyboard=get_quick_action_keyboard(language)
        )
    except Exception as e:
        await handle_error(update, language, e, "quick_action_button_callback")


async def politicians_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the politicians button from main menu."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Show politician options
        await edit_or_reply(
            update,
            _("Which politicians would you like to see?", language),
            keyboard=get_politicians_keyboard(language)
        )
    except Exception as e:
        await handle_error(update, language, e, "politicians_button_callback")


async def view_collective_actions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle view collective actions button."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Get active collective actions
        active_actions = await get_active_collective_actions()

        if not active_actions:
            await edit_or_reply(
                update,
                _("There are no active collective actions at the moment.", language),
                keyboard=get_back_keyboard(language)
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
        await edit_or_reply(
            update,
            actions_text,
            keyboard=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await handle_error(update, language, e, "view_collective_actions_callback")


async def back_to_politicians_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back to politicians list callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if not await require_registration(update, language):
        return

    try:
        # Show politician options
        await edit_or_reply(
            update,
            _("Which politicians would you like to see?", language),
            keyboard=get_politicians_keyboard(language)
        )
    except Exception as e:
        await handle_error(update, language, e, "back_to_politicians_callback")


async def international_politicians_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle international politicians callback."""
    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    if update.callback_query:
        await answer_callback(update)
        if not await require_registration(update, language):
            return

    try:
        # Forward to politicians_type_callback with type "international"
        if update.callback_query:
            # Modify query.data to simulate politicians:international
            update.callback_query.data = "politicians:international"
            await politicians_type_callback(update, context)
        else:
            # Create a fake update with callback_query
            from telegram import CallbackQuery
            fake_query = CallbackQuery(
                id="0",
                from_user=update.effective_user,
                chat_instance="0",
                message=update.message,
                data="politicians:international"
            )
            fake_update = Update(0)
            fake_update._effective_user = update.effective_user
            fake_update._callback_query = fake_query

            await politicians_type_callback(fake_update, context)
    except Exception as e:
        await handle_error(update, language, e, "international_politicians_callback")


async def cancel_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cancel selection callback."""
    await answer_callback(update)

    telegram_id = str(update.effective_user.id)
    language = await get_user_language(telegram_id)

    try:
        await edit_or_reply(
            update,
            _("Action canceled.", language),
            keyboard=get_back_keyboard(language)
        )
    except Exception as e:
        await handle_error(update, language, e, "cancel_selection_callback")


# Register these additional callbacks in register_callbacks function:
def register_additional_callbacks(application) -> None:
    """Register additional callback handlers."""
    # News pagination
    application.add_handler(CallbackQueryHandler(news_page_callback, pattern=r"^news_page:"))

    # Settings and language
    application.add_handler(CallbackQueryHandler(settings_menu_callback, pattern=r"^settings$"))
    application.add_handler(CallbackQueryHandler(language_menu_callback, pattern=r"^settings:language$"))
    application.add_handler(CallbackQueryHandler(language_setting_callback, pattern=r"^language:"))

def register_callbacks(registry) -> None:
    """Register all callback query handlers."""
    # Main menu callbacks
    registry.register_callback("^status$", status_callback)
    registry.register_callback("^map$", map_callback)
    registry.register_callback("^news$", news_callback)
    registry.register_callback("^resources$", resources_callback)
    registry.register_callback("^action$", action_button_callback)
    registry.register_callback("^quick_action$", quick_action_button_callback)
    registry.register_callback("^politicians$", politicians_button_callback)

    # Secondary menu callbacks
    registry.register_callback("^actions_left$", actions_left_callback)
    registry.register_callback("^controlled_districts$", controlled_districts_callback)
    registry.register_callback("^check_income$", check_income_callback)
    registry.register_callback("^select_district$", select_district_callback)
    registry.register_callback("^view_collective_actions$", view_collective_actions_callback)

    # Information callbacks
    registry.register_callback("^district:", district_info_callback)
    registry.register_callback("^back_to_politicians$", back_to_politicians_callback)
    registry.register_callback("^politicians:", politicians_type_callback)
    registry.register_callback("^politician:", politician_info_callback)

    # Action callbacks
    registry.register_callback("^exchange_resources$", exchange_resources_callback)
    registry.register_callback("^politician_action:", politician_action_handler)
    registry.register_callback("^join_collective_action:", join_collective_action_callback)
    registry.register_callback("^cancel_selection$", cancel_selection_callback)

    # Help callbacks
    registry.register_callback("^help:", help_section_callback_wrapper)

    # Navigation callbacks
    registry.register_callback("^(back_to_menu|help)$", general_callback)

    # News pagination
    registry.register_callback("^news_page:", news_page_callback)

    # Settings and language
    registry.register_callback("^settings$", settings_menu_callback)
    registry.register_callback("^settings:language$", language_menu_callback)
    registry.register_callback("^language:", language_setting_callback)

    # Register catch-all handler for any remaining patterns
    registry.register_other_handler(CallbackQueryHandler(general_callback))
