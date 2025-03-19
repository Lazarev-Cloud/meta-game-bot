#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Joint Actions for Belgrade Game Bot
Implements functionality for cooperative player actions
"""

import logging
import sqlite3
import datetime
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def get_expired_joint_actions() -> List[Dict[str, Any]]:
    """Get all expired joint actions that need to be processed"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        current_time = datetime.datetime.now().isoformat()

        cursor.execute("""
            SELECT 
                ja.action_id,
                ja.initiator_id,
                ja.district_id,
                ja.action_type,
                GROUP_CONCAT(jap.player_id) as participants,
                GROUP_CONCAT(jap.resources) as resources
            FROM joint_actions ja
            LEFT JOIN joint_action_participants jap ON ja.action_id = jap.action_id
            WHERE ja.status = 'pending'
            AND ja.expires_at < ?
            GROUP BY ja.action_id
        """, (current_time,))

        actions = []
        for row in cursor.fetchall():
            action_id, initiator_id, district_id, action_type, participants, resources = row

            participants_list = participants.split(',') if participants else []
            resources_list = resources.split(',') if resources else []

            actions.append({
                'action_id': action_id,
                'initiator_id': initiator_id,
                'district_id': district_id,
                'action_type': action_type,
                'participants': participants_list,
                'resources': resources_list
            })

        conn.close()
        return actions

    except Exception as e:
        logger.error(f"Error getting expired joint actions: {e}")
        return []


def calculate_joint_action_power(action: Dict[str, Any]) -> float:
    """Calculate the power multiplier based on participants and resources"""
    base_multiplier = 1.0
    participant_count = len(action['participants'])

    # Base bonus for each additional participant
    if participant_count > 1:
        base_multiplier += (participant_count - 1) * 0.2  # +20% for each additional participant

    # Resource bonus
    resource_count = len(action['resources'])
    if resource_count > 0:
        base_multiplier += resource_count * 0.1  # +10% for each resource committed

    return min(base_multiplier, 2.5)  # Cap at 250% power


def process_expired_joint_actions():
    """Process all expired joint actions"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        expired_actions = get_expired_joint_actions()

        for action in expired_actions:
            try:
                # Calculate power multiplier
                power_multiplier = calculate_joint_action_power(action)

                # Import here to avoid circular imports
                from game.actions import process_action

                # Process the base action with multiplier
                result = process_action(
                    action['action_id'],
                    action['initiator_id'],
                    action['action_type'],
                    'district',
                    action['district_id'],
                    power_multiplier=power_multiplier
                )

                # Update action status
                cursor.execute("""
                    UPDATE joint_actions 
                    SET status = 'completed'
                    WHERE action_id = ?
                """, (action['action_id'],))

                # Add a news entry about the joint action
                from languages import get_text
                from db.queries import add_news

                # Use 'en' language for news (or better would be to get initiator's language)
                lang = 'en'

                add_news(
                    get_text("joint_action_title", lang, district=action['district_id']),
                    get_text("joint_action_description", lang,
                             action_type=get_text(f"action_type_{action['action_type']}", lang),
                             count=len(action['participants']),
                             multiplier=power_multiplier),
                    is_public=True,
                    is_fake=False
                )

                # Return resources if action failed
                if result.get('status') == 'failed':
                    # Import resource handling functions
                    from db.queries import update_player_resources

                    for player_id, resources in zip(action['participants'], action['resources']):
                        # Parse resources from string
                        try:
                            resources_dict = json.loads(resources)
                            for resource_type, amount in resources_dict.items():
                                update_player_resources(player_id, resource_type, amount)
                        except json.JSONDecodeError:
                            logger.error(f"Error parsing resources JSON: {resources}")
                            continue

            except Exception as e:
                logger.error(f"Error processing joint action {action['action_id']}: {e}")
                continue

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Error in process_expired_joint_actions: {e}")


def cleanup_old_joint_actions():
    """Clean up old completed joint actions"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Keep actions for 24 hours after completion
        cleanup_time = (datetime.datetime.now() - datetime.timedelta(hours=24)).isoformat()

        cursor.execute("""
            DELETE FROM joint_action_participants
            WHERE action_id IN (
                SELECT action_id 
                FROM joint_actions 
                WHERE status = 'completed' 
                AND expires_at < ?
            )
        """, (cleanup_time,))

        cursor.execute("""
            DELETE FROM joint_actions
            WHERE status = 'completed'
            AND expires_at < ?
        """, (cleanup_time,))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Error cleaning up old joint actions: {e}")


