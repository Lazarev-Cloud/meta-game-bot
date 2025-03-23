#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete Supabase client implementation for the Meta Game bot.
"""

import logging
import os
from typing import Dict, Any, Optional, List, Union

from supabase import create_client, Client

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
        # Create client without the problematic options
        _supabase_client = create_client(supabase_url, supabase_key)
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
    """Execute a Postgres function through Supabase RPC."""
    client = get_supabase()
    try:
        # Properly prefix the function name with schema
        if not function_name.startswith("game."):
            function_name = f"game.{function_name}"

        response = client.rpc(function_name, params).execute()

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
    """Check if the game schema exists using a more portable approach."""
    try:
        # Use information_schema instead of pg_catalog
        query = """
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.schemata 
            WHERE schema_name = 'game'
        );
        """

        result = await execute_sql(query)
        if result and result[0] and 'exists' in result[0]:
            exists = result[0]['exists']
            logger.info(f"Game schema exists: {exists}")
            return exists
        return False
    except Exception as e:
        logger.error(f"Error checking if schema exists: {str(e)}")
        return False


async def execute_sql(sql: str) -> Any:
    """Execute a raw SQL query."""
    client = get_supabase()
    try:
        response = client.rpc("exec_sql", {"sql": sql}).execute()
        if hasattr(response, 'data'):
            return response.data
        return None
    except Exception as e:
        logger.error(f"Error executing SQL: {str(e)}")
        raise


# Player-related functions

async def player_exists(telegram_id: str) -> bool:
    """Check if a player exists by Telegram ID."""
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
    """Get player information by Telegram ID."""
    try:
        result = await execute_function("api_get_player_status", {"p_telegram_id": telegram_id})
        return result
    except Exception as e:
        logger.error(f"Error getting player data: {str(e)}")

        # Fallback to basic query if API function fails
        try:
            client = get_supabase()
            # FIXED: Use from_ instead of table
            response = client.from_("players").select("*").eq("telegram_id", telegram_id).execute()

            if not hasattr(response, 'data') or not response.data:
                return None

            player = response.data[0]

            # Get resources separately
            # FIXED: Use from_ instead of table
            resources_response = client.from_("resources").select("*").eq("player_id", player["player_id"]).execute()
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
    """Get player by Telegram ID directly."""
    try:
        client = get_supabase()
        # Use game schema prefix
        response = client.from_("game.players").select("*").eq("telegram_id", telegram_id).execute()

        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting player by Telegram ID: {str(e)}")
        return None


async def register_player(telegram_id: str, name: str, ideology_score: int = 0) -> Dict[str, Any]:
    """Register a new player."""
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
    """Cancel the latest action submitted by a player."""
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


async def get_districts() -> List[Dict[str, Any]]:
    """Get all districts."""
    try:
        client = get_supabase()
        # Use correct table reference without public prefix
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
    """Get information about a district."""
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


async def get_cycle_info(language: str = "en_US") -> Dict[str, Any]:
    """Get information about the current game cycle."""
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


async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Dict[str, Any]:
    """Get the latest news for a player."""
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


async def get_map_data(language: str = "en_US") -> Dict[str, Any]:
    """Get the current map data showing district control."""
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


async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Dict[str, Any]:
    """Exchange resources."""
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
    """Check expected resource income."""
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


async def get_politicians(telegram_id: str, type: str = "local", language: str = "en_US") -> Dict[str, Any]:
    """Get politicians of specified type."""
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
    """Get detailed information about a politician."""
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
    """Join a collective action."""
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
    """Get all active collective actions."""
    try:
        client = get_supabase()
        # Use game schema prefix
        response = client.from_("game.collective_actions").select("*").eq("status", "active").execute()

        if hasattr(response, 'data'):
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error getting active collective actions: {str(e)}")
        return []


async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific collective action."""
    try:
        client = get_supabase()
        # Use game schema prefix
        response = client.from_("game.collective_actions").select("*").eq("collective_action_id", action_id).execute()

        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting collective action: {str(e)}")
        return None

async def get_player_language(telegram_id: str) -> str:
    """Get a player's preferred language."""
    try:
        client = get_supabase()
        # Use game schema prefix
        response = client.from_("game.players").select("language").eq("telegram_id", telegram_id).execute()

        if hasattr(response, 'data') and response.data and response.data[0].get("language"):
            return response.data[0]["language"]
        return "en_US"
    except Exception as e:
        logger.error(f"Error getting player language: {str(e)}")
        return "en_US"


async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set a player's preferred language."""
    try:
        client = get_supabase()

        # Check if player exists
        # Use game schema prefix
        player_response = client.from_("game.players").select("player_id").eq("telegram_id", telegram_id).execute()

        if hasattr(player_response, 'data') and player_response.data:
            # Update language
            # Use game schema prefix
            client.from_("game.players").update({"language": language}).eq("telegram_id", telegram_id).execute()
            return True

        # Player doesn't exist yet, will be set during registration
        return True
    except Exception as e:
        logger.error(f"Error setting player language: {str(e)}")
        return False

async def admin_process_actions(telegram_id: str) -> Dict[str, Any]:
    """Process all pending actions (admin only)."""
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
    """Generate international effects (admin only)."""
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


# Additional utility functions

async def get_remaining_actions(player_id: str) -> tuple:
    """Get remaining actions for a player."""
    try:
        client = get_supabase()
        response = client.rpc(
            "game.get_player_actions_remaining",
            {"p_player_id": player_id}
        ).execute()

        if hasattr(response, 'data'):
            data = response.data
            return data.get("remaining_actions", 0), data.get("remaining_quick_actions", 0)
        return 0, 0
    except Exception as e:
        logger.error(f"Error getting remaining actions: {str(e)}")
        return 0, 0