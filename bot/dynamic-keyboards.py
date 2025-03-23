#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dynamic keyboard generators for the Meta Game bot.
"""

import logging
from typing import Dict, Any, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import get_player, get_active_collective_actions, is_submission_open
from utils.config import get_config
from utils.i18n import _

# Initialize logger
logger = logging.getLogger(__name__)

async def get_player_status_keyboard(telegram_id: str, language: str) -> InlineKeyboardMarkup:
    """
    Generate a status keyboard customized for the player's current state.
    
    This shows/hides buttons based on the player's current resources, 
    controlled districts, and other factors.
    
    Args:
        telegram_id: The user's Telegram ID
        language: The user's language preference
        
    Returns:
        A customized status keyboard
    """
    # Get player data
    player_data = await get_player(telegram_id)
    
    # Base keyboard buttons that are always shown
    keyboard = [
        [
            InlineKeyboardButton(_("View Resources", language), callback_data="resources"),
            InlineKeyboardButton(_("Check Actions", language), callback_data="actions_left")
        ]
    ]
    
    # Add controlled districts button if player has any
    controlled_districts = player_data.get("controlled_districts", [])
    if controlled_districts:
        keyboard.append([
            InlineKeyboardButton(_("View Controlled Districts", language), callback_data="controlled_districts"),
            InlineKeyboardButton(_("Check Income", language), callback_data="check_income")
        ])
    else:
        # Just show income button without districts if player has no controlled districts
        keyboard.append([
            InlineKeyboardButton(_("Check Potential Income", language), callback_data="check_income")
        ])
    
    # Check if submissions are open, add action buttons if yes
    is_open = await is_submission_open()
    if is_open:
        # Show action buttons
        actions_remaining = player_data.get("actions_remaining", 0)
        quick_actions_remaining = player_data.get("quick_actions_remaining", 0)
        
        action_text = _("Main Action", language)
        if actions_remaining > 0:
            action_text += f" ({actions_remaining})"
            
        quick_action_text = _("Quick Action", language)
        if quick_actions_remaining > 0:
            quick_action_text += f" ({quick_actions_remaining})"
        
        keyboard.append([
            InlineKeyboardButton(action_text, callback_data="action"),
            InlineKeyboardButton(quick_action_text, callback_data="quick_action")
        ])
    
    # Add back button
    keyboard.append([
        InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def get_collective_actions_keyboard(telegram_id: str, language: str) -> InlineKeyboardMarkup:
    """
    Generate a keyboard with active collective actions that can be joined.
    
    Args:
        telegram_id: The user's Telegram ID
        language: The user's language preference
        
    Returns:
        A keyboard with active collective actions
    """
    # Get active collective actions
    active_actions = await get_active_collective_actions()
    
    keyboard = []
    
    # Add buttons for active actions
    if active_actions:
        for action in active_actions[:5]:  # Limit to 5 actions for cleaner UI
            action_id = action.get("collective_action_id", "unknown")
            action_type = action.get("action_type", "unknown")
            district = action.get("district_id", {}).get("name", "unknown")
            
            button_text = f"{_(action_type, language)} in {district}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"join_collective_action:{action_id}")
            ])
    
    # Add button to initiate a new collective action if submissions are open
    is_open = await is_submission_open()
    if is_open:
        keyboard.append([
            InlineKeyboardButton(_("Start New Collective Action", language), callback_data="start_collective_action")
        ])
    
    # Add back button
    keyboard.append([
        InlineKeyboardButton(_("Back to Menu", language), callback_data="back_to_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def get_politician_action_keyboard(telegram_id: str, politician_data: Dict[str, Any], language: str) -> InlineKeyboardMarkup:
    """
    Generate a keyboard with possible actions for a specific politician.
    
    Shows only actions that are available based on the current relationships.
    
    Args:
        telegram_id: The user's Telegram ID
        politician_data: Data about the politician
        language: The user's language preference
        
    Returns:
        A keyboard with available politician actions
    """
    possible_actions = politician_data.get("possible_actions", {})
    
    keyboard = []
    actions = []
    
    # Check if submissions are open
    is_open = await is_submission_open()
    
    if is_open:
        # Only show action buttons if submissions are open
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
        row = actions[i:i+2]
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton(_("Back", language), callback_data="back_to_politicians")])
    
    return InlineKeyboardMarkup(keyboard)

async def get_resource_amount_keyboard_dynamic(telegram_id: str, resource_type: str, language: str) -> InlineKeyboardMarkup:
    """
    Generate a keyboard for selecting resource amounts based on what the player has available.
    
    Args:
        telegram_id: The user's Telegram ID
        resource_type: The type of resource ('influence', 'money', 'information', 'force')
        language: The user's language preference
        
    Returns:
        A keyboard with available resource amounts
    """
    # Get player data
    player_data = await get_player(telegram_id)
    resources = player_data.get("resources", {})
    available = resources.get(resource_type, 0)
    
    # Calculate max amount (limited to 5 for UI cleanliness)
    max_amount = min(available, 5)
    
    keyboard = []
    
    # Create buttons for amounts 1 to max_amount
    if max_amount > 0:
        amounts = list(range(1, max_amount + 1))
        
        # Group into rows of 3
        for i in range(0, len(amounts), 3):
            row = []
            for amount in amounts[i:i+3]:
                row.append(InlineKeyboardButton(str(amount), callback_data=f"amount:{amount}"))
            keyboard.append(row)
    else:
        # No resources available
        keyboard.append([
            InlineKeyboardButton(_("Not enough resources", language), callback_data="not_enough_resources")
        ])
    
    # Add cancel button
    keyboard.append([
        InlineKeyboardButton(_("Cancel", language), callback_data="cancel_selection")
    ])
    
    return InlineKeyboardMarkup(keyboard)
