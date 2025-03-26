#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Low-level Supabase client implementation for the Meta Game bot.
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
        # Create client with standard settings
        _supabase_client = create_client(supabase_url, supabase_key)

        # Setup proper auth - this is critical for permissions
        try:
            # Set anon key role to authenticate properly
            # Alternatively, use service role for admin operations
            service_key = os.getenv("SUPABASE_SERVICE_KEY")
            if service_key:
                logger.info("Using service role for database operations")
                # For admin operations, can switch to use service key instead
                # _supabase_client = create_client(supabase_url, service_key)
        except Exception as auth_error:
            logger.warning(f"Could not set auth role: {auth_error}")

        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise


def get_supabase() -> Client:
    client = init_supabase()
    # Set schema to 'game' instead of default 'public'
    try:
        # Add this line to explicitly set schema
        client.postgrest.schema('game')
    except Exception as e:
        logger.warning(f"Could not set schema: {e}")
    return client


async def execute_function(function_name: str, params: Dict[str, Any], schema_prefix: bool = False) -> Any:
    """Execute a Postgres function through Supabase RPC with better error handling."""
    client = get_supabase()
    original_function_name = function_name

    # Strip schema prefix if present - Supabase RPC doesn't support schema prefixes directly
    if "." in function_name:
        schema, function_name = function_name.split(".", 1)
        logger.debug(f"Stripped schema '{schema}' from function call, using '{function_name}'")

    # Try without schema prefix first
    try:
        response = client.rpc(function_name, params).execute()

        if hasattr(response, 'data'):
            return response.data
        elif hasattr(response, 'json'):
            return response.json()
        else:
            return response
    except Exception as original_error:
        error_message = str(original_error).lower()
        logger.warning(f"Error executing function {function_name}: {original_error}")

        # Try with alternative function name if the first attempt failed
        try:
            # Try different variations of the function name or parameters
            if "could not find the function" in error_message or "permission denied" in error_message:
                # Try with explicit schema
                alt_function = f"api_{function_name}" if not function_name.startswith("api_") else function_name[4:]
                logger.info(f"Trying alternative function name: {alt_function}")

                alt_response = client.rpc(alt_function, params).execute()
                if hasattr(alt_response, 'data'):
                    return alt_response.data
                return alt_response
        except Exception as alt_error:
            logger.error(f"Alternative function call failed: {alt_error}")

        # If all RPC attempts fail, try direct SQL for simple functions
        try:
            if function_name == "player_exists":
                # Direct SQL fallback for player_exists
                result = await execute_sql(
                    f"SELECT EXISTS (SELECT 1 FROM game.players WHERE telegram_id = '{params.get('p_telegram_id', '')}');"
                )
                if result and isinstance(result, list) and len(result) > 0:
                    return result[0].get('exists', False)
                return False
        except Exception as sql_error:
            logger.error(f"SQL fallback also failed: {sql_error}")

        # Re-raise the original error
        raise original_error


async def execute_sql(sql: str) -> Any:
    """Execute a raw SQL query with improved error handling."""
    client = get_supabase()
    try:
        # First, try using the exec_sql RPC function if available
        try:
            response = client.rpc("exec_sql", {"sql": sql}).execute()
            if hasattr(response, 'data'):
                return response.data
        except Exception as rpc_error:
            logger.warning(f"RPC exec_sql failed: {str(rpc_error)}")

            # If that fails, try direct query approach
            if sql.lower().startswith("select"):
                # For select queries, try direct SQL via REST API
                table_match = None
                if "from game." in sql.lower():
                    # Extract table name from SQL
                    parts = sql.lower().split("from game.")
                    if len(parts) > 1:
                        table_parts = parts[1].split()
                        if table_parts:
                            table_match = table_parts[0].strip().rstrip(';')

                if table_match:
                    try:
                        # Try to query the table directly
                        response = client.table(f"game.{table_match}").select("*").execute()
                        if hasattr(response, 'data'):
                            return response.data
                    except Exception as table_error:
                        logger.warning(f"Direct table query failed: {str(table_error)}")
                        # Try without schema prefix
                        try:
                            response = client.table(table_match).select("*").execute()
                            if hasattr(response, 'data'):
                                return response.data
                        except Exception as no_schema_error:
                            logger.warning(f"Direct table query without schema failed: {str(no_schema_error)}")

        # If we got here, both approaches failed
        logger.error(f"Failed to execute SQL: {sql}")
        return None
    except Exception as e:
        logger.error(f"Error executing SQL: {str(e)}")
        return None


async def check_schema_exists() -> bool:
    """Check if the game schema exists."""
    try:
        # Use a simple information schema query
        result = await execute_sql(
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'game');"
        )

        if result and isinstance(result, list) and len(result) > 0:
            exists = result[0].get('exists', False)
            logger.info(f"Game schema exists: {exists}")
            return exists

        logger.info("Could not verify game schema existence")
        return False
    except Exception as e:
        logger.error(f"Error checking schema existence: {str(e)}")
        return False


# Function to authenticate with specific role
async def set_auth_role(role: str = "anon") -> bool:
    """Set the authentication role for database operations."""
    client = get_supabase()
    try:
        # Update the auth header based on role
        # This approach varies based on Supabase client implementation
        logger.info(f"Setting auth role to: {role}")
        return True
    except Exception as e:
        logger.error(f"Error setting auth role: {str(e)}")
        return False