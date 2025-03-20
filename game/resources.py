import sqlite3
import logging
import math
from typing import Dict, List, Optional, Any
from db.queries import db_connection_pool, db_transaction
from languages import get_text
from datetime import datetime

logger = logging.getLogger(__name__)

def calculate_resource_amount(control_points: int, base_amount: int) -> int:
    """Calculate resource amount based on control points."""
    if control_points >= 75:  # Absolute control
        return math.ceil(base_amount * 1.2)  # 120%
    elif control_points >= 50:  # Strong control
        return base_amount  # 100%
    elif control_points >= 35:  # Firm control
        return math.ceil(base_amount * 0.8)  # 80%
    elif control_points >= 20:  # Contested control
        return math.ceil(base_amount * 0.6)  # 60%
    else:  # Weak control
        return math.ceil(base_amount * 0.4)  # 40%

@db_transaction
def distribute_district_resources(conn: Any):
    """Distribute resources to players based on their district control."""
    try:
        cursor = conn.cursor()
        
        player_gains = {}
        
        # Get all districts with their resource production and control info
        cursor.execute("""
            SELECT 
                d.district_id,
                d.name,
                d.influence_resource,
                d.resources_resource,
                d.information_resource,
                d.force_resource,
                dc.player_id,
                dc.control_points
            FROM districts d
            LEFT JOIN district_control dc ON d.district_id = dc.district_id
            WHERE dc.player_id IS NOT NULL  -- Only districts with controlling players
            AND dc.control_points >= 25  -- Only players with sufficient control
        """)
        
        districts = cursor.fetchall()
        
        for district in districts:
            district_id, district_name, influence, resources, information, force, player_id, control = district
            
            # Process each resource type if it has a non-zero value
            resource_types = {
                'influence': influence,
                'resources': resources,
                'information': information,
                'force': force
            }
            
            # Determine control type for message
            if control >= 75:
                control_type = "absolute"
            elif control >= 50:
                control_type = "strong"
            elif control >= 35:
                control_type = "firm"
            elif control >= 20:
                control_type = "contested"
            else:
                control_type = "weak"
            
            # Initialize player's gains tracking if not exists
            if player_id not in player_gains:
                player_gains[player_id] = []
            
            # Process each resource type
            for resource_type, base_amount in resource_types.items():
                if base_amount > 0:  # Only process if there's any resource to distribute
                    # Calculate actual amount based on control
                    amount = calculate_resource_amount(control, base_amount)
                    
                    # Update player resources
                    update_player_resources(player_id, resource_type, amount)
                    
                    # Track this gain
                    player_gains[player_id].append({
                        'district': district_name,
                        'resource_type': resource_type,
                        'amount': amount,
                        'base_amount': base_amount,
                        'control_type': control_type,
                        'control_points': control
                    })
                    
                    logger.info(f"Distributed {amount} {resource_type} to player {player_id} from district {district_id} (control: {control})")
    except Exception as e:
        logger.error(f"Error distributing district resources: {e}")

@db_transaction
def get_player_resources(player_id: int) -> Dict[str, int]:
    """Get all resources for a player."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT resource_type, amount
                FROM player_resources
                WHERE player_id = ?
            """, (player_id,))
            
            resources = {}
            for row in cursor.fetchall():
                resources[row[0]] = row[1]
            return resources
    except Exception as e:
        logger.error(f"Error getting player resources: {e}")
        return {}

@db_transaction
def update_player_resources(player_id: int, resource_type: str, amount: int) -> bool:
    """Update a player's resources."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE player_resources
                SET amount = amount + ?
                WHERE player_id = ? AND resource_type = ?
            """, (amount, player_id, resource_type))
            return True
    except Exception as e:
        logger.error(f"Error updating player resources: {e}")
        return False

@db_transaction
def get_district_resources(district_id: int) -> Dict[str, int]:
    """Get resource production rates for a district."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT resource_type, production_rate
                FROM district_resources
                WHERE district_id = ?
            """, (district_id,))
            
            resources = {}
            for row in cursor.fetchall():
                resources[row[0]] = row[1]
            return resources
    except Exception as e:
        logger.error(f"Error getting district resources: {e}")
        return {}

@db_transaction
def update_base_resources_for_all():
    """Update base resources for all players at the start of each cycle."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT player_id FROM players")
            players = cursor.fetchall()
            
            for player in players:
                update_base_resources(player[0])
    except Exception as e:
        logger.error(f"Error updating base resources: {e}")

def format_resource_info(resources: Dict[str, int], lang: str = 'en') -> str:
    """Format resource information for display."""
    if not resources:
        return get_text("no_resources", lang)
    
    lines = []
    for resource_type, amount in sorted(resources.items()):
        lines.append(f"{get_text(resource_type, lang)}: {amount}")
    
    return "\n".join(lines)

def get_player_resource_summary(player_id: int, lang: str = 'en') -> str:
    """Get a formatted summary of a player's resources."""
    resources = get_player_resources(player_id)
    if not resources:
        return get_text("no_resources", lang)
    
    return format_resource_info(resources, lang)

def get_district_resource_summary(district_id: int, lang: str = 'en') -> str:
    """Get a formatted summary of a district's resource production."""
    resources = get_district_resources(district_id)
    if not resources:
        return get_text("no_district_resources", lang)
    
    lines = [get_text("district_resources_header", lang)]
    for resource_type, rate in sorted(resources.items()):
        lines.append(f"{get_text(resource_type, lang)}: {rate}/hour")
    
    return "\n".join(lines)

def update_resources(player_id: int, resources: Dict[str, int], lang: str = "en") -> str:
    """Update player's resources and return a summary of changes."""
    try:
        with db_connection_pool.get_connection() as conn:
            update_player_resources(player_id, resources, conn)
        return get_text("resources_updated", lang)
    except Exception as e:
        return get_text("resources_update_failed", lang)

# Example usage
distribute_district_resources() 