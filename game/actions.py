#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Meta Game - Actions Module
Handles player actions and their effects
"""

import logging
import random
import sqlite3
import datetime
from datetime import timedelta
from telegram import Update
from telegram.ext import ContextTypes
import json

logger = logging.getLogger(__name__)

# Resource types
RESOURCE_TYPES = ["influence", "resources", "information", "force"]

# Action Type Constants
ACTION_ATTACK = "attack"
ACTION_DEFENSE = "defend"

async def take_action(update: Update, context: ContextTypes.DEFAULT_TYPE, player_id: str, action_type: str, district_id: str = None, resource_type: str = None, amount: int = 0):
    """
    Process a player action.
    
    Args:
        update: Telegram update
        context: Bot context
        player_id: ID of the player taking the action
        action_type: Type of action (collect, control, etc.)
        district_id: ID of the district (if applicable)
        resource_type: Type of resource (if applicable)
        amount: Amount of resource (if applicable)
        
    Returns:
        tuple: (success, message)
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Record the action in the database
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO actions 
            (player_id, action_type, district_id, resource_type, amount, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (player_id, action_type, district_id, resource_type, amount, now)
        )
        
        # Handle specific action types
        if action_type == "collect":
            success, message = await handle_collect_action(cursor, player_id, district_id)
        elif action_type == "control":
            success, message = await handle_control_action(cursor, player_id, district_id, amount)
        elif action_type == "attack":
            success, message = await handle_attack_action(cursor, player_id, district_id, amount)
        elif action_type == "defend":
            success, message = await handle_defend_action(cursor, player_id, district_id, amount)
        elif action_type == "influence":
            success, message = await handle_influence_action(cursor, player_id, district_id, amount)
        else:
            success = False
            message = "Unknown action type."
        
        if success:
            conn.commit()
        else:
            conn.rollback()
            
        conn.close()
        return success, message
        
    except Exception as e:
        logger.error(f"Error processing action: {e}")
        return False, "An error occurred while processing your action."

async def handle_collect_action(cursor, player_id, district_id):
    """
    Handle resource collection from a district.
    
    Args:
        cursor: Database cursor
        player_id: ID of the player
        district_id: ID of the district
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if player has presence in the district
        cursor.execute(
            """
            SELECT control_points 
            FROM district_control
            WHERE player_id = ? AND district_id = ?
            """,
            (player_id, district_id)
        )
        
        control_result = cursor.fetchone()
        if not control_result or control_result[0] < 5:
            return False, "You need at least 5 control points in this district to collect resources."
        
        control_points = control_result[0]
        
        # Get district resource generation rates
        cursor.execute(
            """
            SELECT influence_resource, resources_resource, information_resource, force_resource
            FROM districts
            WHERE district_id = ?
            """,
            (district_id,)
        )
        
        district = cursor.fetchone()
        if not district:
            return False, "District not found."
        
        # Calculate resource amounts based on control (higher control = higher percentage)
        control_percentage = min(1.0, control_points / 100)
        influence_amount = round(district[0] * control_percentage)
        resources_amount = round(district[1] * control_percentage)
        information_amount = round(district[2] * control_percentage)
        force_amount = round(district[3] * control_percentage)
        
        # Add resources to player
        resources_added = 0
        for resource_type, amount in [
            ("influence", influence_amount),
            ("resources", resources_amount),
            ("information", information_amount),
            ("force", force_amount)
        ]:
            if amount > 0:
                cursor.execute(
                    """
                    INSERT INTO resources (player_id, resource_type, amount)
                    VALUES (?, ?, ?)
                    ON CONFLICT(player_id, resource_type) 
                    DO UPDATE SET amount = amount + ?
                    """,
                    (player_id, resource_type, amount, amount)
                )
                resources_added += 1
        
        if resources_added == 0:
            return False, "This district doesn't generate any resources."
        
        # Record last collection time
        now = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            UPDATE player_presence
            SET last_collected = ?
            WHERE player_id = ? AND district_id = ?
            """,
            (now, player_id, district_id)
        )
        
        # If no rows were updated, insert a new record
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO player_presence (player_id, district_id, last_collected)
                VALUES (?, ?, ?)
                """,
                (player_id, district_id, now)
            )
        
        return True, f"You've collected resources from this district based on your control level ({control_points}%)."
        
    except Exception as e:
        logger.error(f"Error handling collect action: {e}")
        return False, "An error occurred while collecting resources."

async def handle_control_action(cursor, player_id, district_id, amount):
    """
    Handle increasing control in a district.
    
    Args:
        cursor: Database cursor
        player_id: ID of the player
        district_id: ID of the district
        amount: Amount of influence to spend
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if player has enough influence
        cursor.execute(
            """
            SELECT amount 
            FROM resources 
            WHERE player_id = ? AND resource_type = 'influence'
            """,
            (player_id,)
        )
        
        resource = cursor.fetchone()
        if not resource or resource[0] < amount:
            return False, f"You don't have enough influence. You need {amount} but have {resource[0] if resource else 0}."
        
        # Reduce influence
        cursor.execute(
            """
            UPDATE resources
            SET amount = amount - ?
            WHERE player_id = ? AND resource_type = 'influence'
            """,
            (amount, player_id)
        )
        
        # Increase control points
        control_gain = amount  # 1 influence = 1 control point
        
        cursor.execute(
            """
            INSERT INTO district_control (player_id, district_id, control_points)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, district_id) 
            DO UPDATE SET control_points = control_points + ?
            """,
            (player_id, district_id, control_gain, control_gain)
        )
        
        # Get new control points
        cursor.execute(
            """
            SELECT control_points 
            FROM district_control
            WHERE player_id = ? AND district_id = ?
            """,
            (player_id, district_id)
        )
        
        new_control = cursor.fetchone()[0]
        
        return True, f"You've increased your control in this district by {control_gain} points. Your total control is now {new_control} points."
        
    except Exception as e:
        logger.error(f"Error handling control action: {e}")
        return False, "An error occurred while increasing district control."

