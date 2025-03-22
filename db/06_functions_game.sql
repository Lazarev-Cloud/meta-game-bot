-- 06_functions_game.sql
-- Game-specific functions for processing actions and game mechanics

-- Process end of cycle and distribute resources
CREATE OR REPLACE FUNCTION game.process_end_of_cycle()
RETURNS VOID AS $$
DECLARE
    current_cycle game.cycles;
    district_rec RECORD;
    player_rec RECORD;
    resource_calc RECORD;
    ideology_bonus INTEGER;
BEGIN
    -- Get current cycle
    SELECT * INTO current_cycle FROM game.get_current_cycle();
    
    -- Ensure we're at the end of a cycle
    IF current_cycle IS NULL OR NOW() < current_cycle.results_time THEN
        RAISE EXCEPTION 'Cannot process end of cycle before results time';
    END IF;
    
    -- Process resources for all district controls
    FOR player_rec IN (
        SELECT DISTINCT p.player_id
        FROM game.players p
        JOIN game.district_control dc ON p.player_id = dc.player_id
    ) LOOP
        -- For each district the player has control in
        FOR district_rec IN (
            SELECT DISTINCT d.district_id, d.name
            FROM game.districts d
            JOIN game.district_control dc ON d.district_id = dc.district_id
            WHERE dc.player_id = player_rec.player_id
        ) LOOP
            -- Calculate resources from this district
            SELECT * INTO resource_calc 
            FROM game.calculate_district_resources(player_rec.player_id, district_rec.district_id);
            
            -- Add ideological compatibility with district's politicians
            SELECT SUM(game.calculate_ideology_compatibility(player_rec.player_id, p.politician_id))
            INTO ideology_bonus
            FROM game.politicians p
            WHERE p.district_id = district_rec.district_id;
            
            -- Default to zero if NULL
            IF ideology_bonus IS NULL THEN
                ideology_bonus := 0;
            END IF;
            
            -- Apply ideology bonus/penalty to district control
            IF ideology_bonus != 0 THEN
                UPDATE game.district_control
                SET control_points = control_points + ideology_bonus
                WHERE player_id = player_rec.player_id AND district_id = district_rec.district_id;
                
                -- Log the control point change
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id,
                    related_district_id
                ) VALUES (
                    current_cycle.cycle_id,
                    'Ideological Influence in ' || district_rec.name,
                    'Your ideological alignment has ' || 
                    CASE 
                        WHEN ideology_bonus > 0 THEN 'strengthened'
                        ELSE 'weakened'
                    END || 
                    ' your control in this district by ' || ABS(ideology_bonus) || ' points.',
                    'faction',
                    player_rec.player_id,
                    district_rec.district_id
                );
            END IF;
            
            -- Apply district resources to player
            UPDATE game.resources
            SET 
                influence_amount = influence_amount + resource_calc.influence_gain,
                money_amount = money_amount + resource_calc.money_gain,
                information_amount = information_amount + resource_calc.information_gain,
                force_amount = force_amount + resource_calc.force_gain
            WHERE player_id = player_rec.player_id;
            
            -- Record resource history
            IF resource_calc.influence_gain > 0 OR resource_calc.money_gain > 0 OR 
               resource_calc.information_gain > 0 OR resource_calc.force_gain > 0 THEN
                
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
                    player_rec.player_id,
                    current_cycle.cycle_id,
                    'district_income',
                    resource_calc.influence_gain,
                    resource_calc.money_gain,
                    resource_calc.information_gain,
                    resource_calc.force_gain,
                    'Income from ' || district_rec.name || ' district'
                );
                
                -- Create news for the player
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id,
                    related_district_id
                ) VALUES (
                    current_cycle.cycle_id,
                    'Resource Income from ' || district_rec.name,
                    'You received resources from controlling ' || district_rec.name || '.' ||
                    CASE WHEN resource_calc.influence_gain > 0 THEN ' Influence: +' || resource_calc.influence_gain ELSE '' END ||
                    CASE WHEN resource_calc.money_gain > 0 THEN ' Money: +' || resource_calc.money_gain ELSE '' END ||
                    CASE WHEN resource_calc.information_gain > 0 THEN ' Information: +' || resource_calc.information_gain ELSE '' END ||
                    CASE WHEN resource_calc.force_gain > 0 THEN ' Force: +' || resource_calc.force_gain ELSE '' END,
                    'faction',
                    player_rec.player_id,
                    district_rec.district_id
                );
            END IF;
        END LOOP;
    END LOOP;
    
    -- Apply decay to inactive district controls (no actions in the past cycle)
    UPDATE game.district_control
    SET control_points = control_points - 5
    WHERE last_action_cycle_id IS NULL OR last_action_cycle_id != current_cycle.cycle_id;
    
    -- Create the next cycle
    PERFORM game.create_next_cycle();
END;
$$ LANGUAGE plpgsql;

-- Process specific action
CREATE OR REPLACE FUNCTION game.process_action(p_action_id UUID)
RETURNS VOID AS $$
DECLARE
    action_rec game.actions;
    success_chance INTEGER;
    roll INTEGER;
    outcome TEXT;
    control_points INTEGER := 0;
    base_points INTEGER;
    district_rec game.districts;
    district_control_rec game.district_control;
    target_district_control_rec game.district_control;
    politician_rec game.politicians;
    relation_rec game.player_politician_relations;
