#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Consolidated database client for Meta Game.

This module serves as the primary interface for all database operations,
providing a clean, consistent API.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, TypeVar, Callable

from db.error_handling import db_retry, DatabaseError
from db.supabase_client import (
    get_supabase,
    execute_function,
    execute_sql
)

# Initialize logger
logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')


# Standardized database operation wrapper
async def db_operation(operation_name: str,
                       func: Callable,
                       *args,
                       default_return=None,
                       log_error: bool = True,
                       max_retries: int = 3,
                       retry_delay: float = 1.5,
                       **kwargs) -> Any:
    """
    Execute a database operation with standardized error handling and retries.

    Args:
        operation_name: Name of operation for logging
        func: Function to execute
        default_return: Value to return on error
        log_error: Whether to log errors
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Result of the function or default_return on error
    """
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            retries += 1

            if log_error:
                logger.warning(
                    f"Database operation '{operation_name}' failed (attempt {retries}/{max_retries}): {str(e)}"
                )

            if retries < max_retries:
                # Wait before retrying with exponential backoff
                await asyncio.sleep(retry_delay * retries)
            elif log_error:
                # Log final failure
                logger.error(f"Database operation '{operation_name}' failed after {max_retries} attempts: {str(e)}")

    # Return default value on complete failure
    return default_return


# ---------------------------
# Player-related functions
# ---------------------------

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
            pass

        # Fallback to direct query with proper schema handling
        response = client.from_("players").schema("game").select("player_id").eq("telegram_id", telegram_id).execute()
        return hasattr(response, 'data') and len(response.data) > 0
    except Exception as e:
        logger.error(f"Error checking if player exists: {str(e)}")
        return False


@db_retry
async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive player information including resources, actions, etc."""
    return await db_operation(
        "get_player",
        execute_function,
        "api_get_player_status",
        {"p_telegram_id": telegram_id}
    )


async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get basic player record by Telegram ID."""
    async def fetch_player():
        client = get_supabase()
        response = client.from_("players").schema("game").select("*").eq("telegram_id", telegram_id).execute()
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None

    return await db_operation("get_player_by_telegram_id", fetch_player)


@db_retry
async def register_player(telegram_id: str, name: str, ideology_score: int = 0) -> Dict[str, Any]:
    """Register a new player."""
    return await db_operation(
        "register_player",
        execute_function,
        "api_register_player",
        {
            "p_telegram_id": telegram_id,
            "p_name": name,
            "p_ideology_score": ideology_score
        },
        log_error=True
    )


# ---------------------------
# Language & Preferences
# ---------------------------

async def get_player_language(telegram_id: str) -> str:
    """Get a player's preferred language."""

    async def fetch_language():
        client = get_supabase()
        response = client.from_("players").schema("game").select("language").eq("telegram_id", telegram_id).execute()
        if hasattr(response, 'data') and response.data and response.data[0].get("language"):
            return response.data[0]["language"]
        return "en_US"

    result = await db_operation("get_player_language", fetch_language, default_return="en_US")
    return result


async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set user's preferred language."""

    async def update_language():
        client = get_supabase()
        player_response = client.from_("players").schema("game").select("player_id").eq("telegram_id", telegram_id).execute()
        if hasattr(player_response, 'data') and player_response.data:
            client.from_("players").schema("game").update({"language": language}).eq("telegram_id", telegram_id).execute()
        return True

    return await db_operation("set_player_language", update_language, default_return=False)


# ---------------------------
# Game cycle and actions
# ---------------------------

async def get_cycle_info(language: str = "en_US") -> Dict[str, Any]:
    """Get information about the current game cycle."""
    return await db_operation(
        "get_cycle_info",
        execute_function,
        "api_get_cycle_info",
        {"p_language": language},
        default_return={}
    )


async def is_submission_open() -> bool:
    """Check if submissions are open for the current cycle."""

    async def check_submission():
        client = get_supabase()
        response = client.rpc("game.is_submission_open").execute()
        if hasattr(response, 'data'):
            return response.data
        return False

    return await db_operation("is_submission_open", check_submission, default_return=False)


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
) -> Dict[str, Any]:
    """Submit a player action."""
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

    return await db_operation("submit_action", execute_function, "api_submit_action", params)


