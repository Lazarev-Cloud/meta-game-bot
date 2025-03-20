import logging
import sqlite3
from db.queries import (
    get_politician_info, get_all_politicians,
    update_politician_friendliness
)

logger = logging.getLogger(__name__)


def get_politician_by_name(name):
    """Find a politician by name (case-insensitive partial match)."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM politicians WHERE name LIKE ? ORDER BY is_international, name",
            (f"%{name}%",)
        )
        politicians = cursor.fetchall()
        conn.close()

        return politicians[0] if politicians else None
    except Exception as e:
        logger.error(f"Error finding politician by name: {e}")
        return None


def get_politician_by_id(politician_id):
    """Find a politician by ID."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT politician_id, name, role, ideology_score, district_id, influence, friendliness, is_international, description FROM politicians WHERE politician_id = ?",
            (politician_id,)
        )
        politician_tuple = cursor.fetchone()
        conn.close()

        if not politician_tuple:
            return None
            
        # Convert tuple to dictionary
        politician = {
            "politician_id": politician_tuple[0],
            "name": politician_tuple[1],
            "role": politician_tuple[2],
            "ideology_score": politician_tuple[3],
            "district_id": politician_tuple[4],
            "influence": politician_tuple[5],
            "friendliness": politician_tuple[6],
            "is_international": politician_tuple[7],
            "description": politician_tuple[8]
        }
        
        return politician
    except Exception as e:
        logger.error(f"Error finding politician by ID: {e}")
        return None


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


def format_politician_info(politician_id, player_id, lang="en"):
    """Format detailed information about a politician for display."""
    from languages import get_text, format_ideology

    politician = get_politician_info(politician_id=politician_id)
    if not politician:
        return None

    pol_id, name, role, ideology, district_id, influence, friendliness, is_intl, description = politician

    # Get the player's specific relationship with this politician
    relationship = get_politician_relationship(pol_id, player_id)
    player_friendliness = relationship["friendliness"] if relationship else 50

    # Get player's ideology
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT ideology_score FROM players WHERE player_id = ?", (player_id,))
        player_record = cursor.fetchone()
        player_ideology = player_record[0] if player_record else 0
        conn.close()
    except Exception as e:
        logger.error(f"Error getting player ideology: {e}")
        player_ideology = 0

    # Format ideology
    ideology_desc = format_ideology(ideology, lang)

    # Determine player's ideological compatibility
    ideology_diff = abs(player_ideology - ideology)
    if ideology_diff <= 2:
        compatibility = get_text("compatibility_good", lang)
    elif ideology_diff <= 5:
        compatibility = get_text("compatibility_moderate", lang)
    else:
        compatibility = get_text("compatibility_poor", lang)

    # Get district name if applicable
    district_name = ""
    if district_id:
        try:
            conn = sqlite3.connect('belgrade_game.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM districts WHERE district_id = ?", (district_id,))
            district_record = cursor.fetchone()
            if district_record:
                district_name = district_record[0]
            conn.close()
        except Exception as e:
            logger.error(f"Error getting district name: {e}")

    # Build response
    politician_text = [
        f"*{name}*",
        f"{role}",
        "",
        f"*{get_text('ideology', lang, default='Ideology')}:* {ideology_desc} ({ideology})",
        f"*{get_text('influence', lang, default='Influence')}:* {influence}",
        f"*{get_text('relationship', lang, default='Relationship')}:* {player_friendliness}%",
        f"*{get_text('compatibility', lang, default='Compatibility')}:* {compatibility}"
    ]

    if district_name:
        politician_text.append(f"*{get_text('district', lang, default='District')}:* {district_name}")

    if description:
        politician_text.append("")
        politician_text.append(f"{description}")

    return "\n".join(politician_text)


def format_politicians_list(is_international=False, lang="en"):
    """Format a list of politicians for display."""
    from languages import get_text, format_ideology

    politicians = get_all_politicians(is_international=is_international)

    if not politicians:
        return get_text("no_politicians" if not is_international else "no_international", lang)

    title = get_text("politicians_title" if not is_international else "international_title", lang)

    politicians_text = [f"*{title}*\n"]

    for politician in politicians:
        pol_id, name, role, ideology, district_id, influence, friendliness, _, _ = politician

        # Format ideology
        ideology_desc = format_ideology(ideology, lang)

        politicians_text.append(f"• *{name}* - {role}")
        politicians_text.append(f"  {get_text('ideology', lang, default='Ideology')}: {ideology_desc} ({ideology})")

    if is_international:
        politicians_text.append("\n" + get_text("international_note", lang))

    return "\n".join(politicians_text)


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