BEGIN
    -- Get action details
    SELECT * INTO action_rec FROM game.actions WHERE action_id = p_action_id;
    
    IF action_rec IS NULL THEN
        RAISE EXCEPTION 'Action not found';
    END IF;
    
    -- Calculate base success chance (50-70%)
    success_chance := 60;
    
    -- Modify based on resource type and amount
    success_chance := success_chance + (action_rec.resource_amount * 5);
    
    -- Cap success chance at 95%
    IF success_chance > 95 THEN
        success_chance := 95;
    END IF;
    
    -- Add bonus for physical presence
    IF action_rec.physical_presence THEN
        success_chance := success_chance + 20;
    END IF;
    
    -- Determine if action succeeds
    roll := game.random_int(1, 100);
    
    -- Process action based on type
    CASE action_rec.action_type
        
        -- Influence action
        WHEN 'influence' THEN
            IF roll <= success_chance THEN
                -- Success: +10 OP
                base_points := 10;
                IF action_rec.physical_presence THEN
                    base_points := base_points + 20;
                END IF;
                
                outcome := 'Success! You have increased your influence in the district.';
                control_points := base_points;
            ELSIF roll <= success_chance + 20 THEN
                -- Partial success: +5 OP
                base_points := 5;
                IF action_rec.physical_presence THEN
                    base_points := base_points + 20;
                END IF;
                
                outcome := 'Partial success. You have slightly increased your influence in the district.';
                control_points := base_points;
            ELSE
                -- Failure: No change
                outcome := 'Failed to increase influence in the district.';
                control_points := 0;
            END IF;
            
            -- Update district control
            SELECT * INTO district_control_rec 
            FROM game.district_control 
            WHERE district_id = action_rec.district_id AND player_id = action_rec.player_id;
            
            IF district_control_rec IS NULL THEN
                -- Create new control record
                INSERT INTO game.district_control (
                    district_id,
                    player_id,
                    control_points,
                    last_action_cycle_id
                ) VALUES (
                    action_rec.district_id,
                    action_rec.player_id,
                    control_points,
                    action_rec.cycle_id
                );
            ELSE
                -- Update existing control
                UPDATE game.district_control
                SET 
                    control_points = district_control_rec.control_points + control_points,
                    last_action_cycle_id = action_rec.cycle_id
                WHERE control_id = district_control_rec.control_id;
            END IF;
            
        -- Attack action
        WHEN 'attack' THEN
            IF roll <= success_chance THEN
                -- Success: -10 OP to target, +10 OP to attacker
                base_points := 10;
                IF action_rec.physical_presence THEN
                    base_points := base_points + 20;
                END IF;
                
                outcome := 'Attack successful! You have reduced enemy influence and increased your own.';
                control_points := base_points;
            ELSIF roll <= success_chance + 20 THEN
                -- Partial success: -5 OP to target, +5 OP to attacker
                base_points := 5;
                IF action_rec.physical_presence THEN
                    base_points := base_points + 20;
                END IF;
                
                outcome := 'Attack partially successful. Small reduction in enemy influence and small gain for you.';
                control_points := base_points;
            ELSE
                -- Failure: No change
                outcome := 'Attack failed. No change in district control.';
                control_points := 0;
            END IF;
            
            -- Update district control for target if specified
            IF action_rec.target_player_id IS NOT NULL AND control_points > 0 THEN
                SELECT * INTO target_district_control_rec 
                FROM game.district_control 
                WHERE district_id = action_rec.district_id AND player_id = action_rec.target_player_id;
                
                IF target_district_control_rec IS NOT NULL THEN
                    -- Reduce target's control
                    UPDATE game.district_control
                    SET control_points = GREATEST(0, target_district_control_rec.control_points - control_points)
                    WHERE control_id = target_district_control_rec.control_id;
                    
                    -- Create news for the target player
                    INSERT INTO game.news (
                        cycle_id,
                        title,
                        content,
                        news_type,
                        target_player_id,
                        related_district_id
                    ) VALUES (
                        action_rec.cycle_id,
                        'Attack on Your Control in ' || (SELECT name FROM game.districts WHERE district_id = action_rec.district_id),
                        'Your control in this district has been reduced by ' || control_points || ' points due to an enemy attack.',
                        'faction',
                        action_rec.target_player_id,
                        action_rec.district_id
                    );
                END IF;
            END IF;
            
            -- Update attacker's control
            SELECT * INTO district_control_rec 
            FROM game.district_control 
            WHERE district_id = action_rec.district_id AND player_id = action_rec.player_id;
            
            IF district_control_rec IS NULL AND control_points > 0 THEN
                -- Create new control record
                INSERT INTO game.district_control (
                    district_id,
                    player_id,
                    control_points,
                    last_action_cycle_id
                ) VALUES (
                    action_rec.district_id,
                    action_rec.player_id,
                    control_points,
                    action_rec.cycle_id
                );
            ELSIF control_points > 0 THEN
                -- Update existing control
                UPDATE game.district_control
                SET 
                    control_points = district_control_rec.control_points + control_points,
                    last_action_cycle_id = action_rec.cycle_id
                WHERE control_id = district_control_rec.control_id;
            END IF;
            
        -- Defense action
        WHEN 'defense' THEN
            IF roll <= success_chance THEN
                -- Success: Block up to 10 OP of damage
                base_points := 10;
                IF action_rec.physical_presence THEN
                    base_points := base_points + 20;
                END IF;
                
                outcome := 'Defense successfully established. You can block up to ' || base_points || ' points of damage.';
                control_points := base_points; -- Store as defense points
            ELSIF roll <= success_chance + 20 THEN
                -- Partial success: Block up to 5 OP of damage
                base_points := 5;
                IF action_rec.physical_presence THEN
                    base_points := base_points + 20;
                END IF;
                
                outcome := 'Defense partially established. You can block up to ' || base_points || ' points of damage.';
                control_points := base_points; -- Store as defense points
            ELSE
                -- Failure: No defense
                outcome := 'Failed to establish defense. Your district remains vulnerable.';
                control_points := 0;
            END IF;
            
            -- Update district control for defender
            SELECT * INTO district_control_rec 
            FROM game.district_control 
            WHERE district_id = action_rec.district_id AND player_id = action_rec.player_id;
            
            IF district_control_rec IS NULL THEN
                -- Create new control record with defense points
                INSERT INTO game.district_control (
                    district_id,
                    player_id,
                    control_points,
                    last_action_cycle_id
                ) VALUES (
                    action_rec.district_id,
                    action_rec.player_id,
                    control_points,
                    action_rec.cycle_id
                );
            ELSE
                -- Update existing control and mark as defended
                UPDATE game.district_control
                SET 
                    control_points = district_control_rec.control_points + control_points,
                    last_action_cycle_id = action_rec.cycle_id
                WHERE control_id = district_control_rec.control_id;
            END IF;
            
        -- Reconnaissance action
        WHEN 'reconnaissance' THEN
            IF roll <= success_chance THEN
                -- Success: Get full intel
                outcome := 'Reconnaissance successful! You have gathered complete information about the district.';
                
                -- Create detailed news for the player
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id,
                    related_district_id
                ) VALUES (
                    action_rec.cycle_id,
                    'Reconnaissance Report: ' || (SELECT name FROM game.districts WHERE district_id = action_rec.district_id),
                    'Your reconnaissance operation was successful. Here is the detailed information about the district.',
                    'faction',
                    action_rec.player_id,
                    action_rec.district_id
                );
            ELSE
                -- Failure: Limited intel
                outcome := 'Reconnaissance partially successful. You have gathered some information about the district.';
                
                -- Create limited news for the player
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id,
                    related_district_id
                ) VALUES (
                    action_rec.cycle_id,
                    'Partial Reconnaissance: ' || (SELECT name FROM game.districts WHERE district_id = action_rec.district_id),
                    'Your reconnaissance operation retrieved limited information. Some details remain unknown.',
                    'faction',
                    action_rec.player_id,
                    action_rec.district_id
                );
            END IF;
            
        -- Information spread action
        WHEN 'information_spread' THEN
            IF roll <= success_chance THEN
                -- Success: Information spreads widely
                outcome := 'Information spread successfully! Your narrative has reached a wide audience.';
                
                -- Create public news based on player's information
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    related_district_id,
                    created_by
                ) VALUES (
                    action_rec.cycle_id,
                    'Breaking News: ' || COALESCE(action_rec.expected_outcome, 'New Developments'),
                    'Reports indicate significant developments in the area. Local sources confirm the information.',
                    'public',
                    action_rec.district_id,
                    action_rec.player_id
                );
            ELSE
                -- Failure: Limited spread
                outcome := 'Information spread partially. Your narrative has reached a limited audience.';
                
                -- Create faction-specific news
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id,
                    related_district_id
                ) VALUES (
                    action_rec.cycle_id,
                    'Limited Information Spread',
                    'Your information campaign had limited reach. Consider using more resources next time.',
                    'faction',
                    action_rec.player_id,
                    action_rec.district_id
                );
            END IF;
            
        -- Support action
        WHEN 'support' THEN
            -- Support always succeeds but with variable effectiveness
            base_points := 5;
            IF action_rec.physical_presence THEN
                base_points := base_points + 20;
            END IF;
            
            outcome := 'Support action completed. You have reinforced your position in the district.';
            control_points := base_points;
            
            -- Update district control
            SELECT * INTO district_control_rec 
            FROM game.district_control 
            WHERE district_id = action_rec.district_id AND player_id = action_rec.player_id;
            
            IF district_control_rec IS NULL THEN
                -- Create new control record
                INSERT INTO game.district_control (
                    district_id,
                    player_id,
                    control_points,
                    last_action_cycle_id
                ) VALUES (
                    action_rec.district_id,
                    action_rec.player_id,
                    control_points,
                    action_rec.cycle_id
                );
            ELSE
                -- Update existing control
                UPDATE game.district_control
                SET 
                    control_points = district_control_rec.control_points + control_points,
                    last_action_cycle_id = action_rec.cycle_id
                WHERE control_id = district_control_rec.control_id;
            END IF;
            
        -- Politician influence action
        WHEN 'politician_influence' THEN
            IF action_rec.target_politician_id IS NULL THEN
                outcome := 'Failed: No target politician specified.';
            ELSE
                SELECT * INTO politician_rec FROM game.politicians WHERE politician_id = action_rec.target_politician_id;
                
                IF roll <= success_chance THEN
                    -- Success: +10 to friendliness
                    outcome := 'Successfully increased influence with ' || politician_rec.name || '.';
                    
                    -- Update or create relation
                    SELECT * INTO relation_rec 
                    FROM game.player_politician_relations 
                    WHERE player_id = action_rec.player_id AND politician_id = action_rec.target_politician_id;
                    
                    IF relation_rec IS NULL THEN
                        INSERT INTO game.player_politician_relations (
                            player_id,
                            politician_id,
                            friendliness_level
                        ) VALUES (
                            action_rec.player_id,
                            action_rec.target_politician_id,
                            60
                        );
                    ELSE
                        UPDATE game.player_politician_relations
                        SET friendliness_level = LEAST(100, relation_rec.friendliness_level + 10)
                        WHERE relation_id = relation_rec.relation_id;
                    END IF;
                ELSE
                    -- Failure
                    outcome := 'Failed to increase influence with ' || politician_rec.name || '.';
                END IF;
            END IF;
            
        -- Politician reputation attack
        WHEN 'politician_reputation_attack' THEN
            IF action_rec.target_politician_id IS NULL THEN
                outcome := 'Failed: No target politician specified.';
            ELSE
                SELECT * INTO politician_rec FROM game.politicians WHERE politician_id = action_rec.target_politician_id;
                
                IF roll <= success_chance THEN
                    -- Success: Reduce influence in district
                    outcome := 'Successfully undermined ' || politician_rec.name || '''s reputation.';
                    
                    -- Reduce politician's influence in district if they're a local politician
                    IF politician_rec.district_id IS NOT NULL THEN
                        UPDATE game.politicians
                        SET influence_in_district = GREATEST(0, influence_in_district - 2)
                        WHERE politician_id = action_rec.target_politician_id;
                    END IF;
                    
                    -- Create public news about the scandal
                    INSERT INTO game.news (
                        cycle_id,
                        title,
                        content,
                        news_type,
                        related_district_id
                    ) VALUES (
                        action_rec.cycle_id,
                        'Scandal Involving ' || politician_rec.name,
                        'Recent revelations have cast doubt on the credibility of ' || politician_rec.name || '.',
                        'public',
                        politician_rec.district_id
                    );
                ELSE
                    -- Failure
                    outcome := 'Failed to undermine ' || politician_rec.name || '''s reputation.';
                END IF;
            END IF;
            
        -- Politician displacement action
        WHEN 'politician_displacement' THEN
            IF action_rec.target_politician_id IS NULL THEN
                outcome := 'Failed: No target politician specified.';
            ELSE
                SELECT * INTO politician_rec FROM game.politicians WHERE politician_id = action_rec.target_politician_id;
                
                IF roll <= success_chance THEN
                    -- Success: Significantly reduce influence in district
                    outcome := 'Successfully displaced ' || politician_rec.name || ' from their position of power.';
                    
                    -- Reduce politician's influence in district if they're a local politician
                    IF politician_rec.district_id IS NOT NULL THEN
                        UPDATE game.politicians
                        SET influence_in_district = GREATEST(0, influence_in_district - 5)
                        WHERE politician_id = action_rec.target_politician_id;
                    END IF;
                    
                    -- Create public news about the displacement
                    INSERT INTO game.news (
                        cycle_id,
                        title,
                        content,
                        news_type,
                        related_district_id
                    ) VALUES (
                        action_rec.cycle_id,
                        politician_rec.name || ' Loses Political Standing',
                        politician_rec.name || ' has experienced a significant reduction in their influence and power.',
                        'public',
                        politician_rec.district_id
                    );
                ELSE
                    -- Failure
                    outcome := 'Failed to displace ' || politician_rec.name || ' from their position.';
                END IF;
            END IF;
            
        -- International negotiations action
        WHEN 'international_negotiations' THEN
            IF roll <= success_chance THEN
                -- Success: International effect reduced
                outcome := 'International negotiations successful! You have reduced international pressure.';
                
                -- Logic to reduce active international effects would go here
                -- For now, just create news
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id
                ) VALUES (
                    action_rec.cycle_id,
                    'Successful International Negotiations',
                    'Your diplomatic efforts have successfully reduced international pressure against you.',
                    'faction',
                    action_rec.player_id
                );
            ELSE
                -- Failure
                outcome := 'International negotiations failed. The international pressure remains.';
            END IF;
            
        -- Kompromat search action
        WHEN 'kompromat_search' THEN
            IF action_rec.target_politician_id IS NULL THEN
                outcome := 'Failed: No target politician specified.';
            ELSE
                SELECT * INTO politician_rec FROM game.politicians WHERE politician_id = action_rec.target_politician_id;
                
                IF roll <= success_chance THEN
                    -- Success: Found compromising information
                    outcome := 'Successfully found compromising information on ' || politician_rec.name || '.';
                    
                    -- Add to player resources
                    UPDATE game.resources
                    SET information_amount = information_amount + 2
                    WHERE player_id = action_rec.player_id;
                    
                    -- Log the resource gain
                    INSERT INTO game.resource_history (
                        player_id,
                        cycle_id,
                        change_type,
                        information_change,
                        reason
                    ) VALUES (
                        action_rec.player_id,
                        action_rec.cycle_id,
                        'kompromat_gain',
                        2,
                        'Compromising information found on ' || politician_rec.name
                    );
                    
                    -- Create faction news about the kompromat
                    INSERT INTO game.news (
                        cycle_id,
                        title,
                        content,
                        news_type,
                        target_player_id
                    ) VALUES (
                        action_rec.cycle_id,
                        'Compromising Information Found',
                        'Your agents have discovered compromising information about ' || politician_rec.name || 
                        '. This can be used for leverage.',
                        'faction',
                        action_rec.player_id
                    );
                ELSE
                    -- Failure
                    outcome := 'Failed to find compromising information on ' || politician_rec.name || '.';
                END IF;
            END IF;
            
        -- Lobbying action
        WHEN 'lobbying' THEN
            IF roll <= success_chance THEN
                -- Success: Influence international policy
                outcome := 'Lobbying successful! You have influenced international policy.';
                
                -- Create news effect
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id
                ) VALUES (
                    action_rec.cycle_id,
                    'Successful Lobbying Campaign',
                    'Your lobbying efforts have successfully influenced international policy in your favor.',
                    'faction',
                    action_rec.player_id
                );
                
                -- Public news about policy shift
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type
                ) VALUES (
                    action_rec.cycle_id,
                    'Shift in International Policy',
                    'Observers note a subtle shift in international approach to the region.',
                    'public'
                );
            ELSE
                -- Failure
                outcome := 'Lobbying efforts failed. International policy remains unchanged.';
            END IF;
            
        ELSE
            outcome := 'Unknown action type: ' || action_rec.action_type;
    END CASE;
    
    -- Update action with results
    UPDATE game.actions
    SET 
        status = 'completed',
        actual_outcome = outcome,
        outcome_control_points = control_points,
        processed_at = NOW()
    WHERE action_id = action_rec.action_id;
    
    -- Create news about the action result for the player
    INSERT INTO game.news (
        cycle_id,
        title,
        content,
        news_type,
        target_player_id,
        related_district_id
    ) VALUES (
        action_rec.cycle_id,
        action_rec.action_type || ' Action Result',
        outcome,
        'faction',
        action_rec.player_id,
        action_rec.district_id
    );