def create_joint_action(initiator_id: int, district_id: str, action_type: str, expires_in_minutes: int = 30) -> int:
    """
    Create a new joint action that other players can join

    Args:
        initiator_id: Player initiating the action
        district_id: Target district
        action_type: Type of action (influence, attack, defense)
        expires_in_minutes: Time until action executes

    Returns:
        Joint action ID or 0 on failure
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Calculate expiration time
        expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=expires_in_minutes)).isoformat()

        # Create the joint action
        cursor.execute("""
            INSERT INTO joint_actions 
            (initiator_id, district_id, action_type, created_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (initiator_id, district_id, action_type, datetime.datetime.now().isoformat(), expires_at))

        action_id = cursor.lastrowid

        # Add the initiator as a participant
        cursor.execute("""
            INSERT INTO joint_action_participants
            (action_id, player_id, join_time)
            VALUES (?, ?, ?)
        """, (action_id, initiator_id, datetime.datetime.now().isoformat()))

        conn.commit()
        conn.close()

        return action_id

    except Exception as e:
        logger.error(f"Error creating joint action: {e}")
        return 0


def join_joint_action(action_id: int, player_id: int, resources: Dict[str, int]) -> bool:
    """
    Join an existing joint action

    Args:
        action_id: Joint action ID
        player_id: Player joining the action
        resources: Resources to contribute

    Returns:
        True if successfully joined
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Verify action exists and is pending
        cursor.execute("""
            SELECT action_id, initiator_id, expires_at
            FROM joint_actions
            WHERE action_id = ? AND status = 'pending'
        """, (action_id,))

        action = cursor.fetchone()
        if not action:
            logger.error(f"Joint action {action_id} not found or not pending")
            conn.close()
            return False

        # Check if expiration time is still in the future
        expires_at = datetime.datetime.fromisoformat(action[2])
        if datetime.datetime.now() >= expires_at:
            logger.error(f"Joint action {action_id} has already expired")
            conn.close()
            return False

        # Verify player has required resources
        from db.queries import get_player_resources
        player_resources = get_player_resources(player_id)

        if not player_resources:
            logger.error(f"Player {player_id} not found or has no resources")
            conn.close()
            return False

        for resource_type, amount in resources.items():
            if player_resources.get(resource_type, 0) < amount:
                logger.error(
                    f"Player {player_id} lacks {resource_type}: needs {amount}, has {player_resources.get(resource_type, 0)}")
                conn.close()
                return False

        # Check if player is already a participant
        cursor.execute("""
            SELECT player_id FROM joint_action_participants
            WHERE action_id = ? AND player_id = ?
        """, (action_id, player_id))

        if cursor.fetchone():
            logger.error(f"Player {player_id} is already a participant in joint action {action_id}")
            conn.close()
            return False

        # Add player as participant
        cursor.execute("""
            INSERT INTO joint_action_participants
            (action_id, player_id, join_time, resources)
            VALUES (?, ?, ?, ?)
        """, (action_id, player_id, datetime.datetime.now().isoformat(), json.dumps(resources)))

        # Deduct resources from player
        from db.queries import update_player_resources
        for resource_type, amount in resources.items():
            update_player_resources(player_id, resource_type, -amount)

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        logger.error(f"Error joining joint action: {e}")
        return False