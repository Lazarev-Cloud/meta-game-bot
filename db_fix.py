#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database fix script to resolve schema and function access issues.
This script creates the necessary schema and functions with proper permissions.
"""

import asyncio
import logging
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("db_fix.log")
    ]
)

logger = logging.getLogger("db_fix")

# Try to use the supabase client from the project
try:
    from db.supabase_client import get_supabase, init_supabase, execute_sql
except ImportError:
    logger.error("Cannot import from db.supabase_client. Make sure you're running this script from the project root.")
    sys.exit(1)


async def check_and_create_schema():
    """Check if game schema exists and create it if not."""
    try:
        # Initialize the Supabase client
        init_supabase()
        client = get_supabase()

        # Check if game schema exists
        logger.info("Checking if game schema exists...")

        try:
            # Try to execute a direct query to check if the schema exists
            sql = "SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = 'public');"
            response = await execute_sql(sql)

            schema_exists = False
            if response and response[0] and 'exists' in response[0]:
                schema_exists = response[0]['exists']

            if schema_exists:
                logger.info("Game schema already exists.")
            else:
                logger.info("Game schema does not exist. Creating it...")
                await execute_sql("CREATE SCHEMA IF NOT EXISTS game;")
                logger.info("Game schema created successfully.")

            # Create the player_exists function with public schema visibility
            logger.info("Creating player_exists function with public accessibility...")
            sql = """
            CREATE OR REPLACE FUNCTION public.player_exists(p_telegram_id TEXT)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN EXISTS (
                    SELECT 1 FROM players WHERE telegram_id = p_telegram_id
                );
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
            """
            await execute_sql(sql)
            logger.info("player_exists function created successfully.")

            # Create the get_player_by_telegram_id function
            logger.info("Creating get_player_by_telegram_id function...")
            sql = """
            CREATE OR REPLACE FUNCTION public.get_player_by_telegram_id(p_telegram_id TEXT)
            RETURNS JSONB AS $$
            DECLARE
                player_rec RECORD;
            BEGIN
                SELECT * INTO player_rec FROM players WHERE telegram_id = p_telegram_id;

                IF player_rec IS NULL THEN
                    RETURN NULL;
                END IF;

                RETURN to_jsonb(player_rec);
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
            """
            await execute_sql(sql)
            logger.info("get_player_by_telegram_id function created successfully.")

            # Make sure the players table exists
            logger.info("Creating players table if it doesn't exist...")
            sql = """
            CREATE TABLE IF NOT EXISTS players (
                player_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                telegram_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                ideology_score INTEGER NOT NULL CHECK (ideology_score >= -5 AND ideology_score <= 5),
                remaining_actions INTEGER NOT NULL DEFAULT 1,
                remaining_quick_actions INTEGER NOT NULL DEFAULT 2,
                is_admin BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                language TEXT DEFAULT 'en_US',
                registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await execute_sql(sql)
            logger.info("Players table is ready.")

            # Make sure districts table exists
            logger.info("Creating districts table if it doesn't exist...")
            sql = """
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
            await execute_sql(sql)
            logger.info("Districts table is ready.")

            # Add the schema to search_path
            logger.info("Adding game schema to search_path...")
            sql = "ALTER ROLE %CURRENT_USER% SET search_path TO public, game;"
            await execute_sql(sql)
            logger.info("Search path updated.")

            # Create sample district data
            logger.info("Creating sample district data...")
            sql = """
            INSERT INTO districts (name, description, influence_resource, money_resource, information_resource, force_resource)
            VALUES 
            ('Stari Grad', 'Historical and administrative center of Novi-Sad', 2, 0, 2, 0),
            ('Liman', 'University and scientific center', 2, 0, 2, 0),
            ('Petrovaradin', 'Cultural heritage and tourism area', 2, 1, 0, 0),
            ('Podbara', 'Industrial district', 0, 3, 0, 1),
            ('Detelinara', 'Residential area, working class neighborhood', 2, 2, 0, 0),
            ('Satelit', 'New district with economic growth', 1, 3, 0, 0),
            ('Adamovicevo', 'Military objects and security zone', 1, 0, 0, 3),
            ('Sremska Kamenica', 'Suburb with shadow economy', 0, 0, 1, 3)
            ON CONFLICT (name) DO NOTHING;
            """
            await execute_sql(sql)
            logger.info("Sample district data created.")

            # Create the api_register_player function
            logger.info("Creating api_register_player function...")
            sql = """
            CREATE OR REPLACE FUNCTION public.api_register_player(
                p_telegram_id TEXT,
                p_name TEXT,
                p_ideology_score INTEGER DEFAULT 0
            )
            RETURNS JSONB AS $$
            DECLARE
                new_player_id UUID;
                resources_rec RECORD;
            BEGIN
                -- Check if player already exists
                IF EXISTS (SELECT 1 FROM players WHERE telegram_id = p_telegram_id) THEN
                    RETURN jsonb_build_object('success', false, 'message', 'Player already exists');
                END IF;

                -- Create player record
                INSERT INTO players (
                    telegram_id,
                    name,
                    ideology_score
                ) VALUES (
                    p_telegram_id,
                    p_name,
                    p_ideology_score
                ) RETURNING player_id INTO new_player_id;

                -- Create initial resources for player
                INSERT INTO resources (
                    player_id,
                    influence_amount,
                    money_amount,
                    information_amount,
                    force_amount
                ) VALUES (
                    new_player_id,
                    5, -- Starting influence
                    10, -- Starting money
                    3, -- Starting information
                    2  -- Starting force
                ) RETURNING * INTO resources_rec;

                RETURN jsonb_build_object(
                    'success', true,
                    'player_id', new_player_id,
                    'player_name', p_name,
                    'ideology_score', p_ideology_score,
                    'resources', jsonb_build_object(
                        'influence', resources_rec.influence_amount,
                        'money', resources_rec.money_amount,
                        'information', resources_rec.information_amount,
                        'force', resources_rec.force_amount
                    ),
                    'actions_remaining', 1,
                    'quick_actions_remaining', 2
                );
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
            """
            await execute_sql(sql)
            logger.info("api_register_player function created successfully.")

            # Create resources table if needed
            logger.info("Creating resources table if it doesn't exist...")
            sql = """
            CREATE TABLE IF NOT EXISTS resources (
                resource_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
                influence_amount INTEGER NOT NULL DEFAULT 0 CHECK (influence_amount >= 0),
                money_amount INTEGER NOT NULL DEFAULT 0 CHECK (money_amount >= 0),
                information_amount INTEGER NOT NULL DEFAULT 0 CHECK (information_amount >= 0),
                force_amount INTEGER NOT NULL DEFAULT 0 CHECK (force_amount >= 0),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE (player_id)
            );
            """
            await execute_sql(sql)
            logger.info("Resources table is ready.")

            logger.info("Database schema and functions have been set up successfully.")
        except Exception as e:
            logger.error(f"Error during database setup: {e}")
            raise
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        raise


async def main():
    """Run the main repair process."""
    try:
        await check_and_create_schema()
    except Exception as e:
        logger.error(f"Error fixing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
