#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
User context management for the Meta Game bot.
"""

import time
from typing import Dict, Any

# Global context storage with timeout mechanism
# Structure: {telegram_id: {'data': {...}, 'timestamp': time.time()}}
user_context: Dict[str, Dict[str, Any]] = {}

# Timeout for user context (30 minutes)
USER_CONTEXT_TIMEOUT = 1800  # seconds
MAX_CONTEXTS = 1000


def get_user_context(telegram_id: str) -> Dict[str, Any]:
    """Get user context data, initializing if needed."""
    # Check if we need to clean up first
    if len(user_context) >= MAX_CONTEXTS:
        cleanup_expired_contexts()

    if telegram_id not in user_context:
        user_context[telegram_id] = {'data': {}, 'timestamp': time.time()}
    else:
        # Update timestamp on access
        user_context[telegram_id]['timestamp'] = time.time()

    return user_context[telegram_id]['data']


def set_user_context(telegram_id: str, data: Dict[str, Any]) -> None:
    """Set user context data with timestamp."""
    user_context[telegram_id] = {
        'data': data,
        'timestamp': time.time()
    }


def clear_user_context(telegram_id: str) -> None:
    """Clear a specific user's context."""
    if telegram_id in user_context:
        del user_context[telegram_id]


def cleanup_expired_contexts() -> int:
    """Remove expired contexts to prevent memory leaks.
    Returns the number of contexts cleaned up.
    """
    current_time = time.time()
    expired_ids = [
        tid for tid, context_data in user_context.items()
        if current_time - context_data.get('timestamp', 0) > USER_CONTEXT_TIMEOUT
    ]

    for telegram_id in expired_ids:
        clear_user_context(telegram_id)

    return len(expired_ids)