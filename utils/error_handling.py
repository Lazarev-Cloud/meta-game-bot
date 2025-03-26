#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified error handling utilities for the Meta Game bot.
"""

import asyncio
import logging
import functools
from typing import Callable, TypeVar, Optional, Dict, Any, Awaitable, Union

from telegram import Update

# Initialize logger
logger = logging.getLogger(__name__)

# Type variables for better typing
T = TypeVar('T')

# Configuration for retry mechanism
MAX_RETRIES = 3
RETRY_DELAY = 1.5  # seconds


class DatabaseError(Exception):
    """Base class for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Error related to database connection issues."""
    pass


class QueryError(DatabaseError):
    """Error related to database query issues."""
    pass


class AuthenticationError(DatabaseError):
    """Error related to database authentication issues."""
    pass


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
    """
    Execute a database operation with automatic retries and standardized error handling.

    Args:
        operation_name: Name of the operation for logging
        func: Async function to execute
        *args: Arguments to pass to the function
        default_return: Value to return on failure
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        log_error: Whether to log errors
        raise_error: Whether to raise errors after all retries fail
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call or default_return on failure

    Raises:
        DatabaseError: If raise_error is True and all retries fail
    """
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            result = await func(*args, **kwargs)
            # Handle cases where result is a number or boolean that could be mistaken for an error
            if result is not None or isinstance(result, (int, float, bool)):
                return result
            return default_return
        except Exception as e:
            last_exception = e
            retries += 1

            if log_error:
                logger.warning(
                    f"Operation '{operation_name}' failed (attempt {retries}/{max_retries}): {str(e)}"
                )

            if retries < max_retries:
                # Wait before retrying with exponential backoff
                await asyncio.sleep(retry_delay * retries)
            elif log_error:
                logger.error(f"Operation '{operation_name}' failed after {max_retries} attempts: {str(e)}")

    # Handle failure after all retries
    if raise_error and last_exception:
        # Convert to appropriate database error type
        if "connection" in str(last_exception).lower():
            raise ConnectionError(f"Unable to connect to database: {str(last_exception)}")
        elif "permission" in str(last_exception).lower() or "access" in str(last_exception).lower():
            raise AuthenticationError(f"Authentication error: {str(last_exception)}")
        else:
            raise QueryError(f"Database query error: {str(last_exception)}")

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


def handle_db_error(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """Decorator to handle database errors and return None instead of raising exceptions."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in database operation '{func.__name__}': {str(e)}")
            return None

    return wrapper


async def operation_with_retry(
        operation_name: str,
        func: Callable,
        *args,
        default_return: Any = None,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        **kwargs
) -> Any:
    """
    Execute an operation with automatic retries.

    Args:
        operation_name: Name of the operation for logging
        func: Function to execute
        *args: Arguments for the function
        default_return: Value to return on failure
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        **kwargs: Keyword arguments for the function

    Returns:
        Result of the function or default_return on failure
    """
    # Use the more advanced db_operation function
    return await db_operation(
        operation_name,
        func,
        *args,
        default_return=default_return,
        max_retries=max_retries,
        retry_delay=retry_delay,
        **kwargs
    )


async def handle_error(
        update: Update,
        language: str,
        error: Exception,
        operation: str,
        custom_message: Optional[str] = None
) -> None:
    """
    Unified error handler for both commands and callbacks.

    Args:
        update: The update object
        language: User's language code
        error: The exception that occurred
        operation: Name of the operation where the error occurred
        custom_message: Optional custom error message to show the user
    """
    logger.error(f"Error in {operation}: {str(error)}")

    # Import translation function here to avoid circular imports
    from utils.i18n import _

    # Default message
    message = custom_message or _("Database connection error. Please try again later.", language)

    # Customize message based on error type
    error_text = str(error).lower()
    if isinstance(error, DatabaseError):
        if isinstance(error, ConnectionError):
            message = _("Database connection error. Please try again later.", language)
        elif isinstance(error, AuthenticationError):
            message = _("You don't have permission to perform this action.", language)
        elif isinstance(error, QueryError):
            message = _("Error retrieving data. Please try again later.", language)
    elif "resource" in error_text:
        message = _("You don't have enough resources for this action.", language)
    elif "permission" in error_text:
        message = _("You don't have permission to perform this action.", language)
    elif "not found" in error_text:
        message = _("The requested item was not found.", language)
    elif "deadline" in error_text:
        message = _("The submission deadline for this cycle has passed.", language)

    try:
        # Handle different update types
        if update.callback_query:
            # For callback queries
            query = update.callback_query
            # Callback answers have character limit
            await query.answer(message[:200])
            try:
                await query.edit_message_text(message)
            except Exception:
                # Message might be unchanged or too old
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
    """
    Check if player is registered and send error message if not.
    Works with both messages and callback queries.

    Args:
        update: The update object
        language: User's language code

    Returns:
        True if registered, False otherwise
    """
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


def async_error_handler(
        operation_name: str,
        default_return: Any = None,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY
) -> Callable:
    """
    Decorator to handle errors in async functions with retries and default return value.

    Args:
        operation_name: Name of the operation for logging
        default_return: Value to return on error
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await db_operation(
                operation_name,
                func,
                *args,
                default_return=default_return,
                max_retries=max_retries,
                retry_delay=retry_delay,
                raise_error=False,
                **kwargs
            )

        return wrapper

    return decorator