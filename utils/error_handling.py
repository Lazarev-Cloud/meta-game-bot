#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified error handling utilities for the Meta Game bot.
"""

import logging
from typing import Optional

from telegram import Update

from utils.i18n import _

# Initialize logger
logger = logging.getLogger(__name__)


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
    if "resource" in error_text:
        message = _("You don't have enough resources for this action.", language)
    elif "permission" in error_text:
        message = _("You don't have permission to perform this action.", language)
    elif "not found" in error_text:
        message = _("The requested item was not found.", language)
    elif "deadline" in error_text:
        message = _("The submission deadline for this cycle has passed.", language)

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