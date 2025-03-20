#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Politician utilities for Belgrade Game Bot
Extends the base politicians.py functionality with additional utilities
"""

import logging
import sqlite3
import random
from typing import Dict, List, Tuple, Optional, Any
from languages import format_ideology
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
    from languages import get_text

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


def process_international_politician_activation(cycle_name: str) -> List[Dict[str, Any]]:
    """
    Process the activation of random international politicians based on the game cycle

    Args:
        cycle_name: Current game cycle name ('morning' or 'evening')

    Returns:
        List[Dict]: List of activated politicians and their actions
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get all international politicians
        cursor.execute(
            """
            SELECT politician_id, name, role, ideology_score, influence, description
            FROM politicians
            WHERE is_international = 1
            """
        )
        international_politicians = cursor.fetchall()

        # Choose number of politicians to activate (1-3)
        num_to_activate = random.randint(1, min(3, len(international_politicians)))

        # Select random politicians to activate
        politicians_to_activate = random.sample(international_politicians, num_to_activate)

        activated_politicians = []

        for politician in politicians_to_activate:
            pol_id, name, role, ideology, influence, description = politician

            # Determine action type based on politician's ideology
            if ideology < -3:  # Strongly pro-reform
                action_types = ['sanctions', 'support_opposition', 'diplomatic_pressure']
                weights = [0.4, 0.4, 0.2]
            elif ideology > 3:  # Strongly conservative
                action_types = ['support_regime', 'destabilize', 'diplomatic_support']
                weights = [0.4, 0.4, 0.2]
            else:  # Moderate
                action_types = ['economic', 'diplomatic', 'humanitarian']
                weights = [0.33, 0.33, 0.34]

            # Choose action type
            action_type = random.choices(action_types, weights=weights, k=1)[0]

            # Process the action based on type
            action_result = process_international_action(pol_id, name, role, ideology, action_type)

            # Add to activated list
            activated_politicians.append({
                "politician_id": pol_id,
                "name": name,
                "role": role,
                "ideology": ideology,
                "action_type": action_type,
                "effect": action_result
            })

        conn.close()
        return activated_politicians

    except Exception as e:
        logger.error(f"Error activating international politicians: {e}")
        return []


