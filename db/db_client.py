#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified database operations for Meta 

This module provides robust database operations with multiple fallback approaches,
comprehensive error handling, and detailed logging for troubleshooting.
"""

import asyncio
import logging
import random
from typing import Dict, Any, Optional, List, TypeVar, Callable, Awaitable, Union, Tuple

from utils.i18n import _
from utils.error_handling import db_retry, DatabaseError
from db.supabase_client import get_supabase, execute_function, execute_sql

# Initialize logger
logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')


# ===== Core database utility functions =====

async def db_operation(
        operation_name: str,
        func: Callable,
        *args,
        default_return=None,
        log_error: bool = True,
        max_retries: int = 3,
        retry_delay: float = 1.5,
        **kwargs
) -> Any:
    """Execute a database operation with standardized error handling and retries."""
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            result = await func(*args, **kwargs)
            # Handle cases where result is a number that could be mistaken for an error
            if result is not None or isinstance(result, (int, float, bool)):
                return result
            return default_return
        except Exception as e:
            last_exception = e
            retries += 1

            if log_error:
                logger.warning(
                    f"Database operation '{operation_name}' failed (attempt {retries}/{max_retries}): {str(e)}"
                )

            if retries < max_retries:
                # Exponential backoff with jitter for retries
                delay = retry_delay * (2 ** (retries - 1)) * (0.9 + 0.2 * random.random())
                await asyncio.sleep(delay)
            elif log_error:
                logger.error(f"Database operation '{operation_name}' failed after {max_retries} attempts: {str(e)}")

    # Return default value on complete failure
    return default_return


async def get_record(
        table: str,
        column: str,
        value: Any,
        schema: str = "public",
        operation_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get a single record by column value with improved error handling."""
    op_name = operation_name or f"get_{table}_by_{column}"
    logger.debug(f"Getting record: {op_name}, {value}")

    # Try direct SQL first
    try:
        sql = f"SELECT * FROM {schema}.{table} WHERE {column} = '{value}' LIMIT 1;"
        result = await execute_sql(sql)
        if result and len(result) > 0:
            logger.debug(f"SQL query found record in {table}")
            return result[0]
    except Exception as sql_error:
        logger.warning(f"Direct SQL get_record failed: {sql_error}")

    # Try using Supabase query builder
    try:
        client = get_supabase()
        response = client.table(f"{table}").select("*").eq(column, value).limit(1).execute()
        if hasattr(response, 'data') and response.data and len(response.data) > 0:
            return response.data[0]
    except Exception as builder_error:
        logger.warning(f"Query builder get_record failed: {builder_error}")

        # Try without schema prefix
        try:
            response = client.table(table).select("*").eq(column, value).limit(1).execute()
            if hasattr(response, 'data') and response.data and len(response.data) > 0:
                return response.data[0]
        except Exception as no_schema_error:
            logger.warning(f"No schema get_record failed: {no_schema_error}")

    return None


