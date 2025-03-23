-- 11_fix_player_exists.sql
-- Create public.player_exists function for better accessibility

-- This function mirrors game.player_exists but is in the public schema
-- and has SECURITY DEFINER to ensure it works with RLS policies
CREATE OR REPLACE FUNCTION public.player_exists(p_telegram_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM game.players WHERE telegram_id = p_telegram_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to anon and authenticated roles
GRANT EXECUTE ON FUNCTION public.player_exists(TEXT) TO anon, authenticated;

-- Also create a similar function for getting a player by telegram_id
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

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.get_player_by_telegram_id(TEXT) TO anon, authenticated;

-- Create a function to get translations
CREATE OR REPLACE FUNCTION public.get_translations()
RETURNS JSONB AS $$
DECLARE
    translations JSONB;
BEGIN
    SELECT jsonb_object_agg(translation_key,
        jsonb_build_object(
            'en_US', en_US,
            'ru_RU', ru_RU
        )
    ) INTO translations
    FROM game.translations;

    RETURN translations;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.get_translations() TO anon, authenticated;