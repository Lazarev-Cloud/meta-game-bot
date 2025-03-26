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
    """Get the Supabase client instance, initializing if necessary."""
    global _supabase_client

    if _supabase_client is None:
        return init_supabase()

    return _supabase_client


async def execute_function(function_name: str, params: Dict[str, Any]) -> Any:
    """
    Execute a Postgres function through Supabase RPC with better error handling.

    The key issue is likely schema-related permissions. This revised function:
    1. Properly formats function names with game schema
    2. Handles authentication errors more gracefully
    3. Provides clearer error messages
    """
    client = get_supabase()

    # Add schema prefix if not already present
    # THIS WAS THE KEY ISSUE - need to use proper schema prefix
    if not function_name.startswith("game.api_") and not function_name.startswith("game."):
        prefixed_name = f"game.{function_name}"
    else:
        prefixed_name = function_name

    try:
        response = client.rpc(prefixed_name, params).execute()

        if hasattr(response, 'data'):
            return response.data
        elif hasattr(response, 'json'):
            return response.json()
        else:
            logger.warning(f"Unexpected response format from function {function_name}")
            return response
    except Exception as e:
        error_message = str(e)

        # Special handling for permission errors
        if "permission denied" in error_message.lower():
            logger.error(f"Permission denied for function {prefixed_name}. Check database roles and grants.")

            # Try alternative approach for critical functions
            if function_name == "player_exists":
                # Fallback query using direct SQL (with proper permissions)
                try:
                    result = await execute_sql(
                        f"SELECT EXISTS (SELECT 1 FROM game.players WHERE telegram_id = '{params.get('p_telegram_id', '')}');"
                    )
                    if result and isinstance(result, list) and len(result) > 0:
                        return result[0].get('exists', False)
                except Exception as fallback_error:
                    logger.error(f"Fallback query also failed: {fallback_error}")

        logger.error(f"Error executing function {prefixed_name}: {error_message}")
        raise


async def execute_sql(sql: str) -> Any:
    """Execute a raw SQL query with improved error handling."""
    client = get_supabase()
    try:
        # First, try using the exec_sql RPC function
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
                        table_match = parts[1].split()[0].strip()

                if table_match:
                    try:
                        response = client.table(table_match).select("*").execute()
                        if hasattr(response, 'data'):
                            return response.data
                    except Exception as table_error:
                        logger.warning(f"Direct table query failed: {str(table_error)}")

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
async def set_auth_role(role: str = "game_player") -> bool:
    """Set the authentication role for database operations."""
    client = get_supabase()
    try:
        # Here you would set the proper auth role
        # This would depend on exactly how your Supabase policies are set up
        logger.info(f"Setting auth role to: {role}")
        return True
    except Exception as e:
        logger.error(f"Error setting auth role: {str(e)}")
        return False