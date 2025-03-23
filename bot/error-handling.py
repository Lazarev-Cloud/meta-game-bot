#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error handling utilities for the Meta Game bot.
"""

import logging
import traceback
from typing import Optional, Union, Callable, Awaitable, Any

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.keyboards import get_back_keyboard
from utils.i18n import _, get_user_language

# Initialize logger
logger = logging.getLogger(__name__)

class BotError(Exception):
    """Base class for bot-specific errors."""
    def __init__(self, message: str, user_message: Optional[str] = None):
        self.message = message
        self.user_message = user_message or message
        super().__init__(self.message)

class ResourceError(BotError):
    """Error raised when a player doesn't have enough resources."""
    pass

class PermissionError(BotError):
    """Error raised when a player doesn't have permission for an action."""
    pass

class NotFoundError(BotError):
    """Error raised when a requested item is not found."""
    pass

class DeadlineError(BotError):
    """Error raised when an action is attempted after a deadline."""
    pass

class DatabaseError(BotError):
    """Error raised for database-related issues."""
    pass

async def handle_error(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    error: Exception,
    keyboard_generator: Optional[Callable[[str], Awaitable[InlineKeyboardMarkup]]] = None
) -> None:
    """
    Handle errors with user-friendly messages and proper logging.
    
    Args:
        update: The update that caused the error
        context: The context for the error
        error: The error that occurred
        keyboard_generator: Optional function to generate a keyboard for the error message
    """
    telegram_id = None
    language = "en_US"
    
    # Try to get the user's language for error messages
    if update and update.effective_user:
        telegram_id = str(update.effective_user.id)
        try:
            language = await get_user_language(telegram_id)
        except:
            pass
    
    # Log the error
    logger.error(f"Exception while handling an update: {error}")
    
    # Get detailed error info for logging
    error_details = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    logger.error(f"Detailed error: {error_details}")
    
    # Create user-friendly message based on error type
    user_message = _("An error occurred while processing your request.", language)
    
    if isinstance(error, ResourceError):
        user_message = _(error.user_message, language)
    elif isinstance(error, PermissionError):
        user_message = _(error.user_message, language)
    elif isinstance(error, NotFoundError):
        user_message = _(error.user_message, language)
    elif isinstance(error, DeadlineError):
        user_message = _(error.user_message, language)
    elif isinstance(error, DatabaseError):
        user_message = _("Database connection error. Please try again later.", language)
    elif "resource" in str(error).lower():
        user_message = _("You don't have enough resources for this action.", language)
    elif "permission" in str(error).lower():
        user_message = _("You don't have permission to perform this action.", language)
    elif "not found" in str(error).lower():
        user_message = _("The requested item was not found.", language)
    elif "deadline" in str(error).lower():
        user_message = _("The submission deadline for this cycle has passed.", language)
    
    # Generate keyboard if a generator was provided
    keyboard = None
    if keyboard_generator and telegram_id:
        try:
            keyboard = await keyboard_generator(telegram_id)
        except Exception as e:
            logger.error(f"Error generating keyboard for error message: {e}")
            keyboard = get_back_keyboard(language)
    else:
        keyboard = get_back_keyboard(language)
    
    # Send the error message to the user
    try:
        if update.callback_query:
            await update.callback_query.answer(
                user_message[:200]  # Callback answers have a character limit
            )
            # Try to edit the message if possible
            try:
                await update.callback_query.edit_message_text(
                    user_message,
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Failed to edit message: {e}")
        elif update.message:
            await update.message.reply_text(
                user_message,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Failed to send error message to user: {e}")

def error_handler(func: Callable) -> Callable:
    """
    Decorator to handle errors in command and callback handlers.
    
    Args:
        func: The function to wrap with error handling
        
    Returns:
        Wrapped function with error handling
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await handle_error(update, context, e)
    
    return wrapper
