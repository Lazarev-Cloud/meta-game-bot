from typing import Dict, Optional
from datetime import datetime, timedelta
import sqlite3
from logger import logger

class PoliticianAbility:
    def __init__(self, name: str, description: str, cost: Dict[str, int], 
                 cooldown_days: int, min_friendliness: int):
        self.name = name
        self.description = description
        self.cost = cost
        self.cooldown_days = cooldown_days
        self.min_friendliness = min_friendliness

# Определяем уникальные способности
POLITICIAN_ABILITIES = {
    # Местные политики
    "administrative": PoliticianAbility(
        name="administrative_resource",
        description="ability_administrative_desc",
        cost={"influence": 2},
        cooldown_days=1,
        min_friendliness=60
    ),
    "student_protest": PoliticianAbility(
        name="student_protest",
        description="ability_student_protest_desc",
        cost={"influence": 2, "information": 1},
        cooldown_days=2,
        min_friendliness=60
    ),
    "shadow_conversion": PoliticianAbility(
        name="shadow_conversion",
        description="ability_shadow_conversion_desc",
        cost={"influence": 2},
        cooldown_days=1,
        min_friendliness=60
    ),
    
    # Международные политики
    "diplomatic_immunity": PoliticianAbility(
        name="diplomatic_immunity",
        description="ability_diplomatic_immunity_desc",
        cost={"influence": 2, "information": 1},
        cooldown_days=3,
        min_friendliness=60
    ),
    "media_pressure": PoliticianAbility(
        name="media_pressure",
        description="ability_media_pressure_desc",
        cost={"influence": 2, "information": 2},
        cooldown_days=2,
        min_friendliness=60
    )
}

def get_politician_abilities(politician_id: int, player_id: int) -> List[Dict]:
    """Get available abilities for a politician based on relationship."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Получаем данные о политике и отношениях
        relationship = get_politician_relationship(politician_id, player_id)
        friendliness = relationship.get('friendliness', 0) if relationship else 0
        
        cursor.execute("""
            SELECT ability_type, last_used 
            FROM politician_abilities 
            WHERE politician_id = ? AND player_id = ?
        """, (politician_id, player_id))
        
        cooldowns = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Получаем способности политика
        cursor.execute("SELECT ability_types FROM politicians WHERE politician_id = ?", 
                      (politician_id,))
        ability_types = cursor.fetchone()[0].split(',')
        
        abilities = []
        for ability_type in ability_types:
            if ability_type not in POLITICIAN_ABILITIES:
                continue
                
            ability = POLITICIAN_ABILITIES[ability_type]
            
            # Проверяем доступность способности
            is_available = friendliness >= ability.min_friendliness
            is_free = friendliness >= 80
            
            # Проверяем кулдаун
            last_used = cooldowns.get(ability_type)
            on_cooldown = False
            if last_used:
                cooldown_end = datetime.strptime(last_used, '%Y-%m-%d %H:%M:%S') + \
                             timedelta(days=ability.cooldown_days)
                on_cooldown = datetime.now() < cooldown_end
            
            abilities.append({
                'id': ability_type,
                'name': ability.name,
                'description': ability.description,
                'cost': ability.cost if not is_free else {},
                'cooldown_days': ability.cooldown_days,
                'available': is_available and not on_cooldown
            })
            
        return abilities
        
    except Exception as e:
        logger.error(f"Error getting politician abilities: {e}")
        return [] 