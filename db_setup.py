#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database setup helper script for the Meta Game bot.

This script performs manual setup of the database schema and functions
that are needed for the game to work properly.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("db_setup.log")
    ]
)

logger = logging.getLogger("db_setup")

# Global Supabase client
client = None


def init_client() -> Client:
    """Initialize the Supabase client."""
    global client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Missing Supabase credentials. Check your .env file.")
        sys.exit(1)

    try:
        client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        sys.exit(1)


async def execute_sql(sql: str) -> Optional[List[Dict[str, Any]]]:
    """Execute SQL directly using a direct query."""
    global client

    try:
        # For simple queries like CREATE SCHEMA, we can use the SQL endpoint
        # This bypasses the need for the exec_sql function
        response = client.rpc("exec_sql", {"sql": sql}).execute()
        if hasattr(response, 'data'):
            logger.info(f"SQL executed successfully: {sql[:50]}...")
            return response.data
        return None
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        logger.error(f"SQL statement: {sql[:100]}...")
        return None


async def check_schema_exists() -> bool:
    """Check if the game schema exists."""
    try:
        response = client.from_("pg_catalog.pg_namespace").select("nspname").eq("nspname", "public").execute()
        exists = hasattr(response, 'data') and len(response.data) > 0
        logger.info(f"Game schema exists: {exists}")
        return exists
    except Exception as e:
        logger.error(f"Error checking if schema exists: {e}")
        return False


async def setup_database():
    """Perform the database setup."""
    try:
        # Initialize Supabase client
        init_client()

        # Check if game schema exists
        schema_exists = await check_schema_exists()

        if not schema_exists:
            logger.info("Creating game schema...")
            await execute_sql("CREATE SCHEMA IF NOT EXISTS game;")
        else:
            logger.info("Game schema already exists")

        # Create essential tables if they don't exist
        logger.info("Creating essential tables...")

        # Create players table
        await execute_sql("""
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
        """)

        # Create districts table
        await execute_sql("""
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
        """)

        # Create resources table
        await execute_sql("""
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
        """)

        # Create translations table
        await execute_sql("""
        CREATE TABLE IF NOT EXISTS translations (
            translation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            translation_key TEXT NOT NULL UNIQUE,
            en_US TEXT NOT NULL,
            ru_RU TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)

        # Create a function to check if a player exists
        await execute_sql("""
        CREATE OR REPLACE FUNCTION player_exists(p_telegram_id TEXT)
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN EXISTS (
                SELECT 1 FROM players WHERE telegram_id = p_telegram_id
            );
        END;
        $$ LANGUAGE plpgsql;
        """)

        # Create sample data - districts
        logger.info("Creating sample data...")
        await execute_sql("""
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
        """)

        # Create a minimal player registration function
        await execute_sql("""
        CREATE OR REPLACE FUNCTION api_register_player(
            p_telegram_id TEXT,
            p_name TEXT,
            p_ideology_score INTEGER DEFAULT 0
        )
        RETURNS JSONB AS $$
        DECLARE
            new_player_id UUID;
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
            );

            RETURN jsonb_build_object(
                'success', true,
                'player_id', new_player_id,
                'message', 'Player registered successfully'
            );
        END;
        $$ LANGUAGE plpgsql;
        """)

        # Create a basic function to get player status
        await execute_sql("""
        CREATE OR REPLACE FUNCTION api_get_player_status(
            p_telegram_id TEXT,
            p_language TEXT DEFAULT 'en_US'
        )
        RETURNS JSONB AS $$
        DECLARE
            player_rec RECORD;
            resources_rec RECORD;
        BEGIN
            -- Get player data
            SELECT * INTO player_rec FROM players WHERE telegram_id = p_telegram_id;

            IF player_rec IS NULL THEN
                RETURN jsonb_build_object('success', false, 'message', 'Player not found');
            END IF;

            -- Get player resources
            SELECT * INTO resources_rec FROM resources WHERE player_id = player_rec.player_id;

            -- Return player status
            RETURN jsonb_build_object(
                'success', true,
                'player_name', player_rec.name,
                'ideology_score', player_rec.ideology_score,
                'resources', jsonb_build_object(
                    'influence', COALESCE(resources_rec.influence_amount, 0),
                    'money', COALESCE(resources_rec.money_amount, 0),
                    'information', COALESCE(resources_rec.information_amount, 0),
                    'force', COALESCE(resources_rec.force_amount, 0)
                ),
                'actions_remaining', player_rec.remaining_actions,
                'quick_actions_remaining', player_rec.remaining_quick_actions
            );
        END;
        $$ LANGUAGE plpgsql;
        """)

        logger.info("Database setup completed successfully")

    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Starting database setup...")
    asyncio.run(setup_database())
    print("Setup complete. Check db_setup.log for details.")
