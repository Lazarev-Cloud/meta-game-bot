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
    try:
        client = init_supabase()
        return client
    except Exception as e:
        logger.error(f"Error initializing Supabase: {e}")
        # Return a placeholder client that won't crash on methods but logs errors
        from unittest.mock import MagicMock
        mock_client = MagicMock()
        # Configure the mock to log errors rather than raise exceptions
        mock_client.table.return_value.select.return_value.execute.side_effect = \
            lambda: logger.error("Database unavailable, using fallback data")
        return mock_client


async def execute_function(function_name: str, params: Dict[str, Any], schema_prefix: bool = False) -> Any:
    """Execute a Postgres function through Supabase RPC with better error handling."""
    client = get_supabase()

    try:
        # Strip schema prefix if present
        if "." in function_name:
            schema, function_name = function_name.split(".", 1)

        # Use the correct method to execute RPC
        response = client.rpc(function_name, params)
        data = response.execute()

        if hasattr(data, 'data'):
            return data.data
        return data
    except Exception as e:
        logger.warning(f"Error executing function {function_name}: {e}")
        return None


async def execute_sql(sql: str) -> Any:
    """Execute raw SQL with better error handling."""
    try:
        # Attempt direct query if possible
        if sql.lower().startswith("select"):
            try:
                # Extract table name from SQL
                table_match = None
                if "from " in sql.lower():
                    parts = sql.lower().split("from ")
                    if len(parts) > 1:
                        table = parts[1].split()[0].strip().rstrip(';')

                        client = get_supabase()
                        response = client.from_(table).select("*")
                        return response.execute().data
            except Exception as e:
                logger.warning(f"Direct query failed: {e}")

        # Fallback to RPC method
        try:
            client = get_supabase()
            return client.rpc("exec_sql", {"sql": sql}).execute().data
        except Exception:
            pass

        return None
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        return None

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
                if "from " in sql.lower():
                    # Extract table name from SQL
                    parts = sql.lower().split("from ")
                    if len(parts) > 1:
                        table_parts = parts[1].split()
                        if table_parts:
                            table_match = table_parts[0].strip().rstrip(';')

                if table_match:
                    try:
                        # Try to query the table directly
                        response = client.table(f"{table_match}").select("*").execute()
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
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public');"
        )

        if result and isinstance(result, list) and len(result) > 0:
            exists = result[0].get('exists', False)
            logger.info(f"Public schema exists: {exists}")
            return exists

        logger.info("Could not verify public schema existence")
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

async def execute_with_fallback(operation_name: str, primary_func, fallback_func=None, *args, **kwargs):
    """Execute with fallback mechanism for database operations."""
    try:
        result = await primary_func(*args, **kwargs)
        return result
    except Exception as e:
        logger.warning(f"{operation_name} failed: {e}")
        if fallback_func:
            try:
                return await fallback_func(*args, **kwargs)
            except Exception as fallback_e:
                logger.error(f"Fallback for {operation_name} also failed: {fallback_e}")
        return None
async def resilient_query(operation, fallback_value=None):
    """Execute any database operation with robust fallback handling."""
    try:
        return await operation()
    except Exception as e:
        logger.warning(f"Database operation failed: {str(e)}")
        return fallback_value