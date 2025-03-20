#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Politician utilities for Belgrade Game Bot
Extends the base politicians.py functionality with additional utilities
"""

import logging
import sqlite3
import random
import json
from typing import Dict, List, Tuple, Optional, Any
from languages import format_ideology, get_text
from db.queries import db_connection_pool, db_transaction
logger = logging.getLogger(__name__)


def calculate_ideology_compatibility(player_ideology: int, politician_ideology: int) -> float:
    """
    Calculate compatibility score between player and politician ideologies

    Args:
        player_ideology: Player's ideology score (-5 to +5)
        politician_ideology: Politician's ideology score (-5 to +5)

    Returns:
        float: Compatibility score from 0.0 (incompatible) to 1.0 (perfect match)
    """
    # Calculate absolute difference (0-10 range)
    difference = abs(player_ideology - politician_ideology)

    # Convert to compatibility score (0.0-1.0)
    # 0 difference -> 1.0 score
    # 10 difference -> 0.0 score
    return max(0.0, 1.0 - (difference / 10.0))


def get_politician_action_options(politician_id: int, player_id: int, lang="en") -> List[Dict[str, Any]]:
    """
    Get available actions a player can take with a politician based on relationship

    Args:
        politician_id: Politician ID
        player_id: Player ID
        lang: Language code

    Returns:
        List[Dict]: List of possible actions
    """
    try:
        # Get relationship data
        relationship = get_politician_relationship(politician_id, player_id)
        friendliness = relationship.get('friendliness', 50) if relationship else 50

        # Get politician data
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, is_international FROM politicians WHERE politician_id = ?", (politician_id,))
        politician_data = cursor.fetchone()

        if not politician_data:
            conn.close()
            return []

        name, is_international = politician_data
        conn.close()

        # Base actions always available
        actions = [
            {
                'id': 'info',
                'name': get_text('action_pol_info', lang, default='Gather Information'),
                'description': get_text('action_pol_info_desc', lang, default='Learn more about this politician'),
                'cost': {'information': 1},
                'action_type': 'quick'
            },
            {
                'id': 'influence',
                'name': get_text('action_pol_influence', lang, default='Influence'),
                'description': get_text('action_pol_influence_desc', lang, default='Try to improve your relationship'),
                'cost': {'influence': 2},
                'action_type': 'main'
            }
        ]

        # Add actions based on friendliness level
        if friendliness >= 30:
            # Medium friendliness allows for some collaboration
            actions.append({
                'id': 'collaborate',
                'name': get_text('action_pol_collaborate', lang, default='Collaborate'),
                'description': get_text('action_pol_collaborate_desc', lang,
                                        default='Work together on a political initiative'),
                'cost': {'influence': 1, 'resources': 1},
                'action_type': 'main'
            })

        if friendliness >= 60:
            # High friendliness allows for requesting resources
            actions.append({
                'id': 'request_resources',
                'name': get_text('action_pol_request', lang, default='Request Resources'),
                'description': get_text('action_pol_request_desc', lang,
                                        default='Ask for political support and resources'),
                'cost': {'influence': 2},
                'action_type': 'main'
            })

        if friendliness >= 80:
            # Very high friendliness allows for using their influence
            actions.append({
                'id': 'use_influence',
                'name': get_text('action_pol_power', lang, default='Use Political Power'),
                'description': get_text('action_pol_power_desc', lang,
                                        default='Use their political influence to pressure others'),
                'cost': {'influence': 3},
                'action_type': 'main'
            })

        # Add actions that can be used against the politician
        if friendliness <= 70:
            # Lower friendliness allows for undermining
            actions.append({
                'id': 'undermine',
                'name': get_text('action_pol_undermine', lang, default='Undermine'),
                'description': get_text('action_pol_undermine_desc', lang, default='Weaken their influence'),
                'cost': {'information': 2},
                'action_type': 'main'
            })

        if friendliness <= 40:
            # Low friendliness allows for spreading rumors
            actions.append({
                'id': 'rumors',
                'name': get_text('action_pol_rumors', lang, default='Spread Rumors'),
                'description': get_text('action_pol_rumors_desc', lang, default='Damage their public reputation'),
                'cost': {'information': 1, 'influence': 1},
                'action_type': 'quick'
            })

        if friendliness <= 20:
            # Very low friendliness allows for direct attacks
            actions.append({
                'id': 'scandal',
                'name': get_text('action_pol_scandal', lang, default='Create Scandal'),
                'description': get_text('action_pol_scandal_desc', lang,
                                        default='Expose them in a major political scandal'),
                'cost': {'information': 3, 'influence': 2},
                'action_type': 'main'
            })

        # International politicians have different action options
        if is_international:
            # Replace some actions with international-specific ones
            actions = [a for a in actions if a['id'] not in ['undermine', 'scandal']]

            # Add diplomatic channel action
            if friendliness >= 50:
                actions.append({
                    'id': 'diplomatic',
                    'name': get_text('action_pol_diplomatic', lang, default='Diplomatic Channel'),
                    'description': get_text('action_pol_diplomatic_desc', lang,
                                            default='Establish a diplomatic connection'),
                    'cost': {'influence': 2, 'information': 1},
                    'action_type': 'main'
                })

            # Add international pressure action
            if friendliness >= 70:
                actions.append({
                    'id': 'pressure',
                    'name': get_text('action_pol_pressure', lang, default='International Pressure'),
                    'description': get_text('action_pol_pressure_desc', lang,
                                            default='Use international pressure against your opponents'),
                    'cost': {'influence': 3, 'information': 1},
                    'action_type': 'main'
                })

        return actions

    except Exception as e:
        logger.error(f"Error getting politician action options: {e}")
        return []


def get_politician_relationship(politician_id: int, player_id: int) -> Dict[str, Any]:
    """
    Get the relationship status between a politician and a player

    Args:
        politician_id: Politician ID
        player_id: Player ID

    Returns:
        Dict: Relationship data
    """
    conn = None
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
        return {
            "politician_id": politician_id,
            "player_id": player_id,
            "friendliness": 50,
            "interaction_count": 0,
            "last_interaction": None
        }
    finally:
        if conn:
            conn.close()


def process_international_politicians(cycle_name: str = None):
    """Unified function for processing international politician actions"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Get active politicians
        cursor.execute("""
            SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence, 
                   p.description, p.is_international
            FROM politicians p
            WHERE p.is_international = 1
        """)
        politicians = cursor.fetchall()
        
        activated_events = []
        for pol_id, name, role, ideology_score, influence, description, is_international in politicians:
            event = process_international_action(pol_id, name, role, ideology_score, influence, description, is_international)
            if event:
                activated_events.append(event)
                
        conn.close()
        return activated_events
        
    except Exception as e:
        logger.error(f"Error processing international politicians: {e}")
        return []


