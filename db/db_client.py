#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified database operations for Meta Game.

This module consolidates database operations into a set of generic
functions that handle errors, retries, and common patterns.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, TypeVar, Callable, Awaitable, Union, Tuple

from telegram import Update

from utils import _
from utils.error_handling import db_retry, DatabaseError
from db.supabase_client import get_supabase, execute_function, execute_sql

# Initialize logger
logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')


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
            result = await func(*args, **kwargs)
            # Handle cases where result is a number that could be mistaken for an error
            # (e.g., 0 is a valid result but might be treated as falsey)
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
                # Wait before retrying with exponential backoff
                await asyncio.sleep(retry_delay * retries)
            elif log_error:
                # Log final failure
                logger.error(f"Database operation '{operation_name}' failed after {max_retries} attempts: {str(e)}")

    # Return default value on complete failure
    return default_return


async def execute_rpc(
        function_name: str,
        params: Dict[str, Any],
        schema_prefix: bool = False,  # Change default to False
        operation_name: Optional[str] = None
) -> Any:
    """
    Execute an RPC function with proper error handling.
    """
    op_name = operation_name or function_name

    # Only prefix if explicitly requested
    prefixed_name = f"game.{function_name}" if schema_prefix else function_name

    return await db_operation(
        op_name,
        execute_function,
        prefixed_name,
        params
    )


async def execute_query(
        query: str,
        operation_name: str,
        params: Optional[Dict[str, Any]] = None,
        table: str = "",
        schema: str = "game",
) -> Any:
    """
    Execute a database query with proper error handling.

    Args:
        query: SQL query or query type like "select", "insert", etc.
        operation_name: Name for logging
        params: Query parameters
        table: Table name for Supabase operations
        schema: Schema name

    Returns:
        Query results or None on error
    """

    async def run_query():
        client = get_supabase()

        # Handle raw SQL queries
        if query.lower().startswith(("select", "insert", "update", "delete")):
            return await execute_sql(query)

        # Handle Supabase query builder operations
        if table:
            builder = client.from_(table).schema(schema)

            if query == "select":
                columns = params.get("columns", "*") if params else "*"
                builder = builder.select(columns)
            elif query == "insert":
                builder = builder.insert(params)
            elif query == "update":
                builder = builder.update(params)
            elif query == "delete":
                builder = builder.delete()

            # Apply filters if provided
            if params and "filters" in params:
                for filter_item in params["filters"]:
                    column = filter_item.get("column")
                    operator = filter_item.get("operator", "eq")
                    value = filter_item.get("value")

                    if column and value is not None:
                        if operator == "eq":
                            builder = builder.eq(column, value)
                        elif operator == "gt":
                            builder = builder.gt(column, value)
                        elif operator == "lt":
                            builder = builder.lt(column, value)
                        elif operator == "gte":
                            builder = builder.gte(column, value)
                        elif operator == "lte":
                            builder = builder.lte(column, value)
                        elif operator == "neq":
                            builder = builder.neq(column, value)
                        elif operator == "in":
                            builder = builder.in_(column, value)
                        elif operator == "like":
                            builder = builder.like(column, value)

            # Apply order if provided
            if params and "order" in params:
                for order_item in params["order"]:
                    column = order_item.get("column")
                    ascending = order_item.get("ascending", True)

                    if column:
                        builder = builder.order(column, ascending=ascending)

            # Apply limit and offset if provided
            if params and "limit" in params:
                builder = builder.limit(params["limit"])

            if params and "offset" in params:
                builder = builder.offset(params["offset"])

            response = builder.execute()

            if hasattr(response, 'data'):
                return response.data

        return None

    return await db_operation(operation_name, run_query)


