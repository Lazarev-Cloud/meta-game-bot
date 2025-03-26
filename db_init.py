#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database initialization script for setting up the necessary schema.
Run this script once to create the database tables and functions.
"""

import asyncio
import os
import logging
import sys

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("db_init")

# Import dotenv to load environment variables
from dotenv import load_dotenv

load_dotenv()

# Import Supabase client
from supabase import create_client


async def read_sql_file(filename):
    """Read SQL from a file."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_dir = os.path.join(script_dir, "db")
        file_path = os.path.join(db_dir, filename)

        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading SQL file {filename}: {e}")
        return None


async def execute_sql_script(client, sql):
    """Execute SQL script through Supabase client."""
    if not sql:
        return False

    try:
        # For most SQL DDL operations, we need to use custom RPC functions
        # or direct connection. Here we're using a simplified approach.

        # Break the script into individual statements
        statements = sql.split(';')
        success_count = 0

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue

            try:
                # Try to execute using an RPC function if available
                logger.info(f"Executing: {stmt[:50]}...")

                # For Supabase, we'll need an RPC function that can execute SQL
                # Here's a simplified approach - may need to be adjusted
                response = client.rpc("exec_sql", {"sql": stmt}).execute()
                success_count += 1
            except Exception as stmt_error:
                logger.warning(f"Error executing statement: {stmt_error}")

        logger.info(f"Executed {success_count} SQL statements successfully")
        return success_count > 0
    except Exception as e:
        logger.error(f"Error executing SQL script: {e}")
        return False


async def create_exec_sql_function(client):
    """Create the exec_sql function in the database if it doesn't exist."""
    logger.info("Creating exec_sql function...")
    try:
        # SQL to create the exec_sql function
        sql = """
        CREATE OR REPLACE FUNCTION exec_sql(sql text)
        RETURNS SETOF json AS $$
        BEGIN
            RETURN QUERY EXECUTE sql;
        EXCEPTION WHEN OTHERS THEN
            RAISE;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """

        # Execute the SQL directly (this is a simplification)
        response = client.rpc("exec_sql", {"sql": sql}).execute()
        logger.info("exec_sql function created successfully")
        return True
    except Exception as e:
        logger.warning(f"Failed to create exec_sql function: {e}")
        logger.info("Will try to continue with schema creation anyway")
        return False


async def create_minimal_schema(client):
    """Create a minimal schema with essential tables if they don't exist."""
    logger.info("Creating minimal schema...")
    try:
        # Create players table if it doesn't exist
        players_sql = """
        CREATE TABLE IF NOT EXISTS players (
            player_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            ideology_score INTEGER NOT NULL DEFAULT 0,
            language TEXT DEFAULT 'en_US',
            remaining_actions INTEGER NOT NULL DEFAULT 1,
            remaining_quick_actions INTEGER NOT NULL DEFAULT 2,
            is_admin BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        # Create resources table if it doesn't exist
        resources_sql = """
        CREATE TABLE IF NOT EXISTS resources (
            resource_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            player_id UUID NOT NULL,
            influence_amount INTEGER NOT NULL DEFAULT 0,
            money_amount INTEGER NOT NULL DEFAULT 0,
            information_amount INTEGER NOT NULL DEFAULT 0,
            force_amount INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        # Create districts table if it doesn't exist
        districts_sql = """
        CREATE TABLE IF NOT EXISTS districts (
            district_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            influence_resource INTEGER NOT NULL DEFAULT 0,
            money_resource INTEGER NOT NULL DEFAULT 0,
            information_resource INTEGER NOT NULL DEFAULT 0,
            force_resource INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        # Execute the SQL statements
        await execute_sql_script(client, players_sql)
        await execute_sql_script(client, resources_sql)
        await execute_sql_script(client, districts_sql)

        logger.info("Minimal schema created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating minimal schema: {e}")
        return False


async def main():
    """Main function to initialize the database."""
    logger.info("Starting database initialization")

    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please check your .env file.")
        return False

    try:
        # Initialize Supabase client
        logger.info(f"Connecting to Supabase at {supabase_url}")
        client = create_client(supabase_url, supabase_key)

        # Check if we can connect
        try:
            logger.info("Testing connection...")
            response = client.table("players").select("count", count="exact").limit(1).execute()
            logger.info("Connection successful and players table exists")

            # Ask if user wants to reinitialize
            answer = input("Database tables already exist. Reinitialize? (y/N): ").lower()
            if answer != 'y':
                logger.info("Initialization cancelled by user")
                return True

        except Exception as test_error:
            logger.info(f"Connection test result: {test_error}")
            logger.info("Will attempt to create schema")

        # Try to create the exec_sql function first
        await create_exec_sql_function(client)

        # Create minimal schema
        await create_minimal_schema(client)

        # Run SQL scripts in order if needed
        sql_files = [
            "01_schema.sql",
            "02_tables.sql",
            "03_indexes.sql",
            "04_validation.sql",
            "05_functions_core.sql",
            "06_functions_game.sql",
            "07_functions_api.sql",
            "08_security.sql"
        ]

        answer = input("Do you want to run the full SQL schema scripts? (y/N): ").lower()
        if answer == 'y':
            for sql_file in sql_files:
                logger.info(f"Processing {sql_file}...")
                sql = await read_sql_file(sql_file)
                if sql:
                    success = await execute_sql_script(client, sql)
                    if success:
                        logger.info(f"Successfully executed {sql_file}")
                    else:
                        logger.warning(f"Failed to execute {sql_file}")

        logger.info("Database initialization complete")
        return True

    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)