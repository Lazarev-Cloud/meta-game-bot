#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified message handling utilities for the Meta Game bot.
"""

import logging
from typing import Optional, Union, Dict, Any

from telegram import Update, InlineKeyboardMarkup, Message
from telegram.ext import ContextTypes

# Initialize logger
logger = logging.getLogger(__name__)


async def send_message(
        update: Update,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> Optional[Message]:
    """
    Send a message to the user, handling both regular messages and callback queries.

    Args:
        update: The update object
        text: Message text to send
        keyboard: Optional inline keyboard markup
        parse_mode: Message parsing mode
        context: PTB context object (optional)

    Returns:
        The sent message object, or None if sending failed
    """
    try:
        if update.callback_query:
            # For callback queries, edit the existing message
            return await update.callback_query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        elif update.message:
            # For regular messages, send a new reply
            return await update.message.reply_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        elif context and context.bot:
            # Fallback if neither callback_query nor message is available
            # but we have the context with user's chat_id
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id:
                return await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=keyboard
                )
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")

    return None


async def edit_or_reply(
        update: Update,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown"
) -> Optional[Message]:
    """
    Edit message for callback queries or reply for regular messages.

    Args:
        update: The update object
        text: Message text
        keyboard: Optional inline keyboard markup
        parse_mode: Message parsing mode

    Returns:
        The message object, or None if failed
    """
    return await send_message(update, text, keyboard, parse_mode)


async def answer_callback(
        update: Update,
        text: Optional[str] = None,
        show_alert: bool = False
) -> None:
    """
    Answer a callback query with optional text.

    Args:
        update: The update object
        text: Optional text to show (limited to 200 characters)
        show_alert: Whether to show as alert or toast notification
    """
    if update.callback_query:
        try:
            await update.callback_query.answer(
                text=text[:200] if text else None,
                show_alert=show_alert
            )
        except Exception as e:
            logger.error(f"Error answering callback query: {str(e)}")


async def send_action_confirmation(
        update: Update,
        action_data: Dict[str, Any],
        language: str
) -> Optional[Message]:
    """
    Send standardized action confirmation message.

    Args:
        update: The update object
        action_data: Data about the confirmed action
        language: User's language code

    Returns:
        The sent message object, or None if sending failed
    """
    from utils.i18n import _
    from utils.formatting import format_action_confirmation

    # Format the action confirmation text
    confirmation_text = await format_action_confirmation(action_data, language)

    # Send the message
    return await send_message(update, confirmation_text)