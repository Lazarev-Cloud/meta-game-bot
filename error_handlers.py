import logging
import json
import traceback
import html
import sqlite3
import sys
import os
import signal
import psutil
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import (
    TelegramError, BadRequest, TimedOut, NetworkError, ChatMigrated, Conflict
)
from languages import get_text, get_player_language
from db.utils import close_all_connections
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Map of error keys to user-friendly messages
USER_FRIENDLY_ERRORS = {
    "database is locked": "The system is busy. Please try again in a moment.",
    "connection refused": "Cannot connect to server. Please try again later.",
    "timed out": "The operation timed out. Please try again.",
    "message is not modified": "No changes were needed.",
    "message to edit not found": "The message could not be updated.",
    "bot was blocked": "The bot cannot send messages to you. Please unblock the bot.",
    "not enough rights": "The bot doesn't have permission to perform this action.",
    "have no rights": "The bot doesn't have permission to perform this action.",
    "message can't be deleted": "The message cannot be deleted.",
    "query is too old": "This action has expired. Please try a new command.",
    "replied message not found": "The message you replied to was not found.",
    "too many requests": "Too many requests. Please wait a moment before trying again.",
    "error checking physical presence": "Could not verify your physical presence. Please try again.",
    "insufficient resources": "You don't have enough resources for this action.",
    "terminated by other getUpdates request": "The bot is restarting. Please try again in a moment."
}

# Categorize errors for better handling
NETWORK_ERRORS = [
    "connection refused", "timed out", "server error", "not enough rights", 
    "gateway timeout", "too many requests"
]

DATABASE_ERRORS = [
    "database is locked", "disk i/o error", "database disk image is malformed",
    "no such table", "constraint failed", "database corrupted"
]

USER_ACTION_ERRORS = [
    "message is not modified", "message to edit not found", "replied message not found",
    "query is too old", "not enough rights", "have no rights"
]

FATAL_ERRORS = [
    "terminated by other getUpdates request", "conflict"
]

