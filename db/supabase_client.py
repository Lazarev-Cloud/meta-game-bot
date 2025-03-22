#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Supabase client for database interactions.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client

# Initialize logger
logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client = None

def init_supabase() -> Client:
    """Initialize the Supabase client."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("Supabase credentials not found. Please check your .env file.")
        raise ValueError("Missing Supabase credentials")
    
    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise

def get_supabase() -> Client:
    """Get the Supabase client instance."""
    global _supabase_client
    
    if _supabase_client is None:
        return init_supabase()
    
    return _supabase_client

async def execute_function(function_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Postgres function through Supabase RPC."""
    client = get_supabase()
    try:
        response = client.rpc(function_name, params).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}")
        raise

async def get_player(telegram_id: str) -> Optional[Dict[str, Any]]:
    """Get player information by Telegram ID."""
    try:
        return await execute_function("api_get_player_status", {"p_telegram_id": telegram_id})
    except Exception:
        return None

async def register_player(telegram_id: str, name: str, ideology_score: int = 0) -> Dict[str, Any]:
    """Register a new player."""
    return await execute_function(
        "api_register_player", 
        {
            "p_telegram_id": telegram_id,
            "p_name": name,
            "p_ideology_score": ideology_score
        }
    )

async def submit_action(
    telegram_id: str,
    action_type: str,
    is_quick_action: bool,
    district_name: Optional[str] = None,
    target_player_name: Optional[str] = None,
    target_politician_name: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_amount: Optional[int] = None,
    physical_presence: bool = False,
    expected_outcome: Optional[str] = None,
    language: str = "en_US"
) -> Dict[str, Any]:
    """Submit an action."""
    return await execute_function(
        "api_submit_action",
        {
            "p_telegram_id": telegram_id,
            "p_action_type": action_type,
            "p_is_quick_action": is_quick_action,
            "p_district_name": district_name,
            "p_target_player_name": target_player_name,
            "p_target_politician_name": target_politician_name,
            "p_resource_type": resource_type,
            "p_resource_amount": resource_amount,
            "p_physical_presence": physical_presence,
            "p_expected_outcome": expected_outcome,
            "p_language": language
        }
    )

async def cancel_latest_action(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """Cancel the latest action submitted by a player."""
    return await execute_function(
        "api_cancel_latest_action",
        {
            "p_telegram_id": telegram_id,
            "p_language": language
        }
    )

async def get_district_info(telegram_id: str, district_name: str, language: str = "en_US") -> Dict[str, Any]:
    """Get information about a district."""
    return await execute_function(
        "api_get_district_info",
        {
            "p_telegram_id": telegram_id,
            "p_district_name": district_name,
            "p_language": language
        }
    )

async def get_cycle_info(language: str = "en_US") -> Dict[str, Any]:
    """Get information about the current game cycle."""
    return await execute_function(
        "api_get_cycle_info",
        {
            "p_language": language
        }
    )

async def get_latest_news(telegram_id: str, count: int = 5, language: str = "en_US") -> Dict[str, Any]:
    """Get the latest news for a player."""
    return await execute_function(
        "api_get_latest_news",
        {
            "p_telegram_id": telegram_id,
            "p_count": count,
            "p_language": language
        }
    )

async def get_map_data(language: str = "en_US") -> Dict[str, Any]:
    """Get the current map data showing district control."""
    return await execute_function(
        "api_get_map_data",
        {
            "p_language": language
        }
    )

async def exchange_resources(
    telegram_id: str,
    from_resource: str,
    to_resource: str,
    amount: int,
    language: str = "en_US"
) -> Dict[str, Any]:
    """Exchange resources."""
    return await execute_function(
        "api_exchange_resources",
        {
            "p_telegram_id": telegram_id,
            "p_from_resource": from_resource,
            "p_to_resource": to_resource,
            "p_amount": amount,
            "p_language": language
        }
    )

async def check_income(telegram_id: str, language: str = "en_US") -> Dict[str, Any]:
    """Check expected resource income."""
    return await execute_function(
        "api_check_income",
        {
            "p_telegram_id": telegram_id,
            "p_language": language
        }
    )

async def get_politicians(telegram_id: str, type: str = "local", language: str = "en_US") -> Dict[str, Any]:
    """Get politicians of specified type."""
    return await execute_function(
        "api_get_politicians",
        {
            "p_telegram_id": telegram_id,
            "p_type": type,
            "p_language": language
        }
    )

async def get_politician_status(telegram_id: str, politician_name: str, language: str = "en_US") -> Dict[str, Any]:
    """Get detailed information about a politician."""
    return await execute_function(
        "api_get_politician_status",
        {
            "p_telegram_id": telegram_id,
            "p_politician_name": politician_name,
            "p_language": language
        }
    )

async def initiate_collective_action(
    telegram_id: str,
    action_type: str,
    district_name: str,
    target_player_name: Optional[str] = None,
    resource_type: str = "influence",
    resource_amount: int = 1,
    physical_presence: bool = False,
    language: str = "en_US"
) -> Dict[str, Any]:
    """Initiate a collective action."""
    return await execute_function(
        "api_initiate_collective_action",
        {
            "p_telegram_id": telegram_id,
            "p_action_type": action_type,
            "p_district_name": district_name,
            "p_target_player_name": target_player_name,
            "p_resource_type": resource_type,
            "p_resource_amount": resource_amount,
            "p_physical_presence": physical_presence,
            "p_language": language
        }
    )

async def join_collective_action(
    telegram_id: str,
    collective_action_id: str,
    resource_type: str,
    resource_amount: int,
    physical_presence: bool = False,
    language: str = "en_US"
) -> Dict[str, Any]:
    """Join a collective action."""
    return await execute_function(
        "api_join_collective_action",
        {
            "p_telegram_id": telegram_id,
            "p_collective_action_id": collective_action_id,
            "p_resource_type": resource_type,
            "p_resource_amount": resource_amount,
            "p_physical_presence": physical_presence,
            "p_language": language
        }
    )

# Admin functions
async def admin_process_actions(telegram_id: str) -> Dict[str, Any]:
    """Process all pending actions (admin only)."""
    return await execute_function(
        "api_admin_process_actions",
        {
            "p_telegram_id": telegram_id
        }
    )

async def admin_generate_international_effects(telegram_id: str, count: int = 2) -> Dict[str, Any]:
    """Generate international effects (admin only)."""
    return await execute_function(
        "api_admin_generate_international_effects",
        {
            "p_telegram_id": telegram_id,
            "p_count": count
        }
    )