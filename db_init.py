#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database initialization script for the Meta Game bot.

This script initializes all necessary tables in the Supabase database.
It reads the SQL files in the db directory and executes them in the correct order.
"""

import asyncio
import os

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
        statements = sql.split(";")
        executed = 0

        for statement in statements:
            # Skip empty statements
            if statement.strip():
                try:
                    # Execute the SQL statement
                    client.postgrest.rpc("exec_sql", {"sql": statement + ";"})
                    executed += 1
                except Exception as e:
                    logger.error(f"Error executing SQL statement: {e}")
                    logger.error(f"Statement: {statement[:100]}...")

        logger.info(f"Executed {executed} SQL statements from {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"Error executing SQL file {file_path}: {e}")
        raise


async def init_database() -> None:
    """Initialize the database with all necessary tables and data."""
    try:
        # Initialize Supabase client
        init_supabase()
        client = get_supabase()

        # Check if DB already initialized
        try:
            response = client.table("players").select("count").execute()
            if response.data:
                logger.warning("Database already appears to be initialized. Aborting.")
                return
        except:
            # Table doesn't exist yet, which is expected
            pass

        # Get database folder path
        db_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db")

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
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")


if __name__ == "__main__":
    asyncio.run(init_database())
