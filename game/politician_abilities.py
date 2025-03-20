from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import sqlite3
from logger import logger
from db.queries import db_connection_pool, db_transaction
from languages import get_text

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

@db_transaction
def get_politician_abilities(politician_id: int, conn: Any) -> List[Dict[str, Any]]:
    """Get list of abilities for a politician."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.ability_id, a.name, a.description,
               a.cooldown_hours, a.cost,
               h.used_timestamp as last_used
        FROM politician_abilities a
        LEFT JOIN ability_history h ON a.ability_id = h.ability_id
        WHERE a.politician_id = ?
        ORDER BY a.ability_id
    """, (politician_id,))
    
    abilities = []
    for row in cursor.fetchall():
        ability_id, name, desc, cooldown, cost, last_used = row
        abilities.append({
            'id': ability_id,
            'name': name,
            'description': desc,
            'cooldown_hours': cooldown,
            'cost': cost,
            'last_used': last_used
        })
    return abilities

@db_transaction
def get_ability_info(ability_id: int, conn: Any) -> Optional[Dict[str, Any]]:
    """Get detailed information about an ability."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ability_id, name, description,
               cooldown_hours, cost
        FROM politician_abilities
        WHERE ability_id = ?
    """, (ability_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
        
    ability_id, name, desc, cooldown, cost = row
    return {
        'id': ability_id,
        'name': name,
        'description': desc,
        'cooldown_hours': cooldown,
        'cost': cost
    }

@db_transaction
def use_ability(player_id: int, ability_id: int, conn: Any) -> bool:
    """Use a politician's ability."""
    cursor = conn.cursor()
    
    # Check if ability exists
    ability = get_ability_info(ability_id, conn)
    if not ability:
        return False
    
    # Check cooldown
    cursor.execute("""
        SELECT used_timestamp
        FROM ability_history
        WHERE ability_id = ? AND player_id = ?
    """, (ability_id, player_id))
    
    row = cursor.fetchone()
    if row and row[0]:
        cursor.execute("""
            SELECT datetime('now') <= datetime(?, '+' || ? || ' hours')
            FROM ability_history
            WHERE ability_id = ? AND player_id = ?
        """, (row[0], ability['cooldown_hours'], ability_id, player_id))
        if cursor.fetchone()[0]:
            return False
    
    # Record ability usage
    cursor.execute("""
        INSERT OR REPLACE INTO ability_history
        (ability_id, player_id, used_timestamp)
        VALUES (?, ?, datetime('now'))
    """, (ability_id, player_id))
    
    return True

def format_ability_info(ability_id: int, lang: str = "en") -> str:
    """Format ability information for display."""
    with db_connection_pool.get_connection() as conn:
        ability = get_ability_info(ability_id, conn)
        if not ability:
            return get_text("ability_not_found", lang)

        info = [
            f"*{ability['name']}*",
            f"{ability['description']}",
            f"{get_text('cooldown', lang)}: {ability['cooldown_hours']} {get_text('hours', lang)}",
            f"{get_text('cost', lang)}: {ability['cost']}"
        ]
        return "\n".join(info)

def get_politician_ability_list(politician_id: int, lang: str = "en") -> str:
    """Get formatted list of politician's abilities."""
    with db_connection_pool.get_connection() as conn:
        abilities = get_politician_abilities(politician_id, conn)
        
        if not abilities:
            return get_text("no_abilities", lang)

        ability_list = [get_text("politician_abilities", lang)]
        for ability in abilities:
            ability_list.append(format_ability_info(ability['id'], lang))
            if ability['last_used']:
                ability_list.append(f"{get_text('last_used', lang)}: {ability['last_used']}")
            ability_list.append("")

        return "\n".join(ability_list).strip()

def use_politician_ability(player_id: int, ability_id: int, lang: str = "en") -> str:
    """Use a politician's ability and return the result."""
    try:
        with db_connection_pool.get_connection() as conn:
            if use_ability(player_id, ability_id, conn):
                return get_text("ability_used", lang)
            else:
                return get_text("ability_failed", lang)
    except Exception as e:
        return get_text("ability_error", lang) 