from typing import List, Dict, Any
import sqlite3
import datetime
import logging
from .actions import process_action
from .resources import modify_resources
from .languages import get_text

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
            
            participants = participants.split(',') if participants else []
            resources = resources.split(',') if resources else []
            
            actions.append({
                'action_id': action_id,
                'initiator_id': initiator_id,
                'district_id': district_id,
                'action_type': action_type,
                'participants': participants,
                'resources': resources
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
                
                # Create news entry about joint action
                cursor.execute("""
                    INSERT INTO news (title, content, created_at)
                    VALUES (?, ?, ?)
                """, (
                    get_text("joint_action_title", lang, district=action['district_id']),
                    get_text("joint_action_description", lang, 
                            action_type=get_text(f"action_type_{action['action_type']}", lang),
                            count=len(action['participants']),
                            multiplier=power_multiplier),
                    datetime.datetime.now().isoformat()
                ))
                
                # Return resources if action failed
                if result.get('status') == 'failed':
                    for player_id, resources in zip(action['participants'], action['resources']):
                        modify_resources(player_id, resources, add=True)
                
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