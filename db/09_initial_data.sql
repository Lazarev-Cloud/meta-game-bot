-- 09_initial_data.sql
-- Initial data required for the game to function

-- Initialize districts (from document)
INSERT INTO game.districts (name, description, influence_resource, money_resource, information_resource, force_resource) VALUES
('Stari Grad', 'Historical and administrative center of Novi-Sad', 2, 0, 2, 0),
('Liman', 'University and scientific center', 2, 0, 2, 0),
('Petrovaradin', 'Cultural heritage and tourism area', 2, 1, 0, 0),
('Podbara', 'Industrial district', 0, 3, 0, 1),
('Detelinara', 'Residential area, working class neighborhood', 2, 2, 0, 0),
('Satelit', 'New district with economic growth', 1, 3, 0, 0),
('Adamovicevo', 'Military objects and security zone', 1, 0, 0, 3),
('Sremska Kamenica', 'Suburb with shadow economy', 0, 0, 1, 3);

-- Initialize local politicians (from document)
INSERT INTO game.politicians (name, type, description, ideological_leaning, district_id, influence_in_district) VALUES
('Nemanja Kovacevic', 'local', 'Head of city administration, loyal to Milosevic regime', 5, 
    (SELECT district_id FROM game.districts WHERE name = 'Stari Grad'), 6),
('Miroslav Vasilevic', 'local', 'Deputy head of administration', 3, 
    (SELECT district_id FROM game.districts WHERE name = 'Stari Grad'), 4),
('Professor Dragan Jovic', 'local', 'University rector, supporter of democratization', -5, 
    (SELECT district_id FROM game.districts WHERE name = 'Liman'), 7),
('Zoran "Zoki" Novakovic', 'local', 'Leader of local criminal group', 2, 
    (SELECT district_id FROM game.districts WHERE name = 'Sremska Kamenica'), 5),
('Jovan Miric', 'local', 'Diplomat with international connections', 3, 
    (SELECT district_id FROM game.districts WHERE name = 'Petrovaradin'), 4),
('Colonel Branko Petrovic', 'local', 'Commander of military garrison', 4, 
    (SELECT district_id FROM game.districts WHERE name = 'Adamovicevo'), 6),
('Goran Radic', 'local', 'Leader of machinery workers union', -2, 
    (SELECT district_id FROM game.districts WHERE name = 'Podbara'), 4),
('Maria Kovac', 'local', 'Leader of student movement "Otpor"', -4, 
    (SELECT district_id FROM game.districts WHERE name = 'Liman'), 5),
('Bishop Irinej', 'local', 'Head of Orthodox Church in Novi-Sad', 1, 
    (SELECT district_id FROM game.districts WHERE name = 'Petrovaradin'), 5);

-- Initialize international politicians (from document)
INSERT INTO game.politicians (name, type, description, ideological_leaning, activity_percentage, country) VALUES
('Bill Clinton', 'international', 'US President, strong supporter of democratic reform', -5, 80, 'USA'),
('Tony Blair', 'international', 'British Prime Minister, proponent of economic reforms', -4, 60, 'United Kingdom'),
('Jacques Chirac', 'international', 'French President, diplomatic approach', -3, 50, 'France'),
('Joschka Fischer', 'international', 'German Foreign Minister, supports democratic activists', -2, 40, 'Germany'),
('Javier Solana', 'international', 'NATO Secretary General, political pressure', -3, 70, 'NATO'),
('Vladimir Zhirinovsky', 'international', 'Russian politician supporting chaos', 4, 50, 'Russia'),
('Yevgeny Primakov', 'international', 'Russian diplomat supporting regime', 2, 60, 'Russia'),
('Slobodan Milosevic', 'international', 'President of Yugoslavia', 5, 90, 'Yugoslavia'),
('Vaclav Havel', 'international', 'Czech President, supports opposition', -5, 40, 'Czech Republic'),
('Madeleine Albright', 'international', 'US Secretary of State, sanctions supporter', -4, 70, 'USA');

-- Initialize translations for English
INSERT INTO game.translations (translation_key, en_US, ru_RU) VALUES
-- Resource names
('resources.influence', 'Influence', 'Влияние'),
('resources.money', 'Money', 'Деньги'),
('resources.information', 'Information', 'Информация'),
('resources.force', 'Force', 'Сила'),

-- Cycle types
('cycle.morning', 'Morning', 'Утро'),
('cycle.evening', 'Evening', 'Вечер'),

-- Action types
('action.influence', 'Influence', 'Влияние'),
('action.attack', 'Attack', 'Атака'),
('action.defense', 'Defense', 'Защита'),
('action.reconnaissance', 'Reconnaissance', 'Разведка'),
('action.information_spread', 'Information Spread', 'Распространение информации'),
('action.support', 'Support', 'Поддержка'),
('action.politician_influence', 'Politician Influence', 'Влияние на политика'),
('action.politician_reputation_attack', 'Reputation Attack', 'Атака на репутацию'),
('action.politician_displacement', 'Politician Displacement', 'Вытеснение политика'),
('action.international_negotiations', 'International Negotiations', 'Международные переговоры'),
('action.kompromat_search', 'Kompromat Search', 'Поиск компромата'),
('action.lobbying', 'Lobbying', 'Лоббирование'),

