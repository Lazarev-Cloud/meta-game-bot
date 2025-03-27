#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified context management for the Meta Game bot.
"""

import logging
import time
from typing import Dict, Any, Optional

from telegram.ext import ContextTypes

# Initialize logger
logger = logging.getLogger(__name__)

# Timeout for user context (30 minutes)
USER_CONTEXT_TIMEOUT = 1800  # seconds
MAX_CONTEXTS = 1000


class ContextManager:
    """Unified manager for user context data across the application."""

    def __init__(self):
        # Internal context storage
        self._storage: Dict[str, Dict[str, Any]] = {}

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get value from context by key with optional default."""
        if user_id not in self._storage:
            return default

        self._refresh_timestamp(user_id)
        return self._storage[user_id].get('data', {}).get(key, default)

    def set(self, user_id: str, key: str, value: Any) -> None:
        """Set value in context by key."""
        if user_id not in self._storage:
            self._storage[user_id] = {
                'data': {},
                'timestamp': time.time()
            }
        else:
            self._refresh_timestamp(user_id)

        self._storage[user_id]['data'][key] = value

    def get_all(self, user_id: str) -> Dict[str, Any]:
        """Get all context data for a user."""
        if user_id not in self._storage:
            self._storage[user_id] = {
                'data': {},
                'timestamp': time.time()
            }
            return {}

        self._refresh_timestamp(user_id)
        return self._storage[user_id].get('data', {}).copy()

    def set_all(self, user_id: str, data: Dict[str, Any]) -> None:
        """Set all context data for a user."""
        self._storage[user_id] = {
            'data': data,
            'timestamp': time.time()
        }

    def clear(self, user_id: str) -> None:
        """Clear all context data for a user."""
        if user_id in self._storage:
            del self._storage[user_id]

    def _refresh_timestamp(self, user_id: str) -> None:
        """Update the timestamp for a user's context."""
        if user_id in self._storage:
            self._storage[user_id]['timestamp'] = time.time()

    def cleanup_expired(self) -> int:
        """Remove expired contexts. Returns the number of items cleaned up."""
        current_time = time.time()
        expired_ids = [
            tid for tid, context_data in self._storage.items()
            if current_time - context_data.get('timestamp', 0) > USER_CONTEXT_TIMEOUT
        ]

        for user_id in expired_ids:
            self.clear(user_id)

        return len(expired_ids)

    def size(self) -> int:
        """Get the number of user contexts in storage."""
        return len(self._storage)

    def check_cleanup_needed(self) -> bool:
        """Check if cleanup is needed due to large context size."""
        return len(self._storage) >= MAX_CONTEXTS


# Global context manager instance
context_manager = ContextManager()


# Helper functions for working with both PTB context and our custom context
def get_user_data(telegram_id: str, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> Dict[str, Any]:
    """
    Get user data, combining PTB context (if provided) with our custom context.
    Always returns a copy to prevent unintended modifications.
    """
    # Check if cleanup is needed
    if context_manager.check_cleanup_needed():
        context_manager.cleanup_expired()

    # Get data from our custom context
    data = context_manager.get_all(telegram_id)

    # If PTB context is provided, merge its data
    if context and hasattr(context, 'user_data'):
        # Make a copy of context.user_data to avoid modifying it directly
        ptb_data = dict(context.user_data) if context.user_data else {}
        # Update our data with PTB data, giving PTB priority
        data.update(ptb_data)

    return data

def set_user_data(telegram_id: str, key: str, value: Any, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
    """Set user data in both our custom context and PTB context if provided."""
    # Set in our custom context
    context_manager.set(telegram_id, key, value)

    # Also set in PTB context if provided
    if context and hasattr(context, 'user_data'):
        context.user_data[key] = value


def clear_user_data(telegram_id: str, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
    """Clear user data from both our custom context and PTB context if provided."""
    # Clear our custom context
    context_manager.clear(telegram_id)

    # Also clear PTB context if provided
    if context and hasattr(context, 'user_data'):
        context.user_data.clear()


# Legacy aliases for backward compatibility
def get_user_context(telegram_id: str) -> Dict[str, Any]:
    """Legacy alias for get_user_data for backward compatibility."""
    return context_manager.get_all(telegram_id)


def set_user_context(telegram_id: str, data: Dict[str, Any]) -> None:
    """Legacy alias for set_user_data for backward compatibility."""
    context_manager.set_all(telegram_id, data)


def clear_user_context(telegram_id: str) -> None:
    """Legacy alias for clear_user_data for backward compatibility."""
    context_manager.clear(telegram_id)