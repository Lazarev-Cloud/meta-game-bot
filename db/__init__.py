"""
Database module for the Meta Game bot.

This module provides a unified API for database operations.
"""

# First, import core database functions that don't depend on i18n
from db.supabase_client import (
    init_supabase,
    get_supabase,
    execute_function,
    execute_sql,
    check_schema_exists
)

# Import the database functions but we'll handle player_exists/get_player specially
from db.db_client import (
    # Core database operations that don't use i18n
    db_operation,
    get_record,
    call_api_function,
    get_player_by_telegram_id,

    # Functions that use i18n which we need to modify
    player_exists,
    get_player,
    register_player,
    get_player_language,
    set_player_language,
    get_cycle_info,
    is_submission_open,
    submit_action,
    cancel_latest_action,
    get_districts,
    get_district_info,
    get_map_data,
    exchange_resources,
    check_income,
    get_latest_news,
    get_politicians,
    get_politician_status,
    initiate_collective_action,
    join_collective_action,
    get_active_collective_actions,
    get_collective_action,
    admin_process_actions,
    admin_generate_international_effects
)
def initialize_db():
    # Import remaining functions
    from db.db_client import (
        player_exists,
        get_player,
        # Additional imports
    )
    return {
        'player_exists': player_exists,
        'get_player': get_player,
    }