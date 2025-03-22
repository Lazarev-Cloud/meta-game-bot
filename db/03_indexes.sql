-- 03_indexes.sql
-- Create indexes to optimize query performance

-- Players indexes
CREATE INDEX IF NOT EXISTS idx_players_telegram_id ON game.players(telegram_id);
CREATE INDEX IF NOT EXISTS idx_players_ideology ON game.players(ideology_score);

-- Cycles indexes
CREATE INDEX IF NOT EXISTS idx_cycles_dates ON game.cycles(cycle_date, cycle_type);
CREATE INDEX IF NOT EXISTS idx_cycles_active ON game.cycles(is_active) WHERE is_active = TRUE;

-- Politicians indexes
CREATE INDEX IF NOT EXISTS idx_politicians_type ON game.politicians(type);
CREATE INDEX IF NOT EXISTS idx_politicians_district ON game.politicians(district_id);
CREATE INDEX IF NOT EXISTS idx_politicians_ideology ON game.politicians(ideological_leaning);

-- District control indexes
CREATE INDEX IF NOT EXISTS idx_district_control_district ON game.district_control(district_id);
CREATE INDEX IF NOT EXISTS idx_district_control_player ON game.district_control(player_id);
CREATE INDEX IF NOT EXISTS idx_district_control_points ON game.district_control(control_points);
CREATE INDEX IF NOT EXISTS idx_district_control_last_action ON game.district_control(last_action_cycle_id);

-- Resources indexes
CREATE INDEX IF NOT EXISTS idx_resources_player ON game.resources(player_id);

-- Resource history indexes
CREATE INDEX IF NOT EXISTS idx_resource_history_player ON game.resource_history(player_id);
CREATE INDEX IF NOT EXISTS idx_resource_history_cycle ON game.resource_history(cycle_id);
CREATE INDEX IF NOT EXISTS idx_resource_history_created ON game.resource_history(created_at);

-- Actions indexes
CREATE INDEX IF NOT EXISTS idx_actions_player ON game.actions(player_id);
CREATE INDEX IF NOT EXISTS idx_actions_cycle ON game.actions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_actions_district ON game.actions(district_id);
CREATE INDEX IF NOT EXISTS idx_actions_target_player ON game.actions(target_player_id);
CREATE INDEX IF NOT EXISTS idx_actions_target_politician ON game.actions(target_politician_id);
CREATE INDEX IF NOT EXISTS idx_actions_type ON game.actions(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_status ON game.actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_quick ON game.actions(is_quick_action);
CREATE INDEX IF NOT EXISTS idx_actions_created ON game.actions(created_at);

-- Collective actions indexes
CREATE INDEX IF NOT EXISTS idx_collective_actions_initiator ON game.collective_actions(initiator_player_id);
CREATE INDEX IF NOT EXISTS idx_collective_actions_district ON game.collective_actions(district_id);
CREATE INDEX IF NOT EXISTS idx_collective_actions_cycle ON game.collective_actions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_collective_actions_status ON game.collective_actions(status);
CREATE INDEX IF NOT EXISTS idx_collective_actions_target ON game.collective_actions(target_player_id);

-- Collective action participants indexes
CREATE INDEX IF NOT EXISTS idx_action_participants_action ON game.collective_action_participants(collective_action_id);
CREATE INDEX IF NOT EXISTS idx_action_participants_player ON game.collective_action_participants(player_id);

-- Player-politician relations indexes
CREATE INDEX IF NOT EXISTS idx_player_politician_player ON game.player_politician_relations(player_id);
CREATE INDEX IF NOT EXISTS idx_player_politician_politician ON game.player_politician_relations(politician_id);
CREATE INDEX IF NOT EXISTS idx_player_politician_friendliness ON game.player_politician_relations(friendliness_level);

-- News indexes
CREATE INDEX IF NOT EXISTS idx_news_cycle ON game.news(cycle_id);
CREATE INDEX IF NOT EXISTS idx_news_type ON game.news(news_type);
CREATE INDEX IF NOT EXISTS idx_news_target_player ON game.news(target_player_id);
CREATE INDEX IF NOT EXISTS idx_news_district ON game.news(related_district_id);
CREATE INDEX IF NOT EXISTS idx_news_created ON game.news(created_at);

-- Translations indexes
CREATE INDEX IF NOT EXISTS idx_translations_key ON game.translations(translation_key);

-- International effects indexes
CREATE INDEX IF NOT EXISTS idx_international_effects_politician ON game.international_effects(politician_id);
CREATE INDEX IF NOT EXISTS idx_international_effects_cycle ON game.international_effects(cycle_id);
CREATE INDEX IF NOT EXISTS idx_international_effects_district ON game.international_effects(target_district_id);
CREATE INDEX IF NOT EXISTS idx_international_effects_type ON game.international_effects(effect_type);
CREATE INDEX IF NOT EXISTS idx_international_effects_expiry ON game.international_effects(expires_at);
