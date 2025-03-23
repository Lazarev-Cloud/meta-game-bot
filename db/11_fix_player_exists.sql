-- Create the game schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS game;

-- Create the players table if it doesn't exist
CREATE TABLE IF NOT EXISTS game.players (
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

-- Create resources table if it doesn't exist
CREATE TABLE IF NOT EXISTS game.resources (
    resource_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES game.players(player_id) ON DELETE CASCADE,
    influence_amount INTEGER NOT NULL DEFAULT 0 CHECK (influence_amount >= 0),
    money_amount INTEGER NOT NULL DEFAULT 0 CHECK (money_amount >= 0),
    information_amount INTEGER NOT NULL DEFAULT 0 CHECK (information_amount >= 0),
    force_amount INTEGER NOT NULL DEFAULT 0 CHECK (force_amount >= 0),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (player_id)
);

-- Create the player_exists function in the PUBLIC schema
CREATE OR REPLACE FUNCTION public.player_exists(p_telegram_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM game.players WHERE telegram_id = p_telegram_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the get_player_by_telegram_id function in the PUBLIC schema
CREATE OR REPLACE FUNCTION public.get_player_by_telegram_id(p_telegram_id TEXT)
RETURNS JSONB AS $$
DECLARE
    player_rec RECORD;
BEGIN
    SELECT * INTO player_rec FROM game.players WHERE telegram_id = p_telegram_id;

    IF player_rec IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN to_jsonb(player_rec);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the api_register_player function in the PUBLIC schema
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
    IF EXISTS (SELECT 1 FROM game.players WHERE telegram_id = p_telegram_id) THEN
        RETURN jsonb_build_object('success', false, 'message', 'Player already exists');
    END IF;

    -- Create player record
    INSERT INTO game.players (
        telegram_id,
        name,
        ideology_score
    ) VALUES (
        p_telegram_id,
        p_name,
        p_ideology_score
    ) RETURNING player_id INTO new_player_id;

    -- Create initial resources for player
    INSERT INTO game.resources (
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

-- Create function to run raw SQL (needed for other functions)
CREATE OR REPLACE FUNCTION exec_sql(sql text) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    result JSONB;
BEGIN
    EXECUTE sql;
    result := '{"success": true}'::JSONB;
    RETURN result;
EXCEPTION WHEN OTHERS THEN
    result := jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'detail', SQLSTATE
    );
    RETURN result;
END;
$$;


-- Create the translations table in the game schema
CREATE TABLE IF NOT EXISTS game.translations (
    translation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    translation_key TEXT NOT NULL UNIQUE,
    en_US TEXT NOT NULL,
    ru_RU TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert some basic translations
INSERT INTO game.translations (translation_key, en_US, ru_RU) VALUES
('resources.influence', 'Influence', 'Влияние'),
('resources.money', 'Money', 'Деньги'),
('resources.information', 'Information', 'Информация'),
('resources.force', 'Force', 'Сила'),
('cycle.morning', 'Morning', 'Утро'),
('cycle.evening', 'Evening', 'Вечер')
ON CONFLICT (translation_key) DO NOTHING;

-- Fix for the code that tries to access the table
-- Create a function to retrieve translations
CREATE OR REPLACE FUNCTION public.get_translations()
RETURNS JSONB AS $$
DECLARE
    translations_data JSONB;
BEGIN
    SELECT json_object_agg(
        translation_key,
        json_build_object(
            'en_US', en_US,
            'ru_RU', ru_RU
        )
    ) INTO translations_data
    FROM game.translations;

    RETURN translations_data;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Create the translations table in the game schema
CREATE TABLE IF NOT EXISTS game.translations (
    translation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    translation_key TEXT NOT NULL UNIQUE,
    en_US TEXT NOT NULL,
    ru_RU TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert some basic translations
INSERT INTO game.translations (translation_key, en_US, ru_RU) VALUES
('resources.influence', 'Influence', 'Влияние'),
('resources.money', 'Money', 'Деньги'),
('resources.information', 'Information', 'Информация'),
('resources.force', 'Force', 'Сила'),
('cycle.morning', 'Morning', 'Утро'),
('cycle.evening', 'Evening', 'Вечер')
ON CONFLICT (translation_key) DO NOTHING;

-- Create a function to retrieve translations
CREATE OR REPLACE FUNCTION public.get_translations()
RETURNS JSONB AS $$
DECLARE
    translations_data JSONB;
BEGIN
    SELECT json_object_agg(
        translation_key,
        json_build_object(
            'en_US', en_US,
            'ru_RU', ru_RU
        )
    ) INTO translations_data
    FROM game.translations;

    RETURN translations_data;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;