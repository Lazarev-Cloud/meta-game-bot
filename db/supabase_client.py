#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Full Supabase client implementation with comprehensive API functions.
"""

import logging
import os
from typing import Dict, Any, Optional, List

from supabase import create_client, Client

# Initialize logger
logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client = None


def init_supabase() -> Client:
    """Initialize the Supabase client."""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please check your .env file.")
        raise ValueError("Missing Supabase credentials")

    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise


def get_supabase() -> Client:
    """Get the Supabase client instance."""
    global _supabase_client

    if _supabase_client is None:
        return init_supabase()

    return _supabase_client


async def execute_function(function_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Postgres function through Supabase RPC."""
    client = get_supabase()
    try:
        response = client.rpc(function_name, params).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        raise


# Player-related functions

async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player information by Telegram ID."""
    try:
        return await execute_function("api_get_player_status", {"p_telegram_id": telegram_id})
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
        client.table("players").update(params).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating player: {str(e)}")
        return False


async def delete_player(telegram_id: str) -> bool:
    """Delete a player account (admin only)."""
    try:
        client = get_supabase()
        client.table("players").delete().eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting player: {str(e)}")
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


async def get_player_actions(telegram_id: str, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get a player's actions, optionally filtered by cycle."""
    try:
        client = get_supabase()
        query = client.from_("actions").select("*").eq("player_id", (
            client.from_("players").select("player_id").eq("telegram_id", telegram_id)
        ))

        if cycle_id:
            query = query.eq("cycle_id", cycle_id)

        query = query.order("created_at", desc=True)
        response = query.execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error getting player actions: {str(e)}")
        return []


# District-related functions

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


async def get_district_control(telegram_id: str, district_id: str) -> Dict[str, Any]:
    """Get a player's control in a specific district."""
    try:
        client = get_supabase()
        query = client.from_("district_control").select("*").eq("district_id", district_id).eq("player_id", (
            client.from_("players").select("player_id").eq("telegram_id", telegram_id)
        ))
        response = query.execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return {}
    except Exception as e:
        logger.error(f"Error getting district control: {str(e)}")
        return {}


# Cycle-related functions

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


async def create_news(
        telegram_id: str,
        title: str,
        content: str,
        news_type: str = "faction",
        district_name: Optional[str] = None,
        language: str = "en_US"
) -> bool:
    """Create a news item (faction news only)."""
    try:
        district_id = None
        if district_name:
            district_response = await get_district_by_name(district_name)
            if district_response:
                district_id = district_response.get("district_id")

        player_response = await get_player_by_telegram_id(telegram_id)
        if not player_response:
            return False

        player_id = player_response.get("player_id")

        client = get_supabase()
        cycle_id = (client.from_("cycles").select("cycle_id").eq("is_active", True).limit(1).execute()).data[0][
            "cycle_id"]

        client.from_("news").insert({
            "cycle_id": cycle_id,
            "title": title,
            "content": content,
            "news_type": news_type,
            "target_player_id": player_id if news_type == "faction" else None,
            "related_district_id": district_id,
            "created_by": player_id
        }).execute()

        return True
    except Exception as e:
        logger.error(f"Error creating news: {str(e)}")
        return False


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


