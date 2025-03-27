"""
Database module for the Meta Game bot.

This module provides a unified API for database operations with improved error handling
and memory fallbacks to ensure the bot can function even with temporary database issues.
"""

import logging
import asyncio
import random
from typing import Dict, Any, Optional, List, TypeVar, Callable, Awaitable, Union, Tuple

# Initialize logger
logger = logging.getLogger(__name__)

# Import core database functions
from db.supabase_client import (
    init_supabase,
    get_supabase,
    execute_function,
    execute_sql,
    check_schema_exists
)

# Type variable for generic return type
T = TypeVar('T')

# Configuration for retry mechanism
MAX_RETRIES = 3
RETRY_DELAY = 1.5  # seconds


# Error handling decorator for database operations
def db_retry(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Decorator to retry database operations with exponential backoff."""

    async def wrapper(*args, **kwargs) -> T:
        retries = 0
        last_exception = None

        while retries < MAX_RETRIES:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                retries += 1

                logger.warning(
                    f"Database operation '{func.__name__}' failed (attempt {retries}/{MAX_RETRIES}): {str(e)}"
                )

                if retries < MAX_RETRIES:
                    # Exponential backoff with jitter for retries
                    delay = RETRY_DELAY * (2 ** (retries - 1)) * (0.9 + 0.2 * random.random())
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Database operation '{func.__name__}' failed after {MAX_RETRIES} attempts: {str(e)}")

        # Return None on complete failure
        return None

    return wrapper


# Player-related functions
@db_retry
async def player_exists(telegram_id: str) -> bool:
    """Check if player exists with memory fallback."""
    # Check memory cache first for reliability
    from utils.context_manager import context_manager
    if context_manager.get(telegram_id, "is_registered", False):
        return True

    # Then try database
    try:
        client = get_supabase()
        response = client.table("players").select("telegram_id").eq("telegram_id", telegram_id).limit(1).execute()
        exists = hasattr(response, 'data') and len(response.data) > 0
        if exists:
            context_manager.set(telegram_id, "is_registered", True)
        return exists
    except Exception as e:
        logger.error(f"Error checking player: {e}")
        return context_manager.get(telegram_id, "is_registered", False)


@db_retry
async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player by telegram ID."""
    try:
        client = get_supabase()
        response = client.table("players").select("*").eq("telegram_id", telegram_id).limit(1).execute()
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Error in get_player_by_telegram_id: {e}")
        return None


@db_retry
async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player data with resources."""
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


@db_retry
async def register_player(telegram_id: str, name: str, ideology_score: int, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Register a new player with better error handling."""
    logger.info(f"Registering player: {telegram_id}, {name}")

    # Store in memory first for resilience
    from utils.context_manager import context_manager
    context_manager.set(telegram_id, "is_registered", True)
    context_manager.set(telegram_id, "language", language)
    context_manager.set(telegram_id, "player_data", {
        "player_name": name,
        "ideology_score": ideology_score,
        "language": language,
        "resources": {"influence": 5, "money": 10, "information": 3, "force": 2}
    })

    try:
        # Attempt database registration
        client = get_supabase()
        player_data = {
            "telegram_id": telegram_id,
            "name": name,
            "ideology_score": ideology_score,
            "language": language
        }

        response = client.table("players").insert(player_data).execute()

        if response and hasattr(response, 'data') and response.data:
            return response.data[0]
        return context_manager.get(telegram_id, "player_data")
    except Exception as e:
        logger.error(f"Database registration failed: {e}")
        return context_manager.get(telegram_id, "player_data")


@db_retry
async def get_player_language(telegram_id: str) -> str:
    """Get player language with memory fallback."""
    # Check memory cache first
    from utils.context_manager import context_manager
    cached_language = context_manager.get(telegram_id, "language")
    if cached_language in ["en_US", "ru_RU"]:
        return cached_language

    # Try database as fallback
    try:
        client = get_supabase()
        response = client.table("players").select("language").eq("telegram_id", telegram_id).limit(1).execute()

        if hasattr(response, 'data') and response.data and len(response.data) > 0:
            language = response.data[0].get("language")
            if language in ["en_US", "ru_RU"]:
                context_manager.set(telegram_id, "language", language)
                return language
    except Exception as e:
        logger.warning(f"Database language lookup failed: {e}")

    # Default fallback
    return "en_US"


@db_retry
async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set player language with improved error handling."""
    if language not in ["en_US", "ru_RU"]:
        return False

    # Update memory cache immediately
    from utils.context_manager import context_manager
    context_manager.set(telegram_id, "language", language)

    # Try database update
    try:
        client = get_supabase()
        # Check if player exists before updating
        exists = await player_exists(telegram_id)

        if exists:
            # Use table access method properly
            update_query = client.table("players").update({"language": language})
            update_query = update_query.eq("telegram_id", telegram_id)
            update_query.execute()
            return True
    except Exception as e:
        logger.warning(f"Database language update failed: {e}")

    # Return true since we at least updated the cache
    return True


# Game state functions
@db_retry
async def get_cycle_info(language: str = "en_US") -> Dict[str, Any]:
    """Get current game cycle information."""
    try:
        result = await execute_function("api_get_cycle_info", {"p_language": language})
        if result:
            return result
    except Exception as e:
        logger.error(f"Error getting cycle info: {e}")

    # Fallback data if database fails
    return {
        "cycle_type": "morning",
        "cycle_date": "2023-01-01",
        "submission_deadline": "12:00",
        "results_time": "13:00",
        "time_to_deadline": "01:00:00",
        "time_to_results": "02:00:00",
        "is_accepting_submissions": True
    }


@db_retry
async def is_submission_open() -> bool:
    """Check if submissions are open for the current cycle."""
    try:
        result = await execute_function("is_submission_open", {})
        if isinstance(result, bool):
            return result
        return bool(result)
    except Exception as e:
        logger.error(f"Error checking submission status: {e}")
        return True  # Default to open if check fails


@db_retry
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
) -> Optional[Dict[str, Any]]:
    """Submit a game action."""
    params = {
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

    try:
        result = await execute_function("api_submit_action", params)
        return result
    except Exception as e:
        logger.error(f"Error submitting action: {e}")

        # Create minimal error response as fallback
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "action_type": action_type
        }


@db_retry
async def cancel_latest_action(telegram_id: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Cancel the latest action."""
    params = {
        "p_telegram_id": telegram_id,
        "p_language": language
    }

    try:
        return await execute_function("api_cancel_latest_action", params)
    except Exception as e:
        logger.error(f"Error canceling action: {e}")
        return {"success": False, "message": str(e)}


# District and map functions
@db_retry
async def get_districts() -> List[Dict[str, Any]]:
    """Get all districts."""
    try:
        # Try direct query first
        result = await execute_sql("SELECT * FROM districts ORDER BY name")
        if result and isinstance(result, list):
            return result

        # Try getting via the client
        client = get_supabase()
        response = client.table("districts").select("*").order("name").execute()
        if hasattr(response, 'data'):
            return response.data
    except Exception as e:
        logger.error(f"Error getting districts: {e}")

    # Return empty list as fallback
    return []


@db_retry
async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get detailed information about a district."""
    params = {
        "p_telegram_id": telegram_id,
        "p_district_name": district_name,
        "p_language": language
    }

    try:
        return await execute_function("api_get_district_info", params)
    except Exception as e:
        logger.error(f"Error getting district info: {e}")
        return {
            "name": district_name,
            "description": f"District information currently unavailable.",
            "resources": {"influence": 0, "money": 0, "information": 0, "force": 0},
            "player_control": 0
        }


@db_retry
async def get_map_data(language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get map data with district control information."""
    params = {"p_language": language}

    try:
        return await execute_function("api_get_map_data", params)
    except Exception as e:
        logger.error(f"Error getting map data: {e}")
        return {"districts": [], "game_date": "Unknown", "cycle": "Unknown"}


# Resource management functions
@db_retry
async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """Exchange resources between different types."""
    params = {
        "p_telegram_id": telegram_id,
        "p_from_resource": from_resource,
        "p_to_resource": to_resource,
        "p_amount": amount,
        "p_language": language
    }

    try:
        return await execute_function("api_exchange_resources", params)
    except Exception as e:
        logger.error(f"Error exchanging resources: {e}")
        return {"success": False, "message": str(e)}


@db_retry
async def check_income(telegram_id: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Check expected resource income."""
    params = {
        "p_telegram_id": telegram_id,
        "p_language": language
    }

    try:
        return await execute_function("api_check_income", params)
    except Exception as e:
        logger.error(f"Error checking income: {e}")
        return {"district_income": [], "totals": {}}


# News and information functions
@db_retry
async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get latest news items."""
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count,
        "p_language": language
    }

    try:
        return await execute_function("api_get_latest_news", params)
    except Exception as e:
        logger.error(f"Error getting news: {e}")
        return {"public": [], "faction": []}


# Politician functions
@db_retry
async def get_politicians(telegram_id: str, type_filter: str = "all", language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get politicians filtered by type."""
    params = {
        "p_telegram_id": telegram_id,
        "p_type": type_filter,
        "p_language": language
    }

    try:
        return await execute_function("api_get_politicians", params)
    except Exception as e:
        logger.error(f"Error getting politicians: {e}")
        return {"politicians": []}


@db_retry
async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get detailed information about a politician."""
    params = {
        "p_telegram_id": telegram_id,
        "p_politician_name": politician_name,
        "p_language": language
    }

    try:
        return await execute_function("api_get_politician_status", params)
    except Exception as e:
        logger.error(f"Error getting politician status: {e}")
        return {
            "name": politician_name,
            "type": "unknown",
            "description": "Politician information currently unavailable.",
            "possible_actions": {}
        }


# Collective action functions
@db_retry
async def initiate_collective_action(
        telegram_id: str,
        action_type: str,
        district_name: str,
        target_player_name: Optional[str] = None,
        resource_type: str = "influence",
        resource_amount: int = 1,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """Initiate a collective action."""
    params = {
        "p_telegram_id": telegram_id,
        "p_action_type": action_type,
        "p_district_name": district_name,
        "p_target_player_name": target_player_name,
        "p_resource_type": resource_type,
        "p_resource_amount": resource_amount,
        "p_physical_presence": physical_presence,
        "p_language": language
    }

    try:
        return await execute_function("api_initiate_collective_action", params)
    except Exception as e:
        logger.error(f"Error initiating collective action: {e}")
        return {"success": False, "message": str(e)}


@db_retry
async def join_collective_action(
        telegram_id: str,
        collective_action_id: str,
        resource_type: str,
        resource_amount: int,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """Join an existing collective action."""
    params = {
        "p_telegram_id": telegram_id,
        "p_collective_action_id": collective_action_id,
        "p_resource_type": resource_type,
        "p_resource_amount": resource_amount,
        "p_physical_presence": physical_presence,
        "p_language": language
    }

    try:
        return await execute_function("api_join_collective_action", params)
    except Exception as e:
        logger.error(f"Error joining collective action: {e}")
        return {"success": False, "message": str(e)}


@db_retry
async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """Get all active collective actions."""
    try:
        result = await execute_sql("SELECT * FROM collective_actions WHERE status = 'active' ORDER BY created_at DESC")
        if result and isinstance(result, list):
            return result

        # Try fetching via client
        client = get_supabase()
        response = client.table("collective_actions").select("*")
        response = response.eq("status", "active").order("created_at", ascending=False)
        data = response.execute().data

        if data:
            return data
    except Exception as e:
        logger.error(f"Error getting active collective actions: {e}")

    return []


@db_retry
async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific collective action by ID."""
    try:
        client = get_supabase()
        response = client.table("collective_actions").select("*").eq("collective_action_id", action_id).limit(1).execute()

        if hasattr(response, 'data') and response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error getting collective action: {e}")

    return {}


# Admin functions
@db_retry
async def admin_process_actions(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Process all pending actions (admin only)."""
    # Check if user is admin
    try:
        player = await get_player_by_telegram_id(telegram_id)
        if not player or not player.get("is_admin", False):
            return {"success": False, "message": "Unauthorized: Admin privileges required"}

        # Try to process via function
        return await execute_function("api_admin_process_actions", {"p_telegram_id": telegram_id})
    except Exception as e:
        logger.error(f"Error in admin_process_actions: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "actions_processed": 0,
            "collective_actions_processed": 0
        }


@db_retry
async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Optional[Dict[str, Any]]:
    """Generate international effects (admin only)."""
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count
    }

    try:
        return await execute_function("api_admin_generate_international_effects", params)
    except Exception as e:
        logger.error(f"Error generating international effects: {e}")
        return {"success": False, "message": str(e)}


# Initialize database module function for main.py
def initialize_db():
    """Initialize database module and return the functions dictionary."""
    logger.info("Initializing database module")

    # Return the functions dictionary for use in other modules
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