async def handle_attack_action(cursor, player_id, district_id, amount):
    """
    Handle attacking another player's control in a district.
    
    Args:
        cursor: Database cursor
        player_id: ID of the player
        district_id: ID of the district
        amount: Amount of force to spend
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if player has enough force
        cursor.execute(
            """
            SELECT amount 
            FROM resources 
            WHERE player_id = ? AND resource_type = 'force'
            """,
            (player_id,)
        )
        
        resource = cursor.fetchone()
        if not resource or resource[0] < amount:
            return False, f"You don't have enough force. You need {amount} but have {resource[0] if resource else 0}."
        
        # Get top controller (that isn't the attacking player)
        cursor.execute(
            """
            SELECT player_id, control_points 
            FROM district_control
            WHERE district_id = ? AND player_id != ? AND control_points > 0
            ORDER BY control_points DESC
            LIMIT 1
            """,
            (district_id, player_id)
        )
        
        target = cursor.fetchone()
        if not target:
            return False, "There's no one to attack in this district."
        
        target_id, target_control = target
        
        # Check for defense bonuses
        cursor.execute(
            """
            SELECT defense_bonus 
            FROM district_defense
            WHERE district_id = ? AND player_id = ?
            """,
            (district_id, target_id)
        )
        
        defense_result = cursor.fetchone()
        defense_bonus = defense_result[0] if defense_result else 0
        
        # Calculate attack effectiveness
        effectiveness = random.uniform(0.7, 1.3)  # Random factor
        base_damage = amount
        final_damage = max(1, int(base_damage * effectiveness - defense_bonus))
        
        # Reduce control points of target
        cursor.execute(
            """
            UPDATE district_control
            SET control_points = MAX(0, control_points - ?)
            WHERE player_id = ? AND district_id = ?
            """,
            (final_damage, target_id, district_id)
        )
        
        # Spend force resource
        cursor.execute(
            """
            UPDATE resources
            SET amount = amount - ?
            WHERE player_id = ? AND resource_type = 'force'
            """,
            (amount, player_id)
        )
        
        # Get player names for message
        cursor.execute("SELECT username FROM players WHERE player_id = ?", (target_id,))
        target_name = cursor.fetchone()[0]
        
        # Add small amount of control to attacker
        control_gain = final_damage // 4  # Attacker gains a fraction of what they took
        if control_gain > 0:
            cursor.execute(
                """
                INSERT INTO district_control (player_id, district_id, control_points)
                VALUES (?, ?, ?)
                ON CONFLICT(player_id, district_id) 
                DO UPDATE SET control_points = control_points + ?
                """,
                (player_id, district_id, control_gain, control_gain)
            )
        
        return True, f"You attacked {target_name}'s control in this district, reducing it by {final_damage} points. You gained {control_gain} control points."
        
    except Exception as e:
        logger.error(f"Error handling attack action: {e}")
        return False, "An error occurred while attacking."

async def handle_defend_action(cursor, player_id, district_id, amount):
    """
    Handle setting up defenses in a district.
    
    Args:
        cursor: Database cursor
        player_id: ID of the player
        district_id: ID of the district
        amount: Amount of resources to spend
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if player has enough resources
        cursor.execute(
            """
            SELECT amount 
            FROM resources 
            WHERE player_id = ? AND resource_type = 'resources'
            """,
            (player_id,)
        )
        
        resource = cursor.fetchone()
        if not resource or resource[0] < amount:
            return False, f"You don't have enough resources. You need {amount} but have {resource[0] if resource else 0}."
        
        # Check if player has control in the district
        cursor.execute(
            """
            SELECT control_points 
            FROM district_control
            WHERE player_id = ? AND district_id = ?
            """,
            (player_id, district_id)
        )
        
        control_result = cursor.fetchone()
        if not control_result or control_result[0] < 10:
            return False, "You need at least 10 control points in this district to set up defenses."
        
        # Calculate defense bonus - diminishing returns
        defense_bonus = min(10, amount // 10)  # Max 10 bonus from this action
        
        # Set expiry to 12 hours from now
        expires_at = (datetime.datetime.now() + timedelta(hours=12)).isoformat()
        
        # Add or update defense bonus
        cursor.execute(
            """
            INSERT OR REPLACE INTO district_defense
            (district_id, player_id, defense_bonus, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (district_id, player_id, defense_bonus, expires_at)
        )
        
        # Spend resources
        cursor.execute(
            """
            UPDATE resources
            SET amount = amount - ?
            WHERE player_id = ? AND resource_type = 'resources'
            """,
            (amount, player_id)
        )
        
        return True, f"You've set up defenses in this district, giving you a +{defense_bonus} defense bonus for the next 12 hours."
        
    except Exception as e:
        logger.error(f"Error handling defend action: {e}")
        return False, "An error occurred while setting up defenses."

async def handle_influence_action(cursor, player_id, district_id, amount):
    """
    Handle influencing politicians in a district.
    
    Args:
        cursor: Database cursor
        player_id: ID of the player
        district_id: ID of the district
        amount: Amount of influence to spend
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Check if player has enough influence
        cursor.execute(
            """
            SELECT amount 
            FROM resources 
            WHERE player_id = ? AND resource_type = 'influence'
            """,
            (player_id,)
        )
        
        resource = cursor.fetchone()
        if not resource or resource[0] < amount:
            return False, f"You don't have enough influence. You need {amount} but have {resource[0] if resource else 0}."
        
        # Get politicians in the district
        cursor.execute(
            """
            SELECT politician_id, name, influence
            FROM politicians
            WHERE district_id = ?
            """,
            (district_id,)
        )
        
        politicians = cursor.fetchall()
        if not politicians:
            return False, "There are no politicians to influence in this district."
        
        # Choose a random politician weighted by their influence
        total_influence = sum(pol[2] for pol in politicians)
        weights = [pol[2]/total_influence for pol in politicians]
        chosen_politician = random.choices(politicians, weights=weights, k=1)[0]
        politician_id, politician_name, _ = chosen_politician
        
        # Check current friendliness
        cursor.execute(
            """
            SELECT friendliness
            FROM politician_friendliness
            WHERE politician_id = ? AND player_id = ?
            """,
            (politician_id, player_id)
        )
        
        friendliness_result = cursor.fetchone()
        current_friendliness = friendliness_result[0] if friendliness_result else 0
        
        # Calculate friendliness increase (diminishing returns)
        if current_friendliness < 0:
            # Easier to go from negative to neutral
            friendliness_increase = amount // 5
        elif current_friendliness < 50:
            # Moderate difficulty
            friendliness_increase = amount // 10
        else:
            # Hard to increase high friendliness
            friendliness_increase = amount // 20
            
        new_friendliness = min(100, current_friendliness + friendliness_increase)
        
        # Update friendliness
        cursor.execute(
            """
            INSERT INTO politician_friendliness (politician_id, player_id, friendliness)
            VALUES (?, ?, ?)
            ON CONFLICT(politician_id, player_id) 
            DO UPDATE SET friendliness = ?
            """,
            (politician_id, player_id, new_friendliness, new_friendliness)
        )
        
        # Spend influence
        cursor.execute(
            """
            UPDATE resources
            SET amount = amount - ?
            WHERE player_id = ? AND resource_type = 'influence'
            """,
            (amount, player_id)
        )
        
        # Determine message based on friendliness level
        if new_friendliness < 0:
            relationship = "hostile"
        elif new_friendliness < 20:
            relationship = "unfriendly"
        elif new_friendliness < 50:
            relationship = "neutral"
        elif new_friendliness < 80:
            relationship = "friendly"
        else:
            relationship = "very friendly"
            
        return True, f"You've influenced {politician_name}, increasing their friendliness to {new_friendliness}/100. They are now {relationship} towards you."
        
    except Exception as e:
        logger.error(f"Error handling influence action: {e}")
        return False, "An error occurred while influencing politicians."

async def start_coordinated_action(player_id, district_id, action_type, description, min_participants, expires_in_hours):
    """
    Start a coordinated action that requires multiple players.
    
    Args:
        player_id: ID of the initiating player
        district_id: ID of the district
        action_type: Type of coordinated action
        description: Description of the action
        min_participants: Minimum number of participants required
        expires_in_hours: Hours until the action expires
        
    Returns:
        tuple: (success, message, action_id)
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if player has presence in district
        cursor.execute(
            """
            SELECT control_points 
            FROM district_control
            WHERE player_id = ? AND district_id = ?
            """,
            (player_id, district_id)
        )
        
        control_result = cursor.fetchone()
        if not control_result or control_result[0] < 10:
            conn.close()
            return False, "You need at least 10 control points in this district to initiate a coordinated action.", None
        
        # Set expiry time
        created_at = datetime.datetime.now().isoformat()
        expires_at = (datetime.datetime.now() + timedelta(hours=expires_in_hours)).isoformat()
        
        # Create the coordinated action
        cursor.execute(
            """
            INSERT INTO coordinated_actions
            (initiator_id, district_id, action_type, description, min_participants, created_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (player_id, district_id, action_type, description, min_participants, created_at, expires_at)
        )
        
        action_id = cursor.lastrowid
        
        # Add initiator as first participant
        cursor.execute(
            """
            INSERT INTO coordinated_action_participants
            (action_id, player_id, joined_at)
            VALUES (?, ?, ?)
            """,
            (action_id, player_id, created_at)
        )
        
        conn.commit()
        conn.close()
        
        return True, f"You've initiated a coordinated action in this district. It requires {min_participants} participants and will expire in {expires_in_hours} hours.", action_id
        
    except Exception as e:
        logger.error(f"Error starting coordinated action: {e}")
        return False, "An error occurred while initiating the coordinated action.", None

async def join_coordinated_action(player_id, action_id):
    """
    Join an existing coordinated action.
    
    Args:
        player_id: ID of the player joining
        action_id: ID of the coordinated action
        
    Returns:
        tuple: (success, message, is_complete)
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if action exists and is still pending
        cursor.execute(
            """
            SELECT district_id, min_participants, status, expires_at
            FROM coordinated_actions
            WHERE action_id = ?
            """,
            (action_id,)
        )
        
        action = cursor.fetchone()
        if not action:
            conn.close()
            return False, "This coordinated action does not exist.", False
            
        district_id, min_participants, status, expires_at = action
        
        if status != 'pending':
            conn.close()
            return False, f"This coordinated action is already {status}.", False
            
        if datetime.datetime.fromisoformat(expires_at) < datetime.datetime.now():
            cursor.execute("UPDATE coordinated_actions SET status = 'expired' WHERE action_id = ?", (action_id,))
            conn.commit()
            conn.close()
            return False, "This coordinated action has expired.", False
        
        # Check if player has presence in district
        cursor.execute(
            """
            SELECT control_points 
            FROM district_control
            WHERE player_id = ? AND district_id = ?
            """,
            (player_id, district_id)
        )
        
        control_result = cursor.fetchone()
        if not control_result or control_result[0] < 5:
            conn.close()
            return False, "You need at least 5 control points in this district to join the coordinated action.", False
        
        # Check if player is already a participant
        cursor.execute(
            """
            SELECT 1 FROM coordinated_action_participants
            WHERE action_id = ? AND player_id = ?
            """,
            (action_id, player_id)
        )
        
        if cursor.fetchone():
            conn.close()
            return False, "You are already participating in this coordinated action.", False
        
        # Add player as participant
        joined_at = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO coordinated_action_participants
            (action_id, player_id, joined_at)
            VALUES (?, ?, ?)
            """,
            (action_id, player_id, joined_at)
        )
        
        # Check if we've reached the minimum participants
        cursor.execute(
            """
            SELECT COUNT(*) FROM coordinated_action_participants
            WHERE action_id = ?
            """,
            (action_id,)
        )
        
        participant_count = cursor.fetchone()[0]
        is_complete = participant_count >= min_participants
        
        # If complete, update status
        if is_complete:
            cursor.execute(
                """
                UPDATE coordinated_actions
                SET status = 'complete', completed_at = ?
                WHERE action_id = ?
                """,
                (joined_at, action_id)
            )
        
        conn.commit()
        conn.close()
        
        if is_complete:
            return True, "You've joined the coordinated action. The minimum number of participants has been reached!", True
        else:
            remaining = min_participants - participant_count
            return True, f"You've joined the coordinated action. {remaining} more participant(s) needed.", False
        
    except Exception as e:
        logger.error(f"Error joining coordinated action: {e}")
        return False, "An error occurred while joining the coordinated action.", False

async def process_coordinated_action(action_id):
    """
    Process the effects of a completed coordinated action.
    
    Args:
        action_id: ID of the coordinated action
        
    Returns:
        tuple: (success, message)
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Get action details
        cursor.execute(
            """
            SELECT district_id, action_type, status
            FROM coordinated_actions
            WHERE action_id = ?
            """,
            (action_id,)
        )
        
        action = cursor.fetchone()
        if not action:
            conn.close()
            return False, "This coordinated action does not exist."
            
        district_id, action_type, status = action
        
        if status != 'complete':
            conn.close()
            return False, f"This coordinated action is not complete. Current status: {status}."
        
        # Get participants
        cursor.execute(
            """
            SELECT player_id FROM coordinated_action_participants
            WHERE action_id = ?
            """,
            (action_id,)
        )
        
        participants = [row[0] for row in cursor.fetchall()]
        
        # Get district name
        cursor.execute("SELECT name FROM districts WHERE district_id = ?", (district_id,))
        district_name = cursor.fetchone()[0]
        
        # Process based on action type
        if action_type == "rally":
            # Increase control for all participants
            control_gain = 10 * len(participants)  # More participants = more gain
            for player_id in participants:
                cursor.execute(
                    """
                    INSERT INTO district_control (player_id, district_id, control_points)
                    VALUES (?, ?, ?)
                    ON CONFLICT(player_id, district_id) 
                    DO UPDATE SET control_points = control_points + ?
                    """,
                    (player_id, district_id, control_gain, control_gain)
                )
            
            message = f"The rally in {district_name} was successful! All {len(participants)} participants gained {control_gain} control points."
            
        elif action_type == "protest":
            # Find top controller who is not a participant
            participant_list = ", ".join(["?"] * len(participants))
            cursor.execute(
                f"""
                SELECT player_id, control_points 
                FROM district_control
                WHERE district_id = ? AND player_id NOT IN ({participant_list}) AND control_points > 0
                ORDER BY control_points DESC
                LIMIT 1
                """,
                [district_id] + participants
            )
            
            target = cursor.fetchone()
            if target:
                target_id, target_control = target
                
                # Calculate damage based on participants
                damage = 15 * len(participants)
                
                # Reduce target's control
                cursor.execute(
                    """
                    UPDATE district_control
                    SET control_points = MAX(0, control_points - ?)
                    WHERE player_id = ? AND district_id = ?
                    """,
                    (damage, target_id, district_id)
                )
                
                # Get target name
                cursor.execute("SELECT username FROM players WHERE player_id = ?", (target_id,))
                target_name = cursor.fetchone()[0]
                
                message = f"The protest in {district_name} was successful! {target_name}'s control was reduced by {damage} points."
            else:
                message = f"The protest in {district_name} had no effect because there were no opposing players with control."
        
        elif action_type == "resource_boost":
            # Temporarily boost district resource production
            boost_amount = 5 * len(participants)
            
            cursor.execute(
                """
                UPDATE districts
                SET influence_resource = influence_resource + ?,
                    resources_resource = resources_resource + ?,
                    information_resource = information_resource + ?,
                    force_resource = force_resource + ?
                WHERE district_id = ?
                """,
                (boost_amount, boost_amount, boost_amount, boost_amount, district_id)
            )
            
            message = f"The coordinated effort in {district_name} has temporarily boosted resource production by {boost_amount} for all resources!"
            
        else:
            message = f"The coordinated action in {district_name} was completed, but its effects are not yet implemented."
        
        # Mark action as processed
        processed_at = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            UPDATE coordinated_actions
            SET status = 'processed', processed_at = ?
            WHERE action_id = ?
            """,
            (processed_at, action_id)
        )
        
        conn.commit()
        conn.close()
        
        return True, message
        
    except Exception as e:
        logger.error(f"Error processing coordinated action: {e}")
        return False, "An error occurred while processing the coordinated action."