def process_international_action(pol_id: int, name: str, role: str, ideology: int, action_type: str) -> Dict[str, Any]:
    """
    Process an action by an international politician

    Args:
        pol_id: Politician ID
        name: Politician name
        role: Politician role
        ideology: Politician ideology score
        action_type: Type of action

    Returns:
        Dict: Action effect details
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        result = {
            "type": action_type,
            "affected_districts": [],
            "affected_politicians": [],
            "news_title": f"{name} ({role})",
            "news_content": ""
        }

        if action_type == 'sanctions':
            # Apply sanctions: affect resources in conservative districts
            result["news_title"] = f"{name} Announces Sanctions"
            result[
                "news_content"] = f"{name} ({role}) has announced sanctions against the current regime. Districts supporting conservative policies will receive a penalty to control."

            # Apply penalties to conservative districts
            cursor.execute(
                """
                SELECT d.district_id, d.name 
                FROM districts d
                JOIN politicians p ON d.district_id = p.district_id
                WHERE p.ideology_score > 3 AND p.is_international = 0
                """
            )
            conservative_districts = cursor.fetchall()

            for district_id, district_name in conservative_districts:
                # Apply penalty to all players in this district
                cursor.execute(
                    """
                    UPDATE district_control 
                    SET control_points = CASE WHEN control_points > 5 THEN control_points - 5 ELSE control_points END
                    WHERE district_id = ?
                    """,
                    (district_id,)
                )
                result["affected_districts"].append({"id": district_id, "name": district_name, "effect": -5})

        elif action_type == 'support_opposition':
            # Support opposition: boost reformist districts
            result["news_title"] = f"{name} Supports Democratic Forces"
            result[
                "news_content"] = f"{name} ({role}) has expressed support for democratic reform movements in Yugoslavia. Opposition-controlled districts receive a boost."

            # Apply bonuses to reform districts
            cursor.execute(
                """
                SELECT d.district_id, d.name 
                FROM districts d
                JOIN politicians p ON d.district_id = p.district_id
                WHERE p.ideology_score < -3 AND p.is_international = 0
                """
            )
            reform_districts = cursor.fetchall()

            for district_id, district_name in reform_districts:
                # Find player(s) with reform ideology in this district
                cursor.execute(
                    """
                    SELECT dc.player_id, p.ideology_score
                    FROM district_control dc
                    JOIN players p ON dc.player_id = p.player_id
                    WHERE dc.district_id = ? AND p.ideology_score < 0
                    """,
                    (district_id,)
                )
                reform_players = cursor.fetchall()

                for player_id, player_ideology in reform_players:
                    # Boost control based on ideology alignment
                    boost = 5 + min(5, abs(player_ideology))
                    cursor.execute(
                        """
                        UPDATE district_control 
                        SET control_points = control_points + ?
                        WHERE district_id = ? AND player_id = ?
                        """,
                        (boost, district_id, player_id)
                    )

                result["affected_districts"].append({"id": district_id, "name": district_name, "effect": "+5-10"})

        elif action_type == 'support_regime':
            # Support regime: boost conservative districts
            result["news_title"] = f"{name} Stands With Government"
            result[
                "news_content"] = f"{name} ({role}) has expressed support for the current government of Yugoslavia. Pro-government districts receive a boost."

            # Apply bonuses to conservative districts
            cursor.execute(
                """
                SELECT d.district_id, d.name 
                FROM districts d
                JOIN politicians p ON d.district_id = p.district_id
                WHERE p.ideology_score > 3 AND p.is_international = 0
                """
            )
            conservative_districts = cursor.fetchall()

            for district_id, district_name in conservative_districts:
                # Find player(s) with conservative ideology
                cursor.execute(
                    """
                    SELECT dc.player_id, p.ideology_score
                    FROM district_control dc
                    JOIN players p ON dc.player_id = p.player_id
                    WHERE dc.district_id = ? AND p.ideology_score > 0
                    """,
                    (district_id,)
                )
                conservative_players = cursor.fetchall()

                for player_id, player_ideology in conservative_players:
                    # Boost control based on ideology alignment
                    boost = 5 + min(5, player_ideology)
                    cursor.execute(
                        """
                        UPDATE district_control 
                        SET control_points = control_points + ?
                        WHERE district_id = ? AND player_id = ?
                        """,
                        (boost, district_id, player_id)
                    )

                result["affected_districts"].append({"id": district_id, "name": district_name, "effect": "+5-10"})

        elif action_type == 'economic':
            # Economic support: provide resources to moderate districts
            result["news_title"] = f"{name} Announces Economic Initiative"
            result[
                "news_content"] = f"{name} ({role}) has announced economic support for moderate districts in Yugoslavia."

            # Apply bonuses to moderate districts
            cursor.execute(
                """
                SELECT d.district_id, d.name 
                FROM districts d
                JOIN politicians p ON d.district_id = p.district_id
                WHERE p.ideology_score BETWEEN -2 AND 2 AND p.is_international = 0
                """
            )
            moderate_districts = cursor.fetchall()

            for district_id, district_name in moderate_districts:
                # Add 3 control points to all players in this district
                cursor.execute(
                    """
                    UPDATE district_control 
                    SET control_points = control_points + 3
                    WHERE district_id = ?
                    """,
                    (district_id,)
                )
                result["affected_districts"].append({"id": district_id, "name": district_name, "effect": +3})

        elif action_type == 'diplomatic':
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

        elif action_type == 'humanitarian':
            # Humanitarian aid: small boost to all districts
            result["news_title"] = f"{name} Provides Humanitarian Aid"
            result[
                "news_content"] = f"{name} ({role}) has announced humanitarian aid to affected regions in Yugoslavia."

            # Add 2 control points to all player controls
            cursor.execute(
                """
                UPDATE district_control 
                SET control_points = control_points + 2
                """
            )

            # Get all districts for reporting
            cursor.execute("SELECT district_id, name FROM districts")
            all_districts = cursor.fetchall()

            for district_id, district_name in all_districts:
                result["affected_districts"].append({"id": district_id, "name": district_name, "effect": +2})

        else:
            # Default action if type not recognized
            result["news_title"] = f"{name} Makes Statement"
            result[
                "news_content"] = f"{name} ({role}) has made a diplomatic statement regarding the situation in Yugoslavia."

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
            "type": action_type,
            "affected_districts": [],
            "affected_politicians": [],
            "news_title": f"{name} ({role})",
            "news_content": f"International event by {name} ({role})"
        }

# Fix for game/politician_utils.py - In the generate_politician_influence_report function

def generate_politician_influence_report(lang="en"):
    """
    Generate a report on politician influence across districts

    Args:
        lang: Language code

    Returns:
        str: Formatted politician influence report
    """
    from languages import get_text, format_ideology

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
            if len(politician) < 6:
                logger.warning(f"Incomplete politician data: {politician}")
                continue
                
            pol_id, name, role, ideology_score, influence, district_name = politician

            # Format ideology description
            ideology = format_ideology(ideology_score or 0, lang)

            # Format influence tier
            influence = influence or 0  # Ensure influence is not None
            if influence >= 6:
                influence_tier = f"🔵🔵🔵 {get_text('high_influence', lang, default='High influence')}"
            elif influence >= 4:
                influence_tier = f"🔵🔵 {get_text('medium_influence', lang, default='Medium influence')}"
            else:
                influence_tier = f"🔵 {get_text('low_influence', lang, default='Low influence')}"

            district_text = f" ({district_name})" if district_name else ""

            report_lines.append(f"*{name}* - {role}{district_text}")
            report_lines.append(f"  {ideology} ({ideology_score or 0}), {influence_tier}")

        # Add section for international politicians
        report_lines.append(f"\n*{get_text('international_politicians', lang, default='International Politicians')}*\n")

        cursor.execute(
            """
            SELECT politician_id, name, role, ideology_score
            FROM politicians
            WHERE is_international = 1
            ORDER BY name
            """
        )
        international_politicians = cursor.fetchall()

        for politician in international_politicians:
            if len(politician) < 4:
                logger.warning(f"Incomplete international politician data: {politician}")
                continue
                
            pol_id, name, role, ideology_score = politician

            # Format ideology description
            ideology = format_ideology(ideology_score or 0, lang)

            report_lines.append(f"*{name}* - {role}")
            report_lines.append(f"  {ideology} ({ideology_score or 0})")

        conn.close()
        return "\n".join(report_lines)

    except Exception as e:
        logger.error(f"Error generating politician influence report: {e}")
        return get_text('error_generating_report', lang, default="Error generating politician influence report.")