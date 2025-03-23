#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Supabase client implementation with proper schema handling and error recovery.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Initialize logger
logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client = None


def init_supabase() -> Client:
    """Initialize the Supabase client with proper configuration."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please check your .env file.")
        raise ValueError("Missing Supabase credentials")

    try:
        # Create client with proper options to handle timeouts and retries
        options = ClientOptions(
            schema="game",  # Explicitly set schema to 'game'
            headers={"X-Client-Info": "meta-game-bot"},
            auto_refresh_token=True,
            persist_session=True,
            timeout=10  # 10 second timeout
        )

        _supabase_client = create_client(supabase_url, supabase_key, options=options)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise


def get_supabase() -> Client:
    """Get the Supabase client instance, initializing if necessary."""
    global _supabase_client

    if _supabase_client is None:
        return init_supabase()

    return _supabase_client


async def execute_function(function_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a Postgres function through Supabase RPC with proper error handling.

    Args:
        function_name: The name of the function to execute (without schema prefix)
        params: The parameters to pass to the function

    Returns:
        The response data from the function

    Raises:
        Exception: If there was an error executing the function
    """
    client = get_supabase()
    try:
        # Use complete schema prefix for RPC function
        schema_function_name = f"game.{function_name}" if not function_name.startswith("game.") else function_name

        # Execute RPC with proper error handling
        response = client.rpc(schema_function_name, params).execute()

        # Check if response has data attribute
        if hasattr(response, 'data'):
            return response.data
        elif hasattr(response, 'json'):
            return response.json()
        else:
            logger.warning(f"Unexpected response format from function {function_name}")
            return {}
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        raise


async def check_schema_exists() -> bool:
    """
    Check if the game schema exists in the database.

    Returns:
        True if the schema exists, False otherwise
    """
    client = get_supabase()
    try:
        # Query to check if schema exists using a direct SQL query
        response = client.table("_schemas").select("*").eq("name", "game").execute()

        # Check if we got any results
        if hasattr(response, 'data') and response.data:
            return True

        # Try direct SQL for more reliability
        sql_response = client.from_("pg_namespace").select("nspname").eq("nspname", "game").execute()

        if hasattr(sql_response, 'data') and sql_response.data:
            return True

        return False
    except Exception as e:
        logger.error(f"Error checking if schema exists: {str(e)}")
        return False


async def execute_sql(sql: str) -> Any:
    """
    Execute a raw SQL query - use with caution and proper input validation.

    Args:
        sql: The SQL query to execute

    Returns:
        The response data
    """
    client = get_supabase()
    try:
        # Use a special RPC function to execute arbitrary SQL
        # This requires the 'exec_sql' function to be defined in your database
        response = client.rpc("exec_sql", {"sql": sql}).execute()

        if hasattr(response, 'data'):
            return response.data
        else:
            return None
    except Exception as e:
        logger.error(f"Error executing SQL: {str(e)}")
        raise


# Player-related functions with proper schema handling

async def player_exists(telegram_id: str) -> bool:
    """Check if a player exists by Telegram ID."""
    try:
        client = get_supabase()

        # Try to use the RPC function first
        try:
            response = client.rpc(
                "game.player_exists",
                {"p_telegram_id": telegram_id}
            ).execute()

            if hasattr(response, 'data'):
                return response.data
        except Exception as rpc_error:
            logger.warning(f"RPC error in player_exists: {str(rpc_error)}, falling back to direct query")

        # Fallback to direct table query if RPC fails
        response = client.from_("game.players").select("player_id").eq("telegram_id", telegram_id).execute()

        if hasattr(response, 'data'):
            return len(response.data) > 0

        return False
    except Exception as e:
        logger.error(f"Error checking if player exists: {str(e)}")
        return False