# Game cycle functions
def get_current_cycle():
    """
    Get the current game cycle (morning or evening).
    
    Returns:
        str: "morning" or "evening"
    """
    hour = datetime.datetime.now().hour
    return "morning" if 6 <= hour < 18 else "evening"

def get_cycle_deadline():
    """
    Get the deadline for the current cycle.
    
    Returns:
        datetime: Deadline time
    """
    now = datetime.datetime.now()
    if get_current_cycle() == "morning":
        # Morning cycle ends at 18:00
        return now.replace(hour=18, minute=0, second=0, microsecond=0)
    else:
        # Evening cycle ends at 06:00 the next day
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=6, minute=0, second=0, microsecond=0)

def get_cycle_results_time():
    """
    Get the time when results for the current cycle will be processed.
    
    Returns:
        datetime: Results processing time
    """
    deadline = get_cycle_deadline()
    # Process results 5 minutes after deadline
    return deadline + timedelta(minutes=5)

async def process_game_cycle(context: ContextTypes.DEFAULT_TYPE = None):
    """
    Process the end of a game cycle and calculate results.
    This function is called by the scheduler when a cycle ends.
    
    Args:
        context: Bot context (optional)
        
    Returns:
        bool: Success flag
    """
    try:
        logger.info(f"Processing game cycle: {get_current_cycle()}")
        
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Reset player action counts for the new cycle
        cursor.execute(
            """
            UPDATE players
            SET actions_remaining = 3
            """
        )
        
        # Process district control changes
        process_district_control_changes(cursor)
        
        # Process pending attacks and defenses
        process_attack_defense_resolution(cursor)
        
        # Generate news about significant events
        generate_cycle_news(cursor)
        
        conn.commit()
        conn.close()
        
        logger.info("Game cycle processing completed")
        return True
        
    except Exception as e:
        logger.error(f"Error processing game cycle: {e}")
        return False

