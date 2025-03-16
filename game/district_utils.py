#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
District utilities for Belgrade Game Bot
Extends the base district.py functionality with additional utilities
"""

import logging
import sqlite3
import random
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def calculate_action_success_rate(player_id: int, district_id: str, action_type: str) -> float:
    """
    Calculate success rate for an action based on player's control, ideology match, and random factors

    Args:
        player_id: Player ID
        district_id: District ID
        action_type: Type of action ("influence", "attack", "defense")

    Returns:
        float: Success rate between 0.0 and 1.0
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get player's control in district
        cursor.execute(
            "SELECT control_points FROM district_control WHERE player_id = ? AND district_id = ?",
            (player_id, district_id)
        )
        control_result = cursor.fetchone()
        player_control = control_result[0] if control_result else 0

        # Get district's main politician and their ideology
        cursor.execute(
            """
            SELECT p.ideology_score 
            FROM politicians p
            WHERE p.district_id = ?
            ORDER BY p.influence DESC
            LIMIT 1
            """,
            (district_id,)
        )
        politician_result = cursor.fetchone()
        district_ideology = politician_result[0] if politician_result else 0

        # Get player's ideology
        cursor.execute("SELECT ideology_score FROM players WHERE player_id = ?", (player_id,))
        player_result = cursor.fetchone()
        player_ideology = player_result[0] if player_result else 0

        conn.close()

        # Base success rate ranges from 30% to 70%
        base_success_rate = 0.5

        # Control modifier: +0% to +20% based on control (max +20% at 80+ control)
        control_modifier = min(0.2, (player_control / 400))

        # Ideology match: -15% to +15% based on ideology match
        ideology_difference = abs(player_ideology - district_ideology)
        if ideology_difference <= 2:
            ideology_modifier = 0.15  # Good match
        elif ideology_difference <= 5:
            ideology_modifier = 0.0  # Neutral
        else:
            ideology_modifier = -0.15  # Poor match

        # Action type modifier
        if action_type == "influence" and player_control >= 60:
            # Easier to maintain influence
            action_modifier = 0.1
        elif action_type == "attack" and player_control < 20:
            # Harder to attack from a weak position
            action_modifier = -0.1
        elif action_type == "defense" and player_control >= 60:
            # Easier to defend when in control
            action_modifier = 0.15
        else:
            action_modifier = 0.0

        # Random factor: +/-5%
        random_modifier = random.uniform(-0.05, 0.05)

        # Calculate final success rate
        success_rate = base_success_rate + control_modifier + ideology_modifier + action_modifier + random_modifier

        # Clamp between 0.1 (10%) and 0.9 (90%)
        return max(0.1, min(0.9, success_rate))

    except Exception as e:
        logger.error(f"Error calculating action success rate: {e}")
        return 0.5  # Default to 50% on error


def get_district_adjacency(district_id: str) -> List[str]:
    """
    Get adjacent districts to the given district

    Args:
        district_id: District ID

    Returns:
        List[str]: List of adjacent district IDs
    """
    # Define district adjacency (based on Belgrade geography)
    district_adjacency = {
        'stari_grad': ['savski_venac', 'vracar', 'palilula'],
        'novi_beograd': ['zemun', 'cukarica', 'savski_venac'],
        'zemun': ['novi_beograd'],
        'savski_venac': ['stari_grad', 'novi_beograd', 'vracar', 'cukarica', 'vozdovac'],
        'vozdovac': ['savski_venac', 'vracar'],
        'cukarica': ['novi_beograd', 'savski_venac'],
        'palilula': ['stari_grad', 'vracar'],
        'vracar': ['stari_grad', 'savski_venac', 'vozdovac', 'palilula']
    }

    return district_adjacency.get(district_id, [])


def get_district_special_events(district_id: str) -> List[Dict[str, Any]]:
    """
    Get special events that can happen in a district

    Args:
        district_id: District ID

    Returns:
        List[Dict]: List of possible special events
    """
    # District-specific special events
    special_events = {
        'stari_grad': [
            {
                'name': 'government_reshuffle',
                'title_key': 'event_govt_reshuffle',
                'effect': {'influence': 1, 'control_modifier': 5},
                'weight': 0.2
            },
            {
                'name': 'demonstration',
                'title_key': 'event_demonstration',
                'effect': {'control_modifier': -5},
                'weight': 0.3
            }
        ],
        'novi_beograd': [
            {
                'name': 'foreign_investment',
                'title_key': 'event_investment',
                'effect': {'resources': 2},
                'weight': 0.2
            },
            {
                'name': 'economic_sanctions',
                'title_key': 'event_sanctions',
                'effect': {'resources': -1},
                'weight': 0.3
            }
        ],
        'zemun': [
            {
                'name': 'police_raid',
                'title_key': 'event_police_raid',
                'effect': {'force': -1, 'control_modifier': -10},
                'weight': 0.2
            },
            {
                'name': 'smuggling_operation',
                'title_key': 'event_smuggling',
                'effect': {'resources': 2, 'information': 1},
                'weight': 0.3
            }
        ],
        'savski_venac': [
            {
                'name': 'diplomatic_reception',
                'title_key': 'event_diplomatic',
                'effect': {'influence': 2},
                'weight': 0.2
            }
        ],
        'vozdovac': [
            {
                'name': 'military_exercise',
                'title_key': 'event_military',
                'effect': {'force': 2, 'control_modifier': 5},
                'weight': 0.2
            }
        ],
        'cukarica': [
            {
                'name': 'worker_strike',
                'title_key': 'event_strike',
                'effect': {'resources': -1, 'control_modifier': -5},
                'weight': 0.3
            }
        ],
        'palilula': [
            {
                'name': 'student_protest',
                'title_key': 'event_student',
                'effect': {'influence': 1, 'information': 1},
                'weight': 0.3
            }
        ],
        'vracar': [
            {
                'name': 'cultural_festival',
                'title_key': 'event_festival',
                'effect': {'influence': 1, 'control_modifier': 5},
                'weight': 0.2
            }
        ]
    }

    return special_events.get(district_id, [])


