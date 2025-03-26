#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified error handling utilities for the Meta Game bot.
"""

import asyncio
import functools
import logging
import traceback
from typing import Callable, TypeVar, Optional, Any, Awaitable

from telegram import Update

# Initialize logger
logger = logging.getLogger(__name__)

# Type variables for better typing
T = TypeVar('T')

# Configuration for retry mechanism - centralized
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


# Error handling utilities
def classify_error(error: Exception) -> type:
    """Classify an error by type for appropriate handling."""
    error_text = str(error).lower()

    if "permission denied" in error_text or "not authorized" in error_text:
        return PermissionError
    elif "connection" in error_text or "timeout" in error_text or "network" in error_text:
        return ConnectionError
    elif "database" in error_text or "query" in error_text or "sql" in error_text:
        return QueryError
    else:
        return type(error)


async def db_operation(
        operation_name: str,
        func: Callable[..., Awaitable[T]],
        *args,
        default_return: Any = None,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        log_error: bool = True,
        raise_error: bool = False,
        **kwargs
) -> T:
    """Execute a database operation with automatic retries and error handling."""
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            result = await func(*args, **kwargs)
            # Handle cases where result is a primitive type
            if result is not None or isinstance(result, (int, float, bool)):
                return result
            return default_return
        except Exception as e:
            last_exception = e
            error_class = classify_error(e)
            retries += 1

            if log_error:
                logger.warning(
                    f"Operation '{operation_name}' failed (attempt {retries}/{max_retries}): {str(e)}"
                )

            # Don't retry permission errors - they won't resolve without intervention
            if issubclass(error_class, PermissionError):
                logger.error(f"Permission error in operation '{operation_name}': {str(e)}")
                break

            if retries < max_retries:
                # Exponential backoff with jitter for retries
                delay = retry_delay * (2 ** (retries - 1)) * (0.9 + 0.2 * random.random())
                await asyncio.sleep(delay)
            elif log_error:
                logger.error(f"Operation '{operation_name}' failed after {max_retries} attempts: {str(e)}")

    # Handle failure after all retries
    if raise_error and last_exception:
        error_class = classify_error(last_exception)
        if issubclass(error_class, ConnectionError):
            raise ConnectionError(f"Connection error: {str(last_exception)}")
        elif issubclass(error_class, PermissionError):
            raise PermissionError(f"Permission error: {str(last_exception)}")
        elif issubclass(error_class, QueryError):
            raise QueryError(f"Query error: {str(last_exception)}")
        else:
            raise DatabaseError(f"Database error: {str(last_exception)}")

    # Return default value on complete failure
    return default_return


def db_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to retry database operations with exponential backoff."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await db_operation(
            func.__name__,
            func,
            *args,
            raise_error=True,
            **kwargs
        )

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

    # Import translation function here to avoid circular imports
    from utils.i18n import _

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
    elif "resource" in error_text or "not enough" in error_text:
        message = _("You don't have enough resources for this action.", language)
    elif "not found" in error_text:
        message = _("The requested item was not found.", language)
    elif "deadline" in error_text or "closed" in error_text:
        message = _("The submission deadline for this cycle has passed.", language)

    try:
        # Deliver error message based on update type
        if update.callback_query:
            # For callback queries
            query = update.callback_query
            # Callback answers have length limit
            await query.answer(message[:200])
            try:
                await query.edit_message_text(message)
            except Exception:
                # Message might be unchanged
                pass
        elif update.message:
            # For regular messages
            await update.message.reply_text(message)
        else:
            # Just log if we can't respond
            logger.warning(f"Could not send error message to user: {message}")
    except Exception as e:
        logger.error(f"Error sending error message: {e}")


async def require_registration(update: Update, language: str) -> bool:
    """Check if player is registered and send error message if not."""
    from db import player_exists
    from utils.i18n import _

    telegram_id = str(update.effective_user.id)

    try:
        exists = await player_exists(telegram_id)
    except Exception as e:
        logger.error(f"Error checking if player exists: {e}")
        await handle_error(
            update,
            language,
            e,
            "require_registration",
            _("Sorry, we're experiencing technical difficulties. Please try again later.", language)
        )
        return False

    if not exists:
        message = _("You are not registered yet. Use /start to register.", language)

        if update.callback_query:
            await update.callback_query.answer(_("You need to register first.", language))
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return False

    return True


# Add this import for exponential backoff with jitter
import random
