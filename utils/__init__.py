from db import init_supabase, get_supabase, execute_function, execute_sql, check_schema_exists, player_exists, \
    get_player, get_player_by_telegram_id, register_player, get_player_language, set_player_language, get_cycle_info, \
    is_submission_open, submit_action, cancel_latest_action, get_districts, get_district_info, get_map_data, \
    exchange_resources, check_income, get_latest_news, get_politicians, get_politician_status, \
    initiate_collective_action, join_collective_action, get_active_collective_actions, get_collective_action, \
    admin_process_actions, admin_generate_international_effects
from utils.i18n import init_i18n
init_i18n(player_exists_func=player_exists, get_supabase_func=get_supabase)
db_functions = {}


def initialize_utils(db_module):
    global db_functions
    db_functions = {
        'player_exists': db_module.player_exists,
        'get_supabase': db_module.get_supabase,
        # Add other functions as needed
    }

    from utils.i18n import init_i18n
    init_i18n(player_exists_func=db_functions['player_exists'],
              get_supabase_func=db_functions['get_supabase'])


# Export getters for the functions
def get_player_exists():
    return db_functions.get('player_exists')


# Export all the functions
__all__ = [
    # Core database functionality
    'init_supabase',
    'get_supabase',
    'execute_function',
    'execute_sql',
    'check_schema_exists',
    'init_i18n',
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

