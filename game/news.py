import sqlite3
import datetime
import logging
from typing import List, Optional, Dict, Any
from db.queries import db_connection_pool, db_transaction
from languages import get_text

logger = logging.getLogger(__name__)


@db_transaction
def create_cycle_summary(cycle_number: int):
    """Create a summary news entry for the cycle with error handling"""
    try:
        with db_connection_pool.get_connection() as conn:
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

    except Exception as e:
        logger.error(f"Error creating cycle summary: {e}")
        # Log the full traceback for debugging
        import traceback
        logger.error(traceback.format_exc())

@db_transaction
def get_latest_news(limit: int = 10) -> List[Dict[str, Any]]:
    """Get the latest news items."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT news_id, title, content, timestamp
                FROM news
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            news_items = []
            for row in cursor.fetchall():
                news_items.append({
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'timestamp': row[3]
                })
            return news_items
    except Exception as e:
        logger.error(f"Error getting latest news: {e}")
        return []

@db_transaction
def get_news_by_id(news_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific news item by ID."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT news_id, title, content, timestamp
                FROM news
                WHERE news_id = ?
            """, (news_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'timestamp': row[3]
            }
    except Exception as e:
        logger.error(f"Error getting news by ID: {e}")
        return None

@db_transaction
def add_news_item(title: str, content: str) -> bool:
    """Add a new news item."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO news (title, content, timestamp)
                VALUES (?, ?, ?)
            """, (title, content, datetime.datetime.now().isoformat()))
            return True
    except Exception as e:
        logger.error(f"Error adding news item: {e}")
        return False

def format_news_item(news_id: int, lang: str = 'en') -> str:
    """Format a news item for display."""
    news = get_news_by_id(news_id)
    if not news:
        return get_text("news_not_found", lang)
    
    timestamp = datetime.datetime.fromisoformat(news['timestamp'])
    formatted_date = timestamp.strftime("%Y-%m-%d %H:%M")
    
    return f"*{news['title']}*\n{formatted_date}\n\n{news['content']}"

def get_news_feed(lang: str = 'en', limit: int = 5) -> str:
    """Get a formatted news feed."""
    news_items = get_latest_news(limit)
    if not news_items:
        return get_text("no_news", lang)
    
    lines = [get_text("news_feed_header", lang)]
    for news in news_items:
        timestamp = datetime.datetime.fromisoformat(news['timestamp'])
        formatted_date = timestamp.strftime("%Y-%m-%d %H:%M")
        lines.extend([
            f"*{news['title']}*",
            formatted_date,
            news['content'],
            ""
        ])
    
    return "\n".join(lines).strip()

@db_transaction
def create_news(title: str, content: str, lang: str = 'en') -> str:
    """Create a new news item and return a confirmation message."""
    if add_news_item(title, content):
        return get_text("news_created", lang)
    return get_text("news_creation_failed", lang)

@db_transaction
def create_news_item(title: str, content: str, category: str, conn: Any) -> int:
    """Create a new news item."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO news (title, content, category, created_at)
            VALUES (?, ?, ?, ?)
        """, (title, content, category, datetime.datetime.now().isoformat()))
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating news item: {e}")
        return 0

@db_transaction
def get_news_item(news_id: int, conn: Any) -> Optional[Dict[str, Any]]:
    """Get a specific news item."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT news_id, title, content, category, created_at
            FROM news
            WHERE news_id = ?
        """, (news_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        return {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'category': row[3],
            'created_at': row[4]
        }
    except Exception as e:
        logger.error(f"Error getting news item: {e}")
        return None

@db_transaction
def get_news_by_category(category: str, conn: Any, limit: int = 5) -> List[Dict[str, Any]]:
    """Get news items by category."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT news_id, title, content, category, created_at
            FROM news
            WHERE category = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (category, limit))
        
        news_items = []
        for row in cursor.fetchall():
            news_items.append({
                'id': row[0],
                'title': row[1],
                'content': row[2],
                'category': row[3],
                'created_at': row[4]
            })
        return news_items
    except Exception as e:
        logger.error(f"Error getting news by category: {e}")
        return []

def get_category_news(category: str, lang: str = "en", limit: int = 5) -> str:
    """Get formatted news feed for a specific category."""
    with db_connection_pool.get_connection() as conn:
        news_items = get_news_by_category(category, conn, limit)
        
        if not news_items:
            return get_text("no_category_news", lang, params={"category": category})
        
        feed = [get_text("category_news", lang, params={"category": category})]
        for news in news_items:
            created_at = datetime.datetime.fromisoformat(news['created_at'])
            formatted_date = created_at.strftime("%Y-%m-%d %H:%M")
            
            feed.append(
                f"*{news['title']}*\n"
                f"{get_text('date', lang)}: {formatted_date}\n"
                f"{news['content']}\n"
            )
        
        return "\n".join(feed).strip()
