#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database query helpers for common operations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from db.supabase_client import get_supabase

# Initialize logger
logger = logging.getLogger(__name__)


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
        response = client.rpc(
            "get_player_controlled_districts",
            {"p_player_id": player_id}
        ).execute()
        return response.data
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


async def get_remaining_actions(player_id: str) -> Tuple[int, int]:
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


async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """Get all active collective actions."""
    try:
        client = get_supabase()
        response = client.table("collective_actions").select("*").eq("status", "active").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error getting active collective actions: {str(e)}")
        return []


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
