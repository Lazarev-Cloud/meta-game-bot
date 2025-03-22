#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database module for the Belgrade Game.
"""

from db.supabase_client import (
    init_supabase,
    get_supabase,
    execute_function,
    get_player,
    register_player,
    submit_action,
    cancel_latest_action,
    get_district_info,
    get_cycle_info,
    get_latest_news,
    get_map_data,
    exchange_resources,
    check_income,
    get_politicians,
    get_politician_status,
    initiate_collective_action,
    join_collective_action,
    admin_process_actions,
    admin_generate_international_effects
)

from db.queries import (
    player_exists,
    get_districts,
    get_resources,
    get_controlled_districts,
    get_district_by_name,
    get_politician_by_name,
    is_submission_open,
    get_remaining_actions,
    get_player_info,
    get_active_collective_actions,
    get_collective_action,
    get_collective_action_participants,
    get_player_politician_relations,
    get_international_effects,
    set_player_language,
    get_player_language
)

__all__ = [
    'init_supabase',
    'get_supabase',
    'execute_function',
    'get_player',
    'register_player',
    'submit_action',
    'cancel_latest_action',
    'get_district_info',
    'get_cycle_info',
    'get_latest_news',
    'get_map_data',
    'exchange_resources',
    'check_income',
    'get_politicians',
    'get_politician_status',
    'initiate_collective_action',
    'join_collective_action',
    'admin_process_actions',
    'admin_generate_international_effects',
    'player_exists',
    'get_districts',
    'get_resources',
    'get_controlled_districts',
    'get_district_by_name',
    'get_politician_by_name',
    'is_submission_open',
    'get_remaining_actions',
    'get_player_info',
    'get_active_collective_actions',
    'get_collective_action',
    'get_collective_action_participants',
    'get_player_politician_relations',
    'get_international_effects',
    'set_player_language',
    'get_player_language'
]