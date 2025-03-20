import logging
from db.queries import (
    get_district_info, get_all_districts,
    get_district_control, update_district_control
)

logger = logging.getLogger(__name__)


async def generate_text_map():
    """Generate a text representation of the game map."""
    districts = get_all_districts()
    map_text = []

    map_text.append("*Current Control Map of Belgrade*\n")

    for district in districts:
        district_id, name, description, *_ = district
        control_data = get_district_control(district_id)

        map_text.append(f"*{name}* - {description}")

        if control_data:
            # Sort by control points (highest first)
            control_data.sort(key=lambda x: x[1], reverse=True)

            for player_id, control_points, player_name in control_data:
                if control_points > 0:
                    # Determine control status
                    if control_points >= 80:
                        control_status = "🔒"
                    elif control_points >= 60:
                        control_status = "✅"
                    elif control_points >= 20:
                        control_status = "⚠️"
                    else:
                        control_status = "❌"

                    map_text.append(f"  {control_status} {player_name}: {control_points} points")
        else:
            map_text.append("  No control established")

        map_text.append("")  # Add empty line between districts

    map_text.append("Legend:")
    map_text.append("🔒 Strong control (80+ points)")
    map_text.append("✅ Controlled (60-79 points)")
    map_text.append("⚠️ Contested (20-59 points)")
    map_text.append("❌ Weak presence (<20 points)")

    return "\n".join(map_text)


def get_district_by_name(name):
    """Get district by name."""
    import sqlite3
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM districts WHERE name LIKE ?", (f"%{name}%",))
    district = cursor.fetchone()
    
    conn.close()
    return district


def get_district_by_id(district_id):
    """Get district by ID."""
    import sqlite3
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT district_id, name, description, influence_resource, resources_resource, information_resource, force_resource FROM districts WHERE district_id = ?", (district_id,))
    district_tuple = cursor.fetchone()
    
    conn.close()
    
    if not district_tuple:
        return None
        
    # Convert tuple to dictionary
    district = {
        "district_id": district_tuple[0],
        "name": district_tuple[1],
        "description": district_tuple[2],
        "influence_resource": district_tuple[3],
        "resources_resource": district_tuple[4],
        "information_resource": district_tuple[5],
        "force_resource": district_tuple[6]
    }
    
    return district


def get_control_status_text(control_points, lang="en"):
    """Get a textual description of control status."""
    from languages import get_text

    if control_points >= 80:
        return get_text("control_strong", lang)
    elif control_points >= 60:
        return get_text("control_full", lang)
    elif control_points >= 20:
        return get_text("control_contested", lang)
    else:
        return get_text("control_weak", lang)


def format_district_info(district_id, lang="en"):
    """Format detailed information about a district."""
    from languages import get_text, get_resource_name

    district = get_district_info(district_id)
    if not district:
        return None

    district_id, name, description, influence_res, resources_res, info_res, force_res = district

    # Get control information
    control_data = get_district_control(district_id)

    # Get politicians in the district
    import sqlite3
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, role, ideology_score, influence FROM politicians WHERE district_id = ?",
        (district_id,)
    )
    politicians = cursor.fetchall()
    conn.close()

    # Start building the response
    district_text = [
        f"*{name}*",
        f"{description}",
        "",
        "*Resources Provided (when controlled):*",
        f"🔵 {get_resource_name('influence', lang)}: {influence_res}",
        f"💰 {get_resource_name('resources', lang)}: {resources_res}",
        f"🔍 {get_resource_name('information', lang)}: {info_res}",
        f"👊 {get_resource_name('force', lang)}: {force_res}",
        ""
    ]

    if politicians:
        district_text.append("*Key Politicians:*")
        for politician in politicians:
            pol_name, role, ideology, influence = politician

            # Format ideology
            from languages import format_ideology
            ideology_desc = format_ideology(ideology, lang)

            district_text.append(f"• {pol_name} - {role}")
            district_text.append(
                f"  {get_text('ideology', lang, default='Ideology')}: {ideology_desc} ({ideology}), {get_text('influence', lang, default='Influence')}: {influence}")

        district_text.append("")

    if control_data:
        district_text.append("*Current Control:*")
        for player_id, control_points, player_name in control_data:
            if control_points > 0:
                # Get control status text
                control_status = get_control_status_text(control_points, lang)
                district_text.append(
                    f"• {player_name}: {control_points} {get_text('control_points', lang, default='points')} - {control_status}")
    else:
        district_text.append(
            f"*{get_text('current_control', lang, default='Current Control')}:* {get_text('map_no_control', lang, default='No one has established control yet.')}")

    return "\n".join(district_text)