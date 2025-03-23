#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Constants and shared state for the Meta Game bot.
"""
import time
from typing import Dict, Any
from bot.context import get_user_context, set_user_context, clear_user_context

# Define conversation states
(
    # Registration states
    NAME_ENTRY,
    IDEOLOGY_CHOICE,

    # Action selection states
    ACTION_SELECT_DISTRICT,
    ACTION_SELECT_TARGET,
    ACTION_SELECT_RESOURCE,
    ACTION_SELECT_AMOUNT,
    ACTION_PHYSICAL_PRESENCE,
    ACTION_CONFIRM,

    # Resource conversion states
    CONVERT_FROM_RESOURCE,
    CONVERT_TO_RESOURCE,
    CONVERT_AMOUNT,
    CONVERT_CONFIRM,

    # Collective action states
    COLLECTIVE_ACTION_TYPE,
    COLLECTIVE_ACTION_DISTRICT,
    COLLECTIVE_ACTION_TARGET,
    COLLECTIVE_ACTION_RESOURCE,
    COLLECTIVE_ACTION_AMOUNT,
    COLLECTIVE_ACTION_PHYSICAL,
    COLLECTIVE_ACTION_CONFIRM,

    # Join collective action states
    JOIN_ACTION_RESOURCE,
    JOIN_ACTION_AMOUNT,
    JOIN_ACTION_PHYSICAL,
    JOIN_ACTION_CONFIRM
) = range(23)

# Global context storage with timeout mechanism
# Structure: {telegram_id: {'data': {...}, 'timestamp': time.time()}}
user_context: Dict[str, Dict[str, Any]] = {}

# Timeout for user context (30 minutes)
USER_CONTEXT_TIMEOUT = 1800  # seconds




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
