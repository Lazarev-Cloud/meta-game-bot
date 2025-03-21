#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Belgrade Game - Districts Module
Handles district-related functionality
"""

import logging
import random
import sqlite3
import datetime
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

def get_district_by_id(district_id):
    """
    Get district information by its ID.
    
    Args:
        district_id (str): The unique identifier for the district
        
    Returns:
        dict: District information or None if not found
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT district_id, name, description, 
                   influence_resource, resources_resource, information_resource, force_resource
            FROM districts 
            WHERE district_id = ?
            """, 
            (district_id,)
        )
        
        district = cursor.fetchone()
        conn.close()
        
        if not district:
            return None
            
        return {
            'district_id': district[0],
            'name': district[1],
            'description': district[2],
            'resources': {
                'influence': district[3],
                'resources': district[4],
                'information': district[5],
                'force': district[6]
            }
        }
    except Exception as e:
        logger.error(f"Error getting district by ID: {e}")
        return None

def get_district_by_name(district_name):
    """
    Get district information by its name.
    
    Args:
        district_name (str): The name of the district
        
    Returns:
        dict: District information or None if not found
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT district_id, name, description, 
                   influence_resource, resources_resource, information_resource, force_resource
            FROM districts 
            WHERE name = ?
            """, 
            (district_name,)
        )
        
        district = cursor.fetchone()
        conn.close()
        
        if not district:
            return None
            
        return {
            'district_id': district[0],
            'name': district[1],
            'description': district[2],
            'resources': {
                'influence': district[3],
                'resources': district[4],
                'information': district[5],
                'force': district[6]
            }
        }
    except Exception as e:
        logger.error(f"Error getting district by name: {e}")
        return None

def get_all_districts():
    """
    Get all districts in the game.
    
    Returns:
        list: List of district dictionaries
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT district_id, name, description, 
                   influence_resource, resources_resource, information_resource, force_resource
            FROM districts
            """
        )
        
        districts = cursor.fetchall()
        conn.close()
        
        return [
            {
                'district_id': d[0],
                'name': d[1],
                'description': d[2],
                'resources': {
                    'influence': d[3],
                    'resources': d[4],
                    'information': d[5],
                    'force': d[6]
                }
            }
            for d in districts
        ]
    except Exception as e:
        logger.error(f"Error getting all districts: {e}")
        return []

def get_district_controller(district_id):
    """
    Get the player with the most control over a district.
    
    Args:
        district_id (str): The unique identifier for the district
        
    Returns:
        tuple: (player_id, control_points) or None if no controller
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT player_id, control_points
            FROM district_control
            WHERE district_id = ?
            ORDER BY control_points DESC
            LIMIT 1
            """,
            (district_id,)
        )
        
        controller = cursor.fetchone()
        conn.close()
        
        if not controller or controller[1] < 10:  # Require at least 10 control points to be considered controller
            return None
            
        return controller
    except Exception as e:
        logger.error(f"Error getting district controller: {e}")
        return None

def get_players_in_district(district_id):
    """
    Get all players with control in a district.
    
    Args:
        district_id (str): The unique identifier for the district
        
    Returns:
        list: List of (player_id, control_points) tuples
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT player_id, control_points
            FROM district_control
            WHERE district_id = ? AND control_points > 0
            ORDER BY control_points DESC
            """,
            (district_id,)
        )
        
        players = cursor.fetchall()
        conn.close()
        
        return players
    except Exception as e:
        logger.error(f"Error getting players in district: {e}")
        return []

def calculate_district_trend(district_id):
    """
    Calculate the ideological trend of a district based on controlling players.
    
    Args:
        district_id (str): The unique identifier for the district
        
    Returns:
        int: Ideology score (-5 to 5) or 0 if balanced/no strong control
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Get all players with control in this district and their ideology scores
        cursor.execute(
            """
            SELECT p.ideology_score, dc.control_points
            FROM district_control dc
            JOIN players p ON dc.player_id = p.player_id
            WHERE dc.district_id = ? AND dc.control_points > 0
            """,
            (district_id,)
        )
        
        player_data = cursor.fetchall()
        conn.close()
        
        if not player_data:
            return 0
            
        # Calculate weighted average of ideology scores
        total_weight = sum(control for _, control in player_data)
        weighted_sum = sum(ideology * control for ideology, control in player_data)
        
        if total_weight == 0:
            return 0
            
        # Round to nearest integer and limit to -5 to 5 range
        trend = round(weighted_sum / total_weight)
        return max(-5, min(5, trend))
    except Exception as e:
        logger.error(f"Error calculating district trend: {e}")
        return 0