def process_district_control_changes(cursor):
    """Process changes in district control"""
    try:
        # For each district, calculate control point decay
        cursor.execute("SELECT district_id FROM districts")
        districts = cursor.fetchall()
        
        for district in districts:
            district_id = district[0]
            
            # Apply 5% decay to control points for inactive players
            cursor.execute(
                """
                UPDATE district_control
                SET control_points = MAX(0, ROUND(control_points * 0.95))
                WHERE district_id = ? AND player_id NOT IN (
                    SELECT player_id FROM actions 
                    WHERE district_id = ? 
                    AND timestamp > datetime('now', '-1 day')
                )
                """,
                (district_id, district_id)
            )
    except Exception as e:
        logger.error(f"Error processing district control changes: {e}")

def process_attack_defense_resolution(cursor):
    """Process attack and defense actions"""
    try:
        # Get all pending attacks from this cycle
        cycle_start = datetime.datetime.now() - timedelta(hours=12)
        cursor.execute(
            """
            SELECT district_id, 
                   SUM(CASE WHEN action_type = ? THEN amount ELSE 0 END) as total_attack,
                   SUM(CASE WHEN action_type = ? THEN amount ELSE 0 END) as total_defense
            FROM actions
            WHERE (action_type = ? OR action_type = ?) 
            AND timestamp > ?
            GROUP BY district_id
            """,
            (ACTION_ATTACK, ACTION_DEFENSE, ACTION_ATTACK, ACTION_DEFENSE, cycle_start.isoformat())
        )
        
        results = cursor.fetchall()
        
        for district_id, total_attack, total_defense in results:
            # Skip if no meaningful attack
            if total_attack <= 0:
                continue
                
            # Calculate net attack (after defense)
            net_attack = max(0, total_attack - total_defense)
            
            if net_attack > 0:
                # Apply damage to all players' control in the district based on their current control
                cursor.execute(
                    """
                    SELECT player_id, control_points
                    FROM district_control
                    WHERE district_id = ? AND control_points > 0
                    """,
                    (district_id,)
                )
                
                players = cursor.fetchall()
                total_control = sum(control for _, control in players)
                
                for player_id, control_points in players:
                    if total_control > 0:
                        # Distribute damage proportionally to current control
                        damage_share = (control_points / total_control) * net_attack
                        new_control = max(0, control_points - round(damage_share))
                        
                        cursor.execute(
                            """
                            UPDATE district_control
                            SET control_points = ?
                            WHERE player_id = ? AND district_id = ?
                            """,
                            (new_control, player_id, district_id)
                        )
    except Exception as e:
        logger.error(f"Error processing attack/defense resolution: {e}")

