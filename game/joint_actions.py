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
from typing import List, Dict, Any, Optional, Tuple
from db.queries import db_connection_pool, db_transaction
from languages import get_text

logger = logging.getLogger(__name__)


@db_transaction
def get_expired_joint_actions() -> List[Dict[str, Any]]:
    """Get all expired joint actions that need to be processed"""
    try:
        with db_connection_pool.get_connection() as conn:
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


@db_transaction
def process_expired_joint_actions():
    """Process all expired joint actions"""
    try:
        with db_connection_pool.get_connection() as conn:
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

    except Exception as e:
        logger.error(f"Error in process_expired_joint_actions: {e}")


@db_transaction
def get_expired_joint_actions(conn) -> List[Dict[str, Any]]:
    """Get all expired joint actions that need to be processed"""
    try:
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


@db_transaction
def process_expired_joint_actions(conn):
    """Process all expired joint actions"""
    try:
        # Get expired actions with the same connection
        expired_actions = get_expired_joint_actions(conn)
        cursor = conn.cursor()

        for action in expired_actions:
            try:
                # Calculate power multiplier
                power_multiplier = calculate_joint_action_power(action)

                # Import here to avoid circular imports
                from game.actions import process_action_in_transaction

                # Process the base action with multiplier
                result = process_action_in_transaction(
                    conn,
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
                from db.queries import add_news

                # Get district name
                cursor.execute(
                    "SELECT name FROM districts WHERE district_id = ?",
                    (action['district_id'],)
                )
                district_row = cursor.fetchone()
                district_name = district_row[0] if district_row else action['district_id']

                # Use 'en' language for news (or better would be to get initiator's language)
                lang = 'en'

                add_news(
                    f"Joint {action['action_type']} action in {district_name}",
                    f"A group of {len(action['participants'])} players performed a joint {action['action_type']} action in {district_name} with {power_multiplier:.1f}x power.",
                    True,  # is_public
                    None,  # target_player_id
                    False  # is_fake
                )

                # Return resources if action failed
                if result.get('status') == 'failed':
                    # Process resource refunds with the same connection
                    for player_id, resources_json in zip(action['participants'], action['resources']):
                        # Parse resources from string
                        try:
                            resources_dict = json.loads(resources_json)
                            for resource_type, amount in resources_dict.items():
                                cursor.execute(
                                    f"UPDATE resources SET {resource_type} = {resource_type} + ? WHERE player_id = ?",
                                    (amount, player_id)
                                )
                        except (json.JSONDecodeError, TypeError):
                            logger.error(f"Error parsing resources JSON: {resources_json}")
                            continue

            except Exception as e:
                logger.error(f"Error processing joint action {action['action_id']}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in process_expired_joint_actions: {e}")


@db_transaction
def cleanup_old_joint_actions(conn):
    """Clean up old completed joint actions"""
    try:
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

    except Exception as e:
        logger.error(f"Error cleaning up old joint actions: {e}")


@db_transaction
def join_joint_action(conn, action_id: int, player_id: int, resources: Dict[str, int] = None) -> bool:
    """Join a joint action with resources."""
    try:
        cursor = conn.cursor()

        # Check if action exists and is pending
        cursor.execute("""
            SELECT required_participants, status
            FROM joint_actions
            WHERE action_id = ?
        """, (action_id,))

        row = cursor.fetchone()
        if not row or row[1] != 'pending':
            return False

        required_participants = row[0]

        # Check if player already joined
        cursor.execute("""
            SELECT COUNT(*)
            FROM joint_action_participants
            WHERE action_id = ? AND player_id = ?
        """, (action_id, player_id))

        if cursor.fetchone()[0] > 0:
            return False

        # Validate and deduct resources if provided
        resources_json = None
        if resources:
            # Get player's current resources
            cursor.execute(
                """
                SELECT influence, resources, information, force
                FROM resources
                WHERE player_id = ?
                """,
                (player_id,)
            )

            player_res = cursor.fetchone()
            if not player_res:
                return False

            player_resources = {
                "influence": player_res[0],
                "resources": player_res[1],
                "information": player_res[2],
                "force": player_res[3]
            }

            # Check if player has enough resources
            for resource_type, amount in resources.items():
                if player_resources.get(resource_type, 0) < amount:
                    return False

            # Deduct resources
            for resource_type, amount in resources.items():
                cursor.execute(
                    f"UPDATE resources SET {resource_type} = {resource_type} - ? WHERE player_id = ?",
                    (amount, player_id)
                )

            # Convert resources to JSON
            resources_json = json.dumps(resources)

        # Add player as participant
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO joint_action_participants (
                action_id, player_id, join_time, resources
            )
            VALUES (?, ?, ?, ?)
        """, (action_id, player_id, now, resources_json))

        # Check if we have enough participants
        cursor.execute("""
            SELECT COUNT(*)
            FROM joint_action_participants
            WHERE action_id = ?
        """, (action_id,))

        if cursor.fetchone()[0] >= required_participants:
            # Update action status to ready
            cursor.execute("""
                UPDATE joint_actions
                SET status = 'ready'
                WHERE action_id = ?
            """, (action_id,))

        return True
    except Exception as e:
        logger.error(f"Error joining joint action: {e}")
        return False

@db_transaction
def get_joint_actions(player_id: int, conn: Any) -> List[Dict[str, Any]]:
    """Get list of available joint actions."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ja.action_id, ja.title, ja.description,
               ja.required_participants, ja.status,
               ja.created_timestamp, ja.deadline_timestamp,
               p.username as initiator_name,
               GROUP_CONCAT(pp.username) as participant_names
        FROM joint_actions ja
        JOIN players p ON ja.initiator_id = p.player_id
        LEFT JOIN joint_action_participants jap ON ja.action_id = jap.action_id
        LEFT JOIN players pp ON jap.player_id = pp.player_id
        WHERE ja.status = 'pending'
            AND ja.initiator_id != ?
            AND ja.action_id NOT IN (
                SELECT action_id
                FROM joint_action_participants
                WHERE player_id = ?
            )
        GROUP BY ja.action_id
        ORDER BY ja.created_timestamp DESC
    """, (player_id, player_id))
    
    actions = []
    for row in cursor.fetchall():
        action_id, title, desc, required, status, created, deadline, initiator, participants = row
        actions.append({
            'id': action_id,
            'title': title,
            'description': desc,
            'required_participants': required,
            'status': status,
            'created_timestamp': created,
            'deadline_timestamp': deadline,
            'initiator_name': initiator,
            'participant_names': participants.split(',') if participants else []
        })
    return actions


@db_transaction
def get_joint_action_info(action_id: int, conn: Any) -> Optional[Dict[str, Any]]:
    """Get detailed information about a joint action."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ja.action_id, ja.title, ja.description,
               ja.required_participants, ja.status,
               ja.created_timestamp, ja.deadline_timestamp,
               p.username as initiator_name,
               GROUP_CONCAT(pp.username) as participant_names
        FROM joint_actions ja
        JOIN players p ON ja.initiator_id = p.player_id
        LEFT JOIN joint_action_participants jap ON ja.action_id = jap.action_id
        LEFT JOIN players pp ON jap.player_id = pp.player_id
        WHERE ja.action_id = ?
        GROUP BY ja.action_id
    """, (action_id,))
    
    row = cursor.fetchone()
    if not row:
        return None
        
    action_id, title, desc, required, status, created, deadline, initiator, participants = row
    return {
        'id': action_id,
        'title': title,
        'description': desc,
        'required_participants': required,
        'status': status,
        'created_timestamp': created,
        'deadline_timestamp': deadline,
        'initiator_name': initiator,
        'participant_names': participants.split(',') if participants else []
    }


@db_transaction
def create_joint_action(
    initiator_id: int,
    title: str,
    description: str,
    required_participants: int,
    deadline: str,
    conn: Any
) -> int:
    """Create a new joint action."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO joint_actions (
            initiator_id, title, description,
            required_participants, deadline_timestamp
        ) VALUES (?, ?, ?, ?, ?)
    """, (initiator_id, title, description, required_participants, deadline))
    
    return cursor.lastrowid




@db_transaction
def complete_joint_action(action_id: int, conn: Any) -> bool:
    """Complete a joint action."""
    cursor = conn.cursor()
    
    # Check if action is ready
    cursor.execute("""
        SELECT status
        FROM joint_actions
        WHERE action_id = ?
    """, (action_id,))
    
    row = cursor.fetchone()
    if not row or row[0] != 'ready':
        return False
    
    # Complete the action
    cursor.execute("""
        UPDATE joint_actions
        SET status = 'completed'
        WHERE action_id = ?
    """, (action_id,))
    
    return True


def format_joint_action_info(action_id: int, lang: str = "en") -> str:
    """Format joint action information for display."""
    with db_connection_pool.get_connection() as conn:
        action = get_joint_action_info(action_id, conn)
        if not action:
            return get_text("action_not_found", lang)

        info = [
            f"*{action['title']}*",
            f"{action['description']}",
            f"{get_text('initiator', lang)}: {action['initiator_name']}",
            f"{get_text('participants', lang)}: {', '.join(action['participant_names'])}",
            f"{get_text('required_participants', lang)}: {action['required_participants']}",
            f"{get_text('status', lang)}: {get_text(action['status'], lang)}",
            f"{get_text('deadline', lang)}: {action['deadline_timestamp']}"
        ]
        return "\n".join(info)


def get_available_joint_actions(player_id: int, lang: str = "en") -> str:
    """Get formatted list of available joint actions."""
    with db_connection_pool.get_connection() as conn:
        actions = get_joint_actions(player_id, conn)
        
        if not actions:
            return get_text("no_joint_actions", lang)

        action_list = [get_text("available_joint_actions", lang)]
        for action in actions:
            action_list.append(format_joint_action_info(action['id'], lang))
            action_list.append("")

        return "\n".join(action_list).strip()


def start_joint_action(
    initiator_id: int,
    title: str,
    description: str,
    required_participants: int,
    deadline: str,
    lang: str = "en"
) -> str:
    """Start a new joint action and return confirmation."""
    try:
        with db_connection_pool.get_connection() as conn:
            action_id = create_joint_action(
                initiator_id=initiator_id,
                title=title,
                description=description,
                required_participants=required_participants,
                deadline=deadline,
                conn=conn
            )
            return get_text("joint_action_created", lang, params={"action_id": action_id})
    except Exception as e:
        return get_text("joint_action_creation_failed", lang)


def participate_in_joint_action(player_id: int, action_id: int, lang: str = "en") -> str:
    """Join a joint action and return confirmation."""
    try:
        with db_connection_pool.get_connection() as conn:
            if join_joint_action(player_id, action_id, conn):
                return get_text("joined_joint_action", lang)
            else:
                return get_text("join_joint_action_failed", lang)
    except Exception as e:
        return get_text("join_joint_action_error", lang)


def finish_joint_action(action_id: int, lang: str = "en") -> str:
    """Complete a joint action and return confirmation."""
    try:
        with db_connection_pool.get_connection() as conn:
            if complete_joint_action(action_id, conn):
                return get_text("joint_action_completed", lang)
            else:
                return get_text("joint_action_completion_failed", lang)
    except Exception as e:
        return get_text("joint_action_error", lang)

@db_transaction
def create_joint_action(initiator_id: int, action_type: str, target_type: str, target_id: int,
                       required_participants: int, expiration_hours: int = 24) -> Optional[int]:
    """Create a new joint action."""
    try:
        expiration_time = (datetime.now() + timedelta(hours=expiration_hours)).isoformat()
        
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO joint_actions (
                    initiator_id, action_type, target_type, target_id,
                    required_participants, expiration_time, status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (
                initiator_id, action_type, target_type, target_id,
                required_participants, expiration_time
            ))
            
            action_id = cursor.lastrowid
            
            # Add initiator as first participant
            cursor.execute("""
                INSERT INTO joint_action_participants (
                    action_id, player_id, join_time
                )
                VALUES (?, ?, ?)
            """, (action_id, initiator_id, datetime.now().isoformat()))
            
            return action_id
    except Exception as e:
        logger.error(f"Error creating joint action: {e}")
        return None

@db_transaction
def get_joint_action_info(action_id: int) -> Optional[Dict[str, Any]]:
    """Get information about a specific joint action."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ja.action_id, ja.initiator_id, ja.action_type,
                       ja.target_type, ja.target_id, ja.required_participants,
                       ja.expiration_time, ja.status,
                       p.username as initiator_name
                FROM joint_actions ja
                JOIN players p ON ja.initiator_id = p.player_id
                WHERE ja.action_id = ?
            """, (action_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            # Get participants
            cursor.execute("""
                SELECT p.player_id, p.username, jap.join_time
                FROM joint_action_participants jap
                JOIN players p ON jap.player_id = p.player_id
                WHERE jap.action_id = ?
                ORDER BY jap.join_time
            """, (action_id,))
            
            participants = []
            for p_row in cursor.fetchall():
                participants.append({
                    'id': p_row[0],
                    'username': p_row[1],
                    'join_time': p_row[2]
                })
            
            return {
                'id': row[0],
                'initiator_id': row[1],
                'action_type': row[2],
                'target_type': row[3],
                'target_id': row[4],
                'required_participants': row[5],
                'expiration_time': row[6],
                'status': row[7],
                'initiator_name': row[8],
                'participants': participants
            }
    except Exception as e:
        logger.error(f"Error getting joint action info: {e}")
        return None

@db_transaction
def get_active_joint_actions() -> List[Dict[str, Any]]:
    """Get a list of active joint actions."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ja.action_id, ja.initiator_id, ja.action_type,
                       ja.target_type, ja.target_id, ja.required_participants,
                       ja.expiration_time, p.username as initiator_name
                FROM joint_actions ja
                JOIN players p ON ja.initiator_id = p.player_id
                WHERE ja.status = 'pending'
                  AND ja.expiration_time > ?
                ORDER BY ja.expiration_time
            """, (datetime.now().isoformat(),))
            
            actions = []
            for row in cursor.fetchall():
                action_id = row[0]
                
                # Get participants count
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM joint_action_participants
                    WHERE action_id = ?
                """, (action_id,))
                
                participant_count = cursor.fetchone()[0]
                
                actions.append({
                    'id': action_id,
                    'initiator_id': row[1],
                    'action_type': row[2],
                    'target_type': row[3],
                    'target_id': row[4],
                    'required_participants': row[5],
                    'expiration_time': row[6],
                    'initiator_name': row[7],
                    'current_participants': participant_count
                })
            return actions
    except Exception as e:
        logger.error(f"Error getting active joint actions: {e}")
        return []