async def get_record(
        table: str,
        column: str,
        value: Any,
        schema: str = "game",
        operation_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get a single record by column value.

    Args:
        table: Table name
        column: Column name to filter on
        value: Value to filter by
        schema: Schema name
        operation_name: Name for logging

    Returns:
        Record as dictionary or None if not found
    """
    op_name = operation_name or f"get_{table}_by_{column}"

    params = {
        "filters": [
            {"column": column, "value": value}
        ],
        "limit": 1
    }

    result = await execute_query("select", op_name, params, table, schema)

    if result and len(result) > 0:
        return result[0]
    return None


async def get_records(
        table: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        order: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        columns: str = "*",
        schema: str = "game",
        operation_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get records with flexible filtering.

    Args:
        table: Table name
        filters: List of filter conditions
        order: List of order specifications
        limit: Maximum number of records to return
        offset: Number of records to skip
        columns: Columns to select
        schema: Schema name
        operation_name: Name for logging

    Returns:
        List of records as dictionaries
    """
    op_name = operation_name or f"get_{table}_records"

    params = {
        "columns": columns
    }

    if filters:
        params["filters"] = filters

    if order:
        params["order"] = order

    if limit is not None:
        params["limit"] = limit

    if offset is not None:
        params["offset"] = offset

    result = await execute_query("select", op_name, params, table, schema)

    if result:
        return result
    return []


async def create_record(
        table: str,
        data: Dict[str, Any],
        schema: str = "game",
        operation_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a new record.

    Args:
        table: Table name
        data: Record data to insert
        schema: Schema name
        operation_name: Name for logging

    Returns:
        Created record or None on error
    """
    op_name = operation_name or f"create_{table}_record"

    result = await execute_query("insert", op_name, data, table, schema)

    if result and len(result) > 0:
        return result[0]
    return None


async def update_record(
        table: str,
        column: str,
        value: Any,
        data: Dict[str, Any],
        schema: str = "game",
        operation_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Update a record by column value.

    Args:
        table: Table name
        column: Column name to filter on
        value: Value to filter by
        data: Record data to update
        schema: Schema name
        operation_name: Name for logging

    Returns:
        Updated record or None on error
    """
    op_name = operation_name or f"update_{table}_record"

    params = data.copy()
    params["filters"] = [
        {"column": column, "value": value}
    ]

    result = await execute_query("update", op_name, params, table, schema)

    if result and len(result) > 0:
        return result[0]
    return None


async def delete_record(
        table: str,
        column: str,
        value: Any,
        schema: str = "game",
        operation_name: Optional[str] = None
) -> bool:
    """
    Delete a record by column value.

    Args:
        table: Table name
        column: Column name to filter on
        value: Value to filter by
        schema: Schema name
        operation_name: Name for logging

    Returns:
        True if successful, False otherwise
    """
    op_name = operation_name or f"delete_{table}_record"

    params = {
        "filters": [
            {"column": column, "value": value}
        ]
    }

    result = await execute_query("delete", op_name, params, table, schema)

    if result is not None:
        return True
    return False


# Helper function to build RPC parameters
def build_params(params_dict: Dict[str, Any], param_prefix: str = "p_") -> Dict[str, Any]:
    """
    Build parameters for RPC calls with proper prefixing.

    Args:
        params_dict: Dictionary of parameters
        param_prefix: Prefix to add to parameter names

    Returns:
        Dictionary with prefixed parameter names
    """
    return {f"{param_prefix}{k}": v for k, v in params_dict.items()}


# ===== Player-related functions =====

@db_retry
async def player_exists(telegram_id: str) -> bool:
    """Check if a player exists by telegram ID with robust error handling."""
    try:
        # Try first without schema prefix
        params = {"p_telegram_id": telegram_id}
        result = await execute_rpc("player_exists", params, schema_prefix=False)
        return bool(result)
    except Exception as e:
        logger.warning(f"Initial player_exists call failed: {e}")

        # Try direct SQL as ultimate fallback
        try:
            result = await execute_sql(
                f"SELECT EXISTS (SELECT 1 FROM game.players WHERE telegram_id = '{telegram_id}');"
            )
            if result and isinstance(result, list) and len(result) > 0:
                return result[0].get('exists', False)
            return False
        except Exception as sql_error:
            logger.error(f"All player_exists fallbacks failed: {sql_error}")
            return False

async def call_api_function(
    function_name: str,
    params: Dict[str, Any],
    operation_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Generic helper to call API functions with standard parameter handling."""
    # Ensure function name has api_ prefix
    api_name = function_name if function_name.startswith("api_") else f"api_{function_name}"
    return await execute_rpc(api_name, params, operation_name=operation_name)

@db_retry
async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player information by Telegram ID."""
    return await call_api_function("get_player_status", {"p_telegram_id": telegram_id})

@db_retry
async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """Get detailed information about a district."""
    return await call_api_function(
        "get_district_info",
        {
            "p_telegram_id": telegram_id,
            "p_district_name": district_name,
            "p_language": language
        }
    )


async def handle_command_error(
        update: Update,
        language: str,
        error: Exception,
        command_name: str
) -> None:
    """Handle errors in command handlers with standardized messaging."""
    logger.error(f"Error in {command_name}: {str(error)}")

    error_text = str(error).lower()
    message = _("An error occurred. Please try again later.", language)

    if "database" in error_text or "sql" in error_text:
        message = _("Database connection issue. Please try again later.", language)
    elif "resource" in error_text:
        message = _("You don't have enough resources for this action.", language)
    elif "permission" in error_text:
        message = _("You don't have permission to perform this action.", language)

    await update.message.reply_text(message)

@db_retry
async def get_player_by_telegram_id(telegram_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed player record by Telegram ID.

    Args:
        telegram_id: Player's Telegram ID

    Returns:
        Player record as a dictionary or None if not found
    """
    return await get_record("players", "telegram_id", telegram_id)


@db_retry
async def register_player(telegram_id: str, name: str, ideology_score: int) -> Optional[Dict[str, Any]]:
    params = {
        "p_telegram_id": telegram_id,
        "p_name": name,
        "p_ideology_score": ideology_score
    }
    return await execute_rpc("api_register_player", params)


# ===== Language and preferences =====

@db_retry
async def get_player_language(telegram_id: str) -> str:
    """
    Get player's preferred language.

    Args:
        telegram_id: Player's Telegram ID

    Returns:
        Language code (en_US or ru_RU)
    """
    player = await get_record("players", "telegram_id", telegram_id)
    if player and "language" in player:
        return player["language"]
    return "en_US"


@db_retry
async def set_player_language(telegram_id: str, language: str) -> bool:
    """
    Set player's preferred language.

    Args:
        telegram_id: Player's Telegram ID
        language: Language code (en_US or ru_RU)

    Returns:
        True if successful, False otherwise
    """
    if language not in ["en_US", "ru_RU"]:
        return False

    player = await get_record("players", "telegram_id", telegram_id)
    if not player:
        return False

    result = await update_record("players", "telegram_id", telegram_id, {"language": language})
    return result is not None


# ===== Game cycle and actions =====

@db_retry
async def get_cycle_info(language: str = "en_US") -> Optional[Dict[str, Any]]:
    """
    Get current game cycle information.

    Args:
        language: Language code for translations

    Returns:
        Cycle information as a dictionary
    """
    params = {"p_language": language}
    return await execute_rpc("api_get_cycle_info", params)


@db_retry
async def is_submission_open() -> bool:
    """
    Check if submissions are open for the current cycle.

    Returns:
        True if submissions are open, False otherwise
    """
    result = await execute_rpc("is_submission_open", {})
    if isinstance(result, bool):
        return result
    return bool(result)


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
    """
    Submit an action.

    Args:
        telegram_id: Player's Telegram ID
        action_type: Type of action
        is_quick_action: Whether this is a quick action
        district_name: Target district name
        target_player_name: Target player name
        target_politician_name: Target politician name
        resource_type: Type of resource to use
        resource_amount: Amount of resource to use
        physical_presence: Whether player is physically present
        expected_outcome: Expected outcome of action
        language: Language code for translations

    Returns:
        Action result information
    """
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
    return await execute_rpc("api_submit_action", params)


@db_retry
async def cancel_latest_action(telegram_id: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """
    Cancel the latest action.

    Args:
        telegram_id: Player's Telegram ID
        language: Language code for translations

    Returns:
        Cancellation result information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_language": language
    }
    return await execute_rpc("api_cancel_latest_action", params)


# ===== Districts and map =====

@db_retry
async def get_districts() -> List[Dict[str, Any]]:
    """
    Get all districts.

    Returns:
        List of district records
    """
    return await get_records("districts", order=[{"column": "name", "ascending": True}])


@db_retry
async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a district.

    Args:
        telegram_id: Player's Telegram ID
        district_name: District name
        language: Language code for translations

    Returns:
        District information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_district_name": district_name,
        "p_language": language
    }
    return await execute_rpc("api_get_district_info", params)


@db_retry
async def get_map_data(language: str = "en_US") -> Optional[Dict[str, Any]]:
    """
    Get map data with district control information.

    Args:
        language: Language code for translations

    Returns:
        Map data
    """
    params = {"p_language": language}
    return await execute_rpc("api_get_map_data", params)


# ===== Resources and economy =====

@db_retry
async def exchange_resources(
        telegram_id: str,
        from_resource: str,
        to_resource: str,
        amount: int,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """
    Exchange resources.

    Args:
        telegram_id: Player's Telegram ID
        from_resource: Source resource type
        to_resource: Target resource type
        amount: Amount to exchange
        language: Language code for translations

    Returns:
        Exchange result information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_from_resource": from_resource,
        "p_to_resource": to_resource,
        "p_amount": amount,
        "p_language": language
    }
    return await execute_rpc("api_exchange_resources", params)


@db_retry
async def check_income(telegram_id: str, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """
    Check expected resource income.

    Args:
        telegram_id: Player's Telegram ID
        language: Language code for translations

    Returns:
        Income information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_language": language
    }
    return await execute_rpc("api_check_income", params)


# ===== News and information =====

@db_retry
async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Optional[Dict[str, Any]]:
    """
    Get latest news.

    Args:
        telegram_id: Player's Telegram ID
        count: Number of news items to retrieve
        language: Language code for translations

    Returns:
        News information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count,
        "p_language": language
    }
    return await execute_rpc("api_get_latest_news", params)


# ===== Politicians =====

@db_retry
async def get_politicians(telegram_id: str, type_filter: str = "all", language: str = "en_US") -> Optional[
    Dict[str, Any]]:
    """
    Get politicians.

    Args:
        telegram_id: Player's Telegram ID
        type_filter: Type of politicians to retrieve (local, international, or all)
        language: Language code for translations

    Returns:
        Politicians information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_type": type_filter,
        "p_language": language
    }
    return await execute_rpc("api_get_politicians", params)


@db_retry
async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Optional[
    Dict[str, Any]]:
    """
    Get detailed information about a politician.

    Args:
        telegram_id: Player's Telegram ID
        politician_name: Politician name
        language: Language code for translations

    Returns:
        Politician information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_politician_name": politician_name,
        "p_language": language
    }
    return await execute_rpc("api_get_politician_status", params)


# ===== Collective actions =====

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
    """
    Initiate a collective action.

    Args:
        telegram_id: Player's Telegram ID
        action_type: Type of action
        district_name: Target district name
        target_player_name: Target player name
        resource_type: Type of resource to use
        resource_amount: Amount of resource to use
        physical_presence: Whether player is physically present
        language: Language code for translations

    Returns:
        Collective action result information
    """
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
    return await execute_rpc("api_initiate_collective_action", params)


@db_retry
async def join_collective_action(
        telegram_id: str,
        collective_action_id: str,
        resource_type: str,
        resource_amount: int,
        physical_presence: bool = False,
        language: str = "en_US"
) -> Optional[Dict[str, Any]]:
    """
    Join a collective action.

    Args:
        telegram_id: Player's Telegram ID
        collective_action_id: Collective action ID
        resource_type: Type of resource to contribute
        resource_amount: Amount of resource to contribute
        physical_presence: Whether player is physically present
        language: Language code for translations

    Returns:
        Join result information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_collective_action_id": collective_action_id,
        "p_resource_type": resource_type,
        "p_resource_amount": resource_amount,
        "p_physical_presence": physical_presence,
        "p_language": language
    }
    return await execute_rpc("api_join_collective_action", params)