def handle_telegram_conflict(error_message):
    """
    Handle Telegram conflicts, particularly the getUpdates conflict.
    This is a fatal error that requires the application to exit.
    """
    logger.error(f"Telegram conflict detected: {error_message}")
    
    # Log detailed information
    logger.error("This instance needs to terminate due to a conflict with another bot instance")
    
    # Kill any duplicate bot processes
    try:
        # Get current process ID
        current_pid = os.getpid()
        logger.error(f"Current process ID: {current_pid}")
        
        # Attempt to identify and kill competing bot processes
        logger.error("Attempting to identify conflicting bot processes...")
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip our own process
                if proc.pid == current_pid:
                    continue
                    
                # Check if it's a Python process related to our bot
                if (proc.info['name'] in ['python', 'python3', 'Python']):
                    cmdline = ' '.join(proc.info['cmdline'] if proc.info['cmdline'] else [])
                    
                    if ('main.py' in cmdline or 
                        'run_novi_sad_game.py' in cmdline or 
                        'telegram' in cmdline or
                        'getUpdates' in cmdline) and proc.pid != current_pid:
                        logger.error(f"Found potential conflicting process: PID {proc.pid}, cmdline: {cmdline}")
                        try:
                            # Kill the competing process
                            proc.terminate()
                            logger.error(f"Terminated competing process: PID {proc.pid}")
                            break  # Exit after killing first competing process
                        except Exception as e:
                            logger.error(f"Failed to terminate process {proc.pid}: {e}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                continue
    except Exception as e:
        logger.error(f"Error while attempting to resolve conflict: {e}")
    
    # Clean up resources
    try:
        close_all_connections()
    except Exception as e:
        logger.error(f"Error closing DB connections: {e}")
    
    # Try to gracefully terminate the process
    logger.error("Terminating process...")
    
    # Exit with a non-zero code to allow supervisor systems to restart
    sys.exit(1)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the Telegram bot."""
    # Log the error
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Extract the error message
    error_message = str(context.error)
    
    # Handle Telegram Conflict errors (like duplicate getUpdates) immediately
    if isinstance(context.error, Conflict) or "terminated by other getUpdates request" in error_message.lower():
        handle_telegram_conflict(error_message)
        return
    
    # Get traceback info
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    
    # Log the traceback for debugging
    logger.error(f"Exception traceback:\n{tb_string}")
    
    # Early return if update is None - this avoids the "NoneType can't be used in await" error
    if update is None:
        logger.error("Update object is None, can't process this error fully")
        
        # Notify administrators about the error with the None update (without using await)
        admin_message = (
            f"An error occurred with a None update:\n"
            f"<pre>Update: None</pre>\n\n"
            f"<pre>Error: {html.escape(error_message)}</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )
        
        # Truncate if the message is too long
        if len(admin_message) > 4000:
            admin_message = admin_message[:3997] + "..."
        
        # Try to notify administrators without using await
        try:
            for admin_id in ADMIN_IDS:
                try:
                    # Use a non-async method or queue the message for later delivery
                    # Since we can't await here, we'll add a handler to send this later
                    context.application.create_task(
                        context.bot.send_message(
                            chat_id=admin_id,
                            text=admin_message,
                            parse_mode=ParseMode.HTML
                        ),
                        update=None  # No associated update
                    )
                except Exception as e:
                    logger.error(f"Failed to queue error message to admin {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
        
        # Clean up database connections
        try:
            logger.info("Attempting to close all DB connections due to error with None update")
            close_all_connections()
        except Exception as e:
            logger.error(f"Error closing DB connections: {e}")
            
        return
    
    # Get traceback info
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    
    # Log the traceback for debugging
    logger.error(f"Traceback: {tb_string}")
    
    # Prepare error message for admins
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    admin_message = (
        f"An error occurred while handling an update:\n"
        f"<pre>{html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    
    # Truncate if the message is too long
    if len(admin_message) > 4000:
        admin_message = admin_message[:3997] + "..."
    
    # Notify administrators
    try:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send error message to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to notify admins: {e}")
    
    # Clean up database connections during serious errors
    if isinstance(context.error, (sqlite3.Error, sqlite3.OperationalError, RuntimeError, KeyError, MemoryError)):
        try:
            logger.info("Attempting to close all DB connections due to serious error")
            close_all_connections()
        except Exception as e:
            logger.error(f"Error closing DB connections: {e}")
    
    # If there's an update and it has an effective chat/user, send a user-friendly message
    if update and (update.effective_chat or update.callback_query):
        # Try to find a user-friendly error message
        user_message = "An error occurred. Please try again later."
        
        # Get user's language if possible
        user_id = update.effective_user.id if update.effective_user else None
        lang = "en"  # Default to English
        
        if user_id:
            try:
                lang = get_player_language(user_id)
            except Exception:
                # Fall back to default language if we can't get user language
                pass
        
        # Determine error type for better messaging
        error_type = "general"
        error_lower = error_message.lower()
        
        for key in DATABASE_ERRORS:
            if key in error_lower:
                error_type = "database"
                break
                
        for key in NETWORK_ERRORS:
            if key in error_lower:
                error_type = "network"
                break
                
        for key in USER_ACTION_ERRORS:
            if key in error_lower:
                error_type = "user_action"
                break
        
        # Get specific error message if available
        for key, friendly_msg in USER_FRIENDLY_ERRORS.items():
            if key.lower() in error_lower:
                user_message = friendly_msg
                break
                
        # If no specific message found, use general message based on error type
        if user_message == "An error occurred. Please try again later.":
            if error_type == "database":
                user_message = get_text("database_error", lang, 
                                       default="Database error occurred. Please try again later.")
            elif error_type == "network":
                user_message = get_text("network_error", lang,
                                       default="Network error occurred. Please try again.")
            elif error_type == "user_action":
                user_message = get_text("action_error", lang,
                                       default="Error with your last action. Please try again.")
        
        try:
            # If it was a callback query, answer it
            if update.callback_query:
                await update.callback_query.answer(
                    text=user_message,
                    show_alert=True
                )
                # Also send a message so the user doesn't wonder what happened
                try:
                    await update.effective_chat.send_message(
                        text=f"⚠️ {user_message}",
                        reply_to_message_id=update.effective_message.message_id if update.effective_message else None
                    )
                except Exception:
                    # If we can't reply to the message, just send a new one
                    await update.effective_chat.send_message(
                        text=f"⚠️ {user_message}"
                    )
            # Otherwise, send a message
            elif update.effective_chat:
                await update.effective_chat.send_message(
                    text=f"⚠️ {user_message}",
                    reply_to_message_id=update.effective_message.message_id if update.effective_message else None
                )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}") 