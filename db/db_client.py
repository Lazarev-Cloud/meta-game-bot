#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Consolidated database client for Meta Game.

This module serves as the primary interface for all database operations,
providing a clean, consistent API and eliminating duplication between
supabase_client.py and queries.py.
"""

import logging
from typing import Dict, Any, Optional, List, Union

# Internal imports from our database modules
from db.supabase_client import (
    init_supabase,
    get_supabase,
    execute_function,
    execute_sql,
    check_schema_exists
)

# Initialize logger
logger = logging.getLogger(__name__)


# ---------------------------
# Player-related functions
# ---------------------------

async def player_exists(telegram_id: str) -> bool:
    """
    Check if a player exists by Telegram ID.

    Args:
        telegram_id: The Telegram ID to check

    Returns:
        True if player exists, False otherwise
    """
    try:
        client = get_supabase()

        # First try using the explicit schema prefix
        try:
            response = client.rpc("game.player_exists", {"p_telegram_id": telegram_id}).execute()
            if hasattr(response, 'data'):
                return response.data
        except Exception:
            # Fallback to direct query if function call fails
            pass

        # Fallback to direct query - Use game schema prefix
        response = client.from_("game.players").select("player_id").eq("telegram_id", telegram_id).execute()
        return hasattr(response, 'data') and len(response.data) > 0
    except Exception as e:
        logger.error(f"Error checking if player exists: {str(e)}")
        return False


async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive player information including resources, actions, etc.

    Args:
        telegram_id: The Telegram ID of the player

    Returns:
        Dictionary with player data or None if player not found
    """
    try:
        result = await execute_function("api_get_player_status", {"p_telegram_id": telegram_id})
        return result
    except Exception as e:
        logger.error(f"Error getting player data: {str(e)}")

        # Fallback to basic query if API function fails
        try:
            client = get_supabase()
            response = client.from_("game.players").select("*").eq("telegram_id", telegram_id).execute()

            if not hasattr(response, 'data') or not response.data:
                return None

            player = response.data[0]

            # Get resources separately
            resources_response = client.from_("game.resources").select("*").eq("player_id",
                                                                               player["player_id"]).execute()
            resources = {}

            if hasattr(resources_response, 'data') and resources_response.data:
                resources_data = resources_response.data[0]
                resources = {
                    "influence": resources_data.get("influence_amount", 0),
                    "money": resources_data.get("money_amount", 0),
                    "information": resources_data.get("information_amount", 0),
                    "force": resources_data.get("force_amount", 0)
                }

            # Format response
            return {
                "player_name": player.get("name", "Unknown"),
                "player_id": player.get("player_id"),
                "ideology_score": player.get("ideology_score", 0),
                "resources": resources,
                "actions_remaining": player.get("remaining_actions", 0),
                "quick_actions_remaining": player.get("remaining_quick_actions", 0),
                "controlled_districts": []
            }
        except Exception as inner_e:
            logger.error(f"Fallback error getting player data: {str(inner_e)}")
            return None


async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """
    Get basic player record by Telegram ID.

    Args:
        telegram_id: The Telegram ID of the player

    Returns:
        Raw player database record or None if not found
    """
    try:
        client = get_supabase()
        response = client.from_("game.players").select("*").eq("telegram_id", telegram_id).execute()

        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting player by Telegram ID: {str(e)}")
        return None


