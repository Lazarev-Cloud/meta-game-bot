#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified error handling module for the Meta Game bot.
"""

import asyncio
import logging
import functools
from typing import Callable, TypeVar, Optional, Dict, Any, Awaitable

from telegram import Update

from utils.i18n import _

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


def db_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to retry database operations with exponential backoff."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        retries = 0
        last_exception = None

        while retries < MAX_RETRIES:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                retries += 1

                # Log the error
                logger.warning(
                    f"Database operation '{func.__name__}' failed (attempt {retries}/{MAX_RETRIES}): {str(e)}"
                )

                if retries < MAX_RETRIES:
                    # Wait before retrying with exponential backoff
                    await asyncio.sleep(RETRY_DELAY * retries)
                else:
                    # Log the final failure
                    logger.error(f"Database operation '{func.__name__}' failed after {MAX_RETRIES} attempts: {str(e)}")

        # Re-raise the last exception with a more informative message
        if last_exception:
            if "connection" in str(last_exception).lower():
                raise ConnectionError(f"Unable to connect to database: {str(last_exception)}")
            elif "permission" in str(last_exception).lower() or "access" in str(last_exception).lower():
                raise AuthenticationError(f"Authentication error: {str(last_exception)}")
            else:
                raise QueryError(f"Database query error: {str(last_exception)}")
        else:
            raise DatabaseError("Unknown database error occurred")

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


async def handle_error(update: Update, language: str, error: Exception, operation: str,
                       custom_message: Optional[str] = None) -> None:
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


async def operation_with_retry(
        operation_name: str,
        func: Callable[..., Awaitable[T]],
        *args,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
        **kwargs
) -> T:
    """
    Execute an operation with automatic retries.

    Args:
        operation_name: Name of the operation for logging
        func: Async function to execute
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call

    Raises:
        Exception: Re-raises the last exception after all retries fail
    """
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            retries += 1

            logger.warning(
                f"Operation '{operation_name}' failed (attempt {retries}/{max_retries}): {str(e)}"
            )

            if retries < max_retries:
                # Wait before retrying with exponential backoff
                await asyncio.sleep(retry_delay * retries)
            else:
                logger.error(f"Operation '{operation_name}' failed after {max_retries} attempts: {str(e)}")

    # Re-raise the last exception
    if last_exception:
        raise last_exception
    else:
        raise Exception(f"Unknown error in operation '{operation_name}'")


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
            try:
                return await operation_with_retry(
                    operation_name,
                    func,
                    *args,
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                    **kwargs
                )
            except Exception as e:
                logger.error(f"Error in {operation_name}: {str(e)}")
                return default_return

        return wrapper

    return decorator