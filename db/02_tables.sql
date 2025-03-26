-- 02_tables.sql
-- Define all tables for the Novi-Sad political game

-- Game cycles (morning/evening cycles)
CREATE TABLE IF NOT EXISTS cycles (
    cycle_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_type TEXT NOT NULL CHECK (cycle_type IN ('morning', 'evening')),
    cycle_date DATE NOT NULL,
    submission_deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    results_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (cycle_date, cycle_type)
);
COMMENT ON TABLE cycles IS 'Game cycles representing morning (12:00 deadline) and evening (18:00 deadline) action periods';

-- Players table
CREATE TABLE IF NOT EXISTS players (
    player_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    ideology_score INTEGER NOT NULL CHECK (ideology_score >= -5 AND ideology_score <= 5),
    remaining_actions INTEGER NOT NULL DEFAULT 1,
    remaining_quick_actions INTEGER NOT NULL DEFAULT 2,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE players IS 'Registered players of the game';

-- Districts (regions of Novi-Sad)
CREATE TABLE IF NOT EXISTS districts (
    district_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    influence_resource INTEGER NOT NULL DEFAULT 0,
    money_resource INTEGER NOT NULL DEFAULT 0,
    information_resource INTEGER NOT NULL DEFAULT 0,
    force_resource INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE districts IS 'Districts of Novi-Sad that can be controlled by players';

-- Politicians (local and international)
CREATE TABLE IF NOT EXISTS politicians (
    politician_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('local', 'international')),
    description TEXT,
    ideological_leaning INTEGER NOT NULL CHECK (ideological_leaning >= -5 AND ideological_leaning <= 5),
    district_id UUID REFERENCES districts(district_id) ON DELETE SET NULL,
    influence_in_district INTEGER CHECK (influence_in_district >= 0 AND influence_in_district <= 10),
    activity_percentage INTEGER CHECK (activity_percentage >= 0 AND activity_percentage <= 100),
    country TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE politicians IS 'Politicians who have influence in the game, both local and international';

-- Player resources
CREATE TABLE IF NOT EXISTS resources (
    resource_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    influence_amount INTEGER NOT NULL DEFAULT 0 CHECK (influence_amount >= 0),
    money_amount INTEGER NOT NULL DEFAULT 0 CHECK (money_amount >= 0),
    information_amount INTEGER NOT NULL DEFAULT 0 CHECK (information_amount >= 0),
    force_amount INTEGER NOT NULL DEFAULT 0 CHECK (force_amount >= 0),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (player_id)
);
COMMENT ON TABLE resources IS 'Resources owned by players (influence, money, information, force)';

-- Resource history
CREATE TABLE IF NOT EXISTS resource_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES cycles(cycle_id) ON DELETE CASCADE,
    change_type TEXT NOT NULL,
    influence_change INTEGER DEFAULT 0,
    money_change INTEGER DEFAULT 0, 
    information_change INTEGER DEFAULT 0,
    force_change INTEGER DEFAULT 0,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE resource_history IS 'History of resource changes for audit and tracking purposes';

-- District control
CREATE TABLE IF NOT EXISTS district_control (
    control_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    district_id UUID NOT NULL REFERENCES districts(district_id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(player_id) ON DELETE SET NULL,
    control_points INTEGER NOT NULL DEFAULT 0 CHECK (control_points >= 0),
    last_action_cycle_id UUID REFERENCES cycles(cycle_id) ON DELETE SET NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (district_id, player_id)
);
COMMENT ON TABLE district_control IS 'Tracks control points of players in districts';

-- Actions table
CREATE TABLE IF NOT EXISTS actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES cycles(cycle_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN (
        'influence', 'attack', 'defense', 
        'reconnaissance', 'information_spread', 'support',
        'politician_influence', 'politician_reputation_attack', 'politician_displacement',
        'international_negotiations', 'kompromat_search', 'lobbying'
    )),
    is_quick_action BOOLEAN NOT NULL,
    district_id UUID REFERENCES districts(district_id) ON DELETE SET NULL,
    target_player_id UUID REFERENCES players(player_id) ON DELETE SET NULL,
    target_politician_id UUID REFERENCES politicians(politician_id) ON DELETE SET NULL,
    resource_type TEXT CHECK (resource_type IN ('influence', 'money', 'information', 'force')),
    resource_amount INTEGER CHECK (resource_amount > 0),
    physical_presence BOOLEAN DEFAULT FALSE,
    expected_outcome TEXT,
    actual_outcome TEXT,
    outcome_control_points INTEGER,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'cancelled')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE actions IS 'Player actions submitted during game cycles';

-- Collective actions
CREATE TABLE IF NOT EXISTS collective_actions (
    collective_action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    initiator_player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('attack', 'defense')),
    district_id UUID NOT NULL REFERENCES districts(district_id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES cycles(cycle_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'cancelled')),
    total_control_points INTEGER DEFAULT 0,
    target_player_id UUID REFERENCES players(player_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE collective_actions IS 'Collective actions initiated by players for coordinated attacks or defense';

-- Collective action participants
CREATE TABLE IF NOT EXISTS collective_action_participants (
    participant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collective_action_id UUID NOT NULL REFERENCES collective_actions(collective_action_id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('influence', 'money', 'information', 'force')),
    resource_amount INTEGER NOT NULL CHECK (resource_amount > 0),
    physical_presence BOOLEAN DEFAULT FALSE,
    control_points_contributed INTEGER DEFAULT 0,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (collective_action_id, player_id)
);
COMMENT ON TABLE collective_action_participants IS 'Participants in collective actions with their resource contributions';

-- Player-politician relations
CREATE TABLE IF NOT EXISTS player_politician_relations (
    relation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    politician_id UUID NOT NULL REFERENCES politicians(politician_id) ON DELETE CASCADE,
    friendliness_level INTEGER NOT NULL DEFAULT 50 CHECK (friendliness_level >= 0 AND friendliness_level <= 100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (player_id, politician_id)
);
COMMENT ON TABLE player_politician_relations IS 'Friendliness level between players and politicians';

-- News and events
CREATE TABLE IF NOT EXISTS news (
    news_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cycle_id UUID NOT NULL REFERENCES cycles(cycle_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    news_type TEXT NOT NULL CHECK (news_type IN ('public', 'faction', 'fake')),
    target_player_id UUID REFERENCES players(player_id) ON DELETE SET NULL,
    related_district_id UUID REFERENCES districts(district_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES players(player_id) ON DELETE SET NULL
);
COMMENT ON TABLE news IS 'News and events generated during the game';

-- Translations table
CREATE TABLE IF NOT EXISTS translations (
    translation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    translation_key TEXT NOT NULL UNIQUE,
    en_US TEXT NOT NULL,
    ru_RU TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
COMMENT ON TABLE translations IS 'Translations for game text in English and Russian';

-- International effects
CREATE TABLE IF NOT EXISTS international_effects (
    effect_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politician_id UUID NOT NULL REFERENCES politicians(politician_id) ON DELETE CASCADE,
    cycle_id UUID NOT NULL REFERENCES cycles(cycle_id) ON DELETE CASCADE,
    effect_type TEXT NOT NULL CHECK (effect_type IN ('sanctions', 'support', 'attack', 'destabilization', 'diplomacy')),
    target_ideology INTEGER CHECK (target_ideology >= -5 AND target_ideology <= 5),
    target_district_id UUID REFERENCES districts(district_id) ON DELETE SET NULL,
    control_points_effect INTEGER,
    resource_effect_type TEXT CHECK (resource_effect_type IN ('influence', 'money', 'information', 'force')),
    resource_effect_amount INTEGER,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);
COMMENT ON TABLE international_effects IS 'Effects created by international politicians on the game state';
