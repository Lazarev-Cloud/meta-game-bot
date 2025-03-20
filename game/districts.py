import logging
from db.queries import (
    get_district_info, get_all_districts,
    get_district_control, update_district_control
)
from typing import Dict, List, Optional
from db.game_queries import (
    get_player_districts
)
from languages import get_text

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


def get_district_by_name(name: str) -> Optional[str]:
    """Get district ID by name."""
    districts = get_all_districts()
    for district_id, district_name in districts:
        if district_name.lower() == name.lower():
            return district_id
    return None


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


def format_district_info(district_id: str, lang: str = "en") -> str:
    """Format district information for display."""
    district = get_district_info(district_id)
    if not district:
        return get_text("district_not_found", lang)

    # Format the information
    info = [
        f"*{get_text('district_name', lang)}:* {district['name']}",
        f"*{get_text('district_description', lang)}:* {district['description']}",
        f"*{get_text('district_control', lang)}:* {district['control_points']}%"
    ]

    if district['controller_name']:
        info.append(f"*{get_text('district_controller', lang)}:* {district['controller_name']}")

    # Add resource production info
    resources = []
    if district['influence_resource'] > 0:
        resources.append(f"{district['influence_resource']} {get_text('influence', lang)}")
    if district['resources_resource'] > 0:
        resources.append(f"{district['resources_resource']} {get_text('resources', lang)}")
    if district['information_resource'] > 0:
        resources.append(f"{district['information_resource']} {get_text('information', lang)}")
    if district['force_resource'] > 0:
        resources.append(f"{district['force_resource']} {get_text('force', lang)}")

    if resources:
        info.append(f"*{get_text('district_production', lang)}:* {', '.join(resources)}")

    return "\n".join(info)


def get_player_district_summary(player_id: int, lang: str = "en") -> str:
    """Get summary of player's district control."""
    districts = get_player_districts(player_id)
    
    if not districts:
        return get_text("no_districts_controlled", lang)

    summary = [get_text("districts_controlled", lang)]
    for district in districts:
        summary.append(
            f"• {district['name']}: {district['control_points']}%"
        )

    return "\n".join(summary)