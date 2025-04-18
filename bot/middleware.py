#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Middleware implementation for the Meta Game bot with improved error handling.
"""

import logging
import time
from typing import Dict, Set, List, Any, Callable, Awaitable, Optional

from telegram import Update
from telegram.ext import ContextTypes, Application, MessageHandler, CallbackQueryHandler, filters

from db import player_exists, get_player
from utils.i18n import _, get_user_language

# Initialize logger
logger = logging.getLogger(__name__)

# Rate limiting storage
rate_limit_data: Dict[int, Dict[str, Any]] = {}
blocked_users: Set[int] = set()
admin_ids: List[int] = []

# Generic middleware handler type
MiddlewareFunc = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Optional[bool]]]


async def apply_middleware_chain(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 middleware_funcs: List[MiddlewareFunc]) -> bool:
    """Apply a chain of middleware functions, stopping if any returns False."""
    for func in middleware_funcs:
        try:
            result = await func(update, context)
            if result is False:  # Explicit check for False return
                return False
        except Exception as e:
            logger.error(f"Error in middleware function {func.__name__}: {e}")
            await error_handler_middleware(update, context, e)
            return False
    return True


async def log_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all updates for debugging and monitoring."""
    user = update.effective_user

    if user:
        user_info = f"User ID: {user.id}, Username: {user.username}, Name: {user.full_name}"
    else:
        user_info = "No user data"

    if update.message and update.message.text:
        logger.info(f"Received message from {user_info}: {update.message.text}")
    elif update.callback_query:
        logger.info(f"Received callback from {user_info}: {update.callback_query.data}")
    else:
        logger.info(f"Received update of type {update.update_id} from {user_info}")


async def authentication_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Authenticate users with graceful degradation when database is unavailable."""
    user = update.effective_user
    if not user:
        return False

    # Allow any user to use /start for registration
    if update.message and update.message.text and update.message.text.startswith("/start"):
        return True

    # Admin commands check
    if update.message and update.message.text and update.message.text.startswith("/admin"):
        return user.id in admin_ids

    # Skip registration check for help command
    if update.message and update.message.text and update.message.text.startswith("/help"):
        return True

    # Check if user is registered for game commands
    if update.message and update.message.text and update.message.text.startswith("/"):
        try:
            is_registered = await player_exists(str(user.id))

            if not is_registered:
                language = "en_US"  # Fallback language
                await update.message.reply_text(
                    _("You are not registered as a player. Please use the /start command to register.", language)
                )
                return False
        except Exception as e:
            logger.error(f"Error checking if player exists: {e}")
            # Allow access when database is unavailable to avoid locking users out
            return True

    return True


async def rate_limit_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Implement rate limiting to prevent abuse."""
    user = update.effective_user

    if not user:
        return False

    user_id = user.id

    # Check if user is blocked
    if user_id in blocked_users:
        logger.warning(f"Blocked user {user_id} attempted to use the bot")
        return False

    # Check rate limiting
    current_time = time.time()

    if user_id not in rate_limit_data:
        rate_limit_data[user_id] = {
            "last_request": current_time,
            "request_count": 1,
            "warning_count": 0
        }
    else:
        # Reset counter if more than 60 seconds since last request
        if current_time - rate_limit_data[user_id]["last_request"] > 60:
            rate_limit_data[user_id] = {
                "last_request": current_time,
                "request_count": 1,
                "warning_count": rate_limit_data[user_id].get("warning_count", 0)
            }
        else:
            # Increment counter
            rate_limit_data[user_id]["last_request"] = current_time
            rate_limit_data[user_id]["request_count"] += 1

    # Check if user is sending too many requests (more than 15 per minute)
    if rate_limit_data[user_id]["request_count"] > 15:
        rate_limit_data[user_id]["warning_count"] += 1
        rate_limit_data[user_id]["request_count"] = 0

        language = await get_user_language(str(user_id))

        # Block user if they've received too many warnings
        if rate_limit_data[user_id]["warning_count"] >= 3:
            blocked_users.add(user_id)
            logger.warning(f"User {user_id} blocked for excessive requests")
            if update.message:
                await update.message.reply_text(
                    _("You have been blocked for sending too many requests. Please contact an administrator.", language)
                )
            return False

        # Warn user
        if update.message:
            await update.message.reply_text(
                _("You are sending too many requests. Please slow down. Warning {count}/3.", language).format(
                    count=rate_limit_data[user_id]["warning_count"]
                )
            )

        return False

    return True


async def error_handler_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
    """Handle errors that occur during request processing."""
    logger.error(f"Exception while handling an update: {error}")

    # Try to notify the user
    if update and update.effective_user:
        user_id = update.effective_user.id
        language = await get_user_language(str(user_id))

        try:
            if update.callback_query:
                await update.callback_query.answer(
                    _("An error occurred. Please try again later.", language)
                )
            elif update.message:
                await update.message.reply_text(
                    _("An error occurred while processing your request. Please try again later.", language)
                )
        except Exception as e:
            logger.error(f"Failed to send error message to user: {e}")


async def language_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store user's language preference in context for easy access."""
    if update.effective_user:
        telegram_id = str(update.effective_user.id)
        language = await get_user_language(telegram_id)
        context.user_data["language"] = language


async def game_state_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and update game state information as needed."""
    if update.effective_user:
        telegram_id = str(update.effective_user.id)

        # Only try to get player data if the user is registered
        registered = await player_exists(telegram_id)
        if registered:
            player_data = await get_player(telegram_id)
            if player_data:
                # Store relevant game state in context.user_data for easy access
                context.user_data["player_data"] = player_data
                context.user_data["resources"] = player_data.get("resources", {})
                context.user_data["actions_remaining"] = player_data.get("actions_remaining", 0)
                context.user_data["quick_actions_remaining"] = player_data.get("quick_actions_remaining", 0)


async def combined_middleware_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Combined middleware handler that runs middleware functions in sequence with optimized error handling."""
    middleware_funcs = [
        log_middleware,
        rate_limit_middleware,
        authentication_middleware,
        language_middleware,
        game_state_middleware
    ]

    await apply_middleware_chain(update, context, middleware_funcs)


def setup_middleware(application: Application, admin_user_ids: List[int]) -> None:
    """Set up all middleware for the application."""
    global admin_ids
    admin_ids = admin_user_ids

    # Create proper handler for middleware
    application.add_handler(
        MessageHandler(filters.ALL, combined_middleware_handler), -1
    )
    application.add_handler(
        CallbackQueryHandler(combined_middleware_handler), -1
    )

    # Register error handler
    application.add_error_handler(
        lambda update, context: error_handler_middleware(update, context, context.error)
    )

    logger.info("Middleware setup complete")