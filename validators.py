#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validation utilities for Belgrade Game Bot
Contains functions for validating user input and game data
"""

import logging
import re
import sqlite3
from typing import Union, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

# Valid resource types
VALID_RESOURCE_TYPES = ["influence", "resources", "information", "force"]

# Valid action types
VALID_MAIN_ACTIONS = ["influence", "attack", "defense"]
VALID_QUICK_ACTIONS = ["recon", "info", "support"]


def validate_resource_type(resource_type: str) -> bool:
    """
    Validate if the resource type is valid

    Args:
        resource_type: Resource type to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return resource_type in VALID_RESOURCE_TYPES


def validate_resource_amount(amount: Union[str, int]) -> Tuple[bool, int, str]:
    """Enhanced resource amount validation with error message"""
    try:
        amount_int = int(amount)

        if amount_int <= 0:
            return False, 0, "Amount must be greater than zero"

        return True, amount_int, ""
    except (ValueError, TypeError):
        return False, 0, "Amount must be a valid number"


def validate_district_id(district_id: str) -> bool:
    """
    Validate if the district ID exists in the database

    Args:
        district_id: District ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute("SELECT district_id FROM districts WHERE district_id = ?", (district_id,))
        result = cursor.fetchone()

        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Error validating district ID: {e}")
        return False


def validate_politician_id(politician_id: Union[str, int]) -> bool:
    """
    Validate if the politician ID exists in the database

    Args:
        politician_id: Politician ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Convert to integer if it's a string
        politician_id_int = int(politician_id)

        cursor.execute("SELECT politician_id FROM politicians WHERE politician_id = ?", (politician_id_int,))
        result = cursor.fetchone()

        conn.close()
        return result is not None
    except (ValueError, TypeError, Exception) as e:
        logger.error(f"Error validating politician ID: {e}")
        return False


def validate_character_name(name: str) -> Tuple[bool, str]:
    """
    Validate a character name with detailed error message
    """
    if not name:
        return False, "Name cannot be empty"

    if len(name) < 2:
        return False, "Name is too short (minimum 2 characters)"

    if len(name) > 30:
        return False, "Name is too long (maximum 30 characters)"

    if re.search(r'[<>/\\]', name):
        return False, "Name contains invalid characters"

    return True, ""


def validate_player_resources(player_id: int, resource_requirements: Dict[str, int]) -> bool:
    """
    Validate that a player has sufficient resources for an action

    Args:
        player_id: Player ID
        resource_requirements: Dictionary of required resources {resource_type: amount}

    Returns:
        bool: True if player has sufficient resources, False otherwise
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        for resource_type, amount in resource_requirements.items():
            # Skip invalid resource types
            if not validate_resource_type(resource_type):
                continue

            cursor.execute(f"SELECT {resource_type} FROM resources WHERE player_id = ?", (player_id,))
            result = cursor.fetchone()

            if not result or result[0] < amount:
                conn.close()
                return False

        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error validating player resources: {e}")
        return False


def validate_action_type(action_type: str, is_main_action: bool = True) -> bool:
    """
    Validate if the action type is valid

    Args:
        action_type: Action type to validate
        is_main_action: Whether this is a main action or quick action

    Returns:
        bool: True if valid, False otherwise
    """
    if is_main_action:
        return action_type in VALID_MAIN_ACTIONS
    else:
        return action_type in VALID_QUICK_ACTIONS


def validate_actions_left(player_id: int, is_main_action: bool = True) -> bool:
    """
    Validate that a player has actions left

    Args:
        player_id: Player ID
        is_main_action: Whether to check for main actions or quick actions

    Returns:
        bool: True if player has actions left, False otherwise
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        field = "main_actions_left" if is_main_action else "quick_actions_left"
        cursor.execute(f"SELECT {field} FROM players WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()

        conn.close()
        return result is not None and result[0] > 0
    except Exception as e:
        logger.error(f"Error validating actions left: {e}")
        return False