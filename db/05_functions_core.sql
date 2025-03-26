-- 05_functions_core.sql
-- Core utility functions for the game

-- Get the current active game cycle
CREATE OR REPLACE FUNCTION get_current_cycle()
RETURNS cycles AS $$
DECLARE
    current_cycle cycles;
BEGIN
    SELECT * INTO current_cycle 
    FROM cycles
    WHERE is_active = TRUE 
    LIMIT 1;
    
    RETURN current_cycle;
END;
$$ LANGUAGE plpgsql;

-- Check if submissions are still open for the current cycle
CREATE OR REPLACE FUNCTION is_submission_open()
RETURNS BOOLEAN AS $$
DECLARE
    current_cycle cycles;
BEGIN
    SELECT * INTO current_cycle FROM get_current_cycle();
    
    IF current_cycle IS NULL THEN
        RETURN FALSE;
    END IF;
    
    RETURN NOW() < current_cycle.submission_deadline;
END;
$$ LANGUAGE plpgsql;

-- Calculate time left until deadline
CREATE OR REPLACE FUNCTION time_until_deadline()
RETURNS INTERVAL AS $$
DECLARE
    current_cycle cycles;
BEGIN
    SELECT * INTO current_cycle FROM get_current_cycle();
    
    IF current_cycle IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN current_cycle.submission_deadline - NOW();
END;
$$ LANGUAGE plpgsql;

-- Calculate time left until results
CREATE OR REPLACE FUNCTION time_until_results()
RETURNS INTERVAL AS $$
DECLARE
    current_cycle cycles;
BEGIN
    SELECT * INTO current_cycle FROM get_current_cycle();
    
    IF current_cycle IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN current_cycle.results_time - NOW();
END;
$$ LANGUAGE plpgsql;

-- Get player by Telegram ID
CREATE OR REPLACE FUNCTION get_player_by_telegram_id(p_telegram_id TEXT)
RETURNS players AS $$
DECLARE
    player_record players;
BEGIN
    SELECT * INTO player_record
    FROM players
    WHERE telegram_id = p_telegram_id;
    
    RETURN player_record;
END;
$$ LANGUAGE plpgsql;

-- Check if a player exists
CREATE OR REPLACE FUNCTION player_exists(p_telegram_id TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM players WHERE telegram_id = p_telegram_id
    );
END;
$$ LANGUAGE plpgsql;

-- Get district by name
CREATE OR REPLACE FUNCTION get_district_by_name(p_district_name TEXT)
RETURNS districts AS $$
DECLARE
    district_record districts;
BEGIN
    SELECT * INTO district_record
    FROM districts
    WHERE LOWER(name) = LOWER(p_district_name);
    
    RETURN district_record;
END;
$$ LANGUAGE plpgsql;

-- Get politician by name
CREATE OR REPLACE FUNCTION get_politician_by_name(p_politician_name TEXT)
RETURNS politicians AS $$
DECLARE
    politician_record politicians;
BEGIN
    SELECT * INTO politician_record
    FROM politicians
    WHERE LOWER(name) = LOWER(p_politician_name);
    
    RETURN politician_record;
END;
$$ LANGUAGE plpgsql;

-- Get player's resources
CREATE OR REPLACE FUNCTION get_player_resources(p_player_id UUID)
RETURNS resources AS $$
DECLARE
    resources_record resources;
BEGIN
    SELECT * INTO resources_record
    FROM resources
    WHERE player_id = p_player_id;
    
    RETURN resources_record;
END;
$$ LANGUAGE plpgsql;

-- Get a player's control in a district
CREATE OR REPLACE FUNCTION get_player_district_control(p_player_id UUID, p_district_id UUID)
RETURNS district_control AS $$
DECLARE
    control_record district_control;
BEGIN
    SELECT * INTO control_record
    FROM district_control
    WHERE player_id = p_player_id AND district_id = p_district_id;
    
    RETURN control_record;
END;
$$ LANGUAGE plpgsql;

-- Get controlling player of a district
CREATE OR REPLACE FUNCTION get_district_controller(p_district_id UUID)
RETURNS players AS $$
DECLARE
    controlling_player players;
BEGIN
    SELECT p.* INTO controlling_player
    FROM players p
    JOIN district_control dc ON p.player_id = dc.player_id
    WHERE dc.district_id = p_district_id AND dc.control_points >= 60
    ORDER BY dc.control_points DESC
    LIMIT 1;
    
    RETURN controlling_player;
END;
$$ LANGUAGE plpgsql;

-- Get a player's relationship with a politician
CREATE OR REPLACE FUNCTION get_player_politician_relation(p_player_id UUID, p_politician_id UUID)
RETURNS player_politician_relations AS $$
DECLARE
    relation_record player_politician_relations;
