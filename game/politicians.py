import logging
import sqlite3
from db.game_queries import (
    get_politician_info,
    get_all_politicians,
    get_player_politicians
)
from languages import get_text, format_ideology
from typing import Dict, List, Optional, Any, Tuple
from db.queries import db_connection_pool, db_transaction

logger = logging.getLogger(__name__)


@db_transaction
def get_politician_by_name(name: str, conn: Any) -> Optional[Dict[str, Any]]:
    """Find a politician by name (case-insensitive partial match)."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, d.name as district_name
            FROM politicians p
            LEFT JOIN districts d ON p.district_id = d.district_id
            WHERE p.name LIKE ? 
            ORDER BY p.is_international, p.name
            LIMIT 1
        """, (f"%{name}%",))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        return {
            'id': row[0],
            'name': row[1],
            'role': row[2],
            'ideology_score': row[3],
            'district_id': row[4],
            'influence': row[5],
            'friendliness': row[6],
            'is_international': bool(row[7]),
            'description': row[8],
            'district_name': row[9]
        }
    except Exception as e:
        logger.error(f"Error getting politician by name: {e}")
        return None


@db_transaction
def get_politician_info(politician_id: int, lang: str = 'en') -> Optional[Dict[str, Any]]:
    """Get detailed information about a politician."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.name, p.role, p.ideology_score, p.influence, p.description,
                       d.name as district_name
                FROM politicians p
                LEFT JOIN districts d ON p.district_id = d.district_id
                WHERE p.politician_id = ?
            """, (politician_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'name': row[0],
                'role': row[1],
                'ideology_score': row[2],
                'influence': row[3],
                'description': row[4],
                'district': row[5]
            }
    except Exception as e:
        logger.error(f"Error getting politician info: {e}")
        return None


@db_transaction
def get_all_politicians(international: bool = False) -> List[Dict[str, Any]]:
    """Get a list of all politicians."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            if international:
                cursor.execute("""
                    SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence,
                           d.name as district_name
                    FROM politicians p
                    LEFT JOIN districts d ON p.district_id = d.district_id
                    WHERE p.is_international = 1
                    ORDER BY p.name
                """)
            else:
                cursor.execute("""
                    SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence,
                           d.name as district_name
                    FROM politicians p
                    LEFT JOIN districts d ON p.district_id = d.district_id
                    ORDER BY p.name
                """)
            
            politicians = []
            for row in cursor.fetchall():
                politicians.append({
                    'id': row[0],
                    'name': row[1],
                    'role': row[2],
                    'ideology_score': row[3],
                    'influence': row[4],
                    'district': row[5]
                })
            return politicians
    except Exception as e:
        logger.error(f"Error getting politicians list: {e}")
        return []


def get_politician_relationship(politician_id, player_id):
    """Get the relationship status between a politician and a player."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check if a relationship record exists
        cursor.execute(
            """
            SELECT friendliness, interaction_count, last_interaction
            FROM politician_relationships
            WHERE politician_id = ? AND player_id = ?
            """,
            (politician_id, player_id)
        )
        relationship = cursor.fetchone()

        if relationship:
            friendliness, interaction_count, last_interaction = relationship
            return {
                "politician_id": politician_id,
                "player_id": player_id,
                "friendliness": friendliness,
                "interaction_count": interaction_count,
                "last_interaction": last_interaction
            }
        else:
            # Return default values if no relationship exists
            return {
                "politician_id": politician_id,
                "player_id": player_id,
                "friendliness": 50,  # Default neutral friendliness
                "interaction_count": 0,
                "last_interaction": None
            }
    except Exception as e:
        logger.error(f"Error getting politician relationship: {e}")
        return None
    finally:
        if conn:
            conn.close()


def format_politician_info(politician_id: int, lang: str = 'en') -> str:
    """Format politician information for display."""
    politician = get_politician_info(politician_id, lang)
    if not politician:
        return get_text("politician_not_found", lang, name=politician_id)
    
    lines = [
        f"*{politician['name']}*",
        f"{get_text('role', lang)}: {get_text(politician['role'], lang)}",
        f"{get_text('ideology', lang)}: {politician['ideology_score']}/100",
        f"{get_text('influence', lang)}: {politician['influence']}"
    ]
    
    if politician['district']:
        lines.append(f"{get_text('district', lang)}: {politician['district']}")
    
    if politician['description']:
        lines.extend(["", politician['description']])
    
    return "\n".join(lines)


def get_politician_list(lang: str = 'en', international: bool = False) -> str:
    """Get a formatted list of politicians."""
    politicians = get_all_politicians(international)
    if not politicians:
        return get_text("no_politicians", lang)
    
    lines = [get_text("politician_list_header", lang)]
    for p in politicians:
        lines.append(
            f"*{p['name']}* - {get_text('ideology', lang)}: {p['ideology_score']}, "
            f"{get_text('influence', lang)}: {p['influence']}"
        )
    
    return "\n".join(lines)


