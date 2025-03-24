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

from db.error_handling import db_retry, DatabaseError
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
        schema_prefix: bool = True,
        operation_name: Optional[str] = None
) -> Any:
    """
    Execute an RPC function with proper error handling.

    Args:
        function_name: Name of the function to call
        params: Parameters to pass to the function
        schema_prefix: Whether to add "game." prefix to function name
        operation_name: Name for logging (defaults to function_name)

    Returns:
        Result of the RPC call or None on error
    """
    op_name = operation_name or function_name
    prefixed_name = f"game.{function_name}" if schema_prefix and not function_name.startswith(
        "game.") else function_name

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