BEGIN
    SELECT * INTO relation_record
    FROM player_politician_relations
    WHERE player_id = p_player_id AND politician_id = p_politician_id;
    
    -- If no relation exists, create a default one
    IF relation_record IS NULL THEN
        INSERT INTO player_politician_relations (
            player_id,
            politician_id,
            friendliness_level
        ) VALUES (
            p_player_id,
            p_politician_id,
            50
        ) RETURNING * INTO relation_record;
    END IF;
    
    RETURN relation_record;
END;
$$ LANGUAGE plpgsql;

-- Create the next cycle
CREATE OR REPLACE FUNCTION create_next_cycle()
RETURNS cycles AS $$
DECLARE
    current_cycle cycles;
    new_cycle cycles;
    next_cycle_type TEXT;
    next_cycle_date DATE;
    next_submission_deadline TIMESTAMP WITH TIME ZONE;
    next_results_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Get the current active cycle
    SELECT * INTO current_cycle FROM get_current_cycle();
    
    -- Determine next cycle type and date
    IF current_cycle IS NULL THEN
        -- If no active cycle, start with morning
        next_cycle_type := 'morning';
        next_cycle_date := CURRENT_DATE;
    ELSE
        -- Set current cycle as completed
        UPDATE cycles SET is_active = FALSE, is_completed = TRUE
        WHERE cycle_id = current_cycle.cycle_id;
        
        -- Determine next cycle
        IF current_cycle.cycle_type = 'morning' THEN
            next_cycle_type := 'evening';
            next_cycle_date := current_cycle.cycle_date;
        ELSE
            next_cycle_type := 'morning';
            next_cycle_date := current_cycle.cycle_date + 1;
        END IF;
    END IF;
    
    -- Set deadline times
    IF next_cycle_type = 'morning' THEN
        next_submission_deadline := (next_cycle_date + TIME '12:00:00')::TIMESTAMP WITH TIME ZONE;
        next_results_time := (next_cycle_date + TIME '13:00:00')::TIMESTAMP WITH TIME ZONE;
    ELSE
        next_submission_deadline := (next_cycle_date + TIME '18:00:00')::TIMESTAMP WITH TIME ZONE;
        next_results_time := (next_cycle_date + TIME '19:00:00')::TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Create the new cycle
    INSERT INTO cycles (
        cycle_type,
        cycle_date,
        submission_deadline,
        results_time,
        is_active
    ) VALUES (
        next_cycle_type,
        next_cycle_date,
        next_submission_deadline,
        next_results_time,
        TRUE
    ) RETURNING * INTO new_cycle;
    
    -- Reset player actions for the new cycle
    UPDATE players
    SET 
        remaining_actions = 1,
        remaining_quick_actions = 2;
    
    RETURN new_cycle;
END;
$$ LANGUAGE plpgsql;

-- Get translation for a key
CREATE OR REPLACE FUNCTION get_translation(p_key TEXT, p_language TEXT DEFAULT 'en_US')
RETURNS TEXT AS $$
DECLARE
    translation_text TEXT;
BEGIN
    IF p_language = 'ru_RU' THEN
        SELECT ru_RU INTO translation_text
        FROM translations
        WHERE translation_key = p_key;
    ELSE
        SELECT en_US INTO translation_text
        FROM translations
        WHERE translation_key = p_key;
    END IF;
    
    -- Return the key if no translation is found
    IF translation_text IS NULL THEN
        RETURN p_key;
    END IF;
    
    RETURN translation_text;
END;
$$ LANGUAGE plpgsql;

-- Calculate resource changes based on district control
CREATE OR REPLACE FUNCTION calculate_district_resources(p_player_id UUID, p_district_id UUID)
RETURNS TABLE(
    influence_gain INTEGER,
    money_gain INTEGER,
    information_gain INTEGER,
    force_gain INTEGER
) AS $$
DECLARE
    district_record districts;
    control_record district_control;
    resource_multiplier DECIMAL;
BEGIN
    -- Get district and control information
    SELECT * INTO district_record FROM districts WHERE district_id = p_district_id;
    SELECT * INTO control_record FROM district_control WHERE player_id = p_player_id AND district_id = p_district_id;
    
    -- Default values if no control exists
    influence_gain := 0;
    money_gain := 0;
    information_gain := 0;
    force_gain := 0;
    
    -- If control exists, calculate resource gains based on control points
    IF control_record IS NOT NULL THEN
        -- Determine multiplier based on control points
        IF control_record.control_points >= 75 THEN
            resource_multiplier := 1.2; -- 120%
        ELSIF control_record.control_points >= 50 THEN
            resource_multiplier := 1.0; -- 100%
        ELSIF control_record.control_points >= 35 THEN
            resource_multiplier := 0.8; -- 80%
        ELSIF control_record.control_points >= 20 THEN
            resource_multiplier := 0.6; -- 60%
        ELSE
            resource_multiplier := 0.4; -- 40%
        END IF;
        
        -- Calculate resource gains
        influence_gain := FLOOR(district_record.influence_resource * resource_multiplier);
        money_gain := FLOOR(district_record.money_resource * resource_multiplier);
        information_gain := FLOOR(district_record.information_resource * resource_multiplier);
        force_gain := FLOOR(district_record.force_resource * resource_multiplier);
    END IF;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Get actions remaining for a player
