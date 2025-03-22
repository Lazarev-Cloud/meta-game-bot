-- 04_validation.sql
-- Triggers and constraints for data validation and integrity

-- Function to update the 'updated_at' field for various tables
CREATE OR REPLACE FUNCTION game.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the updated_at trigger to relevant tables
CREATE TRIGGER trg_resources_updated
BEFORE UPDATE ON game.resources
FOR EACH ROW EXECUTE FUNCTION game.update_timestamp();

CREATE TRIGGER trg_district_control_updated
BEFORE UPDATE ON game.district_control
FOR EACH ROW EXECUTE FUNCTION game.update_timestamp();

CREATE TRIGGER trg_player_politician_relations_updated
BEFORE UPDATE ON game.player_politician_relations
FOR EACH ROW EXECUTE FUNCTION game.update_timestamp();

CREATE TRIGGER trg_translations_updated
BEFORE UPDATE ON game.translations
FOR EACH ROW EXECUTE FUNCTION game.update_timestamp();

-- Function to validate player resources when submitting an action
CREATE OR REPLACE FUNCTION game.validate_action_resources()
RETURNS TRIGGER AS $$
DECLARE
    player_resources game.resources;
BEGIN
    -- Get the player's current resources
    SELECT * INTO player_resources 
    FROM game.resources
    WHERE player_id = NEW.player_id;
    
    -- Check if player has enough resources for the action
    IF NEW.resource_type = 'influence' AND player_resources.influence_amount < NEW.resource_amount THEN
        RAISE EXCEPTION 'Player does not have enough influence resources';
    ELSIF NEW.resource_type = 'money' AND player_resources.money_amount < NEW.resource_amount THEN
        RAISE EXCEPTION 'Player does not have enough money resources';
    ELSIF NEW.resource_type = 'information' AND player_resources.information_amount < NEW.resource_amount THEN
        RAISE EXCEPTION 'Player does not have enough information resources';
    ELSIF NEW.resource_type = 'force' AND player_resources.force_amount < NEW.resource_amount THEN
        RAISE EXCEPTION 'Player does not have enough force resources';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply resource validation trigger to actions
CREATE TRIGGER trg_validate_action_resources
BEFORE INSERT ON game.actions
FOR EACH ROW EXECUTE FUNCTION game.validate_action_resources();

-- Apply resource validation trigger to collective action participants
CREATE TRIGGER trg_validate_collective_action_resources
BEFORE INSERT ON game.collective_action_participants
FOR EACH ROW EXECUTE FUNCTION game.validate_action_resources();

-- Function to validate player's remaining actions per cycle
CREATE OR REPLACE FUNCTION game.validate_player_actions_limit()
RETURNS TRIGGER AS $$
DECLARE
    action_count INTEGER;
    quick_action_count INTEGER;
    player_data game.players;
BEGIN
    -- Get player data
    SELECT * INTO player_data
    FROM game.players
    WHERE player_id = NEW.player_id;
    
    -- Count existing actions for this player in this cycle
    IF NOT NEW.is_quick_action THEN
        SELECT COUNT(*) INTO action_count
        FROM game.actions
        WHERE 
            player_id = NEW.player_id 
            AND cycle_id = NEW.cycle_id 
            AND is_quick_action = FALSE
            AND status != 'cancelled';
            
        IF action_count >= player_data.remaining_actions THEN
            RAISE EXCEPTION 'Player has already used all available actions for this cycle';
        END IF;
    ELSE
        SELECT COUNT(*) INTO quick_action_count
        FROM game.actions
        WHERE 
            player_id = NEW.player_id 
            AND cycle_id = NEW.cycle_id 
            AND is_quick_action = TRUE
            AND status != 'cancelled';
            
        IF quick_action_count >= player_data.remaining_quick_actions THEN
            RAISE EXCEPTION 'Player has already used all available quick actions for this cycle';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply action limit validation trigger
CREATE TRIGGER trg_validate_player_actions_limit
BEFORE INSERT ON game.actions
FOR EACH ROW EXECUTE FUNCTION game.validate_player_actions_limit();

-- Function to validate and update district control status
CREATE OR REPLACE FUNCTION game.update_district_control_status()
RETURNS TRIGGER AS $$
DECLARE
    old_controlling_player UUID;
    threshold_control INTEGER := 60;
