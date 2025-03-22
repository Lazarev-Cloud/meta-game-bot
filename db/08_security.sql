-- 08_security.sql
-- Security setup including roles and row-level security policies

-- Create application roles
CREATE ROLE game_admin;
CREATE ROLE game_player;
CREATE ROLE game_anonymous;

-- Grant usage on schema
GRANT USAGE ON SCHEMA game TO game_admin, game_player, game_anonymous;

-- Administrator permissions (full access)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA game TO game_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA game TO game_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA game TO game_admin;

-- Player permissions (limited access)
GRANT SELECT, INSERT, UPDATE, DELETE ON 
    game.players,
    game.actions,
    game.resource_history,
    game.news
TO game_player;

GRANT SELECT ON
    game.districts,
    game.politicians,
    game.cycles,
    game.translations,
    game.collective_actions,
    game.district_control
TO game_player;

GRANT SELECT, UPDATE ON
    game.resources
TO game_player;

GRANT SELECT, INSERT, UPDATE ON
    game.player_politician_relations,
    game.collective_action_participants
TO game_player;

GRANT EXECUTE ON FUNCTION
    game.api_register_player,
    game.api_get_player_status,
    game.api_submit_action,
    game.api_cancel_latest_action,
    game.api_get_district_info,
    game.api_initiate_collective_action,
    game.api_join_collective_action,
    game.api_get_cycle_info,
    game.api_get_latest_news,
    game.api_get_map_data,
    game.api_exchange_resources,
    game.api_check_income,
    game.api_get_politicians,
    game.api_get_politician_status
TO game_player;

-- Anonymous permissions (very limited)
GRANT SELECT ON
    game.districts,
    game.cycles,
    game.translations
TO game_anonymous;

GRANT EXECUTE ON FUNCTION
    game.api_register_player,
    game.api_get_cycle_info,
    game.api_get_map_data
TO game_anonymous;

-- Enable Row-Level Security on all tables
ALTER TABLE game.players ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.district_control ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.resource_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.player_politician_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.news ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.collective_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE game.collective_action_participants ENABLE ROW LEVEL SECURITY;

-- Create RLS policies

-- Players table
CREATE POLICY players_admin_all ON game.players
    TO game_admin USING (TRUE);

CREATE POLICY players_view_own ON game.players
    TO game_player USING (telegram_id = current_setting('app.current_user_id'));

CREATE POLICY players_view_all_limited ON game.players
    TO game_player USING (TRUE)
    WITH CHECK (telegram_id = current_setting('app.current_user_id'));

-- Resources table
CREATE POLICY resources_admin_all ON game.resources
    TO game_admin USING (TRUE);

CREATE POLICY resources_view_own ON game.resources
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

CREATE POLICY resources_update_own ON game.resources
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    )) WITH CHECK (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

-- Actions table
CREATE POLICY actions_admin_all ON game.actions
    TO game_admin USING (TRUE);

CREATE POLICY actions_view_own ON game.actions
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

CREATE POLICY actions_insert_own ON game.actions
    TO game_player WITH CHECK (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

CREATE POLICY actions_update_own ON game.actions
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    )) WITH CHECK (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

-- District control table
CREATE POLICY district_control_admin_all ON game.district_control
    TO game_admin USING (TRUE);

CREATE POLICY district_control_view_own ON game.district_control
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

CREATE POLICY district_control_view_all_limited ON game.district_control
    TO game_player USING (TRUE);

-- Resource history table
CREATE POLICY resource_history_admin_all ON game.resource_history
    TO game_admin USING (TRUE);

CREATE POLICY resource_history_view_own ON game.resource_history
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

-- Player-politician relations table
CREATE POLICY player_politician_relations_admin_all ON game.player_politician_relations
    TO game_admin USING (TRUE);

CREATE POLICY player_politician_relations_view_own ON game.player_politician_relations
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

CREATE POLICY player_politician_relations_update_own ON game.player_politician_relations
    TO game_player USING (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    )) WITH CHECK (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

-- News table
CREATE POLICY news_admin_all ON game.news
    TO game_admin USING (TRUE);

CREATE POLICY news_view_public ON game.news
    TO game_player USING (news_type = 'public');

CREATE POLICY news_view_own_faction ON game.news
    TO game_player USING (
        news_type = 'faction' AND 
        target_player_id IN (
            SELECT player_id FROM game.players 
            WHERE telegram_id = current_setting('app.current_user_id')
        )
    );

-- Collective actions table
CREATE POLICY collective_actions_admin_all ON game.collective_actions
    TO game_admin USING (TRUE);

CREATE POLICY collective_actions_view_all ON game.collective_actions
    TO game_player USING (TRUE);

CREATE POLICY collective_actions_insert_own ON game.collective_actions
    TO game_player WITH CHECK (initiator_player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

-- Collective action participants table
CREATE POLICY collective_action_participants_admin_all ON game.collective_action_participants
    TO game_admin USING (TRUE);

CREATE POLICY collective_action_participants_view_all ON game.collective_action_participants
    TO game_player USING (TRUE);

CREATE POLICY collective_action_participants_insert_own ON game.collective_action_participants
    TO game_player WITH CHECK (player_id IN (
        SELECT player_id FROM game.players 
        WHERE telegram_id = current_setting('app.current_user_id')
    ));

-- Create function to set current user
CREATE OR REPLACE FUNCTION game.set_current_user(p_telegram_id TEXT)
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_user_id', p_telegram_id, FALSE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to check if user is admin
CREATE OR REPLACE FUNCTION game.is_admin(p_telegram_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    is_admin_user BOOLEAN;
BEGIN
    SELECT is_admin INTO is_admin_user
    FROM game.players
    WHERE telegram_id = p_telegram_id;
    
    RETURN COALESCE(is_admin_user, FALSE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create authentication function for the API
CREATE OR REPLACE FUNCTION game.authenticate_api_user(
    p_telegram_id TEXT
)
RETURNS TEXT AS $$
DECLARE
    user_role TEXT;
BEGIN
    -- Set the current user for RLS
    PERFORM game.set_current_user(p_telegram_id);
    
    -- Check if user exists and is active
    IF EXISTS (
        SELECT 1 FROM game.players 
        WHERE telegram_id = p_telegram_id AND is_active = TRUE
    ) THEN
        -- Check if user is admin
        IF game.is_admin(p_telegram_id) THEN
            user_role := 'game_admin';
        ELSE
            user_role := 'game_player';
        END IF;
    ELSE
        user_role := 'game_anonymous';
    END IF;
    
    RETURN user_role;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