async def get_resource_history(telegram_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get resource history for a player."""
    try:
        client = get_supabase()
        query = client.from_("resource_history").select("*").eq("player_id", (
            client.from_("players").select("player_id").eq("telegram_id", telegram_id)
        ))
        query = query.order("created_at", desc=True).limit(limit)
        response = query.execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error getting resource history: {str(e)}")
        return []


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
        query = client.from_("collective_actions").select("""
            collective_action_id,
            action_type,
            district_id (name),
            cycle_id,
            initiator_player_id (name),
            target_player_id (name),
            status,
            created_at
        """).eq("status", "active")
        response = query.execute()

        return response.data or []
    except Exception as e:
        logger.error(f"Error getting active collective actions: {str(e)}")
        return []


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


# Helper query functions

async def player_exists(telegram_id: str) -> bool:
    """Check if a player exists by Telegram ID."""
    try:
        client = get_supabase()
        response = client.rpc(
            "player_exists",
            {"p_telegram_id": telegram_id}
        ).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error checking if player exists: {str(e)}")
        return False


async def get_districts() -> List[Dict[str, Any]]:
    """Get all districts."""
    try:
        client = get_supabase()
        response = client.table("districts").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting districts: {str(e)}")
        return []


async def get_resources(player_id: str) -> Optional[Dict[str, Any]]:
    """Get resources for a player by ID."""
    try:
        client = get_supabase()
        response = client.table("resources").select("*").eq("player_id", player_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting resources: {str(e)}")
        return None


async def get_controlled_districts(player_id: str) -> List[Dict[str, Any]]:
    """Get districts controlled by a player."""
    try:
        client = get_supabase()
        query = client.from_("district_control").select("""
            control_points,
            district_id (
                district_id,
                name,
                influence_resource,
                money_resource,
                information_resource,
                force_resource
            )
        """).eq("player_id", player_id).gte("control_points", 60)
        response = query.execute()

        # Format response
        result = []
        for item in response.data:
            district = item["district_id"]
            result.append({
                "district_id": district["district_id"],
                "district_name": district["name"],
                "control_points": item["control_points"],
                "resource_influence": district["influence_resource"],
                "resource_money": district["money_resource"],
                "resource_information": district["information_resource"],
                "resource_force": district["force_resource"]
            })

        return result
    except Exception as e:
        logger.error(f"Error getting controlled districts: {str(e)}")
        return []


async def get_district_by_name(district_name: str) -> Optional[Dict[str, Any]]:
    """Get district information by name."""
    try:
        client = get_supabase()
        response = client.rpc(
            "get_district_by_name",
            {"p_district_name": district_name}
        ).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting district by name: {str(e)}")
        return None


async def get_politician_by_name(politician_name: str) -> Optional[Dict[str, Any]]:
    """Get politician information by name."""
    try:
        client = get_supabase()
        response = client.rpc(
            "get_politician_by_name",
            {"p_politician_name": politician_name}
        ).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting politician by name: {str(e)}")
        return None


async def is_submission_open() -> bool:
    """Check if submissions are open for the current cycle."""
    try:
        client = get_supabase()
        response = client.rpc("is_submission_open").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error checking if submissions are open: {str(e)}")
        return False


async def get_remaining_actions(player_id: str) -> tuple[int, int]:
    """Get remaining actions for a player."""
    try:
        client = get_supabase()
        response = client.rpc(
            "get_player_actions_remaining",
            {"p_player_id": player_id}
        ).execute()
        data = response.data
        return data.get("remaining_actions", 0), data.get("remaining_quick_actions", 0)
    except Exception as e:
        logger.error(f"Error getting remaining actions: {str(e)}")
        return 0, 0


async def get_player_info(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get full player information from the database."""
    try:
        client = get_supabase()
        response = client.table("players").select("*").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting player info: {str(e)}")
        return None


async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player record by Telegram ID."""
    try:
        client = get_supabase()
        response = client.table("players").select("*").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting player by Telegram ID: {str(e)}")
        return None


async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific collective action by ID."""
    try:
        client = get_supabase()
        response = client.table("collective_actions").select("*").eq("collective_action_id", action_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error getting collective action: {str(e)}")
        return None


async def get_collective_action_participants(action_id: str) -> List[Dict[str, Any]]:
    """Get participants of a collective action."""
    try:
        client = get_supabase()
        response = client.table("collective_action_participants").select("*").eq("collective_action_id",
                                                                                 action_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting collective action participants: {str(e)}")
        return []


async def get_player_politician_relations(player_id: str) -> List[Dict[str, Any]]:
    """Get all politician relations for a player."""
    try:
        client = get_supabase()
        response = client.table("player_politician_relations").select("*").eq("player_id", player_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting player politician relations: {str(e)}")
        return []


async def get_international_effects() -> List[Dict[str, Any]]:
    """Get all active international effects."""
    try:
        client = get_supabase()
        response = client.table("international_effects").select("*").gte("expires_at", "now()").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting international effects: {str(e)}")
        return []


async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set a player's preferred language."""
    try:
        client = get_supabase()
        client.table("players").update({"language": language}).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error setting player language: {str(e)}")
        return False


async def get_player_language(telegram_id: str) -> str:
    """Get a player's preferred language, defaulting to English."""
    try:
        client = get_supabase()
        response = client.table("players").select("language").eq("telegram_id", telegram_id).execute()
        if response.data and response.data[0].get("language"):
            return response.data[0]["language"]
        return "en_US"
    except Exception as e:
        logger.error(f"Error getting player language: {str(e)}")
        return "en_US"
