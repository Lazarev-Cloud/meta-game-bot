# Translations for compatibility messages
COMPATIBILITY_MESSAGES = {
    # English
    "en": {
        "compatibility_good": "Good ideological compatibility",
        "compatibility_moderate": "Moderate ideological differences",
        "compatibility_poor": "Significant ideological differences",
    },
    # Russian
    "ru": {
        "compatibility_good": "Хорошая идеологическая совместимость",
        "compatibility_moderate": "Умеренные идеологические различия",
        "compatibility_poor": "Существенные идеологические различия",
    }
}

def add_news(title, content, is_public=True, target_player_id=None, is_fake=False):
    # Добавляет новость в таблицу news
    pass

def apply_district_bonus(district_id, ideology_range, bonus_percent, duration):
    # Добавляет запись в таблицу district_bonuses
    # Включает: тип бонуса, размер, длительность, идеологические требования
    pass

def calculate_action_success_chance(player_id, district_id, action_type):
    # При расчете шанса успеха проверяются активные бонусы
    pass

def process_international_politician_action(politician_id, name, role, ideology):
    # В функции process_international_politician_action:
    news_title = f"International News: {name} Takes Action"
    news_content = f"{name} ({role}) has pledged support for stability and traditional governance. Districts with reform movements will face challenges."

    # Добавление новости
    add_news(news_title, news_content)

    if ideology > 3:  # Strongly conservative
        # Применяем штрафы к реформистским районам
        cursor.execute(
            """
            UPDATE district_control 
            SET control_points = CASE WHEN control_points > 5 THEN control_points - 5 ELSE control_points END
            WHERE district_id IN (
                SELECT district_id FROM districts 
                JOIN politicians ON districts.district_id = politicians.district_id
                WHERE politicians.ideology_score < -3 AND politicians.is_international = 0
            )
            """
        )

    event_details = {
        "politician_id": politician_id,
        "name": name,
        "role": role,
        "ideology": ideology,
        "effect_type": "conservative_support",
        "effect_description": "Applied pressure against reform districts"
    }
    return event_details
