import sqlite3
from log import logger

def calculate_resource_amount(control_points: int, base_amount: int) -> int:
    """Calculate resource amount based on control points."""
    if control_points >= 75:  # Absolute control
        return int(base_amount * 1.2)  # 120%
    elif control_points >= 50:  # Strong control
        return base_amount  # 100%
    elif control_points >= 35:  # Firm control
        return int(base_amount * 0.8)  # 80%
    elif control_points >= 20:  # Contested control
        return int(base_amount * 0.6)  # 60%
    else:  # Weak control
        return int(base_amount * 0.4)  # 40%

def distribute_district_resources():
    """Distribute resources to players based on their district control."""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        player_gains = {}
        
        cursor.execute("""
            SELECT 
                d.district_id,
                d.name,
                d.resource_type,
                d.resource_amount,
                dc.player_id,
                dc.control_points
            FROM districts d
            LEFT JOIN district_control dc ON d.district_id = dc.district_id
            WHERE dc.player_id IS NOT NULL  -- Only districts with controlling players
        """)
        
        districts = cursor.fetchall()
        
        for district in districts:
            district_id, district_name, resource_type, base_amount, player_id, control = district
            
            # Calculate resource amount
            amount = calculate_resource_amount(control, base_amount)
            
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
            
            # Update player resources
            update_player_resources(player_id, resource_type, amount)
            
            # Track gains for this player
            if player_id not in player_gains:
                player_gains[player_id] = []
            
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

def update_player_resources(player_id: int, resource_type: str, amount: int):
    # Implementation of update_player_resources function
    pass

# Example usage
distribute_district_resources() 