def generate_cycle_news(cursor):
    """Generate news for the cycle"""
    try:
        # Add cycle change news
        cycle = get_current_cycle()
        news_text = f"Cycle changed to {cycle.upper()}"
        
        cursor.execute(
            """
            INSERT INTO news (news_text, importance, timestamp)
            VALUES (?, ?, ?)
            """,
            (news_text, 1, datetime.datetime.now().isoformat())
        )
        
        # Add news about significant control changes
        cursor.execute(
            """
            SELECT dc.player_id, p.name, d.name, dc.control_points
            FROM district_control dc
            JOIN players p ON dc.player_id = p.player_id
            JOIN districts d ON dc.district_id = d.district_id
            WHERE dc.control_points >= 50
            """
        )
        
        significant_control = cursor.fetchall()
        
        for player_id, player_name, district_name, control_points in significant_control:
            if control_points >= 80:
                news_text = f"{player_name} has established strong control ({control_points}%) over {district_name}!"
                importance = 3
            elif control_points >= 50:
                news_text = f"{player_name} has gained majority control ({control_points}%) in {district_name}."
                importance = 2
            else:
                continue
                
            cursor.execute(
                """
                INSERT INTO news (news_text, importance, timestamp)
                VALUES (?, ?, ?)
                """,
                (news_text, importance, datetime.datetime.now().isoformat())
            )
    except Exception as e:
        logger.error(f"Error generating cycle news: {e}")