async def call_api_function(
        function_name: str,
        params: Dict[str, Any],
        operation_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Generic helper to call API functions with standard parameter handling."""
    # Ensure function name has api_ prefix
    api_name = function_name if function_name.startswith("api_") else f"api_{function_name}"

    logger.debug(f"Calling API function: {api_name}")
    try:
        result = await execute_function(api_name, params)
        return result
    except Exception as e:
        logger.warning(f"API function call {api_name} failed: {e}")
        return None


# ===== Player-related functions =====

@db_retry
async def player_exists(telegram_id: str) -> bool:
    """Check if player exists with multiple fallback methods."""
    try:
        # Try direct database query first
        client = get_supabase()
        try:
            response = client.from_("players").select("telegram_id")
            response = response.eq("telegram_id", telegram_id).limit(1)
            data = response.execute().data
            return len(data) > 0
        except Exception as db_error:
            logger.warning(f"Database query failed: {db_error}")

        # Check memory cache as fallback
        from utils.context_manager import context_manager
        return context_manager.get(telegram_id, "is_registered", False)
    except Exception as e:
        logger.error(f"Error checking player: {e}")
        return False

@db_retry
async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed player record by Telegram ID."""
    return await get_record("players", "telegram_id", telegram_id)


@db_retry
async def register_player(telegram_id: str, name: str, ideology_score: int, language: str = "en_US") -> Optional[
    Dict[str, Any]]:
    """Register a new player with better error handling."""
    logger.info(f"Registering player: {telegram_id}, {name}")

    # Store in memory first for resilience
    from utils.context_manager import context_manager
    context_manager.set(telegram_id, "is_registered", True)
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

        response = client.from_("players").insert(player_data).execute()

        if response and hasattr(response, 'data') and response.data:
            return response.data[0]
        return context_manager.get(telegram_id, "player_data")
    except Exception as e:
        logger.error(f"Database registration failed: {e}")
        return context_manager.get(telegram_id, "player_data")


@db_retry
async def get_player_language(telegram_id: str) -> str:
    """Get player's preferred language."""
    player = await get_record("players", "telegram_id", telegram_id)
    if player and "language" in player:
        return player["language"]
    return "en_US"


@db_retry
async def set_player_language(telegram_id: str, language: str) -> bool:
    """Set player's preferred language."""
    if language not in ["en_US", "ru_RU"]:
        return False

    try:
        # Direct SQL update as it's most reliable
        sql = f"UPDATE players SET language = '{language}' WHERE telegram_id = '{telegram_id}';"
        await execute_sql(sql)
        return True
    except Exception as e:
        logger.warning(f"SQL set_player_language failed: {e}")

    try:
        # Try with Supabase query builder
        client = get_supabase()
        response = client.table("players").update({"language": language}).eq("telegram_id", telegram_id).execute()

        if not (hasattr(response, 'data') and response.data):
            # Try with schema prefix
            response = client.table("players").update({"language": language}).eq("telegram_id",
                                                                                      telegram_id).execute()

        return hasattr(response, 'data') and response.data
    except Exception as e:
        logger.error(f"Query builder set_player_language failed: {e}")
        return False


@db_retry
async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player information by Telegram ID."""
    result = await call_api_function("get_player_status", {"p_telegram_id": telegram_id})

    # Fallback to direct query if API fails
    if result is None:
        logger.debug("API get_player_status failed, trying direct query")
        player = await get_player_by_telegram_id(telegram_id)
        if player:
            # Minimal player info structure
            return {
                "player_name": player.get("name", "Unknown"),
                "ideology_score": player.get("ideology_score", 0),
                "resources": await get_player_resources(telegram_id),
                "actions_remaining": player.get("remaining_actions", 0),
                "quick_actions_remaining": player.get("remaining_quick_actions", 0)
            }

    return result


async def get_player_resources(telegram_id: str) -> Dict[str, int]:
    """Get player resources directly from the database as a fallback."""
    try:
        # Get player ID first
        player = await get_player_by_telegram_id(telegram_id)
        if not player or "player_id" not in player:
            return {"influence": 0, "money": 0, "information": 0, "force": 0}

        player_id = player["player_id"]

        # Get resources by player ID
        resources = await get_record("resources", "player_id", player_id)
        if resources:
            return {
                "influence": resources.get("influence_amount", 0),
                "money": resources.get("money_amount", 0),
                "information": resources.get("information_amount", 0),
                "force": resources.get("force_amount", 0)
            }
    except Exception as e:
        logger.warning(f"Error getting player resources: {e}")

    # Default empty resources
    return {"influence": 0, "money": 0, "information": 0, "force": 0}


# ===== Game action functions =====

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
    """Submit an action with improved error handling."""
    logger.info(f"Submitting action for {telegram_id}: {action_type}, quick={is_quick_action}")

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
        if result and result.get("success"):
            logger.info(f"Successfully submitted action: {action_type}")
        else:
            logger.warning(f"Action submission returned unsuccessful result: {result}")
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
    return await call_api_function("cancel_latest_action", params)


@db_retry
async def get_cycle_info(language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get current game cycle information."""
    params = {"p_language": language}
    return await call_api_function("get_cycle_info", params)


@db_retry
async def is_submission_open() -> bool:
    """Check if submissions are open for the current cycle."""
    result = await execute_function("is_submission_open", {})
    if isinstance(result, bool):
        return result
    return bool(result)


@db_retry
async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """Exchange resources."""
    params = {
        "p_telegram_id": telegram_id,
        "p_from_resource": from_resource,
        "p_to_resource": to_resource,
        "p_amount": amount,
        "p_language": language
    }
    return await call_api_function("api_exchange_resources", params)


@db_retry
async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get detailed information about a district."""
    params = {
        "p_telegram_id": telegram_id,
        "p_district_name": district_name,
        "p_language": language
    }
    return await call_api_function("api_get_district_info", params)


@db_retry
async def get_districts() -> List[Dict[str, Any]]:
    """Get all districts."""
    return await get_records("districts", order=[{"column": "name", "ascending": True}])


async def get_records(
        table: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        order: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None,
        schema: str = "public"
) -> List[Dict[str, Any]]:
    """Get records with filtering options."""
    try:
        client = get_supabase()
        query = client.table(f"{schema}.{table}").select("*")

        if filters:
            for filter_item in filters:
                column = filter_item.get("column")
                value = filter_item.get("value")
                if column and value is not None:
                    query = query.eq(column, value)

        if order:
            for order_item in order:
                column = order_item.get("column")
                ascending = order_item.get("ascending", True)
                if column:
                    query = query.order(column, ascending=ascending)

        if limit:
            query = query.limit(limit)

        response = query.execute()

        if hasattr(response, 'data'):
            return response.data
    except Exception as e:
        logger.warning(f"Error getting records from {table}: {e}")
        # Try SQL fallback
        try:
            sql = f"SELECT * FROM {schema}.{table}"
            conditions = []

            if filters:
                for filter_item in filters:
                    column = filter_item.get("column")
                    value = filter_item.get("value")
                    if column and value is not None:
                        conditions.append(f"{column} = '{value}'")

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            if order:
                order_clauses = []
                for order_item in order:
                    column = order_item.get("column")
                    ascending = order_item.get("ascending", True)
                    if column:
                        direction = "ASC" if ascending else "DESC"
                        order_clauses.append(f"{column} {direction}")

                if order_clauses:
                    sql += " ORDER BY " + ", ".join(order_clauses)

            if limit:
                sql += f" LIMIT {limit}"

            result = await execute_sql(sql)
            if result:
                return result
        except Exception as sql_error:
            logger.error(f"SQL fallback for get_records failed: {sql_error}")

    return []


@db_retry
async def get_map_data(language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get map data with district control information."""
    params = {"p_language": language}
    return await call_api_function("api_get_map_data", params)


@db_retry
async def check_income(telegram_id: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Check expected resource income."""
    params = {
        "p_telegram_id": telegram_id,
        "p_language": language
    }
    return await call_api_function("api_check_income", params)


@db_retry
async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get latest news."""
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count,
        "p_language": language
    }
    return await call_api_function("api_get_latest_news", params)


@db_retry
async def get_politicians(telegram_id: str, type_filter: str = "all", language: str = "en_US") -> Optional[
    Dict[str, Any]]:
    """Get politicians."""
    params = {
        "p_telegram_id": telegram_id,
        "p_type": type_filter,
        "p_language": language
    }
    return await call_api_function("api_get_politicians", params)


@db_retry
async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Optional[
    Dict[str, Any]]:
    """Get detailed information about a politician."""
    params = {
        "p_telegram_id": telegram_id,
        "p_politician_name": politician_name,
        "p_language": language
    }
    return await call_api_function("api_get_politician_status", params)


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
    return await call_api_function("api_initiate_collective_action", params)


@db_retry
async def join_collective_action(
        telegram_id: str,
        collective_action_id: str,
        resource_type: str,
        resource_amount: int,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """Join a collective action."""
    params = {
        "p_telegram_id": telegram_id,
        "p_collective_action_id": collective_action_id,
        "p_resource_type": resource_type,
        "p_resource_amount": resource_amount,
        "p_physical_presence": physical_presence,
        "p_language": language
    }
    return await call_api_function("api_join_collective_action", params)


@db_retry
async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """Get all active collective actions."""
    return await get_records(
        "collective_actions",
        filters=[{"column": "status", "value": "active"}],
        order=[{"column": "created_at", "ascending": False}]
    )


@db_retry
async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Get a collective action by ID."""
    return await get_record("collective_actions", "collective_action_id", action_id)


# ===== Admin functions =====

@db_retry
async def admin_process_actions(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Process all pending actions (admin only)."""
    params = {"p_telegram_id": telegram_id}
    return await call_api_function("api_admin_process_actions", params)


@db_retry
async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Optional[Dict[str, Any]]:
    """Generate international effects (admin only)."""
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count
    }
    return await call_api_function("api_admin_generate_international_effects", params)


async def update_record(table: str, id_field: str, id_value: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a record in the database with improved error handling."""
    logger.debug(f"Updating record in {table} where {id_field}={id_value}")

    try:
        # Try with Supabase query builder
        client = get_supabase()
        response = client.table(table).update(data).eq(id_field, id_value).execute()

        if hasattr(response, 'data') and response.data:
            return response.data[0]

        # Try without schema prefix if first attempt failed
        response = client.table(table).update(data).eq(id_field, id_value).execute()
        if hasattr(response, 'data') and response.data:
            return response.data[0]

    except Exception as e:
        logger.warning(f"Update operation failed: {e}")

        # Try direct SQL as fallback
        try:
            # Build SET clause
            set_clauses = []
            for key, value in data.items():
                if isinstance(value, str):
                    set_clauses.append(f"{key} = '{value}'")
                elif value is None:
                    set_clauses.append(f"{key} = NULL")
                else:
                    set_clauses.append(f"{key} = {value}")

            sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {id_field} = '{id_value}' RETURNING *;"
            result = await execute_sql(sql)
            if result and len(result) > 0:
                return result[0]
        except Exception as sql_error:
            logger.error(f"SQL update fallback failed: {sql_error}")

    return None
