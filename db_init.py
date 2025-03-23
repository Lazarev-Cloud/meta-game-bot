#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced database initialization script for the Meta Game bot.

This script initializes all necessary tables in the Supabase database.
It reads the SQL files in the db directory and executes them in the correct order,
with improved error handling and recovery.
"""

import asyncio
import os
import sys
import time
from typing import List, Optional

from dotenv import load_dotenv

from db.supabase_client import init_supabase, get_supabase, execute_sql
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Setup logging
logger = setup_logger(name="db_init", level="INFO", log_file="logs/db_init.log")

# SQL file execution order
SQL_FILE_ORDER = [
    "01_schema.sql",
    "02_tables.sql",
    "03_indexes.sql",
    "04_validation.sql",
    "05_functions_core.sql",
    "06_functions_game.sql",
    "07_functions_api.sql",
    "08_security.sql",
    "09_initial_data.sql",
    # "10_sample_data.sql",  # Include sample data for testing
    "11_fix_player_exists.sql",
]


async def execute_sql_file(file_path: str) -> None:
    """Execute a SQL file with better error handling."""
    try:
        # Read the SQL file
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()

        # Execute the SQL
        await execute_sql_statements(split_sql_statements(sql), os.path.basename(file_path))

        logger.info(f"Successfully executed SQL file: {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"Error executing SQL file {file_path}: {e}")
        raise


async def execute_sql_statements(statements: List[str], file_name: str) -> None:
    """Execute a list of SQL statements with retries."""
    executed = 0
    failed = 0

    for i, statement in enumerate(statements):
        if not statement.strip():
            continue

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Try to execute the statement
                await execute_sql(statement)
                executed += 1
                break  # Success, exit retry loop
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 1 * retry_count  # Linear backoff
                    logger.warning(f"Retry {retry_count}/{max_retries} for statement {i + 1} in {file_name}: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to execute statement {i + 1} after {max_retries} attempts: {e}")
                    logger.error(f"Statement: {statement[:200]}...")
                    failed += 1
                    # Continue with next statement instead of aborting everything
                    break

    logger.info(f"File {file_name}: Successfully executed {executed} statements, failed {failed} statements")

    # If too many failures, warn but don't stop the entire process
    if failed > len(statements) / 2:
        logger.warning(f"High failure rate in {file_name}: {failed}/{len(statements)} statements failed")


def split_sql_statements(sql: str) -> List[str]:
    """Split a SQL string into individual statements with improved handling."""
    statements = []
    current_statement = []
    in_function_body = False
    in_string = False
    string_delimiter = None
    in_comment = False

    # Add a final newline to ensure last statement is processed
    if not sql.endswith('\n'):
        sql += '\n'

    lines = sql.split('\n')

    for line in lines:
        stripped_line = line.strip()

        # Skip empty lines
        if not stripped_line:
            continue

        # Skip comment lines
        if stripped_line.startswith('--'):
            continue

        # Check for multiline comment start/end
        if '/*' in line and not in_string and not in_comment:
            in_comment = True

        if '*/' in line and in_comment:
            in_comment = False
            continue

        # Skip lines inside comments
        if in_comment:
            continue

        # Check for function body start
        if ('CREATE OR REPLACE FUNCTION' in line or 'CREATE FUNCTION' in line) and not in_function_body:
            in_function_body = True

        # Process the line character by character for string detection
        i = 0
        while i < len(line):
            char = line[i]

            # Handle string literals
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_delimiter = char
            elif char == string_delimiter and in_string and (i == 0 or line[i - 1] != '\\'):
                in_string = False

            i += 1

        # Add line to current statement
        current_statement.append(line)

        # Check for function body end
        if in_function_body and stripped_line.endswith('LANGUAGE plpgsql;'):
            in_function_body = False
            statements.append('\n'.join(current_statement))
            current_statement = []
            continue

        # If we hit a statement end and we're not in a function body or string
        if stripped_line.endswith(';') and not in_function_body and not in_string:
            statements.append('\n'.join(current_statement))
            current_statement = []

    # Add any remaining statements
    if current_statement:
        statements.append('\n'.join(current_statement))

    return statements


async def run_exec_sql_setup() -> None:
    """Set up the exec_sql function for running raw SQL in Supabase."""
    try:
        client = get_supabase()

        # Create the exec_sql function in the public schema
        sql = """
        CREATE OR REPLACE FUNCTION exec_sql(sql text) RETURNS JSONB
        LANGUAGE plpgsql SECURITY DEFINER
        AS $$
        DECLARE
            result JSONB;
        BEGIN
            EXECUTE sql;
            result := '{"success": true}'::JSONB;
            RETURN result;
        EXCEPTION WHEN OTHERS THEN
            result := jsonb_build_object(
                'success', false,
                'error', SQLERRM,
                'detail', SQLSTATE
            );
            RETURN result;
        END;
        $$;
        """

        try:
            # Try to execute it directly first
            response = client.rpc("exec_sql", {"sql": "SELECT 1"}).execute()
            logger.info("exec_sql function already exists")
        except Exception:
            # If it doesn't exist, create it
            logger.info("Creating exec_sql function...")
            # This is a direct call to PostgreSQL, bypassing RLS
            # For Supabase, you'd need to make sure your service role has permissions to create this function
            await execute_sql(sql)
            logger.info("exec_sql function created successfully")
    except Exception as e:
        logger.error(f"Error setting up exec_sql function: {e}")
        # Continue anyway, as we'll try to use the regular SQL methods


async def init_database() -> None:
    """Initialize the database with all necessary tables and data."""
    try:
        # Initialize Supabase client
        init_supabase()

        # Set up exec_sql function if needed
        await run_exec_sql_setup()

        # Create game schema if it doesn't exist
        try:
            logger.info("Creating game schema if it doesn't exist...")
            await execute_sql("CREATE SCHEMA IF NOT EXISTS game;")
        except Exception as schema_error:
            logger.error(f"Error creating game schema: {schema_error}")
            # Continue anyway as it might already exist

        # Get database folder path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_folder = os.path.join(script_dir, "db")

        # Check if db folder exists in the current directory
        if not os.path.exists(db_folder):
            # Try alternative path (when run from project root)
            db_folder = os.path.join(os.getcwd(), "db")

        if not os.path.exists(db_folder):
            logger.error(f"Database folder not found at {db_folder}")
            logger.error("Please make sure the 'db' directory exists with the SQL files")
            sys.exit(1)

        logger.info(f"Initializing database from SQL files in {db_folder}")

        # Execute SQL files in order with retries
        for sql_file in SQL_FILE_ORDER:
            file_path = os.path.join(db_folder, sql_file)

            if not os.path.exists(file_path):
                logger.warning(f"SQL file {sql_file} not found in {db_folder}, skipping")
                continue

            # Wait a short time between files to avoid overwhelming the database
            await asyncio.sleep(1)

            try:
                logger.info(f"Executing {sql_file}...")
                await execute_sql_file(file_path)
            except Exception as file_error:
                logger.error(f"Error executing {sql_file}: {file_error}")
                if sql_file in ["01_schema.sql", "02_tables.sql"]:
                    # Critical files - can't continue without tables
                    raise
                else:
                    # Non-critical files - can continue with warnings
                    logger.warning(f"Skipping {sql_file} due to errors, some functionality may be missing")

        logger.info("Database initialization process completed")

        # Verify initialization by checking for some key tables
        try:
            # Check if players table exists
            result = await execute_sql(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'game' AND table_name = 'players');")
            if result and result[0]['exists']:
                logger.info("Verification: players table exists")
            else:
                logger.warning("Verification failed: players table not found")

            # Check if districts table exists
            result = await execute_sql(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'game' AND table_name = 'districts');")
            if result and result[0]['exists']:
                logger.info("Verification: districts table exists")

                # Check if there's data in the districts table
                result = await execute_sql("SELECT COUNT(*) FROM game.districts;")
                if result and result[0]['count'] > 0:
                    logger.info(f"Verification: districts table has {result[0]['count']} rows")
                else:
                    logger.warning("Verification: districts table is empty")
            else:
                logger.warning("Verification failed: districts table not found")

        except Exception as verify_error:
            logger.error(f"Verification error: {verify_error}")
            logger.warning("Database may not be fully initialized")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Initializing database...")
    print("This will create all the necessary tables and data for the Meta Game bot.")
    print("Make sure your Supabase credentials are set in the .env file.")

    try:
        asyncio.run(init_database())
        print("Database initialization complete! You can now run the bot with 'python main.py'")
    except KeyboardInterrupt:
        print("\nDatabase initialization canceled.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)