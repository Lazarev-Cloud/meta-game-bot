import logging
import traceback
import json
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError
from languages import get_text, get_resource_name
from db.utils import get_db_connection
from db.queries import get_player, get_player_language, add_news

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def send_message_to_player(bot: Bot, player_id: int, message: str, reply_markup=None, parse_mode="HTML"):
    """Send a message to a player with error handling."""
    try:
        await bot.send_message(
            chat_id=player_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramError as e:
        logger.error(f"Failed to send message to player {player_id}: {e}")
        return False

async def notify_all_players(bot: Bot, message_key: str, default_message: str = None, parse_mode="HTML"):
    """Send a notification to all registered players in their preferred language."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get all players and their preferred language
            cursor.execute("SELECT id, lang FROM players")
            players = cursor.fetchall()
            
            success_count = 0
            fail_count = 0
            
            for player_id, lang in players:
                try:
                    # Get localized message
                    localized_message = get_text(message_key, lang, default=default_message)
                    
                    # Send message
                    success = await send_message_to_player(
                        bot, 
                        player_id, 
                        localized_message,
                        parse_mode=parse_mode
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    logger.error(f"Error notifying player {player_id}: {e}")
                    fail_count += 1
            
            logger.info(f"Notification sent to {success_count} players, failed for {fail_count} players")
            return success_count, fail_count
    except Exception as e:
        logger.error(f"Error in notify_all_players: {e}")
        logger.error(traceback.format_exc())
        return 0, 0

def create_inline_keyboard(buttons, row_width=2):
    """
    Create an inline keyboard markup from a list of button tuples.
    Each button is a tuple of (text, callback_data).
    
    Args:
        buttons: List of (text, callback_data) tuples
        row_width: Number of buttons per row
    
    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = []
    row = []
    
    for i, (text, callback_data) in enumerate(buttons):
        row.append(InlineKeyboardButton(text, callback_data=callback_data))
        
        # Start a new row when row_width is reached
        if (i + 1) % row_width == 0:
            keyboard.append(row)
            row = []
    
    # Add any remaining buttons
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

def format_resources(resources, lang):
    """Format a dictionary of resources for display."""
    formatted = []
    for resource_type, amount in resources.items():
        resource_name = get_resource_name(resource_type, lang)
        formatted.append(f"• {resource_name}: {amount}")
    
    if not formatted:
        return get_text("no_resources", lang, default="No resources")
    
    return "\n".join(formatted)

def get_player_language(player_id):
    """Get the preferred language for a player."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lang FROM players WHERE id = ?", (player_id,))
            result = cursor.fetchone()
            return result[0] if result else "en"
    except Exception as e:
        logger.error(f"Error getting player language for {player_id}: {e}")
        return "en"

def log_game_event(event_type, player_id, details, public=False):
    """Log a game event and optionally add it to the news.
    
    Args:
        event_type: The type of event
        player_id: The player's ID
        details: Details about the event
        public: Whether to add this event to public news
    """
    player = get_player(player_id)
    player_name = player["name"] if player else f"Player {player_id}"
    
    logger.info(f"Game event: {event_type} by {player_name} - {details}")
    
    if public:
        # Add the event to news if it should be public
        try:
            lang = get_player_language(player_id) or "en"
            if event_type == "join_action":
                action_id = details.get("action_id")
                resource_type = details.get("resource_type")
                resource_amount = details.get("resource_amount")
                
                news_text = get_text(
                    "news_player_joined_action",
                    lang,
                    player_name=player_name,
                    action_id=action_id,
                    resource_type=get_resource_name(resource_type, lang),
                    resource_amount=resource_amount
                )
                add_news(news_text)
            
            # Add more event types as needed
        except Exception as e:
            logger.error(f"Failed to add news for event {event_type}: {str(e)}", exc_info=True)

async def notify_player(bot, player_id, message, parse_mode="HTML"):
    """Send a notification to a player.
    
    Args:
        bot: The bot instance to use for sending the message
        player_id: The player's Telegram ID
        message: The message to send
        parse_mode: The parse mode to use (default: HTML)
        
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    try:
        await bot.send_message(
            chat_id=player_id,
            text=message,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        logger.error(f"Failed to notify player {player_id}: {str(e)}", exc_info=True)
        return False 