CREATE OR REPLACE FUNCTION get_player_actions_remaining(p_player_id UUID)
RETURNS TABLE(
    remaining_actions INTEGER,
    remaining_quick_actions INTEGER
) AS $$
DECLARE
    player_record players;
    used_actions INTEGER;
    used_quick_actions INTEGER;
    current_cycle UUID;
BEGIN
    -- Get player data
    SELECT * INTO player_record FROM players WHERE player_id = p_player_id;
    
    -- Get current cycle
    SELECT cycle_id INTO current_cycle FROM get_current_cycle();
    
    -- Count used actions in current cycle
    SELECT COUNT(*) INTO used_actions
    FROM actions
    WHERE 
        player_id = p_player_id 
        AND cycle_id = current_cycle 
        AND is_quick_action = FALSE
        AND status != 'cancelled';
    
    SELECT COUNT(*) INTO used_quick_actions
    FROM actions
    WHERE 
        player_id = p_player_id 
        AND cycle_id = current_cycle 
        AND is_quick_action = TRUE
        AND status != 'cancelled';
    
    -- Calculate remaining actions
    remaining_actions := player_record.remaining_actions - used_actions;
    remaining_quick_actions := player_record.remaining_quick_actions - used_quick_actions;
    
    -- Ensure we don't return negative values
    IF remaining_actions < 0 THEN
        remaining_actions := 0;
    END IF;
    
    IF remaining_quick_actions < 0 THEN
        remaining_quick_actions := 0;
    END IF;
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Function to create a new game news item
CREATE OR REPLACE FUNCTION create_news(
    p_title TEXT,
    p_content TEXT,
    p_news_type TEXT DEFAULT 'public',
    p_target_player_id UUID DEFAULT NULL,
    p_related_district_id UUID DEFAULT NULL,
    p_created_by UUID DEFAULT NULL
)
RETURNS news AS $$
DECLARE
    current_cycle UUID;
    new_news news;
BEGIN
    -- Get current cycle
    SELECT cycle_id INTO current_cycle FROM get_current_cycle();
    
    -- Create news item
    INSERT INTO news (
        cycle_id,
        title,
        content,
        news_type,
        target_player_id,
        related_district_id,
        created_by
    ) VALUES (
        current_cycle,
        p_title,
        p_content,
        p_news_type,
        p_target_player_id,
        p_related_district_id,
        p_created_by
    ) RETURNING * INTO new_news;
    
    RETURN new_news;
END;
$$ LANGUAGE plpgsql;

-- Calculate ideological compatibility between player and politician
CREATE OR REPLACE FUNCTION calculate_ideology_compatibility(p_player_id UUID, p_politician_id UUID)
RETURNS INTEGER AS $$
DECLARE
    player_ideology INTEGER;
    politician_ideology INTEGER;
    ideology_difference INTEGER;
    compatibility_bonus INTEGER;
BEGIN
    -- Get ideologies
    SELECT ideology_score INTO player_ideology
    FROM players
    WHERE player_id = p_player_id;
    
    SELECT ideological_leaning INTO politician_ideology
    FROM politicians
    WHERE politician_id = p_politician_id;
    
    -- Calculate difference and resulting bonus/penalty
    ideology_difference := ABS(player_ideology - politician_ideology);
    
    IF ideology_difference <= 2 THEN
        compatibility_bonus := 2; -- Small difference: +2 CP per cycle
    ELSIF ideology_difference >= 3 THEN
        compatibility_bonus := -5; -- Large difference: -5 CP per cycle
    ELSE
        compatibility_bonus := 0; -- Neutral
    END IF;
    
    RETURN compatibility_bonus;
END;
$$ LANGUAGE plpgsql;

-- Random number generator for game mechanics
CREATE OR REPLACE FUNCTION random_int(min_val INTEGER, max_val INTEGER)
RETURNS INTEGER AS $$
BEGIN
    RETURN floor(random() * (max_val - min_val + 1) + min_val)::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- Get the latest action for a player
CREATE OR REPLACE FUNCTION get_latest_player_action(p_player_id UUID)
RETURNS actions AS $$
DECLARE
    latest_action actions;
BEGIN
    SELECT * INTO latest_action
    FROM actions
    WHERE player_id = p_player_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    RETURN latest_action;
END;
$$ LANGUAGE plpgsql;
