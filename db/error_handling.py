#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error handling utilities for database operations.
"""

import logging
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, TypeVar

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