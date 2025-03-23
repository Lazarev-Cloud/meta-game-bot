#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Button validation utilities for the Meta Game bot.
"""

import logging
from typing import Dict, Any, Optional, Tuple

from db import get_player, player_exists, is_submission_open, get_remaining_actions

# Initialize logger
logger = logging.getLogger(__name__)

async def validate_action_button(telegram_id: str, is_quick_action: bool, language: str) -> Tuple[bool, Optional[str]]:
    """
    Validate whether a user can perform an action (main or quick).
    
    Args:
        telegram_id: The user's Telegram ID
        is_quick_action: Whether this is a quick action (True) or main action (False)
        language: The user's language preference
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the action can be performed, False otherwise
        - error_message: Error message to display if is_valid is False, None otherwise
    """
    from utils.i18n import _
    
    # Check if player exists
    exists = await player_exists(telegram_id)
    if not exists:
        return False, _("You are not registered yet. Use /start to register.", language)
    
    # Check if submissions are open
    is_open = await is_submission_open()
    if not is_open:
        return False, _("The submission deadline for this cycle has passed.", language)
    
    # Get player information
    player_data = await get_player(telegram_id)
    if not player_data:
        return False, _("Error retrieving your information. Please try again later.", language)
    
    # Check if player has actions left
    if is_quick_action:
        remaining = player_data.get("quick_actions_remaining", 0)
        if remaining <= 0:
            return False, _("You have no quick actions remaining for this cycle.", language)
    else:
        remaining = player_data.get("actions_remaining", 0)
        if remaining <= 0:
            return False, _("You have no main actions remaining for this cycle.", language)
    
    # All checks passed
    return True, None

async def validate_resource_action(telegram_id: str, resource_type: str, amount: int, language: str) -> Tuple[bool, Optional[str]]:
    """
    Validate whether a user has enough resources for an action.
    
    Args:
        telegram_id: The user's Telegram ID
        resource_type: The type of resource ('influence', 'money', 'information', 'force')
        amount: The amount of resource to use
        language: The user's language preference
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if the user has enough resources, False otherwise
        - error_message: Error message to display if is_valid is False, None otherwise
    """
    from utils.i18n import _
    
    # Get player information
    player_data = await get_player(telegram_id)
    if not player_data:
        return False, _("Error retrieving your information. Please try again later.", language)
    
    # Check resources
    resources = player_data.get("resources", {})
    available = resources.get(resource_type, 0)
    
    if available < amount:
        return False, _("You don't have enough {resource} resources. You have {available}, but need {amount}.", language).format(
            resource=_(resource_type, language),
            available=available,
            amount=amount
        )
    
    # All checks passed
    return True, None
