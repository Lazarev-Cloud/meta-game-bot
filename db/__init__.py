"""
Database module for the Meta Game bot.

This module provides a unified API for database operations and initializes
required components with a design that prevents circular imports.
"""

import logging
import asyncio
from typing import Dict, Any, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# First, import core database functions that don't depend on i18n
from db.supabase_client import (
    init_supabase,
    get_supabase,
    execute_function,
    execute_sql,
    check_schema_exists
)

# Memory cache for database results
_memory_cache = {}

# Basic stub functions that will be replaced when initialize_db is called
async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Stub function for getting player by telegram ID."""
    client = get_supabase()
    try:
        response = client.table("players").select("*").eq("telegram_id", telegram_id).limit(1).execute()
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error in get_player_by_telegram_id: {e}")
        return None


async def player_exists(telegram_id: str) -> bool:
    """Check if player exists with memory fallback."""
    # Check memory cache first for reliability
    from utils.context_manager import context_manager
    if context_manager.get(telegram_id, "is_registered", False):
        return True

    # Then try database
    client = get_supabase()
    try:
        response = client.table("players").select("telegram_id").eq("telegram_id", telegram_id).limit(1).execute()
        exists = hasattr(response, 'data') and len(response.data) > 0
        if exists:
            context_manager.set(telegram_id, "is_registered", True)
        return exists
    except Exception as e:
        logger.error(f"Error checking player: {e}")
        return context_manager.get(telegram_id, "is_registered", False)

async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player data."""
    player = await get_player_by_telegram_id(telegram_id)
    if player:
        # Add basic resources structure
        player['resources'] = {
            'influence': 0,
            'money': 0,
            'information': 0,
            'force': 0
        }

        # Try to get actual resources
        try:
            client = get_supabase()
            response = client.table("resources").select("*").eq("player_id", player.get("player_id")).limit(1).execute()
            if hasattr(response, 'data') and response.data:
                resources = response.data[0]
                player['resources'] = {
                    'influence': resources.get('influence_amount', 0),
                    'money': resources.get('money_amount', 0),
                    'information': resources.get('information_amount', 0),
                    'force': resources.get('force_amount', 0)
                }
        except Exception as e:
            logger.warning(f"Could not get player resources: {e}")

    return player

async def admin_process_actions(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Process all pending actions (admin only)."""
    # Check if user is admin
    player = await get_player_by_telegram_id(telegram_id)
    if not player or not player.get("is_admin", False):
        return {"success": False, "message": "Unauthorized: Admin privileges required"}

    # In a real implementation, we would process actions here
    # For now, just return success
    return {
        "success": True,
        "actions_processed": 0,
        "collective_actions_processed": 0
    }


async def register_player(telegram_id: str, name: str, ideology_score: int, language: str = "en_US") -> Optional[
    Dict[str, Any]]:
    """Register a new player with existing schema."""
    client = get_supabase()
    try:
        # Check if player already exists
        if await player_exists(telegram_id):
            return await get_player(telegram_id)

        # Create new player - WITHOUT language field
        player_data = {
            "telegram_id": telegram_id,
            "name": name,
            "ideology_score": ideology_score
            # Remove language field since it doesn't exist
        }

        # Store registration in memory cache as backup
        from utils.context_manager import context_manager
        context_manager.set(telegram_id, "is_registered", True)
        context_manager.set(telegram_id, "player_name", name)
        context_manager.set(telegram_id, "language", language)

        # Try database insertion
        response = client.table("players").insert(player_data).execute()

        if hasattr(response, 'data') and response.data:
            new_player = response.data[0]

            # Create initial resources
            try:
                resource_data = {
                    "player_id": new_player.get("player_id"),
                    "influence_amount": 5,
                    "money_amount": 10,
                    "information_amount": 3,
                    "force_amount": 2
                }
                client.table("resources").insert(resource_data).execute()
            except Exception as e:
                logger.warning(f"Could not create resources: {e}")

            return await get_player(telegram_id)
        return {"player_name": name, "ideology_score": ideology_score}
    except Exception as e:
        logger.error(f"Error registering player: {e}")
        # Return memory-based info even if DB fails
        return {"player_name": name, "ideology_score": ideology_score}

# Add stub implementations for other required functions
async def get_cycle_info(language: str = "en_US"):
    return {"cycle_type": "morning", "is_accepting_submissions": True}

async def is_submission_open():
    return True

async def submit_action(*args, **kwargs):
    return {"success": True, "message": "Action submitted"}

async def cancel_latest_action(*args, **kwargs):
    return {"success": True}

async def get_districts():
    return []

async def get_district_info(*args, **kwargs):
    return {}

async def get_map_data(*args, **kwargs):
    return {"districts": []}

async def exchange_resources(*args, **kwargs):
    return {"success": True}

async def check_income(*args, **kwargs):
    return {"district_income": [], "totals": {}}

async def get_latest_news(*args, **kwargs):
    return {"public": [], "faction": []}

async def get_politicians(*args, **kwargs):
    return {"politicians": []}

async def get_politician_status(*args, **kwargs):
    return {}

async def initiate_collective_action(*args, **kwargs):
    return {"success": True}

async def join_collective_action(*args, **kwargs):
    return {"success": True}

async def get_active_collective_actions():
    return []

async def get_collective_action(*args):
    return {}

async def admin_generate_international_effects(*args, **kwargs):
    return {"success": True}

async def get_player_language(telegram_id: str) -> str:
    """Get player language."""
    player = await get_player_by_telegram_id(telegram_id)
    if player and "language" in player:
        return player["language"]
    return "en_US"

async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set player language."""
    if language not in ["en_US", "ru_RU"]:
        return False

    client = get_supabase()
    try:
        # First check if player exists
        if not await player_exists(telegram_id):
            return False

        client.table("players").update({"language": language}).eq("telegram_id", telegram_id).execute()
        return True
    except Exception as e:
        logger.warning(f"Could not set player language: {e}")
        return False

def initialize_db():
    """Initialize database functions and prevent circular imports."""
    logger.info("Initializing database module")

    # Return the functions dictionary
    return {
        'player_exists': player_exists,
        'get_player': get_player,
        'get_player_by_telegram_id': get_player_by_telegram_id,
        'register_player': register_player,
        'get_player_language': get_player_language,
        'set_player_language': set_player_language,
        'get_cycle_info': get_cycle_info,
        'is_submission_open': is_submission_open,
        'submit_action': submit_action,
        'cancel_latest_action': cancel_latest_action,
        'get_districts': get_districts,
        'get_district_info': get_district_info,
        'get_map_data': get_map_data,
        'exchange_resources': exchange_resources,
        'check_income': check_income,
        'get_latest_news': get_latest_news,
        'get_politicians': get_politicians,
        'get_politician_status': get_politician_status,
        'initiate_collective_action': initiate_collective_action,
        'join_collective_action': join_collective_action,
        'get_active_collective_actions': get_active_collective_actions,
        'get_collective_action': get_collective_action,
        'admin_process_actions': admin_process_actions,
        'admin_generate_international_effects': admin_generate_international_effects
    }