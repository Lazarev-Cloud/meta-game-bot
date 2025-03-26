-- Create function for player_exists both in game schema and public schema
-- First in game schema for proper organization
CREATE OR REPLACE FUNCTION player_exists(p_telegram_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM players WHERE telegram_id = p_telegram_id
    );
END;
$$ LANGUAGE plpgsql;

-- Then in public schema for Supabase RPC compatibility
CREATE OR REPLACE FUNCTION public.player_exists(p_telegram_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Call the original function in the game schema
    RETURN player_exists(p_telegram_id);
END;
$$ LANGUAGE plpgsql;

-- Create a public version of api_register_player for RPC compatibility
CREATE OR REPLACE FUNCTION public.api_register_player(
    p_telegram_id TEXT,
    p_name TEXT,
    p_ideology_score INTEGER DEFAULT 0,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS json AS $$
DECLARE
    new_player players;
    response json;
BEGIN
    -- Check if player already exists
    IF player_exists(p_telegram_id) THEN
        RAISE EXCEPTION 'Player with this Telegram ID already exists';
    END IF;

    -- Validate ideology score
    IF p_ideology_score < -5 OR p_ideology_score > 5 THEN
        RAISE EXCEPTION 'Ideology score must be between -5 and 5';
    END IF;

    -- Create player record
    INSERT INTO players (
        telegram_id,
        name,
        ideology_score,
        remaining_actions,
        remaining_quick_actions,
        language
    ) VALUES (
        p_telegram_id,
        p_name,
        p_ideology_score,
        1,
        2,
        p_language
    ) RETURNING * INTO new_player;

    -- Create initial resources for player
    INSERT INTO resources (
        player_id,
        influence_amount,
        money_amount,
        information_amount,
        force_amount
    ) VALUES (
        new_player.player_id,
        5, -- Starting influence
        10, -- Starting money
        3, -- Starting information
        2  -- Starting force
    );

    -- Create response JSON
    response := json_build_object(
        'success', true,
        'player_id', new_player.player_id,
        'telegram_id', new_player.telegram_id,
        'name', new_player.name,
        'ideology_score', new_player.ideology_score
    );

    RETURN response;
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql;

-- Create a public version of api_get_player_status for RPC compatibility
CREATE OR REPLACE FUNCTION public.api_get_player_status(
    p_telegram_id TEXT,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS json AS $$
DECLARE
    player_rec players;
    resources_rec resources;
    controlled_districts json;
    response json;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM players WHERE telegram_id = p_telegram_id;

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Get player resources
    SELECT * INTO resources_rec FROM resources WHERE player_id = player_rec.player_id;

    -- Build response with minimal data needed to start
    response := json_build_object(
        'player_id', player_rec.player_id,
        'player_name', player_rec.name,
        'telegram_id', player_rec.telegram_id,
        'ideology_score', player_rec.ideology_score,
        'resources', json_build_object(
            'influence', COALESCE(resources_rec.influence_amount, 0),
            'money', COALESCE(resources_rec.money_amount, 0),
            'information', COALESCE(resources_rec.information_amount, 0),
            'force', COALESCE(resources_rec.force_amount, 0)
        ),
        'actions_remaining', player_rec.remaining_actions,
        'quick_actions_remaining', player_rec.remaining_quick_actions
    );

    RETURN response;
EXCEPTION WHEN OTHERS THEN
    RETURN json_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql;