#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Meta Game - Scheduled Jobs Module
Handles all scheduled jobs and periodic tasks for the game
"""

import logging
import random
import sqlite3
import datetime
from telegram.ext import ContextTypes
from game.districts import update_district_defenses

logger = logging.getLogger(__name__)

async def distribute_resources(context: ContextTypes.DEFAULT_TYPE):
    """
    Scheduled job to distribute resources to players based on district control.
    
    Args:
        context: The context passed by the job queue
    """
    try:
        logger.info("Distributing resources to players...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Get all players
        cursor.execute("SELECT player_id FROM players")
        players = cursor.fetchall()
        
        for player_id in [p[0] for p in players]:
            # Get all districts where player has control
            cursor.execute(
                """
                SELECT d.district_id, d.name, dc.control_points,
                       d.influence_resource, d.resources_resource, d.information_resource, d.force_resource
                FROM district_control dc
                JOIN districts d ON dc.district_id = d.district_id
                WHERE dc.player_id = ? AND dc.control_points >= 10
                """,
                (player_id,)
            )
            
            controlled_districts = cursor.fetchall()
            
            if not controlled_districts:
                logger.info(f"Player {player_id} has no districts with sufficient control")
                continue
                
            # Calculate resources from all controlled districts
            total_influence = 0
            total_resources = 0
            total_information = 0
            total_force = 0
            
            for district in controlled_districts:
                _, _, control_points, influence, resources, information, force = district
                
                # Calculate percentage of control (max 100%)
                control_percentage = min(1.0, control_points / 100)
                
                # Add resources based on control percentage
                total_influence += round(influence * control_percentage)
                total_resources += round(resources * control_percentage)
                total_information += round(information * control_percentage)
                total_force += round(force * control_percentage)
            
            # Update player resources
            if total_influence > 0:
                cursor.execute(
                    """
                    INSERT INTO resources (player_id, resource_type, amount)
                    VALUES (?, 'influence', ?)
                    ON CONFLICT(player_id, resource_type) 
                    DO UPDATE SET amount = amount + ?
                    """,
                    (player_id, total_influence, total_influence)
                )
                
            if total_resources > 0:
                cursor.execute(
                    """
                    INSERT INTO resources (player_id, resource_type, amount)
                    VALUES (?, 'resources', ?)
                    ON CONFLICT(player_id, resource_type) 
                    DO UPDATE SET amount = amount + ?
                    """,
                    (player_id, total_resources, total_resources)
                )
                
            if total_information > 0:
                cursor.execute(
                    """
                    INSERT INTO resources (player_id, resource_type, amount)
                    VALUES (?, 'information', ?)
                    ON CONFLICT(player_id, resource_type) 
                    DO UPDATE SET amount = amount + ?
                    """,
                    (player_id, total_information, total_information)
                )
                
            if total_force > 0:
                cursor.execute(
                    """
                    INSERT INTO resources (player_id, resource_type, amount)
                    VALUES (?, 'force', ?)
                    ON CONFLICT(player_id, resource_type) 
                    DO UPDATE SET amount = amount + ?
                    """,
                    (player_id, total_force, total_force)
                )
            
            # Log the distribution
            logger.info(f"Distributed resources to player {player_id}: I:{total_influence} R:{total_resources} F:{total_information} P:{total_force}")
            
            # Notify player if enabled
            if context and hasattr(context, 'bot'):
                try:
                    # Check if player has notification preferences and has enabled resource notifications
                    cursor.execute(
                        """
                        SELECT username FROM players WHERE player_id = ?
                        """,
                        (player_id,)
                    )
                    player_result = cursor.fetchone()
                    if player_result:
                        district_names = ', '.join([d[1] for d in controlled_districts])
                        message = f"You've received resources from your controlled districts ({district_names}):\n"
                        message += f"• Influence: +{total_influence}\n"
                        message += f"• Resources: +{total_resources}\n"
                        message += f"• Information: +{total_information}\n"
                        message += f"• Force: +{total_force}"
                        
                        await context.bot.send_message(
                            chat_id=player_id,
                            text=message
                        )
                except Exception as e:
                    logger.error(f"Failed to send resource notification to player {player_id}: {e}")
        
        conn.commit()
        conn.close()
        logger.info("Resource distribution complete")
        
    except Exception as e:
        logger.error(f"Error distributing resources: {e}")

async def process_completed_actions(context: ContextTypes.DEFAULT_TYPE):
    """
    Process all completed coordinated actions.
    
    Args:
        context: The context passed by the job queue
    """
    try:
        logger.info("Processing completed coordinated actions...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if processed_at column exists in coordinated_actions table
        try:
            cursor.execute(
                """
                SELECT action_id
                FROM coordinated_actions
                WHERE status = 'complete' AND processed_at IS NULL
                """
            )
            
            actions = cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "no such column: processed_at" in str(e):
                # Column doesn't exist yet, the migration hasn't run
                # Add the column if it doesn't exist
                logger.info("Adding processed_at column to coordinated_actions table...")
                try:
                    cursor.execute("ALTER TABLE coordinated_actions ADD COLUMN processed_at TEXT")
                    conn.commit()
                    logger.info("Added processed_at column")
                    
                    # Now try to fetch completed actions again
                    cursor.execute(
                        """
                        SELECT action_id
                        FROM coordinated_actions
                        WHERE status = 'complete'
                        """
                    )
                    
                    actions = cursor.fetchall()
                except Exception as add_col_err:
                    logger.error(f"Error adding processed_at column: {add_col_err}")
                    conn.close()
                    return
            else:
                # Some other SQLite error occurred
                raise
        
        conn.close()
        
        from game.actions import process_coordinated_action
        
        for action_id, in actions:
            logger.info(f"Processing coordinated action {action_id}")
            success, message = await process_coordinated_action(action_id)
            
            if success and context and hasattr(context, 'bot'):
                try:
                    # Notify participants
                    conn = sqlite3.connect('novi_sad_game.db')
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        """
                        SELECT p.player_id 
                        FROM coordinated_action_participants p
                        WHERE p.action_id = ?
                        """,
                        (action_id,)
                    )
                    
                    participants = cursor.fetchall()
                    conn.close()
                    
                    for player_id, in participants:
                        await context.bot.send_message(
                            chat_id=player_id,
                            text=message
                        )
                except Exception as e:
                    logger.error(f"Error notifying participants for action {action_id}: {e}")
            
            if not success:
                logger.error(f"Failed to process coordinated action {action_id}: {message}")
    except Exception as e:
        logger.error(f"Error processing completed actions: {e}")

async def cleanup_expired_actions(context: ContextTypes.DEFAULT_TYPE):
    """
    Clean up expired coordinated actions.
    
    Args:
        context: The context passed by the job queue
    """
    try:
        logger.info("Cleaning up expired coordinated actions...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        now = datetime.datetime.now().isoformat()
        
        # Find expired actions still in pending status
        cursor.execute(
            """
            SELECT action_id, initiator_id, district_id, action_type
            FROM coordinated_actions
            WHERE status = 'pending' AND expires_at < ?
            """,
            (now,)
        )
        
        expired_actions = cursor.fetchall()
        
        # Update status to expired
        cursor.execute(
            """
            UPDATE coordinated_actions
            SET status = 'expired'
            WHERE status = 'pending' AND expires_at < ?
            """,
            (now,)
        )
        
        conn.commit()
        conn.close()
        
        # Notify initiators if applicable
        if context and hasattr(context, 'bot'):
            for action_id, initiator_id, district_id, action_type in expired_actions:
                try:
                    conn = sqlite3.connect('novi_sad_game.db')
                    cursor = conn.cursor()
                    
                    # Get district name
                    cursor.execute("SELECT name FROM districts WHERE district_id = ?", (district_id,))
                    district_name = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    message = f"Your coordinated action ({action_type}) in {district_name} has expired without reaching the minimum number of participants."
                    
                    await context.bot.send_message(
                        chat_id=initiator_id,
                        text=message
                    )
                except Exception as e:
                    logger.error(f"Error notifying initiator {initiator_id} about expired action {action_id}: {e}")
        
        logger.info(f"Cleaned up {len(expired_actions)} expired coordinated actions")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired actions: {e}")

async def generate_news(context: ContextTypes.DEFAULT_TYPE):
    """
    Generate news items about game events.
    
    Args:
        context: The context passed by the job queue
    """
    try:
        logger.info("Generating news items...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Get top districts by activity
        cursor.execute(
            """
            SELECT d.district_id, d.name, COUNT(a.action_id) as activity
            FROM districts d
            LEFT JOIN actions a ON d.district_id = a.district_id AND a.timestamp > datetime('now', '-24 hours')
            GROUP BY d.district_id
            ORDER BY activity DESC
            LIMIT 3
            """
        )
        
        active_districts = cursor.fetchall()
        
        # Generate news based on district activity
        news_items = []
        for district_id, district_name, activity in active_districts:
            if activity > 5:
                news_items.append((
                    f"Unrest in {district_name}",
                    f"Reports indicate increased political activity in {district_name} as various factions vie for control. Local residents express concern about the growing tensions.",
                    district_id
                ))
            elif activity > 0:
                news_items.append((
                    f"Strategic Movements in {district_name}",
                    f"Political operatives have been observed making moves in {district_name}. Analysts suggest this could be the beginning of a larger power play.",
                    district_id
                ))
        
        # Get districts with recent control changes
        cursor.execute(
            """
            SELECT d.district_id, d.name, p.username, dc.control_points
            FROM district_control dc
            JOIN districts d ON dc.district_id = d.district_id
            JOIN players p ON dc.player_id = p.player_id
            WHERE dc.control_points >= 60
            ORDER BY dc.control_points DESC
            LIMIT 2
            """
        )
        
        controlled_districts = cursor.fetchall()
        
        # Generate news about district control
        for district_id, district_name, player_name, control in controlled_districts:
            news_items.append((
                f"{player_name} Strengthens Grip on {district_name}",
                f"{player_name} now maintains firm control over {district_name} with {control} control points. Local officials appear to be following their directives.",
                district_id
            ))
        
        # Insert news items
        now = datetime.datetime.now().isoformat()
        for title, content, district_id in news_items:
            cursor.execute(
                """
                INSERT INTO news (title, content, timestamp, is_public)
                VALUES (?, ?, ?, 1)
                """,
                (title, content, now)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Generated {len(news_items)} news items")
        
    except Exception as e:
        logger.error(f"Error generating news: {e}")

def schedule_jobs(job_queue):
    """
    Schedule all recurring jobs.
    
    Args:
        job_queue: The job queue to schedule jobs on
    """
    # Resource distribution - every 12 hours
    job_queue.run_repeating(distribute_resources, interval=43200, first=300)
    
    # Update district defenses - daily
    job_queue.run_repeating(update_district_defenses, interval=86400, first=300)
    
    # Process completed coordinated actions - every hour
    job_queue.run_repeating(process_completed_actions, interval=3600, first=600)
    
    # Clean up expired actions - every 3 hours
    job_queue.run_repeating(cleanup_expired_actions, interval=10800, first=900)
    
    # Generate news - every 6 hours
    job_queue.run_repeating(generate_news, interval=21600, first=1200)
    
    logger.info("All game jobs scheduled") 