END;
$$ LANGUAGE plpgsql;

-- Process all pending actions for a cycle
CREATE OR REPLACE FUNCTION game.process_all_pending_actions(p_cycle_id UUID)
RETURNS INTEGER AS $$
DECLARE
    action_rec RECORD;
    processed_count INTEGER := 0;
BEGIN
    -- Process all pending actions for the cycle
    FOR action_rec IN (
        SELECT action_id
        FROM game.actions
        WHERE cycle_id = p_cycle_id AND status = 'pending'
        ORDER BY created_at
    ) LOOP
        BEGIN
            PERFORM game.process_action(action_rec.action_id);
            processed_count := processed_count + 1;
        EXCEPTION WHEN OTHERS THEN
            -- Log the error but continue with other actions
            RAISE NOTICE 'Error processing action %: %', action_rec.action_id, SQLERRM;
            
            -- Mark the action as failed
            UPDATE game.actions
            SET 
                status = 'completed',
                actual_outcome = 'Error: ' || SQLERRM,
                processed_at = NOW()
            WHERE action_id = action_rec.action_id;
        END;
    END LOOP;
    
    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Process collective actions
CREATE OR REPLACE FUNCTION game.process_collective_action(p_collective_action_id UUID)
RETURNS VOID AS $$
DECLARE
    collective_action_rec game.collective_actions;
    participant_rec RECORD;
    total_resources INTEGER := 0;
    base_control_points INTEGER := 0;
    success_chance INTEGER;
    roll INTEGER;
    outcome TEXT;
    district_control_rec game.district_control;
    target_district_control_rec game.district_control;