def register_player_presence(player_id, district_id):
    """
    Register player presence in a district.
    
    Args:
        player_id: ID of the player
        district_id: ID of the district
        
    Returns:
        bool: Success flag
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        now = datetime.datetime.now().isoformat()
        
        # Update presence or insert if not exists
        cursor.execute(
            """
            INSERT INTO player_presence (player_id, district_id, last_presence)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, district_id) 
            DO UPDATE SET last_presence = ?
            """,
            (player_id, district_id, now, now)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error registering player presence: {e}")
        return False

def get_player_presence_status(player_id):
    """
    Get the district where the player is currently present.
    
    Args:
        player_id: ID of the player
        
    Returns:
        dict or None: District info or None if not present
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Get most recent presence
        cursor.execute(
            """
            SELECT pp.district_id, d.name, pp.last_presence
            FROM player_presence pp
            JOIN districts d ON pp.district_id = d.district_id
            WHERE pp.player_id = ?
            ORDER BY pp.last_presence DESC
            LIMIT 1
            """,
            (player_id,)
        )
        
        presence = cursor.fetchone()
        conn.close()
        
        if not presence:
            return None
            
        # Check if presence is recent (within last 2 hours)
        last_presence = datetime.datetime.fromisoformat(presence[2])
        if (datetime.datetime.now() - last_presence).total_seconds() > 7200:  # 2 hours
            return None
            
        return {
            "district_id": presence[0],
            "district_name": presence[1],
            "last_presence": last_presence
        }
    except Exception as e:
        logger.error(f"Error getting player presence: {e}")
        return None