@db_transaction
def join_joint_action(action_id: int, player_id: int) -> bool:
    """Join a joint action."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if action exists and is pending
            cursor.execute("""
                SELECT required_participants, status
                FROM joint_actions
                WHERE action_id = ?
            """, (action_id,))
            
            row = cursor.fetchone()
            if not row or row[1] != 'pending':
                return False
                
            required_participants = row[0]
            
            # Check if player already joined
            cursor.execute("""
                SELECT COUNT(*)
                FROM joint_action_participants
                WHERE action_id = ? AND player_id = ?
            """, (action_id, player_id))
            
            if cursor.fetchone()[0] > 0:
                return False
            
            # Add player as participant
            cursor.execute("""
                INSERT INTO joint_action_participants (
                    action_id, player_id, join_time
                )
                VALUES (?, ?, ?)
            """, (action_id, player_id, datetime.now().isoformat()))
            
            # Check if we have enough participants
            cursor.execute("""
                SELECT COUNT(*)
                FROM joint_action_participants
                WHERE action_id = ?
            """, (action_id,))
            
            if cursor.fetchone()[0] >= required_participants:
                # Update action status to ready
                cursor.execute("""
                    UPDATE joint_actions
                    SET status = 'ready'
                    WHERE action_id = ?
                """, (action_id,))
            
            return True
    except Exception as e:
        logger.error(f"Error joining joint action: {e}")
        return False

@db_transaction
def cancel_joint_action(action_id: int, player_id: int) -> bool:
    """Cancel a joint action."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE joint_actions
                SET status = 'cancelled'
                WHERE action_id = ? AND initiator_id = ? AND status = 'pending'
            """, (action_id, player_id))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error cancelling joint action: {e}")
        return False

def format_joint_action_info(action_id: int, lang: str = 'en') -> str:
    """Format joint action information for display."""
    action = get_joint_action_info(action_id)
    if not action:
        return get_text("joint_action_not_found", lang)
    
    expiration = datetime.fromisoformat(action['expiration_time'])
    formatted_date = expiration.strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"*{get_text('joint_action', lang)}*",
        f"{get_text('initiator', lang)}: {action['initiator_name']}",
        f"{get_text('action_type', lang)}: {get_text(action['action_type'], lang)}",
        f"{get_text('target', lang)}: {action['target_type']} #{action['target_id']}",
        "",
        f"*{get_text('participants', lang)}*"
    ]
    
    for participant in action['participants']:
        join_time = datetime.fromisoformat(participant['join_time'])
        formatted_join = join_time.strftime("%Y-%m-%d %H:%M")
        lines.append(f"- {participant['username']} ({formatted_join})")
    
    lines.extend([
        "",
        f"{get_text('required_participants', lang)}: {action['required_participants']}",
        f"{get_text('current_participants', lang)}: {len(action['participants'])}",
        f"{get_text('expires', lang)}: {formatted_date}",
        f"{get_text('status', lang)}: {get_text(action['status'], lang)}"
    ])
    
    return "\n".join(lines)

def get_active_joint_action_list(lang: str = 'en') -> str:
    """Get a formatted list of active joint actions."""
    actions = get_active_joint_actions()
    if not actions:
        return get_text("no_active_joint_actions", lang)
    
    lines = [get_text("active_joint_actions_header", lang)]
    for action in actions:
        expiration = datetime.fromisoformat(action['expiration_time'])
        formatted_date = expiration.strftime("%Y-%m-%d %H:%M")
        
        lines.extend([
            f"*{get_text('joint_action', lang)} #{action['id']}*",
            f"{get_text('initiator', lang)}: {action['initiator_name']}",
            f"{get_text('action_type', lang)}: {get_text(action['action_type'], lang)}",
            f"{get_text('target', lang)}: {action['target_type']} #{action['target_id']}",
            f"{get_text('participants', lang)}: {action['current_participants']}/{action['required_participants']}",
            f"{get_text('expires', lang)}: {formatted_date}",
            ""
        ])
    
    return "\n".join(lines).strip()