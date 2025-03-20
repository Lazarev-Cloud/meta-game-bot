import sqlite3
import datetime
import logging

logger = logging.getLogger(__name__)


def create_cycle_summary(cycle_number: int):
    """Create a summary news entry for the cycle with error handling"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cycle_start = cycle_number * 3
        cycle_end = cycle_start + 3

        try:
            # Ensure created_at column exists
            cursor.execute("SELECT created_at FROM news LIMIT 1")
        except sqlite3.OperationalError:
            # Add the column if it doesn't exist
            cursor.execute("""
                ALTER TABLE news 
                ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            """)

        # Get all actions in this cycle
        cursor.execute("""
            SELECT 
                action_type,
                target_type,
                target_id,
                COUNT(*) as action_count
            FROM actions 
            WHERE cycle = ? AND status = 'completed'
            GROUP BY action_type, target_type, target_id
        """, (cycle_number,))

        actions_summary = cursor.fetchall()

        # Get district control changes
        cursor.execute("""
            SELECT 
                district_id,
                player_id,
                control_points_change
            FROM district_control_history
            WHERE cycle = ?
            ORDER BY control_points_change DESC
            LIMIT 5
        """, (cycle_number,))

        control_changes = cursor.fetchall()

        # Create summary content
        summary = f"Итоги цикла {cycle_start}:00-{cycle_end}:00\n\n"

        if actions_summary:
            summary += "🎯 Основные действия:\n"
            for action in actions_summary:
                action_type, target_type, target_id, count = action
                summary += f"- {action_type} в {target_id}: {count} раз\n"

        if control_changes:
            summary += "\n🏛 Значимые изменения контроля:\n"
            for change in control_changes:
                district_id, player_id, points = change
                summary += f"- Район {district_id}: {points:+d} очков\n"

        # Add to news with current timestamp
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO news (title, content, created_at, timestamp, is_public)
            VALUES (?, ?, ?, ?, 1)
        """, (
            f"Итоги цикла {cycle_start}:00-{cycle_end}:00",
            summary,
            now,
            now
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        logger.error(f"Error creating cycle summary: {e}")
        # Log the full traceback for debugging
        import traceback
        logger.error(traceback.format_exc())