def process_international_action(pol_id: int, name: str, role: str, ideology: int, influence: int, description: str, is_international: bool) -> Dict[str, Any]:
    """
    Process an action by an international politician

    Args:
        pol_id: Politician ID
        name: Politician name
        role: Politician role
        ideology: Politician ideology score
        influence: Politician influence
        description: Politician description
        is_international: Whether the politician is international

    Returns:
        Dict: Action effect details
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        result = {
            "type": "diplomatic",
            "affected_districts": [],
            "affected_politicians": [],
            "news_title": f"{name} ({role})",
            "news_content": ""
        }

        if is_international:
            # Diplomatic initiative: affect relationships between players and politicians
            result["news_title"] = f"{name} Diplomatic Initiative"
            result[
                "news_content"] = f"{name} ({role}) has applied diplomatic pressure for peaceful resolution of tensions in Yugoslavia."

            # Random diplomatic effect
            effect_type = random.choice(['moderate_shift', 'improve_relations', 'worsen_relations'])

            if effect_type == 'moderate_shift':
                # Moderate politicians shift slightly toward the center
                cursor.execute(
                    """
                    UPDATE politicians
                    SET ideology_score = CASE 
                        WHEN ideology_score > 0 THEN ideology_score - 1
                        WHEN ideology_score < 0 THEN ideology_score + 1
                        ELSE ideology_score
                    END
                    WHERE ABS(ideology_score) <= 3 AND is_international = 0
                    """
                )
                result["news_content"] += " This has encouraged moderate politicians to take more centrist positions."

            elif effect_type == 'improve_relations':
                # Improve relations with a random local politician
                cursor.execute(
                    """
                    SELECT politician_id, name
                    FROM politicians
                    WHERE is_international = 0
                    ORDER BY RANDOM()
                    LIMIT 1
                    """
                )
                target_pol = cursor.fetchone()

                if target_pol:
                    target_id, target_name = target_pol
                    # Improve all player relationships with this politician
                    cursor.execute(
                        """
                        UPDATE politician_relationships
                        SET friendliness = CASE 
                            WHEN friendliness <= 95 THEN friendliness + 5
                            ELSE 100
                        END
                        WHERE politician_id = ?
                        """,
                        (target_id,)
                    )
                    result[
                        "news_content"] += f" {target_name} is now more open to cooperation with all political actors."
                    result["affected_politicians"].append({"id": target_id, "name": target_name, "effect": +5})

            elif effect_type == 'worsen_relations':
                # Worsen relations with a random local politician
                cursor.execute(
                    """
                    SELECT politician_id, name
                    FROM politicians
                    WHERE is_international = 0 AND ideology_score * ? < 0
                    ORDER BY RANDOM()
                    LIMIT 1
                    """,
                    (ideology,)
                )
                target_pol = cursor.fetchone()

                if target_pol:
                    target_id, target_name = target_pol
                    # Worsen all player relationships with this politician
                    cursor.execute(
                        """
                        UPDATE politician_relationships
                        SET friendliness = CASE 
                            WHEN friendliness >= 5 THEN friendliness - 5
                            ELSE 0
                        END
                        WHERE politician_id = ?
                        """,
                        (target_id,)
                    )
                    result[
                        "news_content"] += f" {target_name} has become more difficult to work with due to international pressure."
                    result["affected_politicians"].append({"id": target_id, "name": target_name, "effect": -5})

        # Commit changes and close connection
        conn.commit()
        conn.close()

        return result

    except Exception as e:
        logger.error(f"Error processing international action: {e}")
        # Try to close the connection if it's still open
        try:
            if conn:
                conn.close()
        except:
            pass

        return {
            "type": "diplomatic",
            "affected_districts": [],
            "affected_politicians": [],
            "news_title": f"{name} ({role})",
            "news_content": f"International event by {name} ({role})"
        }


def generate_politician_influence_report(lang="en"):
    """
    Generate a report on politician influence across districts

    Args:
        lang: Language code

    Returns:
        str: Formatted politician influence report
    """

    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get all local politicians with their details
        cursor.execute(
            """
            SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence, d.name as district_name
            FROM politicians p
            LEFT JOIN districts d ON p.district_id = d.district_id
            WHERE p.is_international = 0
            ORDER BY p.influence DESC
            """
        )
        politicians = cursor.fetchall()

        # Build report
        report_lines = [f"*{get_text('politician_influence_title', lang, default='Politician Influence Report')}*\n"]

        for politician in politicians:
            pol_id, name, role, ideology_score, influence, district_name = politician

            # Format ideology description
            ideology = format_ideology(ideology_score, lang)

            # Format influence tier
            if influence >= 6:
                influence_tier = f"🔵🔵🔵 {get_text('high_influence', lang, default='High influence')}"
            elif influence >= 4:
                influence_tier = f"🔵🔵 {get_text('medium_influence', lang, default='Medium influence')}"
            else:
                influence_tier = f"🔵 {get_text('low_influence', lang, default='Low influence')}"

            district_text = f" ({district_name})" if district_name else ""

            report_lines.append(f"*{name}* - {role}{district_text}")
            report_lines.append(f"  {ideology} ({ideology_score}), {influence_tier}")

        # Add section for international politicians
        report_lines.append(f"\n*{get_text('international_politicians', lang, default='International Politicians')}*\n")

        cursor.execute(
            """
            SELECT p.politician_id, p.name, p.role, p.ideology_score, p.influence, 
                   p.description, p.is_international
            FROM politicians p
            WHERE p.is_international = 1
            ORDER BY p.name
            """
        )
        international_politicians = cursor.fetchall()

        for pol_id, name, role, ideology_score, influence, description, is_international in international_politicians:
            # Format ideology description
            ideology = format_ideology(ideology_score, lang)

            report_lines.append(f"*{name}* - {role}")
            report_lines.append(f"  {ideology} ({ideology_score})")

        conn.close()
        return "\n".join(report_lines)

    except Exception as e:
        logger.error(f"Error generating politician influence report: {e}")
        return get_text('error_generating_report', lang, default="Error generating politician influence report.")


def generate_international_initiative():
    """Generate random initiative from international politicians"""
    initiatives = [
        {
            'type': 'diplomatic_mission',
            'title': 'Дипломатическая миссия',
            'description': 'Международный политик предлагает посредничество в переговорах',
            'cost': {'influence': 1},
            'reward': {'information': 2}
        },
        {
            'type': 'economic_support',
            'title': 'Экономическая поддержка',
            'description': 'Предложение экономической помощи в обмен на политическое влияние',
            'cost': {'influence': 2},
            'reward': {'resources': 3}
        },
        {
            'type': 'international_pressure',
            'title': 'Международное давление',
            'description': 'Возможность использовать международное влияние против оппонентов',
            'cost': {'information': 2},
            'reward': {'force': 2}
        }
    ]
    
    return random.choice(initiatives)

def process_daily_international_events():
    """Process daily random events from international politicians"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Get international politicians
        cursor.execute("""
            SELECT politician_id, name, role 
            FROM politicians 
            WHERE is_international = 1
        """)
        international_pols = cursor.fetchall()
        
        # Generate random initiatives
        for pol_id, name, role in international_pols:
            if random.random() < 0.3:  # 30% шанс на инициативу
                initiative = generate_international_initiative()
                
                # Add to available initiatives
                cursor.execute("""
                    INSERT INTO international_initiatives 
                    (politician_id, type, title, description, cost, reward, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    pol_id,
                    initiative['type'],
                    initiative['title'],
                    initiative['description'],
                    json.dumps(initiative['cost']),
                    json.dumps(initiative['reward'])
                ))
                
                # Add news about initiative
                add_news(
                    title=f"Инициатива от {name}",
                    content=f"{name} ({role}) предлагает: {initiative['description']}",
                    type="international",
                    importance=1
                )
                
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error processing international events: {e}")

def get_politician_abilities(politician_id: int, player_id: int, lang="en") -> List[Dict[str, Any]]:
    """
    Get available abilities for a politician based on player's relationship

    Args:
        politician_id: Politician ID
        player_id: Player ID
        lang: Language code

    Returns:
        List[Dict]: List of available abilities
    """
    from languages import get_text
    import json

    try:
        # Get relationship data
        relationship = get_politician_relationship(politician_id, player_id)
        friendliness = relationship.get('friendliness', 50) if relationship else 50

        # Get current cycle
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT current_cycle FROM game_state")
        current_cycle = cursor.fetchone()[0]

        # Get abilities
        cursor.execute(
            """
            SELECT a.ability_id, a.name, a.description, a.cooldown, a.cost, 
                   a.effect_type, a.effect_value, a.required_friendliness,
                   u.last_used_cycle
            FROM politician_abilities a
            LEFT JOIN politician_ability_usage u 
                ON a.ability_id = u.ability_id 
                AND u.politician_id = a.politician_id 
                AND u.player_id = ?
            WHERE a.politician_id = ?
            """,
            (player_id, politician_id)
        )
        abilities = cursor.fetchall()
        conn.close()

        available_abilities = []
        for ability in abilities:
            ability_id, name, description, cooldown, cost_json, effect_type, effect_value, required_friendliness, last_used = ability
            
            # Check if ability is available based on friendliness
            if friendliness < required_friendliness:
                continue

            # Check cooldown
            is_available = True
            if last_used is not None:
                cycles_since_use = current_cycle - last_used
                if cycles_since_use < cooldown:
                    is_available = False

            # Parse cost and effect
            cost = json.loads(cost_json)
            effect = json.loads(effect_value)

            available_abilities.append({
                'id': ability_id,
                'name': name,
                'description': description,
                'cost': cost,
                'effect_type': effect_type,
                'effect': effect,
                'cooldown': cooldown,
                'is_available': is_available,
                'cycles_remaining': max(0, cooldown - (current_cycle - last_used)) if last_used is not None else 0
            })

        return available_abilities

    except Exception as e:
        logger.error(f"Error getting politician abilities: {e}")
        return []

def use_politician_ability(politician_id: int, player_id: int, ability_id: int) -> Tuple[bool, str]:
    """
    Use a politician's ability

    Args:
        politician_id: Politician ID
        player_id: Player ID
        ability_id: Ability ID

    Returns:
        Tuple[bool, str]: (Success, Message)
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get current cycle
        cursor.execute("SELECT current_cycle FROM game_state")
        current_cycle = cursor.fetchone()[0]

        # Get ability details
        cursor.execute(
            """
            SELECT a.cost, a.effect_type, a.effect_value, a.required_friendliness,
                   u.last_used_cycle
            FROM politician_abilities a
            LEFT JOIN politician_ability_usage u 
                ON a.ability_id = u.ability_id 
                AND u.politician_id = a.politician_id 
                AND u.player_id = ?
            WHERE a.ability_id = ? AND a.politician_id = ?
            """,
            (player_id, ability_id, politician_id)
        )
        ability = cursor.fetchone()

        if not ability:
            conn.close()
            return False, "Ability not found"

        cost_json, effect_type, effect_value, required_friendliness, last_used = ability
        cost = json.loads(cost_json)
        effect = json.loads(effect_value)

        # Check friendliness
        relationship = get_politician_relationship(politician_id, player_id)
        friendliness = relationship.get('friendliness', 50) if relationship else 50
        if friendliness < required_friendliness:
            conn.close()
            return False, "Insufficient friendliness"

        # Check cooldown
        if last_used is not None:
            cycles_since_use = current_cycle - last_used
            if cycles_since_use < cooldown:
                conn.close()
                return False, f"Ability on cooldown for {cooldown - cycles_since_use} more cycles"

        # Check resources
        for resource, amount in cost.items():
            cursor.execute(
                "SELECT amount FROM resources WHERE player_id = ? AND resource_type = ?",
                (player_id, resource)
            )
            result = cursor.fetchone()
            if not result or result[0] < amount:
                conn.close()
                return False, f"Insufficient {resource}"

        # Deduct resources
        for resource, amount in cost.items():
            cursor.execute(
                """
                UPDATE resources 
                SET amount = amount - ? 
                WHERE player_id = ? AND resource_type = ?
                """,
                (amount, player_id, resource)
            )

        # Record usage
        cursor.execute(
            """
            INSERT INTO politician_ability_usage (politician_id, player_id, ability_id, last_used_cycle)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(politician_id, player_id, ability_id) 
            DO UPDATE SET last_used_cycle = ?
            """,
            (politician_id, player_id, ability_id, current_cycle, current_cycle)
        )

        # Apply effect based on type
        success = True
        message = "Ability used successfully"
        
        if effect_type == "block_action":
            # Block an action in a district
            district_id = effect.get('district_id')
            cursor.execute(
                """
                INSERT INTO blocked_actions (district_id, player_id, cycle)
                VALUES (?, ?, ?)
                """,
                (district_id, player_id, current_cycle)
            )
            message = f"Action blocked in district {district_id}"
            
        elif effect_type == "attack_bonus":
            # Add attack bonus to a district
            district_id = effect.get('district_id')
            bonus = effect.get('bonus', 0)
            cursor.execute(
                """
                INSERT INTO district_bonuses (district_id, player_id, bonus_type, amount, cycle)
                VALUES (?, ?, 'attack', ?, ?)
                """,
                (district_id, player_id, bonus, current_cycle)
            )
            message = f"Added {bonus} attack bonus to district {district_id}"
            
        elif effect_type == "resource_conversion":
            # Convert resources
            for resource, amount in effect.items():
                cursor.execute(
                    """
                    UPDATE resources 
                    SET amount = amount + ? 
                    WHERE player_id = ? AND resource_type = ?
                    """,
                    (amount, player_id, resource)
                )
            message = "Resources converted successfully"
            
        elif effect_type == "reset_control":
            # Reset control in a district
            district_id = effect.get('district_id')
            cursor.execute(
                """
                UPDATE district_control 
                SET control_points = 0 
                WHERE district_id = ? AND player_id != ?
                """,
                (district_id, player_id)
            )
            message = f"Control reset in district {district_id}"

        conn.commit()
        conn.close()
        return success, message

    except Exception as e:
        logger.error(f"Error using politician ability: {e}")
        if conn:
            conn.close()
        return False, "Error using ability"

@db_transaction
def get_politician_relationships(player_id: int, conn: Any) -> List[Dict[str, Any]]:
    """Get list of politician relationships for a player."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.politician_id, p.name, p.role, p.ideology_score,
               pr.friendliness, pr.interaction_count
        FROM politicians p
        LEFT JOIN politician_relationships pr ON p.politician_id = pr.politician_id 
            AND pr.player_id = ?
        ORDER BY pr.friendliness DESC
    """, (player_id,))
    
    relationships = []
    for row in cursor.fetchall():
        pol_id, name, role, ideology, friendliness, interactions = row
        relationships.append({
            'id': pol_id,
            'name': name,
            'role': role,
            'ideology_score': ideology,
            'friendliness': friendliness or 50,  # Default friendliness
            'interaction_count': interactions or 0
        })
    return relationships