def calculate_participant_power(player_id, resource_commitments):
    """
    Calculate the power a participant contributes to a coordinated action.
    
    Args:
        player_id (str): The ID of the player
        resource_commitments (dict): Dictionary mapping resource types to amounts
        
    Returns:
        int: The calculated power value
    """
    try:
        # Basic power calculation: sum of all resources with different weights
        influence_power = resource_commitments.get('influence', 0) * 1.5
        resources_power = resource_commitments.get('resources', 0) * 1.0
        information_power = resource_commitments.get('information', 0) * 2.0
        force_power = resource_commitments.get('force', 0) * 2.5
        
        # Add bonus for balanced contribution
        resource_types_used = sum(1 for amount in resource_commitments.values() if amount > 0)
        balance_bonus = resource_types_used * 0.1  # 10% bonus per resource type used
        
        # Calculate base power
        base_power = influence_power + resources_power + information_power + force_power
        
        # Apply balance bonus
        total_power = base_power * (1 + balance_bonus)
        
        # Round to integer
        return round(total_power)
    except Exception as e:
        logger.error(f"Error calculating participant power: {e}")
        return 0

async def process_join_with_resources(player_id, action_id, resources_dict):
    """
    Process a player joining a coordinated action with specific resources.
    
    Args:
        player_id (int): The ID of the player joining the action
        action_id (int): The ID of the coordinated action to join
        resources_dict (dict): A dictionary of resources to use {resource_type: amount}
    
    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    try:
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if action exists and is open
        cursor.execute(
            """
            SELECT action_id, status, target_type, target_id, action_type, initiator_id
            FROM coordinated_actions
            WHERE action_id = ?
            """,
            (action_id,)
        )
        
        action = cursor.fetchone()
        if not action:
            conn.close()
            return False, "Action not found"
        
        _, status, target_type, target_id, action_type, initiator_id = action
        
        if status != 'open':
            conn.close()
            return False, f"Action is {status}, cannot join"
        
        # Check if player is already participating
        cursor.execute(
            """
            SELECT player_id
            FROM coordinated_action_participants
            WHERE action_id = ? AND player_id = ?
            """,
            (action_id, player_id)
        )
        
        if cursor.fetchone():
            conn.close()
            return False, "Already participating in this action"
        
        # Check if the player has resources
        player_resources = {}
        cursor.execute(
            """
            SELECT resource_type, amount 
            FROM resources 
            WHERE player_id = ?
            """, 
            (player_id,)
        )
        
        for row in cursor.fetchall():
            resource_type, amount = row
            player_resources[resource_type] = amount
        
        # Check if player has enough of each resource
        for resource_type, amount in resources_dict.items():
            if player_resources.get(resource_type, 0) < amount:
                conn.close()
                return False, f"Not enough {resource_type}"
        
        # Convert resources_dict to JSON for storage
        resources_json = json.dumps(resources_dict)
        
        # Use a main action
        cursor.execute(
            """
            UPDATE players 
            SET main_actions_left = main_actions_left - 1 
            WHERE player_id = ? AND main_actions_left > 0
            """, 
            (player_id,)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "No main actions left"
        
        # Deduct resources
        for resource_type, amount in resources_dict.items():
            cursor.execute(
                """
                UPDATE resources
                SET amount = amount - ?
                WHERE player_id = ? AND resource_type = ?
                """,
                (amount, player_id, resource_type)
            )
        
        # Add player to participants
        joined_at = datetime.datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO coordinated_action_participants
            (action_id, player_id, resources_used, joined_at)
            VALUES (?, ?, ?, ?)
            """,
            (action_id, player_id, resources_json, joined_at)
        )
        
        # Check if this action has enough participants to complete
        # For now, let's assume 2 participants (initiator + 1) is enough
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM coordinated_action_participants
            WHERE action_id = ?
            """,
            (action_id,)
        )
        
        participant_count = cursor.fetchone()[0]
        
        if participant_count >= 2:
            # Set action to complete
            cursor.execute(
                """
                UPDATE coordinated_actions
                SET status = 'complete'
                WHERE action_id = ?
                """,
                (action_id,)
            )
        
        conn.commit()
        
        # Get target name for the message
        target_name = str(target_id)
        if target_type == "district":
            cursor.execute("SELECT name FROM districts WHERE district_id = ?", (target_id,))
            district = cursor.fetchone()
            if district:
                target_name = district[0]
        elif target_type == "politician":
            cursor.execute("SELECT name FROM politicians WHERE politician_id = ?", (target_id,))
            politician = cursor.fetchone()
            if politician:
                target_name = politician[0]
        
        conn.close()
        
        # Check if the action is now complete
        if participant_count >= 2:
            return True, f"Joined and completed the {action_type} action on {target_name}"
        else:
            return True, f"Joined the {action_type} action on {target_name}"
    
    except Exception as e:
        logger.error(f"Error joining coordinated action: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False, "An error occurred while joining the action"