-- Action status messages
('action.submitted', 'Action Submitted', 'Заявка отправлена'),
('action.cancelled', 'Action Cancelled', 'Заявка отменена'),
('action.confirmation.generic', 'Your action has been submitted successfully', 'Ваша заявка успешно отправлена'),
('action.confirmation.influence', 'Your influence action has been submitted. You will see results at the end of the cycle.', 'Ваша заявка на влияние отправлена. Результаты будут в конце цикла.'),
('action.confirmation.attack', 'Your attack action has been submitted. You will see results at the end of the cycle.', 'Ваша заявка на атаку отправлена. Результаты будут в конце цикла.'),
('action.confirmation.defense', 'Your defense action has been submitted. You will see results at the end of the cycle.', 'Ваша заявка на защиту отправлена. Результаты будут в конце цикла.'),
('action.confirmation.reconnaissance', 'Your reconnaissance action has been submitted. You will receive information soon.', 'Ваша заявка на разведку отправлена. Вы получите информацию в ближайшее время.'),
('action.confirmation.support', 'Your support action has been submitted. You will see results at the end of the cycle.', 'Ваша заявка на поддержку отправлена. Результаты будут в конце цикла.'),

-- Collective actions
('collective_action.initiated', 'Collective action has been initiated', 'Коллективное действие инициировано'),
('collective_action.joined', 'You have joined the collective action', 'Вы присоединились к коллективному действию'),
('collective_action.completed', 'Collective action has been completed', 'Коллективное действие завершено'),

-- Resource exchange
('resource.exchange.success', 'Resource exchange completed successfully', 'Обмен ресурсов успешно завершен'),

-- District descriptions - English
('district.Stari Grad.en.description', 'Historical and administrative center of Novi-Sad. Government buildings and traditional architecture dominate this area.', ''),
('district.Liman.en.description', 'University district with scientific institutions and student life. A hub of intellectual activity and youth culture.', ''),
('district.Petrovaradin.en.description', 'Located across the Danube, known for its fortress and cultural heritage. Major tourist attraction.', ''),
('district.Podbara.en.description', 'Industrial zone with factories and working-class population. Economic backbone of the city.', ''),
('district.Detelinara.en.description', 'Residential area predominantly inhabited by working-class families. A neighborhood of apartment blocks and small businesses.', ''),
('district.Satelit.en.description', 'Newer district with developing economy and modern infrastructure. Symbol of growth and international investment.', ''),
('district.Adamovicevo.en.description', 'Military zone with strategic importance. Houses military personnel and security infrastructure.', ''),
('district.Sremska Kamenica.en.description', 'Suburban area with shadow economy activities. Known for its mix of affluent villas and underground businesses.', ''),

-- District descriptions - Russian
('district.Stari Grad.ru.description', 'Исторический и административный центр Нови-Сада. В этом районе преобладают правительственные здания и традиционная архитектура.', ''),
('district.Liman.ru.description', 'Университетский район с научными учреждениями и студенческой жизнью. Центр интеллектуальной активности и молодежной культуры.', ''),
('district.Petrovaradin.ru.description', 'Расположен на другом берегу Дуная, известен своей крепостью и культурным наследием. Основная туристическая достопримечательность.', ''),
('district.Podbara.ru.description', 'Промышленная зона с фабриками и рабочим населением. Экономический фундамент города.', ''),
('district.Detelinara.ru.description', 'Жилой район, преимущественно населенный семьями рабочего класса. Район многоквартирных домов и малого бизнеса.', ''),
('district.Satelit.ru.description', 'Новый район с развивающейся экономикой и современной инфраструктурой. Символ роста и международных инвестиций.', ''),
('district.Adamovicevo.ru.description', 'Военная зона стратегического значения. Здесь размещаются военные и инфраструктура безопасности.', ''),
('district.Sremska Kamenica.ru.description', 'Пригородный район с теневой экономикой. Известен сочетанием богатых вилл и подпольного бизнеса.', '');

-- Create initial game cycle
DO $$
DECLARE
    current_date DATE := CURRENT_DATE;
    current_time TIME := CURRENT_TIME;
    cycle_type TEXT;
    submission_deadline TIMESTAMP WITH TIME ZONE;
    results_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Determine cycle type based on current time
    IF current_time < '12:00:00' THEN
        cycle_type := 'morning';
        submission_deadline := current_date + TIME '12:00:00';
        results_time := current_date + TIME '13:00:00';
    ELSIF current_time < '18:00:00' THEN
        cycle_type := 'evening';
        submission_deadline := current_date + TIME '18:00:00';
        results_time := current_date + TIME '19:00:00';
    ELSE
        -- If after 18:00, create morning cycle for next day
        cycle_type := 'morning';
        current_date := current_date + 1;
        submission_deadline := current_date + TIME '12:00:00';
        results_time := current_date + TIME '13:00:00';
    END IF;
    
    -- Create cycle
    INSERT INTO game.cycles (
        cycle_type,
        cycle_date,
        submission_deadline,
        results_time,
        is_active
    ) VALUES (
        cycle_type,
        current_date,
        submission_deadline,
        results_time,
        TRUE
    );
END $$;
