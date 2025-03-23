#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database module for the Meta Game.

This module provides a unified API for database operations, consolidating
functionality from supabase_client.py and queries.py to eliminate duplication.
"""

# Re-export all public functions from our new db_client module
from db_client import (
    # Core database functionality
    init_supabase,
    get_supabase,
    execute_function,
    execute_sql,
    check_schema_exists,

    # Player management
    player_exists,
    get_player,
    get_player_by_telegram_id,
    register_player,

    # Language and preferences
    get_player_language,
    set_player_language,

    # Game cycle and actions
    get_cycle_info,
    is_submission_open,
    submit_action,
    cancel_latest_action,

    # Districts and map
    get_districts,
    get_district_info,
    get_map_data,

    # Resources and economy
    exchange_resources,
    check_income,

    # News and information
    get_latest_news,

    # Politicians
    get_politicians,
    get_politician_status,

    # Collective actions
    initiate_collective_action,
    join_collective_action,
    get_active_collective_actions,
    get_collective_action,

    # Admin functions
    admin_process_actions,
    admin_generate_international_effects,
)

__all__ = [
    # Core database functionality
    'init_supabase',
    'get_supabase',
    'execute_function',
    'execute_sql',
    'check_schema_exists',

    # Player management
    'player_exists',
    'get_player',
    'get_player_by_telegram_id',
    'register_player',

    # Language and preferences
    'get_player_language',
    'set_player_language',

    # Game cycle and actions
    'get_cycle_info',
    'is_submission_open',
    'submit_action',
    'cancel_latest_action',

    # Districts and map
    'get_districts',
    'get_district_info',
    'get_map_data',

    # Resources and economy
    'exchange_resources',
    'check_income',

    # News and information
    'get_latest_news',

    # Politicians
    'get_politicians',
    'get_politician_status',

    # Collective actions
    'initiate_collective_action',
    'join_collective_action',
    'get_active_collective_actions',
    'get_collective_action',

    # Admin functions
    'admin_process_actions',
    'admin_generate_international_effects',
]
