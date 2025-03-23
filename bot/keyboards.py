#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Keyboard layouts and builders for the Meta Game bot.
"""

import logging
from typing import Dict, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_districts
from utils.i18n import _

# Initialize logger
logger = logging.getLogger(__name__)


def get_start_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get the welcome keyboard for returning players."""
    keyboard = [
        [
            InlineKeyboardButton(_("Status", language), callback_data="status"),
            InlineKeyboardButton(_("Map", language), callback_data="map"),
            InlineKeyboardButton(_("News", language), callback_data="news")
        ],
        [
            InlineKeyboardButton(_("Main Action", language), callback_data="action"),
            InlineKeyboardButton(_("Quick Action", language), callback_data="quick_action")
        ],
        [
            InlineKeyboardButton(_("Resources", language), callback_data="resources"),
            InlineKeyboardButton(_("Politicians", language), callback_data="politicians:all")
        ],
        [
            InlineKeyboardButton(_("Collective Actions", language), callback_data="view_collective_actions"),
            InlineKeyboardButton(_("Help", language), callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_ideology_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for ideology selection."""
    keyboard = [
        [
            InlineKeyboardButton(_("Strong Reformist (-5)", language), callback_data="ideology:-5"),
            InlineKeyboardButton(_("Moderate Reformist (-3)", language), callback_data="ideology:-3")
        ],
        [
            InlineKeyboardButton(_("Slight Reformist (-1)", language), callback_data="ideology:-1"),
            InlineKeyboardButton(_("Neutral (0)", language), callback_data="ideology:0")
        ],
        [
            InlineKeyboardButton(_("Slight Conservative (+1)", language), callback_data="ideology:1"),
            InlineKeyboardButton(_("Moderate Conservative (+3)", language), callback_data="ideology:3")
        ],
        [
            InlineKeyboardButton(_("Strong Conservative (+5)", language), callback_data="ideology:5")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_help_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for help menu."""
    keyboard = [
        [
            InlineKeyboardButton(_("Action Guide", language), callback_data="help:actions"),
            InlineKeyboardButton(_("Resources Guide", language), callback_data="help:resources")
        ],
        [
            InlineKeyboardButton(_("Districts Guide", language), callback_data="help:districts"),
            InlineKeyboardButton(_("Politicians Guide", language), callback_data="help:politicians")
        ],
        [
            InlineKeyboardButton(_("Game Rules", language), callback_data="help:rules")
        ],
        [
            InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_status_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for status menu."""
    keyboard = [
        [
            InlineKeyboardButton(_("View Resources", language), callback_data="resources"),
            InlineKeyboardButton(_("Check Actions", language), callback_data="actions_left")
        ],
        [
            InlineKeyboardButton(_("View Controlled Districts", language), callback_data="controlled_districts"),
            InlineKeyboardButton(_("Check Income", language), callback_data="check_income")
        ],
        [
            InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_map_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for map view."""
    from utils.config import get_config

    # Get map URL from config
    map_url = get_config("bot", "web_map_url")

    keyboard = [
        [
            InlineKeyboardButton(_("View District Details", language), callback_data="select_district"),
            InlineKeyboardButton(_("View Web Map", language), url=map_url)
        ],
        [
            InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_collective_action_info_keyboard(action_id: str, language: str) -> InlineKeyboardMarkup:
    """Create a keyboard for joining a collective action."""
    keyboard = [
        [
            InlineKeyboardButton(
                _("Join Action", language),
                callback_data=f"join_collective_action:{action_id}"
            )
        ],
        [
            InlineKeyboardButton(_("Back", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_action_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for main action selection."""
    keyboard = [
        [
            InlineKeyboardButton(_("Influence", language), callback_data="action:influence"),
            InlineKeyboardButton(_("Attack", language), callback_data="action:attack"),
            InlineKeyboardButton(_("Defense", language), callback_data="action:defense")
        ],
        [
            InlineKeyboardButton(_("Politician Influence", language), callback_data="action:politician_influence"),
            InlineKeyboardButton(_("Politician Attack", language), callback_data="action:politician_reputation_attack")
        ],
        [
            InlineKeyboardButton(_("Politician Displacement", language), callback_data="action:politician_displacement")
        ],
        [
            InlineKeyboardButton(_("International Negotiations", language),
                                 callback_data="action:international_negotiations"),
            InlineKeyboardButton(_("Lobbying", language), callback_data="action:lobbying")
        ],
        [
            InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quick_action_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for quick action selection."""
    keyboard = [
        [
            InlineKeyboardButton(_("Reconnaissance", language), callback_data="quick_action:reconnaissance"),
            InlineKeyboardButton(_("Information Spread", language), callback_data="quick_action:information_spread")
        ],
        [
            InlineKeyboardButton(_("Support", language), callback_data="quick_action:support"),
            InlineKeyboardButton(_("Kompromat Search", language), callback_data="quick_action:kompromat_search")
        ],
        [
            InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def get_districts_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard with all districts."""
    districts = await get_districts()

    # Group districts into rows of 2
    keyboard = []
    row = []

    for district in districts:
        district_name = district.get("name", "Unknown")
        if len(row) < 2:
            row.append(InlineKeyboardButton(district_name, callback_data=f"district:{district_name}"))
        else:
            keyboard.append(row)
            row = [InlineKeyboardButton(district_name, callback_data=f"district:{district_name}")]

    if row:  # Add any remaining items
        keyboard.append(row)

    # Add back button
    keyboard.append([InlineKeyboardButton(_("Back", language), callback_data="back_to_menu")])

    return InlineKeyboardMarkup(keyboard)


def get_resources_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for resource management."""
    keyboard = [
        [
            InlineKeyboardButton(_("Exchange Resources", language), callback_data="exchange_resources"),
            InlineKeyboardButton(_("Check Income", language), callback_data="check_income")
        ],
        [
            InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_resource_type_keyboard(language: str, exclude_type: str = None) -> InlineKeyboardMarkup:
    """Get keyboard for selecting resource type, optionally excluding one type."""
    keyboard = []

    resources = [
        ("influence", _("Influence", language)),
        ("money", _("Money", language)),
        ("information", _("Information", language)),
        ("force", _("Force", language))
    ]

    # Filter out excluded type
    if exclude_type:
        resources = [r for r in resources if r[0] != exclude_type]

    # Group into rows of 2
    row = []
    for resource_type, label in resources:
        if len(row) < 2:
            row.append(InlineKeyboardButton(label, callback_data=f"resource:{resource_type}"))
        else:
            keyboard.append(row)
            row = [InlineKeyboardButton(label, callback_data=f"resource:{resource_type}")]

    if row:  # Add any remaining items
        keyboard.append(row)

    # Add cancel button
    keyboard.append([InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")])

    return InlineKeyboardMarkup(keyboard)


def get_resource_amount_keyboard(language: str, max_amount: int = 5) -> InlineKeyboardMarkup:
    """Get keyboard for selecting resource amount."""
    keyboard = []

    # Create buttons for amounts 1-5 (or max_amount)
    amounts = list(range(1, min(max_amount + 1, 6)))

    # Group into rows of 3
    for i in range(0, len(amounts), 3):
        row = []
        for amount in amounts[i:i + 3]:
            row.append(InlineKeyboardButton(str(amount), callback_data=f"amount:{amount}"))
        keyboard.append(row)

    # Add cancel button
    keyboard.append([InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")])

    return InlineKeyboardMarkup(keyboard)


def get_politicians_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for politician type selection."""
    keyboard = [
        [
            InlineKeyboardButton(_("Local Politicians", language), callback_data="politicians:local"),
            InlineKeyboardButton(_("International Politicians", language), callback_data="politicians:international")
        ],
        [
            InlineKeyboardButton(_("All Politicians", language), callback_data="politicians:all")
        ],
        [
            InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_politician_interaction_keyboard(language: str, politician_data: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Get keyboard for interacting with a politician."""
    possible_actions = politician_data.get("possible_actions", {})

    keyboard = []

    # Add possible actions based on politician data
    actions = []

    if possible_actions.get("influence", False):
        actions.append(InlineKeyboardButton(
            _("Increase Influence", language),
            callback_data=f"politician_action:influence:{politician_data.get('name')}"
        ))

    if possible_actions.get("attack_reputation", False):
        actions.append(InlineKeyboardButton(
            _("Attack Reputation", language),
            callback_data=f"politician_action:attack:{politician_data.get('name')}"
        ))

    if possible_actions.get("displacement", False):
        actions.append(InlineKeyboardButton(
            _("Displacement", language),
            callback_data=f"politician_action:displace:{politician_data.get('name')}"
        ))

    if possible_actions.get("request_resources", False):
        actions.append(InlineKeyboardButton(
            _("Request Resources", language),
            callback_data=f"politician_action:request:{politician_data.get('name')}"
        ))

    # Group actions into rows of 2
    for i in range(0, len(actions), 2):
        row = actions[i:i + 2]
        keyboard.append(row)

    # Add back button
    keyboard.append([InlineKeyboardButton(_("Back", language), callback_data="back_to_politicians")])

    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for confirmation dialogs."""
    keyboard = [
        [
            InlineKeyboardButton(_("Confirm", language), callback_data="confirm"),
            InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_yes_no_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard with Yes/No options."""
    keyboard = [
        [
            InlineKeyboardButton(_("Yes", language), callback_data="yes"),
            InlineKeyboardButton(_("No", language), callback_data="no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_physical_presence_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for physical presence selection."""
    keyboard = [
        [
            InlineKeyboardButton(_("Yes (+20 Control Points)", language), callback_data="physical:yes"),
            InlineKeyboardButton(_("No", language), callback_data="physical:no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(language: str, callback_data: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Get a simple back button keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(_("Back", language), callback_data=callback_data)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for language selection."""
    keyboard = [
        [
            InlineKeyboardButton("English 🇬🇧", callback_data="language:en_US"),
            InlineKeyboardButton("Русский 🇷🇺", callback_data="language:ru_RU")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_collective_action_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for collective action type selection."""
    keyboard = [
        [
            InlineKeyboardButton(_("Attack", language), callback_data="collective:attack"),
            InlineKeyboardButton(_("Defense", language), callback_data="collective:defense")
        ],
        [
            InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def setup_i18n():
    """Initialize the internationalization system."""
    logger.info("Initializing internationalization system")


def get_settings_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard for settings menu."""
    keyboard = [
        [
            InlineKeyboardButton(_("Language", language), callback_data="settings:language"),
            InlineKeyboardButton(_("Notifications", language), callback_data="settings:notifications")
        ],
        [
            InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_news_keyboard(language: str, page: int = 0, has_next: bool = False) -> InlineKeyboardMarkup:
    """Get keyboard for news display with pagination."""
    buttons = []

    # Add pagination buttons if needed
    navigation_row = []

    if page > 0:
        navigation_row.append(InlineKeyboardButton("◀️ " + _("Previous", language), callback_data="news_page:prev"))

    if has_next:
        navigation_row.append(InlineKeyboardButton(_("Next", language) + " ▶️", callback_data="news_page:next"))

    if navigation_row:
        buttons.append(navigation_row)

    # Add other navigation buttons
    buttons.append([
        InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
    ])

    return InlineKeyboardMarkup(buttons)


def get_cancel_button(language: str) -> InlineKeyboardMarkup:
    """Get a simple cancel button keyboard."""
    keyboard = [
        [
            InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_yes_no_cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get keyboard with Yes/No/Cancel options."""
    keyboard = [
        [
            InlineKeyboardButton(_("Yes", language), callback_data="yes"),
            InlineKeyboardButton(_("No", language), callback_data="no")
        ],
        [
            InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_join_collective_action_keyboard(action_id: str, language: str) -> InlineKeyboardMarkup:
    """Get keyboard for joining a specific collective action."""
    keyboard = [
        [
            InlineKeyboardButton(_("Join", language), callback_data=f"join_collective_action:{action_id}")
        ],
        [
            InlineKeyboardButton(_("Back", language), callback_data="back_to_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_extended_start_keyboard(language: str) -> InlineKeyboardMarkup:
    """Get an extended version of the welcome keyboard with more options."""
    keyboard = [
        [
            InlineKeyboardButton(_("Status", language), callback_data="status"),
            InlineKeyboardButton(_("Map", language), callback_data="map"),
            InlineKeyboardButton(_("News", language), callback_data="news")
        ],
        [
            InlineKeyboardButton(_("Main Action", language), callback_data="action"),
            InlineKeyboardButton(_("Quick Action", language), callback_data="quick_action")
        ],
        [
            InlineKeyboardButton(_("Resources", language), callback_data="resources"),
            InlineKeyboardButton(_("Politicians", language), callback_data="politicians:all")
        ],
        [
            InlineKeyboardButton(_("Collective Actions", language), callback_data="view_collective_actions"),
            InlineKeyboardButton(_("Settings", language), callback_data="settings")
        ],
        [
            InlineKeyboardButton(_("Help", language), callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_simple_keyboard(buttons, language):
    """Create a simple keyboard with back button."""
    keyboard = []
    for row in buttons:
        keyboard.append(row)
    # Add back button
    keyboard.append([InlineKeyboardButton(_("Back", language), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)