@db_retry
async def get_active_collective_actions() -> List[Dict[str, Any]]:
    """
    Get all active collective actions.

    Returns:
        List of active collective actions
    """
    return await get_records(
        "collective_actions",
        filters=[{"column": "status", "value": "active"}],
        order=[{"column": "created_at", "ascending": False}]
    )


@db_retry
async def get_collective_action(action_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a collective action by ID.

    Args:
        action_id: Collective action ID

    Returns:
        Collective action record
    """
    return await get_record("collective_actions", "collective_action_id", action_id)


# ===== Admin functions =====

@db_retry
async def admin_process_actions(telegram_id: str) -> Optional[Dict[str, Any]]:
    """
    Process all pending actions (admin only).

    Args:
        telegram_id: Admin's Telegram ID

    Returns:
        Process result information
    """
    params = {"p_telegram_id": telegram_id}
    return await execute_rpc("api_admin_process_actions", params)


@db_retry
async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Optional[Dict[str, Any]]:
    """
    Generate international effects (admin only).

    Args:
        telegram_id: Admin's Telegram ID
        count: Number of effects to generate

    Returns:
        Generation result information
    """
    params = {
        "p_telegram_id": telegram_id,
        "p_count": count
    }
    return await execute_rpc("api_admin_generate_international_effects", params)