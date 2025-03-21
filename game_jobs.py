import logging
import datetime
import sqlite3
import json
from telegram.ext import ContextTypes
from db.queries import db_transaction
from db.utils import get_db_connection
from languages import get_text
from config import DB_PATH

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_next_cycle_time(is_morning=True):
    """Calculate the next time for a morning (8:00) or evening (20:00) cycle."""
    now = datetime.datetime.now()
    target_hour = 8 if is_morning else 20
    
    # Create a datetime for today at the target hour
    target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    
    # If that time has already passed today, move to tomorrow
    if now >= target_time:
        target_time += datetime.timedelta(days=1)
    
    # Calculate seconds until that time
    time_diff = (target_time - now).total_seconds()
    return time_diff

async def morning_cycle(context: ContextTypes.DEFAULT_TYPE):
    """Run the morning cycle tasks: distributing resources, resetting actions."""
    try:
        logging.info("Starting morning cycle...")
        
        # Notify users
        await send_cycle_notification(context, is_morning=True)
        
        # Reset player operations
        reset_player_operations()
        
        # Distribute resources
        distribute_resources()
        
        # Create news about the cycle
        create_cycle_news(is_morning=True)
        
        logging.info("Morning cycle completed successfully")
    except Exception as e:
        logging.error(f"Error during morning cycle: {e}")

async def evening_cycle(context: ContextTypes.DEFAULT_TYPE):
    """Run the evening cycle tasks: distributing resources, resetting actions."""
    try:
        logging.info("Starting evening cycle...")
        
        # Notify users
        await send_cycle_notification(context, is_morning=False)
        
        # Reset player operations
        reset_player_operations()
        
        # Distribute resources
        distribute_resources()
        
        # Create news about the cycle
        create_cycle_news(is_morning=False)
        
        logging.info("Evening cycle completed successfully")
    except Exception as e:
        logging.error(f"Error during evening cycle: {e}")

async def cleanup_expired_actions(context: ContextTypes.DEFAULT_TYPE):
    """Clean up expired coordinated actions."""
    try:
        logging.info("Cleaning up expired coordinated actions...")
        
        # Get current time
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Connect to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get expired actions
            cursor.execute(
                "SELECT id, initiator_id FROM coordinated_actions WHERE expires_at < ?", 
                (now,)
            )
            expired_actions = cursor.fetchall()
            
            if expired_actions:
                # Delete expired actions
                action_ids = [action[0] for action in expired_actions]
                action_ids_str = ','.join(['?'] * len(action_ids))
                cursor.execute(
                    f"DELETE FROM coordinated_actions WHERE id IN ({action_ids_str})",
                    action_ids
                )
                
                # Log the cleanup
                logging.info(f"Cleaned up {len(expired_actions)} expired coordinated actions")
                
                # Notify initiators
                for action_id, initiator_id in expired_actions:
                    try:
                        # Get player language
                        cursor.execute("SELECT lang FROM players WHERE id = ?", (initiator_id,))
                        result = cursor.fetchone()
                        if result:
                            lang = result[0]
                            # Send notification
                            await context.bot.send_message(
                                chat_id=initiator_id,
                                text=get_text('action_expired', lang, default="Your coordinated action has expired.")
                            )
                    except Exception as e:
                        logging.error(f"Failed to notify player {initiator_id} about expired action: {e}")
            else:
                logging.info("No expired coordinated actions found")
                
        conn.commit()
    except Exception as e:
        logging.error(f"Error during cleanup of expired actions: {e}")

async def update_district_defenses(context: ContextTypes.DEFAULT_TYPE):
    """Update district defense levels based on recent activity."""
    try:
        logging.info("Updating district defense levels...")
        
        # Connect to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all districts
            cursor.execute("SELECT id FROM districts")
            districts = cursor.fetchall()
            
            for district_id in [d[0] for d in districts]:
                # Check if district has defense entry
                cursor.execute(
                    "SELECT defense_level FROM district_defense WHERE district_id = ?", 
                    (district_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    # District has defense entry, update it
                    current_level = result[0]
                    # Natural decay of defense levels over time (reduce by 5%)
                    new_level = max(0, int(current_level * 0.95))
                    cursor.execute(
                        "UPDATE district_defense SET defense_level = ?, last_updated = CURRENT_TIMESTAMP WHERE district_id = ?",
                        (new_level, district_id)
                    )
                else:
                    # District doesn't have defense entry, create it
                    cursor.execute(
                        "INSERT INTO district_defense (district_id, defense_level) VALUES (?, 0)",
                        (district_id,)
                    )
            
            conn.commit()
            logging.info("District defense levels updated")
    except Exception as e:
        logging.error(f"Error updating district defense levels: {e}")

@db_transaction
def reset_player_operations(cursor):
    """Reset the operations_left counter for all players."""
    cursor.execute("UPDATE players SET operations_left = 3")
    logging.info("Reset operations for all players")

@db_transaction
def distribute_resources(cursor):
    """Distribute resources to players based on district control."""
    # Get all players
    cursor.execute("SELECT id FROM players")
    players = cursor.fetchall()
    
    for player_id in [p[0] for p in players]:
        # Count controlled districts
        cursor.execute("SELECT COUNT(*) FROM districts WHERE controller_id = ?", (player_id,))
        district_count = cursor.fetchone()[0]
        
        # Base resource amount
        base_amount = 10
        
        # Calculate resource amounts based on district control
        # More districts = more resources
        influence = base_amount + (district_count * 5)
        surveillance = base_amount + (district_count * 4)
        force = base_amount + (district_count * 3)
        wealth = base_amount + (district_count * 6)
        
        # Update player resources
        cursor.execute(
            """
            UPDATE players 
            SET influence = influence + ?, 
                surveillance = surveillance + ?, 
                force = force + ?, 
                wealth = wealth + ?
            WHERE id = ?
            """, 
            (influence, surveillance, force, wealth, player_id)
        )
        
        logging.info(f"Distributed resources to player {player_id}: I:{influence} S:{surveillance} F:{force} W:{wealth}")

@db_transaction
def create_cycle_news(cursor, is_morning=True):
    """Create a news entry for the game cycle."""
    cycle_type = "Morning" if is_morning else "Evening"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create news entry
    cursor.execute(
        """
        INSERT INTO news (timestamp, title, content) 
        VALUES (?, ?, ?)
        """,
        (
            timestamp, 
            f"{cycle_type} Cycle", 
            f"The {cycle_type.lower()} cycle has begun. All players have received resources and operations have been reset."
        )
    )
    
    logging.info(f"Created news entry for {cycle_type.lower()} cycle")

async def send_cycle_notification(context: ContextTypes.DEFAULT_TYPE, is_morning=True):
    """Send notifications to all players about the new cycle."""
    try:
        # Connect to database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all players
            cursor.execute("SELECT id, lang FROM players")
            players = cursor.fetchall()
            
            cycle_type = "morning" if is_morning else "evening"
            
            # Send notifications
            for player_id, lang in players:
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=get_text(
                            f'cycle_{cycle_type}', 
                            lang, 
                            default=f"A new {cycle_type} cycle has begun! Your resources have been replenished and operations reset."
                        )
                    )
                except Exception as e:
                    logging.error(f"Failed to send cycle notification to player {player_id}: {e}")
    except Exception as e:
        logging.error(f"Error sending cycle notifications: {e}") 