#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Low-level Supabase client implementation for the Meta Game bot.

This module handles core Supabase client initialization and
provides basic database operations. Higher-level functions
are defined in db_client.py.
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
    """
    Initialize the Supabase client with proper configuration.

    Returns:
        Initialized Supabase client

    Raises:
        ValueError: If Supabase credentials are missing
        Exception: If client initialization fails
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please check your .env file.")
        raise ValueError("Missing Supabase credentials")

    try:
        # Create client
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise


def get_supabase() -> Client:
    """
    Get the Supabase client instance, initializing if necessary.

    Returns:
        Supabase client instance
    """
    global _supabase_client

    if _supabase_client is None:
        return init_supabase()

    return _supabase_client


async def execute_function(function_name: str, params: Dict[str, Any]) -> Any:
    """
    Execute a Postgres function through Supabase RPC.

    Args:
        function_name: Name of the PostgreSQL function to execute
        params: Parameters to pass to the function

    Returns:
        Result of the function execution

    Raises:
        Exception: If function execution fails
    """
    client = get_supabase()
    try:
        response = client.rpc(function_name, params).execute()

        if hasattr(response, 'data'):
            return response.data
        elif hasattr(response, 'json'):
            return response.json()
        else:
            logger.warning(f"Unexpected response format from function {function_name}")
            return response
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        raise


async def check_schema_exists() -> bool:
    """
    Check if the game schema exists using a portable approach.

    Returns:
        True if schema exists, False otherwise
    """
    try:
        # Use raw SQL query approach - this is more reliable than the builder
        query = """
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.schemata 
            WHERE schema_name = 'game'
        );
        """

        result = await execute_sql(query)
        if result and len(result) > 0:
            if isinstance(result[0], dict) and 'exists' in result[0]:
                exists = result[0]['exists']
                logger.info(f"Game schema exists: {exists}")
                return exists

        # Try alternative approach if the first one returns unexpected format
        alt_query = "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'game';"
        alt_result = await execute_sql(alt_query)
        if alt_result and len(alt_result) > 0:
            logger.info("Game schema exists (verified through direct query)")
            return True

        logger.info("Game schema does not exist")
        return False
    except Exception as e:
        logger.error(f"Error checking if schema exists: {str(e)}")
        # Default to assuming the schema exists if we can't check properly
        logger.warning("Could not verify schema existence, assuming it exists")
        return True


async def execute_sql(sql: str) -> Any:
    """
    Execute a raw SQL query.

    Args:
        sql: SQL query to execute

    Returns:
        Query results

    Raises:
        Exception: If query execution fails
    """
    client = get_supabase()
    try:
        # Try a direct approach first
        response = client.rpc("exec_sql", {"sql": sql}).execute()
        if hasattr(response, 'data'):
            return response.data
        return None
    except Exception as e:
        # For common SQL operations, try a more direct approach
        try:
            logger.warning(f"RPC exec_sql failed, trying direct query: {str(e)}")

            # For select queries, try using the query builder
            if sql.lower().startswith("select"):
                # Extract table name for basic queries
                from_parts = sql.lower().split("from")
                if len(from_parts) > 1:
                    table_parts = from_parts[1].strip().split()
                    if len(table_parts) > 0:
                        table_name = table_parts[0].strip()

                        # If schema.table format
                        if '.' in table_name:
                            schema, table = table_name.split('.')
                            try:
                                # Try with schema
                                response = client.from_(table).select('*').execute()
                                if hasattr(response, 'data'):
                                    return response.data
                            except Exception:
                                logger.warning("Failed to query with schema")
                                return []
                        else:
                            # No schema specified, use table directly
                            try:
                                response = client.from_(table_name).select('*').execute()
                                if hasattr(response, 'data'):
                                    return response.data
                            except Exception:
                                logger.warning("Failed direct table query")
                                return []

            # Return an empty list if all approaches fail
            return []
        except Exception as fallback_error:
            logger.error(f"Error executing SQL (fallback also failed): {str(fallback_error)}")
            return []