async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player information by Telegram ID."""
    try:
        # First try the API function
        try:
            return await execute_function("api_get_player_status", {"p_telegram_id": telegram_id})
        except Exception as api_error:
            logger.warning(f"API error in get_player: {str(api_error)}, falling back to direct query")

        # Fallback to direct query if API fails
        client = get_supabase()
        response = client.from_("game.players").select("*").eq("telegram_id", telegram_id).execute()

        if hasattr(response, 'data') and response.data:
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

            # Format the response to match API output
            return {
                "player_name": player.get("name", "Unknown"),
                "player_id": player.get("player_id"),
                "ideology_score": player.get("ideology_score", 0),
                "resources": resources,
                "actions_remaining": player.get("remaining_actions", 0),
                "quick_actions_remaining": player.get("remaining_quick_actions", 0),
                "controlled_districts": []  # Would need another query to get this
            }

        return None
    except Exception as e:
        logger.error(f"Error getting player data: {str(e)}")
        return None


async def register_player(telegram_id: str, name: str, ideology_score: int = 0) -> Dict[str, Any]:
    """Register a new player."""
    try:
        return await execute_function(
            "api_register_player",
            {
                "p_telegram_id": telegram_id,
                "p_name": name,
                "p_ideology_score": ideology_score
            }
        )
    except Exception as e:
        logger.error(f"Error registering player: {str(e)}")
        raise


async def update_player(telegram_id: str, params: Dict[str, Any]) -> bool:
    """Update player information."""
    try:
        client = get_supabase()
        response = client.from_("game.players").update(params).eq("telegram_id", telegram_id).execute()
        return hasattr(response, 'data')
    except Exception as e:
        logger.error(f"Error updating player: {str(e)}")
        return False


# Action-related functions

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
    """Submit an action."""
    try:
        return await execute_function(
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
    except Exception as e:
        logger.error(f"Error submitting action: {str(e)}")
        raise


async def cancel_latest_action(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """Cancel the latest action submitted by a player."""
    try:
        return await execute_function(
            "api_cancel_latest_action",
            {
                "p_telegram_id": telegram_id,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error canceling action: {str(e)}")
        raise


# District-related functions

async def get_districts() -> List[Dict[str, Any]]:
    """Get all districts."""
    try:
        client = get_supabase()
        response = client.from_("game.districts").select("*").execute()

        if hasattr(response, 'data'):
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error getting districts: {str(e)}")
        return []


async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Dict[str, Any]:
    """Get information about a district."""
    try:
        return await execute_function(
            "api_get_district_info",
            {
                "p_telegram_id": telegram_id,
                "p_district_name": district_name,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error getting district info: {str(e)}")
        return {}


# Game cycle functions

async def get_cycle_info(language: str = "en_US") -> Dict[str, Any]:
    """Get information about the current game cycle."""
    try:
        return await execute_function(
            "api_get_cycle_info",
            {
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error getting cycle info: {str(e)}")
        return {}


async def is_submission_open() -> bool:
    """Check if submissions are open for the current cycle."""
    try:
        client = get_supabase()
        response = client.rpc("game.is_submission_open").execute()

        if hasattr(response, 'data'):
            return response.data
        return False
    except Exception as e:
        logger.error(f"Error checking if submissions are open: {str(e)}")
        return False


# News-related functions

async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Dict[str, Any]:
    """Get the latest news for a player."""
    try:
        return await execute_function(
            "api_get_latest_news",
            {
                "p_telegram_id": telegram_id,
                "p_count": count,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error getting news: {str(e)}")
        return {"public": [], "faction": []}


# Map data function

async def get_map_data(language: str = "en_US") -> Dict[str, Any]:
    """Get the current map data showing district control."""
    try:
        return await execute_function(
            "api_get_map_data",
            {
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error getting map data: {str(e)}")
        return {}


# Resource-related functions

async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Dict[str, Any]:
    """Exchange resources."""
    try:
        return await execute_function(
            "api_exchange_resources",
            {
                "p_telegram_id": telegram_id,
                "p_from_resource": from_resource,
                "p_to_resource": to_resource,
                "p_amount": amount,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error exchanging resources: {str(e)}")
        raise


async def check_income(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """Check expected resource income."""
    try:
        return await execute_function(
            "api_check_income",
            {
                "p_telegram_id": telegram_id,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error checking income: {str(e)}")
        return {}


# Politician-related functions

async def get_politicians(telegram_id: str, type: str = "local", language: str = "en_US") -> Dict[str, Any]:
    """Get politicians of specified type."""
    try:
        return await execute_function(
            "api_get_politicians",
            {
                "p_telegram_id": telegram_id,
                "p_type": type,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error getting politicians: {str(e)}")
        return {"politicians": []}


async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Dict[str, Any]:
    """Get detailed information about a politician."""
    try:
        return await execute_function(
            "api_get_politician_status",
            {
                "p_telegram_id": telegram_id,
                "p_politician_name": politician_name,
                "p_language": language
            }
        )
    except Exception as e:
        logger.error(f"Error getting politician status: {str(e)}")
        return {}


# Collective action functions

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
    """Initiate a collective action."""
    try:
        return await execute_function(
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
    """Join a collective action."""
    try:
        return await execute_function(
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
    except Exception as e:
        logger.error(f"Error joining collective action: {str(e)}")
        raise


async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """Get all active collective actions."""
    try:
        client = get_supabase()
        query = client.from_("game.collective_actions").select("*").eq("status", "active").execute()

        if hasattr(query, 'data'):
            return query.data
        return []
    except Exception as e:
        logger.error(f"Error getting active collective actions: {str(e)}")
        return []


# Language-related functions

async def get_player_language(telegram_id: str) -> str:
    """Get a player's preferred language."""
    try:
        client = get_supabase()
        try:
            response = client.from_("game.players").select("language").eq("telegram_id", telegram_id).execute()

            if hasattr(response, 'data') and response.data and response.data[0].get("language"):
                return response.data[0]["language"]
        except Exception as table_error:
            logger.warning(f"Couldn't retrieve language preference: {table_error}")

        # Default to English if no language preference or error
        return "en_US"
    except Exception as e:
        logger.error(f"Error getting player language: {str(e)}")
        return "en_US"


async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set a player's preferred language."""
    try:
        client = get_supabase()

        # First check if player exists
        player_response = client.from_("game.players").select("player_id").eq("telegram_id", telegram_id).execute()

        if hasattr(player_response, 'data') and player_response.data:
            # Player exists, update language
            update_response = client.from_("game.players").update({"language": language}).eq("telegram_id",
                                                                                             telegram_id).execute()
            return hasattr(update_response, 'data')

        # Player doesn't exist yet, will be set during registration
        return True
    except Exception as e:
        logger.error(f"Error setting player language: {str(e)}")
        return False


# Admin functions

async def admin_process_actions(telegram_id: str) -> Dict[str, Any]:
    """Process all pending actions (admin only)."""
    try:
        return await execute_function(
            "api_admin_process_actions",
            {
                "p_telegram_id": telegram_id
            }
        )
    except Exception as e:
        logger.error(f"Error processing actions: {str(e)}")
        raise


async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Dict[str, Any]:
    """Generate international effects (admin only)."""
    try:
        return await execute_function(
            "api_admin_generate_international_effects",
            {
                "p_telegram_id": telegram_id,
                "p_count": count
            }
        )
    except Exception as e:
        logger.error(f"Error generating international effects: {str(e)}")
        raise