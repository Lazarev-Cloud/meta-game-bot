#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete middleware implementation for the Meta Game bot including 
authentication, logging, and rate limiting.
"""

import logging
import time
from typing import Dict, Set, List, Any

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
    """Authenticate users and ensure they are registered for game commands."""
    user = update.effective_user

    if not user:
        logger.warning("Update received without a user")
        return False

    # Allow any user to use /start for registration
    if update.message and update.message.text and update.message.text.startswith("/start"):
        return True

    # Allow admin commands for admins
    if update.message and update.message.text and update.message.text.startswith("/admin"):
        if user.id in admin_ids:
            return True
        else:
            # Unauthorized admin command attempt
            logger.warning(f"User {user.id} attempted unauthorized admin command: {update.message.text}")
            language = await get_user_language(str(user.id))
            await update.message.reply_text(
                _("You don't have permission to use admin commands.", language)
            )
            return False

    # Check if user is registered for game commands
    if update.message and update.message.text and update.message.text.startswith("/"):
        # Skip common non-game commands
        if update.message.text.startswith("/help"):
            return True

        is_registered = await player_exists(str(user.id))

        if not is_registered:
            language = "en_US"  # Default before registration
            await update.message.reply_text(
                _("You are not registered as a player. Please use the /start command to register.", language)
            )
            return False

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
    """Combined middleware handler to run all middleware functions."""
    try:
        # Always log first
        await log_middleware(update, context)

        # Run rate limiting check
        if not await rate_limit_middleware(update, context):
            return

        # Run authentication check
        if not await authentication_middleware(update, context):
            return

        # Set language in context
        await language_middleware(update, context)

        # Update game state if needed
        await game_state_middleware(update, context)

    except Exception as e:
        # Handle any errors in middleware
        await error_handler_middleware(update, context, e)


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