BEGIN
    -- Check if control has changed
    IF NEW.control_points >= threshold_control AND 
       (OLD.control_points < threshold_control OR OLD.player_id != NEW.player_id) THEN
        
        -- Get current controlling player for this district
        SELECT player_id INTO old_controlling_player
        FROM game.district_control
        WHERE 
            district_id = NEW.district_id 
            AND player_id != NEW.player_id
            AND control_points >= threshold_control;
            
        -- If there was a different controlling player, reduce their control
        IF old_controlling_player IS NOT NULL THEN
            UPDATE game.district_control
            SET control_points = control_points - 10
            WHERE player_id = old_controlling_player AND district_id = NEW.district_id;
            
            -- Generate news about district control change
            INSERT INTO game.news (
                cycle_id,
                title,
                content,
                news_type,
                related_district_id
            )
            VALUES (
                (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE LIMIT 1),
                'Control Change in ' || (SELECT name FROM game.districts WHERE district_id = NEW.district_id),
                'Control of the district has changed to a new faction.',
                'public',
                NEW.district_id
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply district control status trigger
CREATE TRIGGER trg_update_district_control_status
AFTER UPDATE ON game.district_control
FOR EACH ROW EXECUTE FUNCTION game.update_district_control_status();

-- Function to handle resource deduction when action is submitted
CREATE OR REPLACE FUNCTION game.deduct_action_resources()
RETURNS TRIGGER AS $$
BEGIN
    -- Deduct resources based on action type
    IF NEW.resource_type = 'influence' THEN
        UPDATE game.resources
        SET influence_amount = influence_amount - NEW.resource_amount
        WHERE player_id = NEW.player_id;
    ELSIF NEW.resource_type = 'money' THEN
        UPDATE game.resources
        SET money_amount = money_amount - NEW.resource_amount
        WHERE player_id = NEW.player_id;
    ELSIF NEW.resource_type = 'information' THEN
        UPDATE game.resources
        SET information_amount = information_amount - NEW.resource_amount
        WHERE player_id = NEW.player_id;
    ELSIF NEW.resource_type = 'force' THEN
        UPDATE game.resources
        SET force_amount = force_amount - NEW.resource_amount
        WHERE player_id = NEW.player_id;
    END IF;
    
    -- Log the resource change in history
    INSERT INTO game.resource_history (
        player_id,
        cycle_id,
        change_type,
        influence_change,
        money_change,
        information_change,
        force_change,
        reason
    )
    VALUES (
        NEW.player_id,
        NEW.cycle_id,
        'action_deduction',
        CASE WHEN NEW.resource_type = 'influence' THEN -NEW.resource_amount ELSE 0 END,
        CASE WHEN NEW.resource_type = 'money' THEN -NEW.resource_amount ELSE 0 END,
        CASE WHEN NEW.resource_type = 'information' THEN -NEW.resource_amount ELSE 0 END,
        CASE WHEN NEW.resource_type = 'force' THEN -NEW.resource_amount ELSE 0 END,
        'Resource used for ' || NEW.action_type || ' action'
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply resource deduction trigger
CREATE TRIGGER trg_deduct_action_resources
AFTER INSERT ON game.actions
FOR EACH ROW EXECUTE FUNCTION game.deduct_action_resources();

-- Similar trigger for collective action participants
CREATE TRIGGER trg_deduct_collective_action_resources
AFTER INSERT ON game.collective_action_participants
FOR EACH ROW EXECUTE FUNCTION game.deduct_action_resources();

-- Function to validate politician ideological leaning changes
CREATE OR REPLACE FUNCTION game.validate_politician_ideology_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure ideology stays within the -5 to +5 range
    IF NEW.ideological_leaning < -5 THEN
        NEW.ideological_leaning := -5;
    ELSIF NEW.ideological_leaning > 5 THEN
        NEW.ideological_leaning := 5;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply politician ideology validation trigger
CREATE TRIGGER trg_validate_politician_ideology
BEFORE UPDATE ON game.politicians
FOR EACH ROW EXECUTE FUNCTION game.validate_politician_ideology_change();

-- Function to handle action cancellation and refund resources
CREATE OR REPLACE FUNCTION game.handle_action_cancellation()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
        -- Refund resources to the player
        IF NEW.resource_type = 'influence' THEN
            UPDATE game.resources
            SET influence_amount = influence_amount + NEW.resource_amount
            WHERE player_id = NEW.player_id;
        ELSIF NEW.resource_type = 'money' THEN
            UPDATE game.resources
            SET money_amount = money_amount + NEW.resource_amount
            WHERE player_id = NEW.player_id;
        ELSIF NEW.resource_type = 'information' THEN
            UPDATE game.resources
            SET information_amount = information_amount + NEW.resource_amount
            WHERE player_id = NEW.player_id;
        ELSIF NEW.resource_type = 'force' THEN
            UPDATE game.resources
            SET force_amount = force_amount + NEW.resource_amount
            WHERE player_id = NEW.player_id;
        END IF;
        
        -- Log the refund in history
        INSERT INTO game.resource_history (
            player_id,
            cycle_id,
            change_type,
            influence_change,
            money_change,
            information_change,
            force_change,
            reason
        )
        VALUES (
            NEW.player_id,
            NEW.cycle_id,
            'action_refund',
            CASE WHEN NEW.resource_type = 'influence' THEN NEW.resource_amount ELSE 0 END,
            CASE WHEN NEW.resource_type = 'money' THEN NEW.resource_amount ELSE 0 END,
            CASE WHEN NEW.resource_type = 'information' THEN NEW.resource_amount ELSE 0 END,
            CASE WHEN NEW.resource_type = 'force' THEN NEW.resource_amount ELSE 0 END,
            'Resource refunded for cancelled ' || NEW.action_type || ' action'
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply action cancellation trigger
CREATE TRIGGER trg_handle_action_cancellation
AFTER UPDATE ON game.actions
FOR EACH ROW
WHEN (NEW.status = 'cancelled' AND OLD.status != 'cancelled')
EXECUTE FUNCTION game.handle_action_cancellation();

-- Function to validate player ideology score changes
CREATE OR REPLACE FUNCTION game.validate_player_ideology()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure ideology stays within the -5 to +5 range
    IF NEW.ideology_score < -5 THEN
        NEW.ideology_score := -5;
    ELSIF NEW.ideology_score > 5 THEN
        NEW.ideology_score := 5;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply player ideology validation trigger
CREATE TRIGGER trg_validate_player_ideology
BEFORE UPDATE ON game.players
FOR EACH ROW EXECUTE FUNCTION game.validate_player_ideology();

-- Function to validate player-politician friendliness level
CREATE OR REPLACE FUNCTION game.validate_friendliness_level()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure friendliness stays within the 0 to 100 range
    IF NEW.friendliness_level < 0 THEN
        NEW.friendliness_level := 0;
    ELSIF NEW.friendliness_level > 100 THEN
        NEW.friendliness_level := 100;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply friendliness validation trigger
CREATE TRIGGER trg_validate_friendliness_level
BEFORE UPDATE ON game.player_politician_relations
FOR EACH ROW EXECUTE FUNCTION game.validate_friendliness_level();
