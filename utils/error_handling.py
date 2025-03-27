# utils/error_handling.py - Centralized error handling system

import asyncio
import functools
import logging
import random
import traceback
from typing import Callable, TypeVar, Optional, Any, Awaitable, Union

from telegram import Update

from utils.i18n import _
from utils.message_utils import send_message, edit_or_reply

# Initialize logger
logger = logging.getLogger(__name__)

# Type variables for better typing
T = TypeVar('T')

# Configuration for retry mechanism
MAX_RETRIES = 3
RETRY_DELAY = 1.5  # seconds


# Error type classification
class DatabaseError(Exception):
    """Base class for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Database connection issues."""
    pass


class PermissionError(DatabaseError):
    """Database permission issues."""
    pass


class QueryError(DatabaseError):
    """Database query issues."""
    pass


class ResourceError(Exception):
    """Error related to insufficient resources."""
    pass


# Error classification function
def classify_error(error: Exception) -> type:
    """Classify an error by type for appropriate handling."""
    error_text = str(error).lower()

    if "permission denied" in error_text or "not authorized" in error_text:
        return PermissionError
    elif "connection" in error_text or "timeout" in error_text or "network" in error_text:
        return ConnectionError
    elif "database" in error_text or "query" in error_text or "sql" in error_text:
        return QueryError
    elif "not enough" in error_text or "resource" in error_text:
        return ResourceError
    else:
        return type(error)


# Database retry decorator
def db_retry(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Decorator to retry database operations with exponential backoff."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        retries = 0
        last_exception = None

        while retries < MAX_RETRIES:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_class = classify_error(e)
                retries += 1

                logger.warning(
                    f"Operation '{func.__name__}' failed (attempt {retries}/{MAX_RETRIES}): {str(e)}"
                )

                # Don't retry permission errors - they won't resolve without intervention
                if issubclass(error_class, PermissionError):
                    logger.error(f"Permission error in operation '{func.__name__}': {str(e)}")
                    break

                if retries < MAX_RETRIES:
                    # Exponential backoff with jitter for retries
                    delay = RETRY_DELAY * (2 ** (retries - 1)) * (0.9 + 0.2 * random.random())
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Operation '{func.__name__}' failed after {MAX_RETRIES} attempts: {str(e)}")

        # Return None on complete failure
        return None

    return wrapper


async def handle_error(
        update: Update,
        language: str,
        error: Exception,
        operation: str,
        custom_message: Optional[str] = None
) -> None:
    """Unified error handler for both commands and callbacks."""
    logger.error(f"Error in {operation}: {str(error)}")

    # Get traceback for better debugging
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    logger.debug(f"Traceback for {operation}:\n{''.join(tb)}")

    # Default message
    message = custom_message or _("An error occurred. Please try again later.", language)

    # Customize message based on error type
    error_text = str(error).lower()
    error_class = classify_error(error)

    if issubclass(error_class, PermissionError):
        message = _("You don't have permission to perform this action.", language)
    elif issubclass(error_class, ConnectionError):
        message = _("Connection error. Please try again later.", language)
    elif issubclass(error_class, QueryError):
        message = _("Error retrieving data. Please try again later.", language)
    elif issubclass(error_class, ResourceError):
        message = _("You don't have enough resources for this action.", language)
    elif "not found" in error_text:
        message = _("The requested item was not found.", language)
    elif "deadline" in error_text or "closed" in error_text:
        message = _("The submission deadline for this cycle has passed.", language)

    try:
        # Deliver error message based on update type
        if update.callback_query:
            await update.callback_query.answer(_("Error", language), show_alert=True)
            try:
                await update.callback_query.edit_message_text(message)
            except Exception:
                # Message might be unchanged, try using send_message instead
                await send_message(update, message)
        elif update.message:
            await update.message.reply_text(message)
        else:
            logger.warning(f"Could not send error message to user: {message}")
    except Exception as e:
        logger.error(f"Error sending error message: {e}")


async def require_registration(update: Update, language: str) -> bool:
    """Check player registration with memory-first approach."""
    telegram_id = str(update.effective_user.id)

    # Check memory first to reduce database load
    from utils.context_manager import context_manager
    if context_manager.get(telegram_id, "is_registered", False):
        return True

    try:
        # Lazy import to avoid circular dependency
        from db import player_exists
        exists = await player_exists(telegram_id)

        if exists:
            # Update memory state
            context_manager.set(telegram_id, "is_registered", True)
            return True

        # User not registered
        message = _("You are not registered yet. Use /start to register.", language)

        if update.callback_query:
            await update.callback_query.answer(_("You need to register first.", language))
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return False
    except Exception as e:
        logger.error(f"Registration check error: {e}")
        # Fall through and allow access if we can't check
        # This prevents locking users out due to database issues
        return True


# Conversation step error handler
def conversation_step(func: Callable) -> Callable:
    """
    Decorator for conversation steps to add standardized error handling.

    It captures errors, logs them, and provides user-friendly messages.
    """

    @functools.wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        telegram_id = str(update.effective_user.id)

        try:
            from utils.i18n import get_user_language
            language = await get_user_language(telegram_id)

            # Execute the original function
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in conversation step {func.__name__}: {e}")

            try:
                from telegram.ext import ConversationHandler
                from utils.i18n import get_user_language

                # Get user language
                language = await get_user_language(telegram_id)

                # Handle error with user feedback
                await handle_error(update, language, e, func.__name__)

                # End the conversation to avoid getting stuck
                return ConversationHandler.END
            except Exception as nested_e:
                logger.critical(f"Error handling conversation error: {nested_e}")
                # Absolute fallback to end conversation
                from telegram.ext import ConversationHandler
                return ConversationHandler.END

    return wrapper


# Class-based error handler for more complex scenarios
class ErrorHandler:
    """Comprehensive error handling utilities."""

    @staticmethod
    async def handle_db_error(update: Update, operation: str, error: Exception, language: str = "en_US") -> None:
        """Handle database errors with appropriate user feedback."""
        logger.error(f"Database error in {operation}: {str(error)}")

        error_class = classify_error(error)
        message = _("Database error. Please try again later.", language)

        if issubclass(error_class, PermissionError):
            message = _("Permission denied. You don't have access to this feature.", language)
        elif issubclass(error_class, ResourceError):
            message = _("Insufficient resources to perform this action.", language)

        await handle_error(update, language, error, operation, message)

    @staticmethod
    async def handle_action_error(update: Update, action_type: str, error: Exception, language: str) -> None:
        """Handle errors during game actions."""
        logger.error(f"Action error ({action_type}): {str(error)}")

        message = _("Error executing {action} action: {error}", language).format(
            action=_(action_type, language),
            error=str(error)
        )

        await handle_error(update, language, error, f"action_{action_type}", message)

    @staticmethod
    async def handle_initialization_error(error: Exception) -> None:
        """Handle errors during system initialization."""
        logger.critical(f"Initialization error: {str(error)}")
        # No update to handle, just log the error
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        logger.debug(f"Initialization error traceback:\n{''.join(tb)}")