@db_transaction
def update_relationship(
    player_id: int,
    politician_id: int,
    friendliness_change: int,
    conn: Any
) -> Dict[str, Any]:
    """Update relationship with a politician."""
    cursor = conn.cursor()
    
    # Get current relationship
    cursor.execute("""
        SELECT friendliness, interaction_count
        FROM politician_relationships
        WHERE player_id = ? AND politician_id = ?
    """, (player_id, politician_id))
    
    row = cursor.fetchone()
    current_friendliness = row[0] if row else 50
    interaction_count = row[1] if row else 0
    
    # Calculate new friendliness
    new_friendliness = max(0, min(100, current_friendliness + friendliness_change))
    
    # Update or insert relationship
    cursor.execute("""
        INSERT OR REPLACE INTO politician_relationships 
        (player_id, politician_id, friendliness, interaction_count)
        VALUES (?, ?, ?, ?)
    """, (player_id, politician_id, new_friendliness, interaction_count + 1))
    
    return {
        'old_friendliness': current_friendliness,
        'new_friendliness': new_friendliness,
        'interaction_count': interaction_count + 1
    }

def format_relationship_info(player_id: int, politician_id: int, lang: str = "en") -> str:
    """Format relationship information for display."""
    with db_connection_pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, p.role, p.ideology_score,
                   pr.friendliness, pr.interaction_count
            FROM politicians p
            LEFT JOIN politician_relationships pr ON p.politician_id = pr.politician_id 
                AND pr.player_id = ?
            WHERE p.politician_id = ?
        """, (player_id, politician_id))
        
        row = cursor.fetchone()
        if not row:
            return get_text("politician_not_found", lang)
            
        name, role, ideology, friendliness, interactions = row
        
        info = [
            f"*{name}* - {role}",
            f"{get_text('ideology', lang)}: {ideology}",
            f"{get_text('friendliness', lang)}: {friendliness or 50}%",
            f"{get_text('interactions', lang)}: {interactions or 0}"
        ]
        return "\n".join(info)

def get_relationship_summary(player_id: int, lang: str = "en") -> str:
    """Get summary of all politician relationships."""
    with db_connection_pool.get_connection() as conn:
        relationships = get_politician_relationships(player_id, conn)
        
        if not relationships:
            return get_text("no_relationships", lang)

        summary = [get_text("relationship_summary", lang)]
        for rel in relationships:
            summary.append(f"*{rel['name']}* - {rel['role']}")
            summary.append(f"• {get_text('friendliness', lang)}: {rel['friendliness']}%")
            if rel['interaction_count'] > 0:
                summary.append(f"• {get_text('interactions', lang)}: {rel['interaction_count']}")
            summary.append("")

        return "\n".join(summary).strip()

def interact_with_politician(
    player_id: int,
    politician_id: int,
    interaction_type: str,
    lang: str = "en"
) -> str:
    """Process an interaction with a politician."""
    try:
        with db_connection_pool.get_connection() as conn:
            # Get interaction details
            cursor = conn.cursor()
            cursor.execute("""
                SELECT friendliness_change, cooldown_hours
                FROM politician_interactions
                WHERE interaction_type = ?
            """, (interaction_type,))
            
            row = cursor.fetchone()
            if not row:
                return get_text("invalid_interaction", lang)
                
            friendliness_change, cooldown = row
            
            # Check cooldown
            cursor.execute("""
                SELECT last_interaction_time
                FROM politician_interaction_history
                WHERE player_id = ? AND politician_id = ?
                    AND interaction_type = ?
            """, (player_id, politician_id, interaction_type))
            
            row = cursor.fetchone()
            if row and row[0]:
                cursor.execute("""
                    SELECT datetime('now') <= datetime(?, '+' || ? || ' hours')
                    FROM politician_interaction_history
                    WHERE player_id = ? AND politician_id = ?
                        AND interaction_type = ?
                """, (row[0], cooldown, player_id, politician_id, interaction_type))
                if cursor.fetchone()[0]:
                    return get_text("interaction_cooldown", lang)
            
            # Update relationship
            result = update_relationship(player_id, politician_id, friendliness_change, conn)
            
            # Record interaction
            cursor.execute("""
                INSERT OR REPLACE INTO politician_interaction_history
                (player_id, politician_id, interaction_type, last_interaction_time)
                VALUES (?, ?, ?, datetime('now'))
            """, (player_id, politician_id, interaction_type))
            
            return get_text("interaction_success", lang, params={
                "old_friendliness": result['old_friendliness'],
                "new_friendliness": result['new_friendliness']
            })
            
    except Exception as e:
        return get_text("interaction_error", lang)