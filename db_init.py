#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database initialization script for the Meta Game bot.

This script will create the necessary database schema and initial tables.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("db_init")

# Load environment variables
load_dotenv()


async def execute_sql_file(filename):
    """Execute an SQL file with proper error handling."""
    from db.supabase_client import execute_sql

    full_path = Path("db") / filename
    if not full_path.exists():
        logger.error(f"SQL file not found: {full_path}")
        return False

    try:
        with open(full_path, "r") as f:
            sql_content = f.read()

        # Split into individual statements
        statements = sql_content.split(';')

        success_count = 0
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:  # Skip empty statements
                continue

            try:
                logger.debug(f"Executing SQL statement: {stmt[:100]}...")
                await execute_sql(stmt + ';')
                success_count += 1
            except Exception as stmt_error:
                logger.warning(f"Error executing statement: {stmt_error}")

        logger.info(f"Executed {success_count} statements from {filename}")
        return True
    except Exception as e:
        logger.error(f"Error executing SQL file {filename}: {e}")
        return False


async def apply_fixes():
    """Apply SQL fixes for schema and function issues."""
    # Import the necessary functions
    from db.supabase_client import init_supabase, execute_sql

    try:
        # Initialize Supabase client
        init_supabase()
        logger.info("Initialized Supabase client")

        # Create game schema if it doesn't exist
        await execute_sql("CREATE SCHEMA IF NOT EXISTS game;")
        logger.info("Created or verified game schema")

        # Apply critical function fixes
        await execute_sql("""
        -- Create function for player_exists both in game schema and public schema
        CREATE OR REPLACE FUNCTION game.player_exists(p_telegram_id TEXT)
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN EXISTS (
                SELECT 1 FROM game.players WHERE telegram_id = p_telegram_id
            );
        END;
        $$ LANGUAGE plpgsql;
        """)

        await execute_sql("""
        -- Then in public schema for Supabase RPC compatibility
        CREATE OR REPLACE FUNCTION public.player_exists(p_telegram_id TEXT)
        RETURNS BOOLEAN AS $$
        BEGIN
            -- Call the original function in the game schema
            RETURN game.player_exists(p_telegram_id);
        END;
        $$ LANGUAGE plpgsql;
        """)

        logger.info("Applied critical function fixes")

        return True
    except Exception as e:
        logger.error(f"Error applying fixes: {e}")
        return False


async def init_database():
    """Initialize database schema and tables."""
    # Import the necessary functions
    from db.supabase_client import init_supabase, check_schema_exists
    from db.permission_checker import check_database_permissions

    try:
        # Initialize Supabase client
        init_supabase()
        logger.info("Initialized Supabase client")

        # Check if schema exists
        schema_exists = await check_schema_exists()

        if not schema_exists:
            logger.info("Game schema not found, creating...")

            # Apply essential SQL files in order
            files_to_apply = [
                "01_schema.sql",  # Create schema
                "02_tables.sql",  # Create tables
                "03_indexes.sql",  # Create indexes
                "04_validation.sql",  # Create validation triggers
                "05_functions_core.sql",  # Create core functions
                "08_security.sql"  # Set up security roles
            ]

            for sql_file in files_to_apply:
                success = await execute_sql_file(sql_file)
                if not success:
                    logger.warning(f"Failed to fully apply {sql_file}")

            logger.info("Basic database structure created")
        else:
            logger.info("Game schema exists, applying fixes only")

        # Apply specific fixes for common issues
        await apply_fixes()

        # Check permissions to diagnose any remaining issues
        await check_database_permissions()

        logger.info("Database initialization completed")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    try:
        logger.info("Starting database initialization...")
        success = asyncio.run(init_database())
        if success:
            logger.info("Database successfully initialized!")
            sys.exit(0)
        else:
            logger.error("Database initialization had errors")
            sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error during database initialization: {e}")
        sys.exit(1)