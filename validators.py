#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validation utilities for Belgrade Game Bot
Contains functions for validating user input and game data
"""

import logging
import re
import sqlite3
from typing import Union, Tuple, List, Dict, Any, Optional
from db.queries import db_connection_pool, db_transaction
from languages import get_text

logger = logging.getLogger(__name__)

# Valid resource types
VALID_RESOURCE_TYPES = ["money", "influence", "support"]

# Valid action types
VALID_MAIN_ACTIONS = ["influence", "attack", "defense"]
VALID_QUICK_ACTIONS = ["trade", "interact", "support"]

VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_]{3,30}$')


def validate_resource_type(resource_type: str) -> bool:
    """
    Validate if the resource type is valid

    Args:
        resource_type: Resource type to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return resource_type in VALID_RESOURCE_TYPES


def validate_resource_amount(amount: Union[str, int, float]) -> Tuple[bool, int, str]:
    """
    Validate if the resource amount is valid.
    
    Returns:
        Tuple of (is_valid, amount, error_message)
    """
    try:
        amount_int = int(float(amount))
        if amount_int <= 0:
            return False, 0, "Amount must be positive"
        return True, amount_int, ""
    except (ValueError, TypeError):
        return False, 0, "Amount must be a valid number"


@db_transaction
def validate_district_id(district_id: str, conn: Any) -> bool:
    """
    Validate if the district ID exists in the database

    Args:
        district_id: District ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT district_id FROM districts WHERE district_id = ?", (district_id,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        logger.error(f"Error validating district ID: {e}")
        return False


@db_transaction
def validate_politician_id(politician_id: Union[str, int], conn: Any) -> bool:
    """
    Validate if the politician ID exists in the database

    Args:
        politician_id: Politician ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Convert to integer if it's a string
        politician_id_int = int(politician_id)
        
        cursor = conn.cursor()
        cursor.execute("SELECT politician_id FROM politicians WHERE politician_id = ?", (politician_id_int,))
        result = cursor.fetchone()
        return result is not None
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid politician ID format: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating politician ID: {e}")
        return False


def validate_character_name(name: str) -> Tuple[bool, str]:
    """
    Validate if the character name is valid.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or len(name) < 3:
        return False, "Name must be at least 3 characters long"
    
    if len(name) > 30:
        return False, "Name must be at most 30 characters long"
    
    if not VALID_NAME_PATTERN.match(name):
        return False, "Name contains invalid characters"
    
    return True, ""


@db_transaction
def validate_player_resources(player_id: int, resource_requirements: Dict[str, int], conn: Any) -> bool:
    """
    Validate that a player has sufficient resources for an action

    Args:
        player_id: Player ID
        resource_requirements: Dictionary of required resources {resource_type: amount}

    Returns:
        bool: True if player has sufficient resources, False otherwise
    """
    try:
        cursor = conn.cursor()
        
        for resource_type, amount in resource_requirements.items():
            # Skip invalid resource types
            if not validate_resource_type(resource_type):
                continue
            
            cursor.execute("""
                SELECT amount 
                FROM player_resources 
                WHERE player_id = ? AND resource_type = ?
            """, (player_id, resource_type))
            result = cursor.fetchone()
            
            if not result or result[0] < amount:
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating player resources: {e}")
        return False


def validate_action_type(action_type: str, is_quick_action: bool = False) -> bool:
    """
    Validate if the action type is valid

    Args:
        action_type: Action type to validate
        is_quick_action: Whether this is a quick action

    Returns:
        bool: True if valid, False otherwise
    """
    if is_quick_action:
        return action_type in VALID_QUICK_ACTIONS
    else:
        return action_type in VALID_MAIN_ACTIONS


@db_transaction
def validate_actions_left(player_id: int, is_main_action: bool, conn: Any) -> bool:
    """
    Validate that a player has actions left

    Args:
        player_id: Player ID
        is_main_action: Whether to check for main actions or quick actions

    Returns:
        bool: True if player has actions left, False otherwise
    """
    try:
        cursor = conn.cursor()
        
        field = "main_actions_left" if is_main_action else "quick_actions_left"
        cursor.execute(f"SELECT {field} FROM players WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()
        
        return result is not None and result[0] > 0
    except Exception as e:
        logger.error(f"Error validating actions left: {e}")
        return False


@db_transaction
def validate_player_exists(player_id: int, conn: Any) -> bool:
    """Validate that a player exists in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM players WHERE player_id = ?", (player_id,))
    return cursor.fetchone() is not None


@db_transaction
def validate_district_exists(district_id: int, conn: Any) -> bool:
    """Validate that a district exists in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM districts WHERE district_id = ?", (district_id,))
    return cursor.fetchone() is not None


@db_transaction
def validate_politician_exists(politician_id: int, conn: Any) -> bool:
    """Validate that a politician exists in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM politicians WHERE politician_id = ?", (politician_id,))
    return cursor.fetchone() is not None


@db_transaction
def validate_resources(player_id: int, resources: Dict[str, int], conn: Any) -> bool:
    """Validate that a player has sufficient resources."""
    cursor = conn.cursor()
    
    # Get current resources
    cursor.execute("""
        SELECT resource_type, amount 
        FROM player_resources 
        WHERE player_id = ?
    """, (player_id,))
    current_resources = dict(cursor.fetchall())
    
    # Check if player has enough of each resource
    for resource_type, amount in resources.items():
        if amount < 0:
            return False
        current_amount = current_resources.get(resource_type, 0)
        if current_amount < amount:
            return False
    
    return True