def get_player_politician_summary(player_id: int, lang: str = "en") -> str:
    """Get summary of player's relationships with politicians."""
    relationships = get_player_politicians(player_id)
    
    if not relationships:
        return get_text("no_politician_relationships", lang)

    summary = [get_text("politician_relationships", lang)]
    for rel in relationships:
        # Format relationship entry
        entry = [f"• *{rel['name']}*"]
        entry.append(f"  {get_text('friendliness', lang)}: {rel['friendliness']}%")
        if rel['interaction_count'] > 0:
            entry.append(f"  {get_text('interactions', lang)}: {rel['interaction_count']}")
        
        summary.extend(entry)

    return "\n".join(summary)


def get_active_politicians(district_id=None):
    """Get active politicians, optionally filtered by district."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        if district_id:
            cursor.execute(
                """
                SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence, 
                       p.district_id, d.name as district_name 
                FROM politicians p
                LEFT JOIN districts d ON p.district_id = d.district_id
                WHERE p.is_international = 0 AND p.district_id = ?
                ORDER BY p.name
                """,
                (district_id,)
            )
        else:
            cursor.execute(
                """
                SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence, 
                       p.district_id, d.name as district_name 
                FROM politicians p
                LEFT JOIN districts d ON p.district_id = d.district_id
                WHERE p.is_international = 0
                ORDER BY p.name
                """
            )

        politicians = cursor.fetchall()
        conn.close()

        return politicians
    except Exception as e:
        logger.error(f"Error getting active politicians: {e}")
        return []


def get_politician_abilities(politician_id, player_id, lang="en"):
    """Get available abilities for a politician."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get politician's abilities
        cursor.execute(
            """
            SELECT ability_id, name, description, cost, cooldown_cycles
            FROM politician_abilities
            WHERE politician_id = ?
            """,
            (politician_id,)
        )
        abilities = cursor.fetchall()

        # Get last ability usage
        cursor.execute(
            """
            SELECT ability_id, last_used
            FROM ability_usage
            WHERE politician_id = ? AND player_id = ?
            """,
            (politician_id, player_id)
        )
        last_usage = {row[0]: row[1] for row in cursor.fetchall()}

        # Get current cycle
        from game.actions import get_current_cycle
        current_cycle = get_current_cycle()

        result = []
        for ability in abilities:
            ability_id, name, description, cost, cooldown = ability
            cost = eval(cost)  # Convert string representation to dict
            
            # Check if ability is available
            is_available = True
            cycles_remaining = 0
            
            if ability_id in last_usage:
                last_used = last_usage[ability_id]
                cycles_since_use = (current_cycle - last_used) % 2  # Assuming 2 cycles per day
                if cycles_since_use < cooldown:
                    is_available = False
                    cycles_remaining = cooldown - cycles_since_use

            result.append({
                'id': ability_id,
                'name': name,
                'description': description,
                'cost': cost,
                'is_available': is_available,
                'cycles_remaining': cycles_remaining
            })

        conn.close()
        return result

    except Exception as e:
        logger.error(f"Error getting politician abilities: {e}")
        return None


@db_transaction
def get_district_politicians(district_id: int, conn: Any) -> List[Dict[str, Any]]:
    """Get list of politicians in a district."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, d.name as district_name
            FROM politicians p
            LEFT JOIN districts d ON p.district_id = d.district_id
            WHERE p.district_id = ? AND p.is_international = 0
            ORDER BY p.name
        """, (district_id,))
        
        politicians = []
        for row in cursor.fetchall():
            politicians.append({
                'id': row[0],
                'name': row[1],
                'role': row[2],
                'ideology_score': row[3],
                'district_id': row[4],
                'influence': row[5],
                'friendliness': row[6],
                'is_international': bool(row[7]),
                'description': row[8],
                'district_name': row[9]
            })
        return politicians
    except Exception as e:
        logger.error(f"Error getting district politicians: {e}")
        return []


def get_district_politician_summary(district_id: int, lang: str = "en") -> str:
    """Get formatted summary of politicians in a district."""
    with db_connection_pool.get_connection() as conn:
        politicians = get_district_politicians(district_id, conn)
        
        if not politicians:
            return get_text("no_district_politicians", lang)
        
        summary = [get_text("district_politicians", lang)]
        for p in politicians:
            summary.append(
                f"*{p['name']}* - {p['role']}\n"
                f"{get_text('ideology', lang)}: {format_ideology(p['ideology_score'])}, "
                f"{get_text('influence', lang)}: {p['influence']}"
            )
            summary.append("")
        
        return "\n".join(summary).strip()


def format_politicians_list(politicians: List[Dict[str, Any]], lang: str = 'en') -> str:
    """Format a list of politicians with their details."""
    if not politicians:
        return get_text("no_politicians", lang)
    
    lines = [get_text("politician_list_header", lang)]
    for p in politicians:
        ideology = format_ideology(p['ideology_score'], lang)
        lines.extend([
            f"*{p['name']}*",
            f"{get_text('role', lang)}: {get_text(p['role'], lang)}",
            f"{get_text('ideology', lang)}: {ideology}",
            f"{get_text('influence', lang)}: {p['influence']}"
        ])
        
        if p.get('district'):
            lines.append(f"{get_text('district', lang)}: {p['district']}")
        
        lines.append("")  # Add blank line between politicians
    
    return "\n".join(lines).strip()