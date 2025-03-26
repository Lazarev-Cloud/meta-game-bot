-- 03_indexes.sql
-- Create indexes to optimize query performance

-- Players indexes
CREATE INDEX IF NOT EXISTS idx_players_telegram_id ON players(telegram_id);
CREATE INDEX IF NOT EXISTS idx_players_ideology ON players(ideology_score);

-- Cycles indexes
CREATE INDEX IF NOT EXISTS idx_cycles_dates ON cycles(cycle_date, cycle_type);
CREATE INDEX IF NOT EXISTS idx_cycles_active ON cycles(is_active) WHERE is_active = TRUE;

-- Politicians indexes
CREATE INDEX IF NOT EXISTS idx_politicians_type ON politicians(type);
CREATE INDEX IF NOT EXISTS idx_politicians_district ON politicians(district_id);
CREATE INDEX IF NOT EXISTS idx_politicians_ideology ON politicians(ideological_leaning);

-- District control indexes
CREATE INDEX IF NOT EXISTS idx_district_control_district ON district_control(district_id);
CREATE INDEX IF NOT EXISTS idx_district_control_player ON district_control(player_id);
CREATE INDEX IF NOT EXISTS idx_district_control_points ON district_control(control_points);
CREATE INDEX IF NOT EXISTS idx_district_control_last_action ON district_control(last_action_cycle_id);

-- Resources indexes
CREATE INDEX IF NOT EXISTS idx_resources_player ON resources(player_id);

-- Resource history indexes
CREATE INDEX IF NOT EXISTS idx_resource_history_player ON resource_history(player_id);
CREATE INDEX IF NOT EXISTS idx_resource_history_cycle ON resource_history(cycle_id);
CREATE INDEX IF NOT EXISTS idx_resource_history_created ON resource_history(created_at);

-- Actions indexes
CREATE INDEX IF NOT EXISTS idx_actions_player ON actions(player_id);
CREATE INDEX IF NOT EXISTS idx_actions_cycle ON actions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_actions_district ON actions(district_id);
CREATE INDEX IF NOT EXISTS idx_actions_target_player ON actions(target_player_id);
CREATE INDEX IF NOT EXISTS idx_actions_target_politician ON actions(target_politician_id);
CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_quick ON actions(is_quick_action);
CREATE INDEX IF NOT EXISTS idx_actions_created ON actions(created_at);

-- Collective actions indexes
CREATE INDEX IF NOT EXISTS idx_collective_actions_initiator ON collective_actions(initiator_player_id);
CREATE INDEX IF NOT EXISTS idx_collective_actions_district ON collective_actions(district_id);
CREATE INDEX IF NOT EXISTS idx_collective_actions_cycle ON collective_actions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_collective_actions_status ON collective_actions(status);
CREATE INDEX IF NOT EXISTS idx_collective_actions_target ON collective_actions(target_player_id);

-- Collective action participants indexes
CREATE INDEX IF NOT EXISTS idx_action_participants_action ON collective_action_participants(collective_action_id);
CREATE INDEX IF NOT EXISTS idx_action_participants_player ON collective_action_participants(player_id);

-- Player-politician relations indexes
CREATE INDEX IF NOT EXISTS idx_player_politician_player ON player_politician_relations(player_id);
CREATE INDEX IF NOT EXISTS idx_player_politician_politician ON player_politician_relations(politician_id);
CREATE INDEX IF NOT EXISTS idx_player_politician_friendliness ON player_politician_relations(friendliness_level);

-- News indexes
CREATE INDEX IF NOT EXISTS idx_news_cycle ON news(cycle_id);
CREATE INDEX IF NOT EXISTS idx_news_type ON news(news_type);
CREATE INDEX IF NOT EXISTS idx_news_target_player ON news(target_player_id);
CREATE INDEX IF NOT EXISTS idx_news_district ON news(related_district_id);
CREATE INDEX IF NOT EXISTS idx_news_created ON news(created_at);

-- Translations indexes
CREATE INDEX IF NOT EXISTS idx_translations_key ON translations(translation_key);

-- International effects indexes
CREATE INDEX IF NOT EXISTS idx_international_effects_politician ON international_effects(politician_id);
CREATE INDEX IF NOT EXISTS idx_international_effects_cycle ON international_effects(cycle_id);
CREATE INDEX IF NOT EXISTS idx_international_effects_district ON international_effects(target_district_id);
CREATE INDEX IF NOT EXISTS idx_international_effects_type ON international_effects(effect_type);
CREATE INDEX IF NOT EXISTS idx_international_effects_expiry ON international_effects(expires_at);
