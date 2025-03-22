-- 10_sample_data.sql
-- Sample data for testing the game

-- Create test admin user
INSERT INTO game.players (
    telegram_id,
    name,
    ideology_score,
    is_admin,
    remaining_actions,
    remaining_quick_actions
) VALUES (
    'admin123',
    'Game Master',
    0,
    TRUE,
    1,
    2
);

-- Create sample players (different ideologies)
INSERT INTO game.players (
    telegram_id,
    name,
    ideology_score,
    remaining_actions,
    remaining_quick_actions
) VALUES
('user1', 'Reformist Leader', -5, 1, 2),
('user2', 'Conservative General', 5, 1, 2),
('user3', 'Pragmatic Businessman', 2, 1, 2),
('user4', 'Student Activist', -4, 1, 2),
('user5', 'Religious Leader', 3, 1, 2),
('user6', 'Moderate Journalist', -1, 1, 2);

-- Assign resources to players
INSERT INTO game.resources (
    player_id,
    influence_amount,
    money_amount,
    information_amount,
    force_amount
) VALUES
-- Admin
((SELECT player_id FROM game.players WHERE telegram_id = 'admin123'),
 10, 20, 10, 10),
-- Reformist Leader
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 8, 5, 10, 4),
-- Conservative General
((SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 6, 8, 4, 12),
-- Pragmatic Businessman
((SELECT player_id FROM game.players WHERE telegram_id = 'user3'),
 5, 15, 7, 2),
-- Student Activist
((SELECT player_id FROM game.players WHERE telegram_id = 'user4'),
 10, 3, 8, 5),
-- Religious Leader
((SELECT player_id FROM game.players WHERE telegram_id = 'user5'),
 8, 7, 4, 3),
-- Moderate Journalist
((SELECT player_id FROM game.players WHERE telegram_id = 'user6'),
 6, 6, 12, 2);

-- Create initial district control for players
INSERT INTO game.district_control (
    district_id,
    player_id,
    control_points
) VALUES
-- Reformist controls Liman (university district) with strong control
((SELECT district_id FROM game.districts WHERE name = 'Liman'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 78),
 
-- Conservative controls Adamovicevo (military district) with strong control
((SELECT district_id FROM game.districts WHERE name = 'Adamovicevo'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 85),
 
-- Businessman controls Satelit (new economic district) with medium control
((SELECT district_id FROM game.districts WHERE name = 'Satelit'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user3'),
 65),
 
-- Student Activist has some presence in Liman but not controlling
((SELECT district_id FROM game.districts WHERE name = 'Liman'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user4'),
 40),
 
-- Religious Leader controls Petrovaradin (cultural heritage) with medium control
((SELECT district_id FROM game.districts WHERE name = 'Petrovaradin'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user5'),
 68),
 
-- Journalist has some presence in Stari Grad (administrative center)
((SELECT district_id FROM game.districts WHERE name = 'Stari Grad'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user6'),
 35),
 
-- Conservative also has some presence in Stari Grad, competing with Journalist
((SELECT district_id FROM game.districts WHERE name = 'Stari Grad'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 40),
 
-- Criminal control in Sremska Kamenica
((SELECT district_id FROM game.districts WHERE name = 'Sremska Kamenica'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user3'),
 25);

-- Create some player-politician relations
INSERT INTO game.player_politician_relations (
    player_id,
    politician_id,
    friendliness_level
) VALUES
-- Reformist is friendly with Professor Jovic
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Professor Dragan Jovic'),
 85),
 
-- Conservative is friendly with Colonel Petrovic
((SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Colonel Branko Petrovic'),
 90),
 
-- Businessman has connections with Zoki (criminal leader)
((SELECT player_id FROM game.players WHERE telegram_id = 'user3'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Zoran "Zoki" Novakovic'),
 75),
 
-- Student Activist is friendly with Maria Kovac
((SELECT player_id FROM game.players WHERE telegram_id = 'user4'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Maria Kovac'),
 88),
 
-- Religious Leader is friendly with Bishop
((SELECT player_id FROM game.players WHERE telegram_id = 'user5'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Bishop Irinej'),
 92),
 
-- Conservative is hostile to student leader
((SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Maria Kovac'),
 15),
 
-- Reformist is hostile to city administration
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 (SELECT politician_id FROM game.politicians WHERE name = 'Nemanja Kovacevic'),
 20);

-- Create some news items
INSERT INTO game.news (
    cycle_id,
    title,
    content,
    news_type,
    related_district_id
) VALUES
-- Public news
((SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'Tensions Rise in Novi-Sad',
 'Political tensions continue to rise across the city as various factions compete for influence. The university district has seen increased student protests.',
 'public',
 (SELECT district_id FROM game.districts WHERE name = 'Liman')),
 
((SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'Economic Growth in Satelit District',
 'The Satelit district has seen significant economic development with new investments pouring in from various sources.',
 'public',
 (SELECT district_id FROM game.districts WHERE name = 'Satelit')),
 
((SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'International Pressure Increases',
 'Western countries are increasing diplomatic pressure on the Yugoslav government, with potential sanctions looming.',
 'public',
 NULL),
 
-- Faction news for Reformist
((SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'Student Support Growing',
 'Your influence among students is growing stronger. Professor Jovic has indicated his support for your initiatives.',
 'faction',
 (SELECT district_id FROM game.districts WHERE name = 'Liman'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user1')),
 
-- Faction news for Conservative
((SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'Military Support Secured',
 'Colonel Petrovic has pledged his support for maintaining order in the city, strengthening your position in Adamovicevo.',
 'faction',
 (SELECT district_id FROM game.districts WHERE name = 'Adamovicevo'),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user2'));

-- Create some sample actions (already completed)
INSERT INTO game.actions (
    player_id,
    cycle_id,
    action_type,
    is_quick_action,
    district_id,
    resource_type,
    resource_amount,
    physical_presence,
    expected_outcome,
    actual_outcome,
    status,
    processed_at
) VALUES
-- Reformist influence action in Liman
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'influence',
 FALSE,
 (SELECT district_id FROM game.districts WHERE name = 'Liman'),
 'influence',
 2,
 TRUE,
 'Increase control in university district',
 'Success! Control increased by 20 points.',
 'completed',
 NOW() - INTERVAL '1 hour'),
 
-- Conservative defense action in Adamovicevo
((SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'defense',
 FALSE,
 (SELECT district_id FROM game.districts WHERE name = 'Adamovicevo'),
 'force',
 2,
 FALSE,
 'Strengthen defense of military district',
 'Defense successfully established. You can block up to 10 points of damage.',
 'completed',
 NOW() - INTERVAL '1 hour'),
 
-- Businessman reconnaissance action in Stari Grad
((SELECT player_id FROM game.players WHERE telegram_id = 'user3'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'reconnaissance',
 TRUE,
 (SELECT district_id FROM game.districts WHERE name = 'Stari Grad'),
 'information',
 1,
 FALSE,
 'Gather intelligence on Stari Grad district',
 'Reconnaissance successful! You have gathered complete information about the district.',
 'completed',
 NOW() - INTERVAL '1 hour');

-- Create sample collective action
INSERT INTO game.collective_actions (
    initiator_player_id,
    action_type,
    district_id,
    cycle_id,
    status,
    target_player_id
) VALUES
-- Reformist initiates collective attack on Conservative's position in Stari Grad
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 'attack',
 (SELECT district_id FROM game.districts WHERE name = 'Stari Grad'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'active',
 (SELECT player_id FROM game.players WHERE telegram_id = 'user2'));

-- Add participants to collective action
INSERT INTO game.collective_action_participants (
    collective_action_id,
    player_id,
    resource_type,
    resource_amount,
    physical_presence
) VALUES
-- Reformist (initiator)
((SELECT collective_action_id FROM game.collective_actions LIMIT 1),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 'influence',
 2,
 FALSE),
 
-- Student Activist joins
((SELECT collective_action_id FROM game.collective_actions LIMIT 1),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user4'),
 'force',
 1,
 TRUE),
 
-- Journalist joins
((SELECT collective_action_id FROM game.collective_actions LIMIT 1),
 (SELECT player_id FROM game.players WHERE telegram_id = 'user6'),
 'information',
 2,
 FALSE);

-- Create some international effects
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
) VALUES
-- US sanctions (Clinton) targeting conservatives
((SELECT politician_id FROM game.politicians WHERE name = 'Bill Clinton'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'sanctions',
 5,
 NULL,
 -5,
 'money',
 -3,
 'Bill Clinton from USA has imposed economic sanctions affecting regions under conservative control.',
 NOW() + INTERVAL '1 day'),
 
-- Russian support (Primakov) for government forces
((SELECT politician_id FROM game.politicians WHERE name = 'Yevgeny Primakov'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'support',
 5,
 (SELECT district_id FROM game.districts WHERE name = 'Stari Grad'),
 5,
 'influence',
 2,
 'Yevgeny Primakov from Russia has offered diplomatic support to government forces in Stari Grad.',
 NOW() + INTERVAL '1 day');

-- Create resource history for players
INSERT INTO game.resource_history (
    player_id,
    cycle_id,
    change_type,
    influence_change,
    money_change,
    information_change,
    force_change,
    reason
) VALUES
-- Reformist gets district income
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'district_income',
 2,
 0,
 2,
 0,
 'Income from Liman district'),
 
-- Conservative gets district income
((SELECT player_id FROM game.players WHERE telegram_id = 'user2'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'district_income',
 1,
 0,
 0,
 3,
 'Income from Adamovicevo district'),
 
-- Businessman gets district income
((SELECT player_id FROM game.players WHERE telegram_id = 'user3'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'district_income',
 1,
 3,
 0,
 0,
 'Income from Satelit district'),
 
-- Action costs for Reformist
((SELECT player_id FROM game.players WHERE telegram_id = 'user1'),
 (SELECT cycle_id FROM game.cycles WHERE is_active = TRUE),
 'action_deduction',
 -2,
 0,
 0,
 0,
 'Resource used for influence action');