async def register_player(telegram_id: str, name: str, ideology_score: int = 0) -> Dict[str, Any]:
    """
    Register a new player.

    Args:
        telegram_id: The Telegram ID of the player
        name: The player's name
        ideology_score: The player's ideology score (-5 to 5)

    Returns:
        Result of registration containing success status
    """
    try:
        result = await execute_function(
            "api_register_player",
            {
                "p_telegram_id": telegram_id,
                "p_name": name,
                "p_ideology_score": ideology_score
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error registering player: {str(e)}")
        raise


# ---------------------------
# Language & Preferences
# ---------------------------

async def get_player_language(telegram_id: str) -> str:
    """
    Get a player's preferred language.

    Args:
        telegram_id: The Telegram ID of the player

    Returns:
        Language code (e.g., 'en_US', 'ru_RU') or 'en_US' if not set
    """
    try:
        client = get_supabase()
        response = client.from_("game.players").select("language").eq("telegram_id", telegram_id).execute()

        if hasattr(response, 'data') and response.data and response.data[0].get("language"):
            return response.data[0]["language"]
        return "en_US"
    except Exception as e:
        logger.error(f"Error getting player language: {str(e)}")
        return "en_US"


async def set_player_language(telegram_id: str, language: str) -> bool:
    """
    Set a player's preferred language.

    Args:
        telegram_id: The Telegram ID of the player
        language: Language code to set ('en_US', 'ru_RU')

    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_supabase()

        # Check if player exists
        player_response = client.from_("game.players").select("player_id").eq("telegram_id", telegram_id).execute()

        if hasattr(player_response, 'data') and player_response.data:
            # Update language
            client.from_("game.players").update({"language": language}).eq("telegram_id", telegram_id).execute()
            return True

        # Player doesn't exist yet, will be set during registration
        return True
    except Exception as e:
        logger.error(f"Error setting player language: {str(e)}")
        return False


# ---------------------------
# Game cycle and actions
# ---------------------------

async def get_cycle_info(language: str = "en_US") -> Dict[str, Any]:
    """
    Get information about the current game cycle.

    Args:
        language: Language for translations

    Returns:
        Dictionary with cycle information
    """
    try:
        result = await execute_function(
            "api_get_cycle_info",
            {
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting cycle info: {str(e)}")
        return {}


async def is_submission_open() -> bool:
    """
    Check if submissions are open for the current cycle.

    Returns:
        True if submissions are open, False otherwise
    """
    try:
        client = get_supabase()
        response = client.rpc("game.is_submission_open").execute()

        if hasattr(response, 'data'):
            return response.data
        return False
    except Exception as e:
        logger.error(f"Error checking if submissions are open: {str(e)}")
        return False


async def submit_action(
        telegram_id: str,
        action_type: str,
        is_quick_action: bool,
        district_name: Optional[str] = None,
        target_player_name: Optional[str] = None,
        target_politician_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_amount: Optional[int] = None,
        physical_presence: bool = False,
        expected_outcome: Optional[str] = None,
        language: str = "en_US"
) -> Dict[str, Any]:
    """
    Submit a player action.

    Args:
        telegram_id: The Telegram ID of the player
        action_type: Type of action to perform
        is_quick_action: Whether this is a quick action
        district_name: Target district name
        target_player_name: Target player name
        target_politician_name: Target politician name
        resource_type: Type of resource to use
        resource_amount: Amount of resource to use
        physical_presence: Whether player is physically present
        expected_outcome: Expected outcome of the action
        language: Language for translations

    Returns:
        Action submission result
    """
    try:
        result = await execute_function(
            "api_submit_action",
            {
                "p_telegram_id": telegram_id,
                "p_action_type": action_type,
                "p_is_quick_action": is_quick_action,
                "p_district_name": district_name,
                "p_target_player_name": target_player_name,
                "p_target_politician_name": target_politician_name,
                "p_resource_type": resource_type,
                "p_resource_amount": resource_amount,
                "p_physical_presence": physical_presence,
                "p_expected_outcome": expected_outcome,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error submitting action: {str(e)}")
        raise


async def cancel_latest_action(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """
    Cancel the latest action submitted by a player.

    Args:
        telegram_id: The Telegram ID of the player
        language: Language for translations

    Returns:
        Result of cancellation
    """
    try:
        result = await execute_function(
            "api_cancel_latest_action",
            {
                "p_telegram_id": telegram_id,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error canceling action: {str(e)}")
        raise


# ---------------------------
# Districts and map
# ---------------------------

async def get_districts() -> List[Dict[str, Any]]:
    """
    Get all districts.

    Returns:
        List of district information
    """
    try:
        client = get_supabase()
        response = client.from_("game.districts").select("*").execute()

        if hasattr(response, 'data'):
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error getting districts: {str(e)}")
        # Try a fallback approach with raw SQL
        try:
            result = await execute_sql("SELECT * FROM game.districts;")
            if result:
                return result
        except Exception as sql_e:
            logger.error(f"Fallback query failed: {str(sql_e)}")
        return []


async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Dict[str, Any]:
    """
    Get detailed information about a district.

    Args:
        telegram_id: The Telegram ID of the player
        district_name: Name of the district
        language: Language for translations

    Returns:
        District information
    """
    try:
        result = await execute_function(
            "api_get_district_info",
            {
                "p_telegram_id": telegram_id,
                "p_district_name": district_name,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting district info: {str(e)}")
        return {}


async def get_map_data(language: str = "en_US") -> Dict[str, Any]:
    """
    Get the current map data showing district control.

    Args:
        language: Language for translations

    Returns:
        Map data with district control information
    """
    try:
        result = await execute_function(
            "api_get_map_data",
            {
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting map data: {str(e)}")
        return {}


# ---------------------------
# Resources and Economy
# ---------------------------

async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Dict[str, Any]:
    """
    Exchange resources between types.

    Args:
        telegram_id: The Telegram ID of the player
        from_resource: Resource type to convert from
        to_resource: Resource type to convert to
        amount: Amount to convert
        language: Language for translations

    Returns:
        Result of exchange
    """
    try:
        result = await execute_function(
            "api_exchange_resources",
            {
                "p_telegram_id": telegram_id,
                "p_from_resource": from_resource,
                "p_to_resource": to_resource,
                "p_amount": amount,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error exchanging resources: {str(e)}")
        raise


async def check_income(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """
    Check expected resource income.

    Args:
        telegram_id: The Telegram ID of the player
        language: Language for translations

    Returns:
        Expected income information
    """
    try:
        result = await execute_function(
            "api_check_income",
            {
                "p_telegram_id": telegram_id,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error checking income: {str(e)}")
        return {}


# ---------------------------
# News and Information
# ---------------------------

async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Dict[str, Any]:
    """
    Get the latest news for a player.

    Args:
        telegram_id: The Telegram ID of the player
        count: Number of news items to retrieve
        language: Language for translations

    Returns:
        Latest news
    """
    try:
        result = await execute_function(
            "api_get_latest_news",
            {
                "p_telegram_id": telegram_id,
                "p_count": count,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting news: {str(e)}")
        return {"public": [], "faction": []}


# ---------------------------
# Politicians
# ---------------------------

async def get_politicians(telegram_id: str, type: str = "local", language: str = "en_US") -> Dict[str, Any]:
    """
    Get politicians of specified type.

    Args:
        telegram_id: The Telegram ID of the player
        type: Type of politicians to get ('local', 'international', 'all')
        language: Language for translations

    Returns:
        Politicians information
    """
    try:
        result = await execute_function(
            "api_get_politicians",
            {
                "p_telegram_id": telegram_id,
                "p_type": type,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting politicians: {str(e)}")
        return {"politicians": []}


async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Dict[str, Any]:
    """
    Get detailed information about a politician.

    Args:
        telegram_id: The Telegram ID of the player
        politician_name: Name of the politician
        language: Language for translations

    Returns:
        Politician information
    """
    try:
        result = await execute_function(
            "api_get_politician_status",
            {
                "p_telegram_id": telegram_id,
                "p_politician_name": politician_name,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error getting politician status: {str(e)}")
        return {}


# ---------------------------
# Collective Actions
# ---------------------------

async def initiate_collective_action(
        telegram_id: str,
        action_type: str,
        district_name: str,
        target_player_name: Optional[str] = None,
        resource_type: str = "influence",
        resource_amount: int = 1,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Dict[str, Any]:
    """
    Initiate a collective action.

    Args:
        telegram_id: The Telegram ID of the initiator
        action_type: Type of collective action
        district_name: Target district
        target_player_name: Target player (for attacks)
        resource_type: Type of resource to contribute
        resource_amount: Amount of resource to contribute
        physical_presence: Whether player is physically present
        language: Language for translations

    Returns:
        Result of collective action initiation
    """
    try:
        result = await execute_function(
            "api_initiate_collective_action",
            {
                "p_telegram_id": telegram_id,
                "p_action_type": action_type,
                "p_district_name": district_name,
                "p_target_player_name": target_player_name,
                "p_resource_type": resource_type,
                "p_resource_amount": resource_amount,
                "p_physical_presence": physical_presence,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error initiating collective action: {str(e)}")
        raise


async def join_collective_action(
        telegram_id: str,
        collective_action_id: str,
        resource_type: str,
        resource_amount: int,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Dict[str, Any]:
    """
    Join a collective action.

    Args:
        telegram_id: The Telegram ID of the player
        collective_action_id: ID of the collective action
        resource_type: Type of resource to contribute
        resource_amount: Amount of resource to contribute
        physical_presence: Whether player is physically present
        language: Language for translations

    Returns:
        Result of joining collective action
    """
    try:
        result = await execute_function(
            "api_join_collective_action",
            {
                "p_telegram_id": telegram_id,
                "p_collective_action_id": collective_action_id,
                "p_resource_type": resource_type,
                "p_resource_amount": resource_amount,
                "p_physical_presence": physical_presence,
                "p_language": language
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error joining collective action: {str(e)}")
        raise


async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """
    Get all active collective actions.

    Returns:
        List of active collective actions
    """
    try:
        client = get_supabase()
        response = client.from_("game.collective_actions").select("*").eq("status", "active").execute()

        if hasattr(response, 'data'):
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error getting active collective actions: {str(e)}")
        return []


async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """
    Get details of a specific collective action.

    Args:
        action_id: ID of the collective action

    Returns:
        Collective action details or None if not found
    """
    try:
        client = get_supabase()
        response = client.from_("game.collective_actions").select("*").eq("collective_action_id", action_id).execute()

        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting collective action: {str(e)}")
        return None


# ---------------------------
# Admin Functions
# ---------------------------

async def admin_process_actions(telegram_id: str) -> Dict[str, Any]:
    """
    Process all pending actions (admin only).

    Args:
        telegram_id: The Telegram ID of the admin

    Returns:
        Result of processing actions
    """
    try:
        result = await execute_function(
            "api_admin_process_actions",
            {
                "p_telegram_id": telegram_id
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error processing actions: {str(e)}")
        raise


async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Dict[str, Any]:
    """
    Generate international effects (admin only).

    Args:
        telegram_id: The Telegram ID of the admin
        count: Number of effects to generate

    Returns:
        Result of generating effects
    """
    try:
        result = await execute_function(
            "api_admin_generate_international_effects",
            {
                "p_telegram_id": telegram_id,
                "p_count": count
            }
        )
        return result
    except Exception as e:
        logger.error(f"Error generating international effects: {str(e)}")
        raise