BEGIN
    -- Get collective action details
    SELECT * INTO collective_action_rec 
    FROM game.collective_actions 
    WHERE collective_action_id = p_collective_action_id;
    
    IF collective_action_rec IS NULL THEN
        RAISE EXCEPTION 'Collective action not found';
    END IF;
    
    -- Sum up all resources from participants
    SELECT SUM(resource_amount) INTO total_resources
    FROM game.collective_action_participants
    WHERE collective_action_id = p_collective_action_id;
    
    -- Calculate success chance based on total resources
    success_chance := 60 + (total_resources * 3);
    IF success_chance > 95 THEN
        success_chance := 95;
    END IF;
    
    -- Calculate base control points based on action type and resources
    IF collective_action_rec.action_type = 'attack' THEN
        base_control_points := 10 + (total_resources * 2);
    ELSIF collective_action_rec.action_type = 'defense' THEN
        base_control_points := 15 + (total_resources * 3);
    END IF;
    
    -- Determine if collective action succeeds
    roll := game.random_int(1, 100);
    
    -- Process results based on action type
    CASE collective_action_rec.action_type
        WHEN 'attack' THEN
            IF roll <= success_chance THEN
                -- Success
                outcome := 'Collective attack successful! Enemy control reduced significantly.';
                
                -- Process attack against target if specified
                IF collective_action_rec.target_player_id IS NOT NULL THEN
                    SELECT * INTO target_district_control_rec 
                    FROM game.district_control 
                    WHERE district_id = collective_action_rec.district_id 
                    AND player_id = collective_action_rec.target_player_id;
                    
                    IF target_district_control_rec IS NOT NULL THEN
                        -- Reduce target's control
                        UPDATE game.district_control
                        SET control_points = GREATEST(0, target_district_control_rec.control_points - base_control_points)
                        WHERE control_id = target_district_control_rec.control_id;
                        
                        -- Create news for the target player
                        INSERT INTO game.news (
                            cycle_id,
                            title,
                            content,
                            news_type,
                            target_player_id,
                            related_district_id
                        ) VALUES (
                            collective_action_rec.cycle_id,
                            'Massive Attack on Your Control in ' || (SELECT name FROM game.districts WHERE district_id = collective_action_rec.district_id),
                            'A coordinated attack has reduced your control in this district by ' || base_control_points || ' points.',
                            'faction',
                            collective_action_rec.target_player_id,
                            collective_action_rec.district_id
                        );
                    END IF;
                END IF;
                
                -- Distribute control points among participants
                FOR participant_rec IN (
                    SELECT * FROM game.collective_action_participants
                    WHERE collective_action_id = p_collective_action_id
                ) LOOP
                    -- Calculate participant's share of control points
                    -- Based on their resource contribution relative to total
                    DECLARE
                        participant_points INTEGER;
                    BEGIN
                        participant_points := FLOOR((participant_rec.resource_amount::FLOAT / total_resources) * base_control_points);
                        
                        -- Add physical presence bonus if applicable
                        IF participant_rec.physical_presence THEN
                            participant_points := participant_points + 10;
                        END IF;
                        
                        -- Update control points contribution
                        UPDATE game.collective_action_participants
                        SET control_points_contributed = participant_points
                        WHERE participant_id = participant_rec.participant_id;
                        
                        -- Update district control for this participant
                        SELECT * INTO district_control_rec 
                        FROM game.district_control 
                        WHERE district_id = collective_action_rec.district_id 
                        AND player_id = participant_rec.player_id;
                        
                        IF district_control_rec IS NULL THEN
                            -- Create new control record
                            INSERT INTO game.district_control (
                                district_id,
                                player_id,
                                control_points,
                                last_action_cycle_id
                            ) VALUES (
                                collective_action_rec.district_id,
                                participant_rec.player_id,
                                participant_points,
                                collective_action_rec.cycle_id
                            );
                        ELSE
                            -- Update existing control
                            UPDATE game.district_control
                            SET 
                                control_points = district_control_rec.control_points + participant_points,
                                last_action_cycle_id = collective_action_rec.cycle_id
                            WHERE control_id = district_control_rec.control_id;
                        END IF;
                        
                        -- Create news for this participant
                        INSERT INTO game.news (
                            cycle_id,
                            title,
                            content,
                            news_type,
                            target_player_id,
                            related_district_id
                        ) VALUES (
                            collective_action_rec.cycle_id,
                            'Collective Attack Results',
                            'Your participation in the collective attack earned you ' || participant_points || 
                            ' control points in ' || (SELECT name FROM game.districts WHERE district_id = collective_action_rec.district_id) || '.',
                            'faction',
                            participant_rec.player_id,
                            collective_action_rec.district_id
                        );
                    END;
                END LOOP;
            ELSE
                -- Failure
                outcome := 'Collective attack failed. No change in district control.';
                
                -- Inform all participants
                FOR participant_rec IN (
                    SELECT * FROM game.collective_action_participants
                    WHERE collective_action_id = p_collective_action_id
                ) LOOP
                    INSERT INTO game.news (
                        cycle_id,
                        title,
                        content,
                        news_type,
                        target_player_id,
                        related_district_id
                    ) VALUES (
                        collective_action_rec.cycle_id,
                        'Collective Attack Failed',
                        'The coordinated attack on ' || (SELECT name FROM game.districts WHERE district_id = collective_action_rec.district_id) || 
                        ' has failed. Resources were spent, but no control was gained.',
                        'faction',
                        participant_rec.player_id,
                        collective_action_rec.district_id
                    );
                END LOOP;
            END IF;
            
        WHEN 'defense' THEN
            -- Defense has higher base success rate
            IF roll <= success_chance + 10 THEN
                -- Success
                outcome := 'Collective defense successfully established. District is well-protected.';
                
                -- Distribute control points among participants
                FOR participant_rec IN (
                    SELECT * FROM game.collective_action_participants
                    WHERE collective_action_id = p_collective_action_id
                ) LOOP
                    -- Calculate participant's share
                    DECLARE
                        participant_points INTEGER;
                    BEGIN
                        participant_points := FLOOR((participant_rec.resource_amount::FLOAT / total_resources) * base_control_points);
                        
                        -- Add physical presence bonus if applicable
                        IF participant_rec.physical_presence THEN
                            participant_points := participant_points + 10;
                        END IF;
                        
                        -- Update control points contribution
                        UPDATE game.collective_action_participants
                        SET control_points_contributed = participant_points
                        WHERE participant_id = participant_rec.participant_id;
                        
                        -- Update district control for this participant
                        SELECT * INTO district_control_rec 
                        FROM game.district_control 
                        WHERE district_id = collective_action_rec.district_id 
                        AND player_id = participant_rec.player_id;
                        
                        IF district_control_rec IS NULL THEN
                            -- Create new control record
                            INSERT INTO game.district_control (
                                district_id,
                                player_id,
                                control_points,
                                last_action_cycle_id
                            ) VALUES (
                                collective_action_rec.district_id,
                                participant_rec.player_id,
                                participant_points,
                                collective_action_rec.cycle_id
                            );
                        ELSE
                            -- Update existing control
                            UPDATE game.district_control
                            SET 
                                control_points = district_control_rec.control_points + participant_points,
                                last_action_cycle_id = collective_action_rec.cycle_id
                            WHERE control_id = district_control_rec.control_id;
                        END IF;
                        
                        -- Create news for this participant
                        INSERT INTO game.news (
                            cycle_id,
                            title,
                            content,
                            news_type,
                            target_player_id,
                            related_district_id
                        ) VALUES (
                            collective_action_rec.cycle_id,
                            'Collective Defense Results',
                            'Your participation in the collective defense earned you ' || participant_points || 
                            ' control points in ' || (SELECT name FROM game.districts WHERE district_id = collective_action_rec.district_id) || '.',
                            'faction',
                            participant_rec.player_id,
                            collective_action_rec.district_id
                        );
                    END;
                END LOOP;
            ELSE
                -- Failure
                outcome := 'Collective defense partially established. Limited protection provided.';
                
                -- Distribute half the control points
                FOR participant_rec IN (
                    SELECT * FROM game.collective_action_participants
                    WHERE collective_action_id = p_collective_action_id
                ) LOOP
                    -- Calculate participant's share (half the normal amount)
                    DECLARE
                        participant_points INTEGER;
                    BEGIN
                        participant_points := FLOOR(((participant_rec.resource_amount::FLOAT / total_resources) * base_control_points) / 2);
                        
                        -- Update control points contribution
                        UPDATE game.collective_action_participants
                        SET control_points_contributed = participant_points
                        WHERE participant_id = participant_rec.participant_id;
                        
                        -- Update district control for this participant
                        SELECT * INTO district_control_rec 
                        FROM game.district_control 
                        WHERE district_id = collective_action_rec.district_id 
                        AND player_id = participant_rec.player_id;
                        
                        IF district_control_rec IS NULL THEN
                            -- Create new control record
                            INSERT INTO game.district_control (
                                district_id,
                                player_id,
                                control_points,
                                last_action_cycle_id
                            ) VALUES (
                                collective_action_rec.district_id,
                                participant_rec.player_id,
                                participant_points,
                                collective_action_rec.cycle_id
                            );
                        ELSE
                            -- Update existing control
                            UPDATE game.district_control
                            SET 
                                control_points = district_control_rec.control_points + participant_points,
                                last_action_cycle_id = collective_action_rec.cycle_id
                            WHERE control_id = district_control_rec.control_id;
                        END IF;
                        
                        -- Create news for this participant
                        INSERT INTO game.news (
                            cycle_id,
                            title,
                            content,
                            news_type,
                            target_player_id,
                            related_district_id
                        ) VALUES (
                            collective_action_rec.cycle_id,
                            'Collective Defense Partially Successful',
                            'The collective defense was only partially successful. You gained ' || participant_points || 
                            ' control points in ' || (SELECT name FROM game.districts WHERE district_id = collective_action_rec.district_id) || '.',
                            'faction',
                            participant_rec.player_id,
                            collective_action_rec.district_id
                        );
                    END;
                END LOOP;
            END IF;
    END CASE;
    
    -- Update collective action status
    UPDATE game.collective_actions
    SET 
        status = 'completed',
        total_control_points = base_control_points,
        completed_at = NOW()
    WHERE collective_action_id = p_collective_action_id;
    
    -- Create public news about the collective action
    INSERT INTO game.news (
        cycle_id,
        title,
        content,
        news_type,
        related_district_id
    ) VALUES (
        collective_action_rec.cycle_id,
        'Major ' || collective_action_rec.action_type || ' Operation in ' || (SELECT name FROM game.districts WHERE district_id = collective_action_rec.district_id),
        'Reports indicate a coordinated ' || collective_action_rec.action_type || ' operation has taken place in the district.',
        'public',
        collective_action_rec.district_id
    );