@db_retry
async def cancel_latest_action(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """Cancel the latest action submitted by a player."""
    return await db_operation(
        "cancel_latest_action",
        execute_function,
        "api_cancel_latest_action",
        {
            "p_telegram_id": telegram_id,
            "p_language": language
        }
    )


# ---------------------------
# Districts and map
# ---------------------------

async def get_districts() -> List[Dict[str, Any]]:
    """Get all districts."""
    async def fetch_districts():
        client = get_supabase()
        response = client.from_("districts").schema("game").select("*").execute()
        if hasattr(response, 'data'):
            return response.data
        return []

    districts = await db_operation("get_districts", fetch_districts, default_return=[])

    # If primary method fails, try fallback with raw SQL
    if not districts:
        try:
            return await execute_sql("SELECT * FROM game.districts;") or []
        except Exception as e:
            logger.error(f"Fallback query for districts failed: {str(e)}")
            return []

    return districts


async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Dict[str, Any]:
    """Get detailed information about a district."""
    return await db_operation(
        "get_district_info",
        execute_function,
        "api_get_district_info",
        {
            "p_telegram_id": telegram_id,
            "p_district_name": district_name,
            "p_language": language
        },
        default_return={}
    )


async def get_map_data(language: str = "en_US") -> Dict[str, Any]:
    """Get the current map data showing district control."""
    return await db_operation(
        "get_map_data",
        execute_function,
        "api_get_map_data",
        {"p_language": language},
        default_return={}
    )


# ---------------------------
# Resources and Economy
# ---------------------------

@db_retry
async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Dict[str, Any]:
    """Exchange resources between types."""
    params = {
        "p_telegram_id": telegram_id,
        "p_from_resource": from_resource,
        "p_to_resource": to_resource,
        "p_amount": amount,
        "p_language": language
    }

    return await db_operation("exchange_resources", execute_function, "api_exchange_resources", params)


async def check_income(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """Check expected resource income."""
    return await db_operation(
        "check_income",
        execute_function,
        "api_check_income",
        {
            "p_telegram_id": telegram_id,
            "p_language": language
        },
        default_return={}
    )


# ---------------------------
# News and Information
# ---------------------------

async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Dict[str, Any]:
    """Get the latest news for a player."""
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count,
        "p_language": language
    }

    result = await db_operation(
        "get_latest_news",
        execute_function,
        "api_get_latest_news",
        params,
        default_return={"public": [], "faction": []}
    )

    return result


# ---------------------------
# Politicians
# ---------------------------

async def get_politicians(telegram_id: str, type: str = "local", language: str = "en_US") -> Dict[str, Any]:
    """Get politicians of specified type."""
    params = {
        "p_telegram_id": telegram_id,
        "p_type": type,
        "p_language": language
    }

    return await db_operation(
        "get_politicians",
        execute_function,
        "api_get_politicians",
        params,
        default_return={"politicians": []}
    )


async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Dict[str, Any]:
    """Get detailed information about a politician."""
    params = {
        "p_telegram_id": telegram_id,
        "p_politician_name": politician_name,
        "p_language": language
    }

    return await db_operation(
        "get_politician_status",
        execute_function,
        "api_get_politician_status",
        params,
        default_return={}
    )


# ---------------------------
# Collective Actions
# ---------------------------

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
) -> Dict[str, Any]:
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

    return await db_operation("initiate_collective_action", execute_function, "api_initiate_collective_action", params)


@db_retry
async def join_collective_action(
        telegram_id: str,
        collective_action_id: str,
        resource_type: str,
        resource_amount: int,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Dict[str, Any]:
    """Join a collective action."""
    params = {
        "p_telegram_id": telegram_id,
        "p_collective_action_id": collective_action_id,
        "p_resource_type": resource_type,
        "p_resource_amount": resource_amount,
        "p_physical_presence": physical_presence,
        "p_language": language
    }

    return await db_operation("join_collective_action", execute_function, "api_join_collective_action", params)


async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """Get all active collective actions."""
    async def fetch_actions():
        client = get_supabase()
        response = client.from_("collective_actions").schema("game").select("*").eq("status", "active").execute()
        if hasattr(response, 'data'):
            return response.data
        return []

    return await db_operation("get_active_collective_actions", fetch_actions, default_return=[])


async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Get details of a specific collective action."""
    async def fetch_action():
        client = get_supabase()
        response = client.from_("collective_actions").schema("game").select("*").eq("collective_action_id", action_id).execute()
        if hasattr(response, 'data') and response.data:
            return response.data[0]
        return None

    return await db_operation("get_collective_action", fetch_action)


# ---------------------------
# Admin Functions
# ---------------------------

@db_retry
async def admin_process_actions(telegram_id: str) -> Dict[str, Any]:
    """Process all pending actions (admin only)."""
    return await db_operation(
        "admin_process_actions",
        execute_function,
        "api_admin_process_actions",
        {"p_telegram_id": telegram_id}
    )


@db_retry
async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Dict[str, Any]:
    """Generate international effects (admin only)."""
    return await db_operation(
        "admin_generate_international_effects",
        execute_function,
        "api_admin_generate_international_effects",
        {
            "p_telegram_id": telegram_id,
            "p_count": count
        }
    )