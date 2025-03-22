#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database initialization script for the Meta Game bot.

This script initializes all necessary tables in the Supabase database.
It reads the SQL files in the db directory and executes them in the correct order.
"""

import asyncio
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv

from db.supabase_client import get_supabase, init_supabase
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

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
    "10_sample_data.sql",  # Comment this line if you don't want sample data
]


async def execute_sql_file(file_path: str) -> None:
    """Execute a SQL file using the Supabase client."""
    try:
        # Read the SQL file
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()

        # Execute the SQL
        client = get_supabase()

        # For larger files, split into separate statements
        statements = split_sql_statements(sql)
        executed = 0

        for statement in statements:
            if statement.strip():
                try:
                    # Execute the SQL statement
                    client.postgrest.rpc("exec_sql", {"sql": statement})
                    executed += 1
                except Exception as e:
                    logger.error(f"Error executing SQL statement: {e}")
                    logger.error(f"Statement: {statement[:100]}...")

        logger.info(f"Executed {executed} SQL statements from {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"Error executing SQL file {file_path}: {e}")
        raise


def split_sql_statements(sql: str) -> List[str]:
    """Split a SQL string into individual statements, handling edge cases."""
    statements = []
    current_statement = []
    in_function_body = False
    in_string = False
    string_delimiter = None

    lines = sql.split('\n')

    for line in lines:
        # Skip comment lines
        if line.strip().startswith('--'):
            continue

        # Check for function body start/end
        if 'CREATE OR REPLACE FUNCTION' in line or 'CREATE FUNCTION' in line:
            in_function_body = True

        # Process the line character by character for string detection
        for char in line:
            if char in ['"', "'"] and not in_string:
                in_string = True
                string_delimiter = char
            elif char == string_delimiter and in_string:
                in_string = False

        # Check for function body end
        if in_function_body and line.strip().endswith('LANGUAGE plpgsql;'):
            in_function_body = False

        current_statement.append(line)

        # If we hit a statement end and we're not in a function body or string
        if line.strip().endswith(';') and not in_function_body and not in_string:
            statements.append('\n'.join(current_statement))
            current_statement = []

    # Add any remaining statements
    if current_statement:
        statements.append('\n'.join(current_statement))

    return statements


async def init_database() -> None:
    """Initialize the database with all necessary tables and data."""
    try:
        # Initialize Supabase client
        init_supabase()
        client = get_supabase()

        # Check if DB already initialized
        try:
            # Instead of directly accessing tables, use a simple check query
            response = client.postgrest.rpc("exec_sql", {
                "sql": "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'game';"})
            if response.data:
                logger.warning("Database schema 'game' already exists. Proceeding anyway.")
        except Exception as e:
            # Schema doesn't exist yet, which is expected
            logger.info("Database schema doesn't exist yet. Initializing...")

        # Get database folder path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_folder = os.path.join(script_dir, "db")

        if not os.path.exists(db_folder):
            # Try alternative path (when run from project root)
            db_folder = os.path.join(os.getcwd(), "db")

        if not os.path.exists(db_folder):
            logger.error(f"Database folder not found at {db_folder}")
            logger.error("Please run this script from the project root directory")
            sys.exit(1)

        logger.info(f"Initializing database from SQL files in {db_folder}")

        # Execute SQL files in order
        for sql_file in SQL_FILE_ORDER:
            file_path = os.path.join(db_folder, sql_file)

            if os.path.exists(file_path):
                logger.info(f"Executing {sql_file}...")
                await execute_sql_file(file_path)
            else:
                logger.warning(f"SQL file {sql_file} not found in {db_folder}")

        logger.info("Database initialization complete")

        # Verify initialization with a simple query
        try:
            response = client.postgrest.rpc("exec_sql", {"sql": "SELECT COUNT(*) FROM game.players;"})
            logger.info("Successfully verified database initialization!")
        except Exception as e:
            logger.error(f"Error verifying database: {e}")
            logger.error("Database may not be fully initialized. Please check the logs for errors.")

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