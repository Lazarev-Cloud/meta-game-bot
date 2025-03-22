-- 07_functions_api.sql
-- API functions for integration with Telegram bot or other frontends

-- Register a new player
CREATE OR REPLACE FUNCTION game.api_register_player(
    p_telegram_id TEXT,
    p_name TEXT,
    p_ideology_score INTEGER DEFAULT 0
)
RETURNS game.players AS $$
DECLARE
    new_player game.players;
BEGIN
    -- Check if player already exists
    IF game.player_exists(p_telegram_id) THEN
        RAISE EXCEPTION 'Player with this Telegram ID already exists';
    END IF;
    
    -- Validate ideology score
    IF p_ideology_score < -5 OR p_ideology_score > 5 THEN
        RAISE EXCEPTION 'Ideology score must be between -5 and 5';
    END IF;
    
    -- Create player record
    INSERT INTO game.players (
        telegram_id,
        name,
        ideology_score,
        remaining_actions,
        remaining_quick_actions
    ) VALUES (
        p_telegram_id,
        p_name,
        p_ideology_score,
        1,
        2
    ) RETURNING * INTO new_player;
    
    -- Create initial resources for player
    INSERT INTO game.resources (
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
    
    -- Log the initial resources
    INSERT INTO game.resource_history (
        player_id,
        cycle_id,
        change_type,
        influence_change,
        money_change,
        information_change,
        force_change,
        reason
    ) VALUES (
        new_player.player_id,
        (SELECT cycle_id FROM game.get_current_cycle()),
        'initial_grant',
        5,
        10,
        3,
        2,
        'Initial resources for new player'
    );
    
    -- Create welcome news for player
    INSERT INTO game.news (
        cycle_id,
        title,
        content,
        news_type,
        target_player_id
    ) VALUES (
        (SELECT cycle_id FROM game.get_current_cycle()),
        'Welcome to Novi-Sad',
        'Welcome, ' || new_player.name || '! You have joined the game. Use your initial resources wisely to gain control of districts.',
        'faction',
        new_player.player_id
    );
    
    RETURN new_player;
END;
$$ LANGUAGE plpgsql;

-- Get player status with resources and controlled districts
CREATE OR REPLACE FUNCTION game.api_get_player_status(
    p_telegram_id TEXT,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    resources_rec game.resources;
    controlled_districts JSON;
    translatable_text TEXT;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);
    
    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;
    
    -- Get player resources
    SELECT * INTO resources_rec FROM game.get_player_resources(player_rec.player_id);
    
    -- Get controlled districts (with control points >= 60)
    SELECT json_agg(
        json_build_object(
            'district_name', d.name,
            'control_points', dc.control_points,
            'resource_influence', d.influence_resource,
            'resource_money', d.money_resource,
            'resource_information', d.information_resource,
            'resource_force', d.force_resource
        )
    ) INTO controlled_districts
    FROM game.districts d
    JOIN game.district_control dc ON d.district_id = dc.district_id
    WHERE dc.player_id = player_rec.player_id AND dc.control_points >= 60;
    
    -- Handle case when no districts are controlled
    IF controlled_districts IS NULL THEN
        controlled_districts := '[]'::JSON;
    END IF;
    
    -- Translate resource names
    translatable_text := game.get_translation('resources.influence', p_language);
    
    -- Return status as JSON
    RETURN json_build_object(
        'player_name', player_rec.name,
        'ideology_score', player_rec.ideology_score,
        'resources', json_build_object(
            'influence', resources_rec.influence_amount,
            'money', resources_rec.money_amount,
            'information', resources_rec.information_amount,
            'force', resources_rec.force_amount
        ),
        'controlled_districts', controlled_districts,
        'actions_remaining', (SELECT remaining_actions FROM game.get_player_actions_remaining(player_rec.player_id)),
        'quick_actions_remaining', (SELECT remaining_quick_actions FROM game.get_player_actions_remaining(player_rec.player_id))
    );
END;
$$ LANGUAGE plpgsql;

-- Submit a new action
CREATE OR REPLACE FUNCTION game.api_submit_action(
    p_telegram_id TEXT,
    p_action_type TEXT,
    p_is_quick_action BOOLEAN,
    p_district_name TEXT DEFAULT NULL,
    p_target_player_name TEXT DEFAULT NULL,
    p_target_politician_name TEXT DEFAULT NULL,
    p_resource_type TEXT DEFAULT NULL,
    p_resource_amount INTEGER DEFAULT NULL,
    p_physical_presence BOOLEAN DEFAULT FALSE,
    p_expected_outcome TEXT DEFAULT NULL,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    district_rec game.districts;
    target_player_rec game.players;
    target_politician_rec game.politicians;
    remaining_actions INTEGER;
    remaining_quick_actions INTEGER;
    current_cycle UUID;
    new_action game.actions;
    action_response TEXT;
    response_title TEXT;
BEGIN
    -- Check if submissions are open
    IF NOT game.is_submission_open() THEN
        RAISE EXCEPTION 'Submissions are closed for the current cycle';
    END IF;
    
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);
    
    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;
    
    -- Get current cycle
    SELECT cycle_id INTO current_cycle FROM game.get_current_cycle();
    
    -- Get district if specified
    IF p_district_name IS NOT NULL THEN
        SELECT * INTO district_rec FROM game.get_district_by_name(p_district_name);
        
        IF district_rec IS NULL THEN
            RAISE EXCEPTION 'District not found: %', p_district_name;
        END IF;
    END IF;
    
    -- Get target player if specified
    IF p_target_player_name IS NOT NULL THEN
        SELECT * INTO target_player_rec 
        FROM game.players
        WHERE LOWER(name) = LOWER(p_target_player_name);
        
        IF target_player_rec IS NULL THEN
            RAISE EXCEPTION 'Target player not found: %', p_target_player_name;
        END IF;
    END IF;
    
    -- Get target politician if specified
    IF p_target_politician_name IS NOT NULL THEN
        SELECT * INTO target_politician_rec FROM game.get_politician_by_name(p_target_politician_name);
        
        IF target_politician_rec IS NULL THEN
            RAISE EXCEPTION 'Politician not found: %', p_target_politician_name;
        END IF;
    END IF;
    
    -- Check if player has enough actions remaining
    SELECT * INTO remaining_actions, remaining_quick_actions 
    FROM game.get_player_actions_remaining(player_rec.player_id);
    
    IF p_is_quick_action AND remaining_quick_actions <= 0 THEN
        RAISE EXCEPTION 'No quick actions remaining for this cycle';
    ELSIF NOT p_is_quick_action AND remaining_actions <= 0 THEN
        RAISE EXCEPTION 'No regular actions remaining for this cycle';
    END IF;
    
    -- Create action record
    INSERT INTO game.actions (
        player_id,
        cycle_id,
        action_type,
        is_quick_action,
        district_id,
        target_player_id,
        target_politician_id,
        resource_type,
        resource_amount,
        physical_presence,
        expected_outcome,
        status
    ) VALUES (
        player_rec.player_id,
        current_cycle,
        p_action_type,
        p_is_quick_action,
        district_rec.district_id,
        target_player_rec.player_id,
        target_politician_rec.politician_id,
        p_resource_type,
        p_resource_amount,
        p_physical_presence,
        p_expected_outcome,
        'pending'
    ) RETURNING * INTO new_action;
    
    -- Translate response based on language
    response_title := game.get_translation('action.submitted', p_language);
    action_response := game.get_translation('action.confirmation.' || p_action_type, p_language);
    
    IF action_response IS NULL OR action_response = 'action.confirmation.' || p_action_type THEN
        action_response := game.get_translation('action.confirmation.generic', p_language);
    END IF;
    
    -- Return confirmation
    RETURN json_build_object(
        'success', TRUE,
        'action_id', new_action.action_id,
        'title', response_title,
        'message', action_response,
        'action_type', p_action_type,
        'is_quick_action', p_is_quick_action,
        'district', COALESCE(p_district_name, ''),
        'resources_used', json_build_object(
            'type', p_resource_type,
            'amount', p_resource_amount
        ),
        'physical_presence', p_physical_presence,
        'actions_remaining', (CASE WHEN p_is_quick_action THEN remaining_quick_actions - 1 ELSE remaining_actions END),
        'quick_actions_remaining', (CASE WHEN p_is_quick_action THEN remaining_quick_actions - 1 ELSE remaining_quick_actions END)
    );
END;
$$ LANGUAGE plpgsql;

-- Cancel the latest action
CREATE OR REPLACE FUNCTION game.api_cancel_latest_action(
    p_telegram_id TEXT,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    latest_action game.actions;
    cancel_message TEXT;
BEGIN
    -- Check if submissions are open
    IF NOT game.is_submission_open() THEN
        RAISE EXCEPTION 'Submissions are closed for the current cycle';
    END IF;
    
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);
    
    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;
    
    -- Get the latest action for this player
    SELECT * INTO latest_action FROM game.get_latest_player_action(player_rec.player_id);
    
    IF latest_action IS NULL THEN
        RAISE EXCEPTION 'No actions found to cancel';
    END IF;
    
    -- Check if action is still pending
    IF latest_action.status != 'pending' THEN
        RAISE EXCEPTION 'Cannot cancel an action that has already been processed';
    END IF;
    
    -- Cancel the action
    UPDATE game.actions
    SET status = 'cancelled'
    WHERE action_id = latest_action.action_id;
    
    -- Get translated message
    cancel_message := game.get_translation('action.cancelled', p_language);
    
    -- Return confirmation
    RETURN json_build_object(
        'success', TRUE,
        'message', cancel_message,
        'action_id', latest_action.action_id,
        'action_type', latest_action.action_type,
        'resource_refunded', json_build_object(
            'type', latest_action.resource_type,
            'amount', latest_action.resource_amount
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Get district information
CREATE OR REPLACE FUNCTION game.api_get_district_info(
    p_telegram_id TEXT,
    p_district_name TEXT,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    district_rec game.districts;
    controlling_player game.players;
    player_control game.district_control;
    politicians_json JSON;
    control_info JSON;
    use_info_resource BOOLEAN := FALSE;
    translation_prefix TEXT;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);
    
    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;
    
    -- Get district data
    SELECT * INTO district_rec FROM game.get_district_by_name(p_district_name);
    
    IF district_rec IS NULL THEN
        RAISE EXCEPTION 'District not found: %', p_district_name;
    END IF;
    
    -- Get translation prefix based on language
    translation_prefix := CASE 
        WHEN p_language = 'ru_RU' THEN 'district.' || district_rec.name || '.ru'
        ELSE 'district.' || district_rec.name || '.en'
    END;
    
    -- Check if player has used information resource for this district recently
    -- For this example, we'll just check if they have any info resources
    SELECT * INTO player_control 
    FROM game.district_control
    WHERE player_id = player_rec.player_id AND district_id = district_rec.district_id;
    
    IF player_control IS NOT NULL AND player_control.control_points >= 20 THEN
        use_info_resource := TRUE;
    ELSE
        -- Check if player has information resources
        IF (SELECT information_amount FROM game.resources WHERE player_id = player_rec.player_id) > 0 THEN
            use_info_resource := TRUE;
            
            -- Deduct one information resource
            UPDATE game.resources
            SET information_amount = information_amount - 1
            WHERE player_id = player_rec.player_id;
            
            -- Log the resource use
            INSERT INTO game.resource_history (
                player_id,
                cycle_id,
                change_type,
                information_change,
                reason
            ) VALUES (
                player_rec.player_id,
                (SELECT cycle_id FROM game.get_current_cycle()),
                'view_district',
                -1,
                'Used to view ' || district_rec.name || ' district'
            );
        END IF;
    END IF;
    
    -- Get politicians in this district
    SELECT json_agg(
        json_build_object(
            'name', p.name,
            'description', p.description,
            'ideological_leaning', p.ideological_leaning,
            'influence_in_district', p.influence_in_district,
            'friendliness', COALESCE((
                SELECT friendliness_level 
                FROM game.player_politician_relations 
                WHERE player_id = player_rec.player_id AND politician_id = p.politician_id
            ), 50)
        )
    ) INTO politicians_json
    FROM game.politicians p
    WHERE p.district_id = district_rec.district_id;
    
    -- If no politicians, return empty array
    IF politicians_json IS NULL THEN
        politicians_json := '[]'::JSON;
    END IF;
    
    -- Get control information if player has resources or control
    IF use_info_resource THEN
        -- Get detailed control information
        SELECT json_agg(
            json_build_object(
                'player_name', p.name,
                'control_points', dc.control_points,
                'last_active', dc.last_action_cycle_id IS NOT NULL
            )
        ) INTO control_info
        FROM game.district_control dc
        JOIN game.players p ON dc.player_id = p.player_id
        WHERE dc.district_id = district_rec.district_id AND dc.control_points > 0
        ORDER BY dc.control_points DESC;
        
        -- Get controlling player if any
        SELECT * INTO controlling_player FROM game.get_district_controller(district_rec.district_id);
    ELSE
        -- Limited information without using resources
        SELECT json_agg(
            json_build_object(
                'player_name', p.name,
                'control_status', CASE
                    WHEN dc.control_points >= 80 THEN 'strong'
                    WHEN dc.control_points >= 60 THEN 'controlled'
                    WHEN dc.control_points >= 30 THEN 'present'
                    ELSE 'minimal'
                END
            )
        ) INTO control_info
        FROM game.district_control dc
        JOIN game.players p ON dc.player_id = p.player_id
        WHERE dc.district_id = district_rec.district_id AND dc.control_points > 0
        ORDER BY dc.control_points DESC;
    END IF;
    
    -- If no control info, return empty array
    IF control_info IS NULL THEN
        control_info := '[]'::JSON;
    END IF;
    
    -- Return district information
    RETURN json_build_object(
        'name', district_rec.name,
        'description', game.get_translation(translation_prefix || '.description', p_language),
        'resources', json_build_object(
            'influence', district_rec.influence_resource,
            'money', district_rec.money_resource,
            'information', district_rec.information_resource,
            'force', district_rec.force_resource
        ),
        'politicians', politicians_json,
        'control', control_info,
        'controlling_player', CASE 
            WHEN controlling_player IS NOT NULL THEN controlling_player.name
            ELSE NULL
        END,
        'player_control', CASE
            WHEN player_control IS NOT NULL THEN player_control.control_points
            ELSE 0
        END,
        'detailed_info', use_info_resource
    );
END;
$$ LANGUAGE plpgsql;

-- Initiate a collective action
CREATE OR REPLACE FUNCTION game.api_initiate_collective_action(
    p_telegram_id TEXT,
    p_action_type TEXT,
    p_district_name TEXT,
    p_target_player_name TEXT DEFAULT NULL,
    p_resource_type TEXT DEFAULT 'influence',   -- Added default
    p_resource_amount INTEGER DEFAULT 1,        -- Added default
    p_physical_presence BOOLEAN DEFAULT FALSE,
    p_language TEXT DEFAULT 'en_US'
) RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    district_rec game.districts;
    target_player_rec game.players;
    current_cycle UUID;
    new_collective_action game.collective_actions;
BEGIN
    -- Check if submissions are open
    IF NOT game.is_submission_open() THEN
        RAISE EXCEPTION 'Submissions are closed for the current cycle';
    END IF;

    -- Validate action type
    IF p_action_type NOT IN ('attack', 'defense') THEN
        RAISE EXCEPTION 'Invalid collective action type: %. Only attack or defense allowed.', p_action_type;
    END IF;

    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Get current cycle
    SELECT cycle_id INTO current_cycle FROM game.get_current_cycle();

    -- Get district
    SELECT * INTO district_rec FROM game.get_district_by_name(p_district_name);

    IF district_rec IS NULL THEN
        RAISE EXCEPTION 'District not found: %', p_district_name;
    END IF;

    -- Get target player if specified
    IF p_target_player_name IS NOT NULL THEN
        SELECT * INTO target_player_rec
        FROM game.players
        WHERE LOWER(name) = LOWER(p_target_player_name);

        IF target_player_rec IS NULL THEN
            RAISE EXCEPTION 'Target player not found: %', p_target_player_name;
        END IF;
    END IF;

    -- Create collective action record
    INSERT INTO game.collective_actions (
        initiator_player_id,
        action_type,
        district_id,
        cycle_id,
        status,
        target_player_id
    ) VALUES (
        player_rec.player_id,
        p_action_type,
        district_rec.district_id,
        current_cycle,
        'active', -- Immediately active, not pending
        target_player_rec.player_id
    ) RETURNING * INTO new_collective_action;

    -- Add initiator as first participant
    INSERT INTO game.collective_action_participants (
        collective_action_id,
        player_id,
        resource_type,
        resource_amount,
        physical_presence
    ) VALUES (
        new_collective_action.collective_action_id,
        player_rec.player_id,
        p_resource_type,
        p_resource_amount,
        p_physical_presence
    );

    -- Create news about collective action initiation
    INSERT INTO game.news (
        cycle_id,
        title,
        content,
        news_type,
        related_district_id
    ) VALUES (
        current_cycle,
        'Collective ' || p_action_type || ' initiated in ' || district_rec.name,
        player_rec.name || ' has initiated a collective ' || p_action_type ||
        ' in ' || district_rec.name || '. Other players can join using the command /join ' ||
        new_collective_action.collective_action_id,
        'public',
        district_rec.district_id
    );

    -- Return success
    RETURN json_build_object(
        'success', TRUE,
        'message', game.get_translation('collective_action.initiated', p_language),
        'collective_action_id', new_collective_action.collective_action_id,
        'action_type', p_action_type,
        'district', district_rec.name,
        'initiator', player_rec.name,
        'join_command', '/join ' || new_collective_action.collective_action_id::TEXT
    );
END;
$$ LANGUAGE plpgsql;
-- Join a collective action
CREATE OR REPLACE FUNCTION game.api_join_collective_action(
    p_telegram_id TEXT,
    p_collective_action_id UUID,
    p_resource_type TEXT,
    p_resource_amount INTEGER,
    p_physical_presence BOOLEAN DEFAULT FALSE,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    collective_action_rec game.collective_actions;
    district_rec game.districts;
    existing_participant BOOLEAN;
BEGIN
    -- Check if submissions are open
    IF NOT game.is_submission_open() THEN
        RAISE EXCEPTION 'Submissions are closed for the current cycle';
    END IF;

    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Get collective action
    SELECT * INTO collective_action_rec
    FROM game.collective_actions
    WHERE collective_action_id = p_collective_action_id;

    IF collective_action_rec IS NULL THEN
        RAISE EXCEPTION 'Collective action not found';
    END IF;

    -- Check if action is still active
    IF collective_action_rec.status != 'active' THEN
        RAISE EXCEPTION 'This collective action is no longer accepting participants';
    END IF;

    -- Check if player is already participating
    SELECT EXISTS(
        SELECT 1
        FROM game.collective_action_participants
        WHERE collective_action_id = p_collective_action_id AND player_id = player_rec.player_id
    ) INTO existing_participant;

    IF existing_participant THEN
        RAISE EXCEPTION 'You are already participating in this collective action';
    END IF;

    -- Get district information
    SELECT * INTO district_rec
    FROM game.districts
    WHERE district_id = collective_action_rec.district_id;

    -- Add player as participant
    INSERT INTO game.collective_action_participants (
        collective_action_id,
        player_id,
        resource_type,
        resource_amount,
        physical_presence
    ) VALUES (
        p_collective_action_id,
        player_rec.player_id,
        p_resource_type,
        p_resource_amount,
        p_physical_presence
    );

    -- Create news for the initiator
    INSERT INTO game.news (
        cycle_id,
        title,
        content,
        news_type,
        target_player_id,
        related_district_id
    ) VALUES (
        collective_action_rec.cycle_id,
        'New participant in your collective action',
        player_rec.name || ' has joined your collective ' || collective_action_rec.action_type ||
        ' in ' || district_rec.name || ' with ' || p_resource_amount || ' ' || p_resource_type || ' resources.',
        'faction',
        collective_action_rec.initiator_player_id,
        collective_action_rec.district_id
    );

    -- Return success
    RETURN json_build_object(
        'success', TRUE,
        'message', game.get_translation('collective_action.joined', p_language),
        'collective_action_id', p_collective_action_id,
        'action_type', collective_action_rec.action_type,
        'district', district_rec.name,
        'resources_contributed', json_build_object(
            'type', p_resource_type,
            'amount', p_resource_amount
        ),
        'physical_presence', p_physical_presence
    );
END;
$$ LANGUAGE plpgsql;

-- Get game cycle information
CREATE OR REPLACE FUNCTION game.api_get_cycle_info(
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    current_cycle game.cycles;
    time_to_deadline INTERVAL;
    time_to_results INTERVAL;
    cycle_type_translated TEXT;
BEGIN
    -- Get current cycle
    SELECT * INTO current_cycle FROM game.get_current_cycle();

    IF current_cycle IS NULL THEN
        RAISE EXCEPTION 'No active game cycle found';
    END IF;

    -- Calculate time remaining
    time_to_deadline := game.time_until_deadline();
    time_to_results := game.time_until_results();

    -- Translate cycle type
    cycle_type_translated := game.get_translation('cycle.' || current_cycle.cycle_type, p_language);

    -- Return cycle information
    RETURN json_build_object(
        'cycle_id', current_cycle.cycle_id,
        'cycle_type', cycle_type_translated,
        'cycle_date', current_cycle.cycle_date,
        'submission_deadline', current_cycle.submission_deadline,
        'results_time', current_cycle.results_time,
        'time_to_deadline', time_to_deadline,
        'time_to_results', time_to_results,
        'is_active', current_cycle.is_active,
        'is_accepting_submissions', game.is_submission_open()
    );
END;
$$ LANGUAGE plpgsql;

-- Get latest news
CREATE OR REPLACE FUNCTION game.api_get_latest_news(
    p_telegram_id TEXT,
    p_count INTEGER DEFAULT 5,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    public_news JSON;
    faction_news JSON;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Get latest public news
    SELECT json_agg(
        json_build_object(
            'title', title,
            'content', content,
            'cycle_type', (
                SELECT cycle_type FROM game.cycles WHERE cycle_id = n.cycle_id
            ),
            'cycle_date', (
                SELECT cycle_date FROM game.cycles WHERE cycle_id = n.cycle_id
            ),
            'district', (
                SELECT name FROM game.districts WHERE district_id = n.related_district_id
            ),
            'created_at', n.created_at
        )
    ) INTO public_news
    FROM game.news n
    WHERE news_type = 'public'
    ORDER BY created_at DESC
    LIMIT p_count;

    -- Get latest faction news for this player
    SELECT json_agg(
        json_build_object(
            'title', title,
            'content', content,
            'cycle_type', (
                SELECT cycle_type FROM game.cycles WHERE cycle_id = n.cycle_id
            ),
            'cycle_date', (
                SELECT cycle_date FROM game.cycles WHERE cycle_id = n.cycle_id
            ),
            'district', (
                SELECT name FROM game.districts WHERE district_id = n.related_district_id
            ),
            'created_at', n.created_at
        )
    ) INTO faction_news
    FROM game.news n
    WHERE news_type = 'faction' AND target_player_id = player_rec.player_id
    ORDER BY created_at DESC
    LIMIT p_count;

    -- Handle NULLs
    IF public_news IS NULL THEN
        public_news := '[]'::JSON;
    END IF;

    IF faction_news IS NULL THEN
        faction_news := '[]'::JSON;
    END IF;

    -- Return combined news
    RETURN json_build_object(
        'public', public_news,
        'faction', faction_news
    );
END;
$$ LANGUAGE plpgsql;

-- Get map data (simplified version, full one would be done in the app)
CREATE OR REPLACE FUNCTION game.api_get_map_data(
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    districts_data JSON;
BEGIN
    -- Get districts with control data
    SELECT json_agg(
        json_build_object(
            'district_id', d.district_id,
            'name', d.name,
            'controlling_player', (
                SELECT p.name
                FROM game.players p
                JOIN game.district_control dc ON p.player_id = dc.player_id
                WHERE dc.district_id = d.district_id AND dc.control_points >= 60
                ORDER BY dc.control_points DESC
                LIMIT 1
            ),
            'control_level', (
                SELECT
                    CASE
                        WHEN MAX(dc.control_points) >= 80 THEN 'strong'
                        WHEN MAX(dc.control_points) >= 60 THEN 'controlled'
                        WHEN MAX(dc.control_points) >= 30 THEN 'contested'
                        ELSE 'neutral'
                    END
                FROM game.district_control dc
                WHERE dc.district_id = d.district_id
            )
        )
    ) INTO districts_data
    FROM game.districts d;

    -- Return map data
    RETURN json_build_object(
        'districts', districts_data,
        'game_date', (SELECT cycle_date FROM game.get_current_cycle()),
        'cycle', (SELECT cycle_type FROM game.get_current_cycle())
    );
END;
$$ LANGUAGE plpgsql;

-- Exchange resources
CREATE OR REPLACE FUNCTION game.api_exchange_resources(
    p_telegram_id TEXT,
    p_from_resource TEXT,
    p_to_resource TEXT,
    p_amount INTEGER,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    success BOOLEAN;
    from_resource_translated TEXT;
    to_resource_translated TEXT;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Validate resource types
    IF p_from_resource NOT IN ('influence', 'money', 'information', 'force') THEN
        RAISE EXCEPTION 'Invalid source resource type: %', p_from_resource;
    END IF;

    IF p_to_resource NOT IN ('influence', 'money', 'information', 'force') THEN
        RAISE EXCEPTION 'Invalid target resource type: %', p_to_resource;
    END IF;

    -- Cannot exchange same resource type
    IF p_from_resource = p_to_resource THEN
        RAISE EXCEPTION 'Cannot exchange the same resource type';
    END IF;

    -- Perform the exchange
    success := game.exchange_resource(
        player_rec.player_id,
        p_from_resource,
        p_to_resource,
        p_amount
    );

    IF NOT success THEN
        RAISE EXCEPTION 'Exchange failed. You may not have enough resources.';
    END IF;

    -- Get translated resource names
    from_resource_translated := game.get_translation('resources.' || p_from_resource, p_language);
    to_resource_translated := game.get_translation('resources.' || p_to_resource, p_language);

    -- Return success
    RETURN json_build_object(
        'success', TRUE,
        'message', game.get_translation('resource.exchange.success', p_language),
        'from_resource', json_build_object(
            'type', p_from_resource,
            'name', from_resource_translated,
            'amount', p_amount * 2
        ),
        'to_resource', json_build_object(
            'type', p_to_resource,
            'name', to_resource_translated,
            'amount', p_amount
        ),
        'rate', '2:1',
        'current_resources', (
            SELECT json_build_object(
                'influence', influence_amount,
                'money', money_amount,
                'information', information_amount,
                'force', force_amount
            )
            FROM game.resources
            WHERE player_id = player_rec.player_id
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Get information about expected resource income
CREATE OR REPLACE FUNCTION game.api_check_income(
    p_telegram_id TEXT,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    district_rec RECORD;
    income_data JSON;
    total_influence INTEGER := 0;
    total_money INTEGER := 0;
    total_information INTEGER := 0;
    total_force INTEGER := 0;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Calculate income for each controlled district
    SELECT json_agg(
        json_build_object(
            'district', d.name,
            'control_points', dc.control_points,
            'control_percentage',
                CASE
                    WHEN dc.control_points >= 75 THEN '120%'
                    WHEN dc.control_points >= 50 THEN '100%'
                    WHEN dc.control_points >= 35 THEN '80%'
                    WHEN dc.control_points >= 20 THEN '60%'
                    ELSE '40%'
                END,
            'income', (
                SELECT json_build_object(
                    'influence', influence_gain,
                    'money', money_gain,
                    'information', information_gain,
                    'force', force_gain
                )
                FROM game.calculate_district_resources(player_rec.player_id, d.district_id)
            )
        )
    ) INTO income_data
    FROM game.districts d
    JOIN game.district_control dc ON d.district_id = dc.district_id
    WHERE dc.player_id = player_rec.player_id;

    -- Calculate totals
    FOR district_rec IN (
        SELECT d.district_id
        FROM game.districts d
        JOIN game.district_control dc ON d.district_id = dc.district_id
        WHERE dc.player_id = player_rec.player_id
    ) LOOP
        -- Get resources from this district
        SELECT
            influence_gain, money_gain, information_gain, force_gain
        INTO
            district_rec.influence_gain,
            district_rec.money_gain,
            district_rec.information_gain,
            district_rec.force_gain
        FROM game.calculate_district_resources(player_rec.player_id, district_rec.district_id);

        -- Add to totals
        total_influence := total_influence + district_rec.influence_gain;
        total_money := total_money + district_rec.money_gain;
        total_information := total_information + district_rec.information_gain;
        total_force := total_force + district_rec.force_gain;
    END LOOP;

    -- Handle NULL income data
    IF income_data IS NULL THEN
        income_data := '[]'::JSON;
    END IF;

    -- Return income information
    RETURN json_build_object(
        'district_income', income_data,
        'totals', json_build_object(
            'influence', total_influence,
            'money', total_money,
            'information', total_information,
            'force', total_force
        ),
        'next_cycle', json_build_object(
            'type', (SELECT cycle_type FROM game.get_current_cycle()),
            'date', (SELECT cycle_date FROM game.get_current_cycle())
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Get information about politicians
CREATE OR REPLACE FUNCTION game.api_get_politicians(
    p_telegram_id TEXT,
    p_type TEXT DEFAULT 'local', -- 'local', 'international', or 'all'
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    politicians_data JSON;
    type_filter TEXT;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Determine filter
    IF p_type = 'all' THEN
        type_filter := NULL;
    ELSE
        type_filter := p_type;
    END IF;

    -- Get politicians data
    SELECT json_agg(
        json_build_object(
            'name', p.name,
            'type', p.type,
            'description', p.description,
            'ideological_leaning', p.ideological_leaning,
            'country', p.country,
            'district', (
                SELECT name
                FROM game.districts
                WHERE district_id = p.district_id
            ),
            'influence_in_district', p.influence_in_district,
            'friendliness', COALESCE((
                SELECT friendliness_level
                FROM game.player_politician_relations
                WHERE player_id = player_rec.player_id AND politician_id = p.politician_id
            ), 50),
            'ideology_compatibility', game.calculate_ideology_compatibility(player_rec.player_id, p.politician_id)
        )
    ) INTO politicians_data
    FROM game.politicians p
    WHERE type_filter IS NULL OR p.type = type_filter
    ORDER BY p.name;

    -- Handle NULL data
    IF politicians_data IS NULL THEN
        politicians_data := '[]'::JSON;
    END IF;

    -- Return politicians data
    RETURN json_build_object(
        'politicians', politicians_data,
        'type', p_type,
        'player_ideology', player_rec.ideology_score
    );
END;
$$ LANGUAGE plpgsql;

-- Get detailed information about a specific politician
CREATE OR REPLACE FUNCTION game.api_get_politician_status(
    p_telegram_id TEXT,
    p_politician_name TEXT,
    p_language TEXT DEFAULT 'en_US'
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    politician_rec game.politicians;
    relation_rec game.player_politician_relations;
    ideology_compatibility INTEGER;
    active_effects_json JSON;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL THEN
        RAISE EXCEPTION 'Player not found';
    END IF;

    -- Get politician data
    SELECT * INTO politician_rec FROM game.get_politician_by_name(p_politician_name);

    IF politician_rec IS NULL THEN
        RAISE EXCEPTION 'Politician not found: %', p_politician_name;
    END IF;

    -- Get relation data
    SELECT * INTO relation_rec
    FROM game.get_player_politician_relation(player_rec.player_id, politician_rec.politician_id);

    -- Calculate ideology compatibility
    ideology_compatibility := game.calculate_ideology_compatibility(player_rec.player_id, politician_rec.politician_id);

    -- Get active effects for international politicians
    IF politician_rec.type = 'international' THEN
        SELECT json_agg(
            json_build_object(
                'effect_type', effect_type,
                'description', description,
                'target_district', (
                    SELECT name
                    FROM game.districts
                    WHERE district_id = target_district_id
                ),
                'control_points_effect', control_points_effect,
                'resource_effect_type', resource_effect_type,
                'resource_effect_amount', resource_effect_amount,
                'expires_at', expires_at
            )
        ) INTO active_effects_json
        FROM game.international_effects
        WHERE politician_id = politician_rec.politician_id AND expires_at > NOW();
    END IF;

    -- Handle NULL data
    IF active_effects_json IS NULL THEN
        active_effects_json := '[]'::JSON;
    END IF;

    -- Return politician status
    RETURN json_build_object(
        'name', politician_rec.name,
        'type', politician_rec.type,
        'description', politician_rec.description,
        'ideological_leaning', politician_rec.ideological_leaning,
        'country', politician_rec.country,
        'district', (
            SELECT name
            FROM game.districts
            WHERE district_id = politician_rec.district_id
        ),
        'influence_in_district', politician_rec.influence_in_district,
        'activity_percentage', politician_rec.activity_percentage,
        'friendliness', relation_rec.friendliness_level,
        'friendliness_status', CASE
            WHEN relation_rec.friendliness_level >= 80 THEN 'loyal'
            WHEN relation_rec.friendliness_level >= 70 THEN 'friendly'
            WHEN relation_rec.friendliness_level >= 30 THEN 'neutral'
            ELSE 'hostile'
        END,
        'ideology_compatibility', ideology_compatibility,
        'active_effects', active_effects_json,
        'possible_actions', json_build_object(
            'influence', relation_rec.friendliness_level < 90,
            'attack_reputation', TRUE,
            'displacement', relation_rec.friendliness_level < 50,
            'request_resources', relation_rec.friendliness_level >= 70
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Admin function to process all pending actions
CREATE OR REPLACE FUNCTION game.api_admin_process_actions(
    p_telegram_id TEXT
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    current_cycle UUID;
    processed_count INTEGER;
    collective_processed_count INTEGER;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL OR NOT player_rec.is_admin THEN
        RAISE EXCEPTION 'Unauthorized: Admin privileges required';
    END IF;

    -- Get current cycle
    SELECT cycle_id INTO current_cycle FROM game.get_current_cycle();

    -- Process collective actions first
    collective_processed_count := game.process_all_collective_actions(current_cycle);

    -- Process all pending actions
    processed_count := game.process_all_pending_actions(current_cycle);

    -- Apply international effects
    PERFORM game.apply_international_effects();

    -- Process end of cycle and distribute resources
    PERFORM game.process_end_of_cycle();

    -- Return results
    RETURN json_build_object(
        'success', TRUE,
        'actions_processed', processed_count,
        'collective_actions_processed', collective_processed_count,
        'new_cycle', json_build_object(
            'type', (SELECT cycle_type FROM game.get_current_cycle()),
            'date', (SELECT cycle_date FROM game.get_current_cycle()),
            'submission_deadline', (SELECT submission_deadline FROM game.get_current_cycle()),
            'results_time', (SELECT results_time FROM game.get_current_cycle())
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Admin function to generate international effects
CREATE OR REPLACE FUNCTION game.api_admin_generate_international_effects(
    p_telegram_id TEXT,
    p_count INTEGER DEFAULT 2
)
RETURNS JSON AS $$
DECLARE
    player_rec game.players;
    politician_rec RECORD;
    i INTEGER;
    generated_effects JSON;
BEGIN
    -- Get player data
    SELECT * INTO player_rec FROM game.get_player_by_telegram_id(p_telegram_id);

    IF player_rec IS NULL OR NOT player_rec.is_admin THEN
        RAISE EXCEPTION 'Unauthorized: Admin privileges required';
    END IF;

    -- Initialize empty array for effects
    generated_effects := '[]'::JSON;

    -- Generate specified number of international effects
    FOR i IN 1..p_count LOOP
        -- Select a random international politician
        SELECT * INTO politician_rec
        FROM game.politicians
        WHERE type = 'international'
        ORDER BY RANDOM()
        LIMIT 1;

        IF politician_rec IS NOT NULL THEN
            -- Generate effect using the politician
            DECLARE
                new_effect game.international_effects;
            BEGIN
                new_effect := game.generate_international_effect(politician_rec.politician_id);

                -- Append to the effects array
                generated_effects := generated_effects || json_build_object(
                    'politician', politician_rec.name,
                    'effect_type', new_effect.effect_type,
                    'description', new_effect.description
                );
            END;
        END IF;
    END LOOP;

    -- Return results
    RETURN json_build_object(
        'success', TRUE,
        'effects_generated', p_count,
        'effects', generated_effects
    );
END;
$$ LANGUAGE plpgsql;