def calculate_district_importance():
    """
    Calculate current importance of each district based on game state

    Returns:
        Dict[str, float]: District importance scores (0.0-1.0)
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get all districts
        cursor.execute("SELECT district_id FROM districts")
        districts = cursor.fetchall()

        # Get control data for all districts
        cursor.execute(
            """
            SELECT district_id, COUNT(DISTINCT player_id), MAX(control_points)
            FROM district_control
            GROUP BY district_id
            """
        )
        control_data = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        # Get politician influence data
        cursor.execute(
            """
            SELECT district_id, SUM(influence)
            FROM politicians
            WHERE district_id IS NOT NULL
            GROUP BY district_id
            """
        )
        politician_data = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        # Calculate importance scores
        importance_scores = {}
        for (district_id,) in districts:
            # Number of players contesting and max control points
            num_players, max_control = control_data.get(district_id, (0, 0))

            # Politician influence
            politician_influence = politician_data.get(district_id, 0)

            # Base importance (all districts start at 0.5)
            base_importance = 0.5

            # Add 0.1 for each player contesting (max +0.3)
            contest_factor = min(0.3, num_players * 0.1)

            # Add up to 0.2 based on politician influence
            influence_factor = min(0.2, politician_influence / 20)

            # Calculate final importance score
            importance = base_importance + contest_factor + influence_factor

            # Normalize to 0.0-1.0 range
            importance_scores[district_id] = min(1.0, max(0.0, importance))

        return importance_scores

    except Exception as e:
        logger.error(f"Error calculating district importance: {e}")
        return {}


def generate_district_status_report(lang="en"):
    """
    Generate a status report for all districts

    Args:
        lang: Language code

    Returns:
        str: Formatted district status report
    """
    from languages import get_text

    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Get all districts with their details
        cursor.execute("SELECT district_id, name FROM districts ORDER BY name")
        districts = cursor.fetchall()

        # Calculate district importance
        importance_scores = calculate_district_importance()

        # Build report
        report_lines = [f"*{get_text('district_report_title', lang, default='District Status Report')}*\n"]

        for district_id, name in districts:
            # Get controlling players
            cursor.execute(
                """
                SELECT p.character_name, dc.control_points
                FROM district_control dc
                JOIN players p ON dc.player_id = p.player_id
                WHERE dc.district_id = ? AND dc.control_points >= 60
                ORDER BY dc.control_points DESC
                LIMIT 1
                """,
                (district_id,)
            )
            control_result = cursor.fetchone()

            # Get number of contesting players
            cursor.execute(
                """
                SELECT COUNT(DISTINCT player_id)
                FROM district_control
                WHERE district_id = ? AND control_points > 0
                """,
                (district_id,)
            )
            contest_result = cursor.fetchone()
            num_contesting = contest_result[0] if contest_result else 0

            # Format control status
            if control_result:
                controller_name, control_points = control_result
                if control_points >= 80:
                    control_status = f"🔒 {get_text('controlled_by', lang, default='Firmly controlled by')} {controller_name}"
                else:
                    control_status = f"✅ {get_text('controlled_by', lang, default='Controlled by')} {controller_name}"
            elif num_contesting > 0:
                control_status = f"⚠️ {get_text('contested_by', lang, default='Contested by')} {num_contesting} {get_text('players', lang, default='players')}"
            else:
                control_status = f"❌ {get_text('not_controlled', lang, default='Not controlled')}"

            # Format importance
            importance = importance_scores.get(district_id, 0.5)
            if importance >= 0.8:
                importance_text = f"🔥 {get_text('high_importance', lang, default='High importance')}"
            elif importance >= 0.6:
                importance_text = f"⭐️ {get_text('medium_importance', lang, default='Medium importance')}"
            else:
                importance_text = f"⚪️ {get_text('low_importance', lang, default='Low importance')}"

            # Add to report
            report_lines.append(f"*{name}*: {control_status}")
            report_lines.append(f"  {importance_text}")

        conn.close()
        return "\n".join(report_lines)

    except Exception as e:
        logger.error(f"Error generating district status report: {e}")
        return get_text('error_generating_report', lang, default="Error generating district status report.")