END;
$$ LANGUAGE plpgsql;

-- Process all pending collective actions for a cycle
CREATE OR REPLACE FUNCTION game.process_all_collective_actions(p_cycle_id UUID)
RETURNS INTEGER AS $$
DECLARE
    action_rec RECORD;
    processed_count INTEGER := 0;
BEGIN
    -- Process all active collective actions for the cycle
    FOR action_rec IN (
        SELECT collective_action_id
        FROM game.collective_actions
        WHERE cycle_id = p_cycle_id AND status = 'active'
        ORDER BY created_at
    ) LOOP
        BEGIN
            PERFORM game.process_collective_action(action_rec.collective_action_id);
            processed_count := processed_count + 1;
        EXCEPTION WHEN OTHERS THEN
            -- Log the error but continue with other actions
            RAISE NOTICE 'Error processing collective action %: %', action_rec.collective_action_id, SQLERRM;
            
            -- Mark the action as failed
            UPDATE game.collective_actions
            SET 
                status = 'completed',
                completed_at = NOW()
            WHERE collective_action_id = action_rec.collective_action_id;
        END;
    END LOOP;
    
    RETURN processed_count;
END;
$$ LANGUAGE plpgsql;

-- Resource exchange function
CREATE OR REPLACE FUNCTION game.exchange_resource(
    p_player_id UUID,
    p_from_resource TEXT,
    p_to_resource TEXT,
    p_amount INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    resources_rec game.resources;
    exchange_rate INTEGER := 2; -- Default 2:1 exchange rate
BEGIN
    -- Get player resources
    SELECT * INTO resources_rec FROM game.resources WHERE player_id = p_player_id;
    
    -- Check if player has enough of the source resource
    CASE p_from_resource
        WHEN 'money' THEN
            IF resources_rec.money_amount < p_amount * exchange_rate THEN
                RETURN FALSE;
            END IF;
        WHEN 'influence' THEN
            IF resources_rec.influence_amount < p_amount * exchange_rate THEN
                RETURN FALSE;
            END IF;
        WHEN 'information' THEN
            IF resources_rec.information_amount < p_amount * exchange_rate THEN
                RETURN FALSE;
            END IF;
        WHEN 'force' THEN
            IF resources_rec.force_amount < p_amount * exchange_rate THEN
                RETURN FALSE;
            END IF;
        ELSE
            RETURN FALSE;
    END CASE;
    
    -- Deduct source resource
    CASE p_from_resource
        WHEN 'money' THEN
            UPDATE game.resources
            SET money_amount = money_amount - (p_amount * exchange_rate)
            WHERE player_id = p_player_id;
        WHEN 'influence' THEN
            UPDATE game.resources
            SET influence_amount = influence_amount - (p_amount * exchange_rate)
            WHERE player_id = p_player_id;
        WHEN 'information' THEN
            UPDATE game.resources
            SET information_amount = information_amount - (p_amount * exchange_rate)
            WHERE player_id = p_player_id;
        WHEN 'force' THEN
            UPDATE game.resources
            SET force_amount = force_amount - (p_amount * exchange_rate)
            WHERE player_id = p_player_id;
    END CASE;
    
    -- Add target resource
    CASE p_to_resource
        WHEN 'money' THEN
            UPDATE game.resources
            SET money_amount = money_amount + p_amount
            WHERE player_id = p_player_id;
        WHEN 'influence' THEN
            UPDATE game.resources
            SET influence_amount = influence_amount + p_amount
            WHERE player_id = p_player_id;
        WHEN 'information' THEN
            UPDATE game.resources
            SET information_amount = information_amount + p_amount
            WHERE player_id = p_player_id;
        WHEN 'force' THEN
            UPDATE game.resources
            SET force_amount = force_amount + p_amount
            WHERE player_id = p_player_id;
    END CASE;
    
    -- Log the resource exchange
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
        p_player_id,
        (SELECT cycle_id FROM game.get_current_cycle()),
        'resource_exchange',
        CASE 
            WHEN p_from_resource = 'influence' THEN -(p_amount * exchange_rate)
            WHEN p_to_resource = 'influence' THEN p_amount
            ELSE 0
        END,
        CASE 
            WHEN p_from_resource = 'money' THEN -(p_amount * exchange_rate)
            WHEN p_to_resource = 'money' THEN p_amount
            ELSE 0
        END,
        CASE 
            WHEN p_from_resource = 'information' THEN -(p_amount * exchange_rate)
            WHEN p_to_resource = 'information' THEN p_amount
            ELSE 0
        END,
        CASE 
            WHEN p_from_resource = 'force' THEN -(p_amount * exchange_rate)
            WHEN p_to_resource = 'force' THEN p_amount
            ELSE 0
        END,
        'Resource exchange: ' || p_from_resource || ' -> ' || p_to_resource
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Generate international effect
CREATE OR REPLACE FUNCTION game.generate_international_effect(
    p_politician_id UUID
)
RETURNS game.international_effects AS $$
DECLARE
    politician_rec game.politicians;
    current_cycle game.cycles;
    effect_type TEXT;
    target_district_id UUID;
    control_points_effect INTEGER;
    resource_effect_type TEXT;
    resource_effect_amount INTEGER;
    description TEXT;
    new_effect game.international_effects;
    target_ideology INTEGER;
BEGIN
    -- Get politician data
    SELECT * INTO politician_rec FROM game.politicians WHERE politician_id = p_politician_id;
    
    IF politician_rec IS NULL OR politician_rec.type != 'international' THEN
        RAISE EXCEPTION 'Invalid international politician ID';
    END IF;
    
    -- Get current cycle
    SELECT * INTO current_cycle FROM game.get_current_cycle();
    
    -- Determine effect type based on politician's ideology and randomness
    IF politician_rec.ideological_leaning <= -3 THEN
        -- Reformist international politicians tend to use sanctions against conservative players
        effect_type := CASE game.random_int(1, 3)
            WHEN 1 THEN 'sanctions'
            WHEN 2 THEN 'support'
            ELSE 'diplomacy'
        END;
        target_ideology := 5; -- Target conservative players
    ELSIF politician_rec.ideological_leaning >= 3 THEN
        -- Conservative international politicians tend to attack reformist players
        effect_type := CASE game.random_int(1, 3)
            WHEN 1 THEN 'attack'
            WHEN 2 THEN 'destabilization'
            ELSE 'diplomacy'
        END;
        target_ideology := -5; -- Target reformist players
    ELSE
        -- Neutral politicians are more diplomatic
        effect_type := CASE game.random_int(1, 3)
            WHEN 1 THEN 'diplomacy'
            WHEN 2 THEN 'support'
            ELSE 'destabilization'
        END;
        target_ideology := NULL; -- No specific target
    END IF;
    
    -- Choose a random target district
    SELECT district_id INTO target_district_id
    FROM game.districts
    ORDER BY RANDOM()
    LIMIT 1;
    
    -- Set effect parameters based on type
    CASE effect_type
        WHEN 'sanctions' THEN
            control_points_effect := -10;
            resource_effect_type := CASE game.random_int(1, 4)
                WHEN 1 THEN 'influence'
                WHEN 2 THEN 'money'
                WHEN 3 THEN 'information'
                ELSE 'force'
            END;
            resource_effect_amount := -5;
            description := politician_rec.name || ' from ' || politician_rec.country || 
                            ' has imposed sanctions affecting ' || resource_effect_type || ' resources.';
        
        WHEN 'support' THEN
            control_points_effect := 10;
            resource_effect_type := CASE game.random_int(1, 4)
                WHEN 1 THEN 'influence'
                WHEN 2 THEN 'money'
                WHEN 3 THEN 'information'
                ELSE 'force'
            END;
            resource_effect_amount := 5;
            description := politician_rec.name || ' from ' || politician_rec.country || 
                            ' has offered support, increasing ' || resource_effect_type || ' resources.';
        
        WHEN 'attack' THEN
            control_points_effect := -15;
            resource_effect_type := NULL;
            resource_effect_amount := NULL;
            description := politician_rec.name || ' from ' || politician_rec.country || 
                            ' has launched a political attack, significantly reducing control in ' ||
                            (SELECT name FROM game.districts WHERE district_id = target_district_id) || ' district.';
        
        WHEN 'destabilization' THEN
            control_points_effect := -8;
            resource_effect_type := NULL;
            resource_effect_amount := NULL;
            description := politician_rec.name || ' from ' || politician_rec.country || 
                            ' has caused destabilization in ' ||
                            (SELECT name FROM game.districts WHERE district_id = target_district_id) || ' district.';
        
        WHEN 'diplomacy' THEN
            control_points_effect := 5;
            resource_effect_type := 'influence';
            resource_effect_amount := 3;
            description := politician_rec.name || ' from ' || politician_rec.country || 
                            ' has initiated diplomatic efforts, slightly increasing influence in ' ||
                            (SELECT name FROM game.districts WHERE district_id = target_district_id) || ' district.';
    END CASE;
    
    -- Create the international effect
    INSERT INTO game.international_effects (
        politician_id,
        cycle_id,
        effect_type,
        target_ideology,
        target_district_id,
        control_points_effect,
        resource_effect_type,
        resource_effect_amount,
        description,
        expires_at
    ) VALUES (
        p_politician_id,
        current_cycle.cycle_id,
        effect_type,
        target_ideology,
        target_district_id,
        control_points_effect,
        resource_effect_type,
        resource_effect_amount,
        description,
        NOW() + INTERVAL '1 day' -- Effect lasts for 1 day
    ) RETURNING * INTO new_effect;
    
    -- Create news about the international effect
    INSERT INTO game.news (
        cycle_id,
        title,
        content,
        news_type,
        related_district_id
    ) VALUES (
        current_cycle.cycle_id,
        'International Development: ' || politician_rec.name || ' (' || politician_rec.country || ')',
        description,
        'public',
        target_district_id
    );
    
    RETURN new_effect;
END;
$$ LANGUAGE plpgsql;

-- Apply international effects to players
CREATE OR REPLACE FUNCTION game.apply_international_effects()
RETURNS INTEGER AS $$
DECLARE
    effect_rec RECORD;
    player_rec RECORD;
    district_control_rec game.district_control;
    applied_count INTEGER := 0;
BEGIN
    -- Get all active international effects
    FOR effect_rec IN (
        SELECT *
        FROM game.international_effects
        WHERE expires_at > NOW()
    ) LOOP
        -- Find players affected by this effect based on ideology and district
        FOR player_rec IN (
            SELECT p.*
            FROM game.players p
            JOIN game.district_control dc ON p.player_id = dc.player_id
            WHERE dc.district_id = effect_rec.target_district_id
            AND (
                effect_rec.target_ideology IS NULL -- Effect targets everyone
                OR 
                (effect_rec.target_ideology > 0 AND p.ideology_score > 0) -- Effect targets conservatives
                OR 
                (effect_rec.target_ideology < 0 AND p.ideology_score < 0) -- Effect targets reformists
            )
        ) LOOP
            -- Apply control point effect
            IF effect_rec.control_points_effect IS NOT NULL THEN
                SELECT * INTO district_control_rec
                FROM game.district_control
                WHERE district_id = effect_rec.target_district_id AND player_id = player_rec.player_id;
                
                IF district_control_rec IS NOT NULL THEN
                    UPDATE game.district_control
                    SET control_points = GREATEST(0, district_control_rec.control_points + effect_rec.control_points_effect)
                    WHERE control_id = district_control_rec.control_id;
                    
                    -- Create news for the player about control effect
                    INSERT INTO game.news (
                        cycle_id,
                        title,
                        content,
                        news_type,
                        target_player_id,
                        related_district_id
                    ) VALUES (
                        (SELECT cycle_id FROM game.get_current_cycle()),
                        'International Effect on District Control',
                        'Due to international action by ' || 
                        (SELECT name || ' (' || country || ')' FROM game.politicians WHERE politician_id = effect_rec.politician_id) || 
                        ', your control in ' || 
                        (SELECT name FROM game.districts WHERE district_id = effect_rec.target_district_id) || 
                        ' has changed by ' || effect_rec.control_points_effect || ' points.',
                        'faction',
                        player_rec.player_id,
                        effect_rec.target_district_id
                    );
                END IF;
            END IF;
            
            -- Apply resource effect
            IF effect_rec.resource_effect_type IS NOT NULL AND effect_rec.resource_effect_amount IS NOT NULL THEN
                CASE effect_rec.resource_effect_type
                    WHEN 'influence' THEN
                        UPDATE game.resources
                        SET influence_amount = GREATEST(0, influence_amount + effect_rec.resource_effect_amount)
                        WHERE player_id = player_rec.player_id;
                    WHEN 'money' THEN
                        UPDATE game.resources
                        SET money_amount = GREATEST(0, money_amount + effect_rec.resource_effect_amount)
                        WHERE player_id = player_rec.player_id;
                    WHEN 'information' THEN
                        UPDATE game.resources
                        SET information_amount = GREATEST(0, information_amount + effect_rec.resource_effect_amount)
                        WHERE player_id = player_rec.player_id;
                    WHEN 'force' THEN
                        UPDATE game.resources
                        SET force_amount = GREATEST(0, force_amount + effect_rec.resource_effect_amount)
                        WHERE player_id = player_rec.player_id;
                END CASE;
                
                -- Record resource history
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
                    player_rec.player_id,
                    (SELECT cycle_id FROM game.get_current_cycle()),
                    'international_effect',
                    CASE WHEN effect_rec.resource_effect_type = 'influence' THEN effect_rec.resource_effect_amount ELSE 0 END,
                    CASE WHEN effect_rec.resource_effect_type = 'money' THEN effect_rec.resource_effect_amount ELSE 0 END,
                    CASE WHEN effect_rec.resource_effect_type = 'information' THEN effect_rec.resource_effect_amount ELSE 0 END,
                    CASE WHEN effect_rec.resource_effect_type = 'force' THEN effect_rec.resource_effect_amount ELSE 0 END,
                    'International effect from ' || 
                    (SELECT name FROM game.politicians WHERE politician_id = effect_rec.politician_id)
                );
                
                -- Create news for the player about resource effect
                INSERT INTO game.news (
                    cycle_id,
                    title,
                    content,
                    news_type,
                    target_player_id
                ) VALUES (
                    (SELECT cycle_id FROM game.get_current_cycle()),
                    'International Effect on Resources',
                    'Due to international action by ' || 
                    (SELECT name || ' (' || country || ')' FROM game.politicians WHERE politician_id = effect_rec.politician_id) || 
                    ', your ' || effect_rec.resource_effect_type || ' resources have changed by ' || 
                    effect_rec.resource_effect_amount || '.',
                    'faction',
                    player_rec.player_id
                );
            END IF;
            
            applied_count := applied_count + 1;
        END LOOP;
    END LOOP;
    
    RETURN applied_count;
END;
$$ LANGUAGE plpgsql;
