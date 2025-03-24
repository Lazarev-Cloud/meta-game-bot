#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error handling utilities for database operations.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Optional, TypeVar, Any

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

    @wraps(func)
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

    @wraps(func)
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
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            result = await func(*args, **kwargs)
            # Handle cases where result is a number that could be mistaken for an error
            if result is not None or isinstance(result, (int, float, bool)):
                return result
            return default_return
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

    # Return default value on complete failure
    return default_return