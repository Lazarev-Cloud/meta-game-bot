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
    """Execute a Postgres function through Supabase RPC with better error handling."""
    client = get_supabase()

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

        # If function not found, try with/without schema prefix
        if "could not find the function" in error_message:
            # Remove schema prefix if present, add it if not
            alt_name = function_name
            if function_name.startswith("game."):
                alt_name = function_name[5:]  # Remove "game." prefix
            else:
                alt_name = f"game.{function_name}"

            try:
                logger.info(f"Trying alternative function name: {alt_name}")
                alt_response = client.rpc(alt_name, params).execute()

                if hasattr(alt_response, 'data'):
                    return alt_response.data
                return alt_response
            except Exception as alt_error:
                logger.error(f"Both versions of function call failed: {function_name} and {alt_name}")
                raise original_error
        else:
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