def update_district_resources(district_id, influence=0, resources=0, information=0, force=0):
    """
    Update the resource generation values for a district.
    
    Args:
        district_id (str): The unique identifier for the district
        influence (int): Change to influence resource generation
        resources (int): Change to economic resource generation
        information (int): Change to information resource generation
        force (int): Change to force resource generation
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Get current values
        cursor.execute(
            """
            SELECT influence_resource, resources_resource, information_resource, force_resource
            FROM districts
            WHERE district_id = ?
            """,
            (district_id,)
        )
        
        current = cursor.fetchone()
        if not current:
            conn.close()
            return False
            
        # Calculate new values
        new_influence = max(0, current[0] + influence)
        new_resources = max(0, current[1] + resources)
        new_information = max(0, current[2] + information)
        new_force = max(0, current[3] + force)
        
        # Update the district
        cursor.execute(
            """
            UPDATE districts
            SET influence_resource = ?,
                resources_resource = ?,
                information_resource = ?,
                force_resource = ?
            WHERE district_id = ?
            """,
            (new_influence, new_resources, new_information, new_force, district_id)
        )
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error updating district resources: {e}")
        return False

async def update_district_defenses(context: ContextTypes.DEFAULT_TYPE):
    """
    Scheduled job to update district defenses:
    - Remove expired defenses
    - Adjust defense levels based on district controllers
    
    Args:
        context: The context passed by the job queue
    """
    try:
        logger.info("Updating district defenses...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # 1. Remove expired defenses
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            DELETE FROM district_defense
            WHERE expires_at < ?
            """,
            (now,)
        )
        expired_count = cursor.rowcount
        logger.info(f"Removed {expired_count} expired district defenses")
        
        # 2. Get all districts
        cursor.execute("SELECT district_id FROM districts")
        districts = cursor.fetchall()
        
        for district_id in [d[0] for d in districts]:
            # Check the main controller of the district
            controller = get_district_controller(district_id)
            if not controller:
                continue
                
            player_id, control_points = controller
            
            # Add baseline defense proportional to control level
            defense_bonus = min(10, control_points // 10)
            
            # Set expiry to 24 hours from now
            expires_at = (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()
            
            # Add or update defense bonus
            cursor.execute(
                """
                INSERT OR REPLACE INTO district_defense
                (district_id, player_id, defense_bonus, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (district_id, player_id, defense_bonus, expires_at)
            )
            
            logger.info(f"Updated defense for district {district_id}, controller {player_id}, bonus {defense_bonus}")
        
        conn.commit()
        conn.close()
        logger.info("District defenses update completed")
    except Exception as e:
        logger.error(f"Error updating district defenses: {e}")

def generate_text_map():
    """
    Generate a text-based map showing districts and their controllers.
    
    Returns:
        str: Formatted text representation of the game map
    """
    try:
        districts = get_all_districts()
        
        if not districts:
            return "Map unavailable - no districts found"
        
        # Create the map header
        map_text = "🗺️ NOVI SAD GAME MAP 🗺️\n\n"
        
        # Add each district to the map
        for district in sorted(districts, key=lambda d: d['name']):
            district_id = district['district_id']
            district_name = district['name']
            
            # Get controller info
            controller = get_district_controller(district_id)
            controller_text = "⚪ Neutral"
            
            if controller:
                player_id, control_points = controller
                try:
                    conn = sqlite3.connect('novi_sad_game.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT name, ideology_score FROM players WHERE player_id = ?", (player_id,))
                    player = cursor.fetchone()
                    conn.close()
                    
                    if player:
                        player_name, ideology = player
                        # Choose emoji based on ideology
                        if ideology > 2:
                            icon = "🔵" # Conservative/Right
                        elif ideology < -2:
                            icon = "🔴" # Progressive/Left
                        else:
                            icon = "⚪" # Moderate/Neutral
                        
                        controller_text = f"{icon} {player_name} ({control_points} pts)"
                except Exception as e:
                    logger.error(f"Error getting controller info: {e}")
            
            # Get resources
            resources = district['resources']
            resource_icons = []
            
            if resources['influence'] > 0:
                resource_icons.append(f"🎭{resources['influence']}")
            if resources['resources'] > 0:
                resource_icons.append(f"💰{resources['resources']}")
            if resources['information'] > 0:
                resource_icons.append(f"📰{resources['information']}")
            if resources['force'] > 0:
                resource_icons.append(f"💪{resources['force']}")
                
            resource_text = " ".join(resource_icons)
            
            # Add district to map
            map_text += f"📍 {district_name}: {controller_text}\n   {resource_text}\n"
        
        # Add map footer with legend
        map_text += "\n🔵 Conservative | ⚪ Neutral | 🔴 Progressive"
        
        return map_text
    except Exception as e:
        logger.error(f"Error generating text map: {e}")
        return "Error generating map"

def format_district_info(district_id, lang="en"):
    """Format detailed information about a district."""
    district = get_district_by_id(district_id)
    if not district:
        return None

    # Get control information
    players_in_district = get_players_in_district(district_id)
    
    # Get politicians in the district
    conn = sqlite3.connect('novi_sad_game.db')
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT politician_id, name, role, ideology_score, influence 
        FROM politicians 
        WHERE district_id = ?
        """,
        (district_id,)
    )
    politicians = cursor.fetchall()
    conn.close()

    # Start building the response
    district_text = [
        f"*{district['name']}*",
        f"{district['description']}",
        "",
        "*Resources Provided (when controlled):*",
        f"🔵 Influence: {district['resources']['influence']}",
        f"💰 Resources: {district['resources']['resources']}",
        f"🔍 Information: {district['resources']['information']}",
        f"👊 Force: {district['resources']['force']}",
        ""
    ]

    if politicians:
        district_text.append("*Key Politicians:*")
        for politician in politicians:
            politician_id, name, role, ideology, influence = politician

            # Format ideology
            ideology_desc = get_ideology_description(ideology)

            district_text.append(f"• {name} - {role}")
            district_text.append(
                f"  Ideology: {ideology_desc} ({ideology}), Influence: {influence}")

        district_text.append("")

    if players_in_district:
        district_text.append("*Current Control:*")
        
        # Sort by control points (highest first)
        players_in_district.sort(key=lambda x: x[1], reverse=True)
        
        for player_id, control_points in players_in_district:
            if control_points > 0:
                # Get player name
                conn = sqlite3.connect('novi_sad_game.db')
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM players WHERE player_id = ?", (player_id,))
                player_result = cursor.fetchone()
                conn.close()
                
                player_name = player_result[0] if player_result else f"Player {player_id}"
                
                # Get control status text
                control_status = get_control_status_text(control_points)
                district_text.append(
                    f"• {player_name}: {control_points} points - {control_status}")
    else:
        district_text.append("*Current Control:* No one has established control yet.")

    return "\n".join(district_text)

def get_control_status_text(control_points):
    """Get a textual description of control status."""
    if control_points >= 80:
        return "Strong Control"
    elif control_points >= 60:
        return "Full Control"
    elif control_points >= 20:
        return "Contested Control"
    else:
        return "Weak Presence"

def get_ideology_description(score):
    """Convert ideology score to a text description."""
    if score < -4:
        return "Radical Progressive"
    elif score < -2:
        return "Progressive"
    elif score < 0:
        return "Moderate Progressive"
    elif score == 0:
        return "Centrist"
    elif score <= 2:
        return "Moderate Conservative"
    elif score <= 4:
        return "Conservative"
    else:
        return "Radical Conservative"