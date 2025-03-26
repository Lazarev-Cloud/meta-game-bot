#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified messaging utilities for the Meta Game bot.
"""

import logging
import re
from typing import Optional, Dict, Any, List, Union, Tuple

from telegram import Update, InlineKeyboardMarkup, Message, InlineKeyboardButton, Bot
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TimedOut, TelegramError

# Initialize logger
logger = logging.getLogger(__name__)

# Maximum message length for Telegram
MAX_MESSAGE_LENGTH = 4096


async def send_message(
        update: Update,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        disable_web_page_preview: bool = True,
        chat_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None
) -> Optional[Message]:
    """
    Send a message to the user, handling both regular messages and callback queries.
    """
    # Ensure text is not None or empty
    if not text:
        text = "No message content"

    # Get the chat ID if not provided
    if not chat_id and update.effective_chat:
        chat_id = update.effective_chat.id

    # If we don't have a chat_id, we can't send a message
    if not chat_id and not update.callback_query:
        logger.error("No chat ID available to send message")
        return None

    # Clean up Markdown to avoid parsing errors
    text, parse_mode = await fixup_message_text(text, parse_mode)

    # Safely truncate text if it's too long
    if len(text) > MAX_MESSAGE_LENGTH:
        logger.warning(f"Message too long ({len(text)} chars), truncating")
        text = text[:MAX_MESSAGE_LENGTH - 3] + "..."

    try:
        if update.callback_query:
            # For callback queries, edit the existing message
            return await update.callback_query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard,
                disable_web_page_preview=disable_web_page_preview
            )
        elif update.message and not chat_id:
            # For regular messages, send a new reply
            return await update.message.reply_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard,
                disable_web_page_preview=disable_web_page_preview,
                reply_to_message_id=reply_to_message_id
            )
        elif chat_id:
            # When a specific chat_id is provided
            bot = context.bot if context else update.get_bot()
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard,
                disable_web_page_preview=disable_web_page_preview,
                reply_to_message_id=reply_to_message_id
            )
    except (BadRequest, TimedOut) as e:
        # Handle specific Telegram API errors
        error_text = str(e).lower()

        if "message is not modified" in error_text:
            # Not a real error - message is identical
            logger.debug("Message not modified (identical content)")
            if update.callback_query and update.callback_query.message:
                return update.callback_query.message
            return None
        elif "message to edit not found" in error_text:
            # Message was deleted or is too old
            logger.warning("Message to edit not found")
            # Try sending a new message if context is available
            if context and chat_id:
                try:
                    return await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as new_msg_error:
                    logger.error(f"Failed to send new message: {new_msg_error}")
        elif "can't parse entities" in error_text:
            # Parsing mode error, try without parse_mode
            logger.warning(f"Parse mode error, trying without formatting: {e}")
            return await send_message(
                update,
                text,
                keyboard=keyboard,
                parse_mode=None,
                context=context,
                disable_web_page_preview=disable_web_page_preview,
                chat_id=chat_id
            )
        else:
            logger.error(f"Error sending message: {e}")
            # Try a simplified message as last resort
            try:
                if update.callback_query:
                    return await update.callback_query.edit_message_text(
                        text=text[:1000] + "..." if len(text) > 1000 else text,
                        reply_markup=keyboard
                    )
                elif update.message and not chat_id:
                    return await update.message.reply_text(
                        text=text[:1000] + "..." if len(text) > 1000 else text,
                        reply_markup=keyboard
                    )
                elif chat_id and context:
                    return await context.bot.send_message(
                        chat_id=chat_id,
                        text=text[:1000] + "..." if len(text) > 1000 else text,
                        reply_markup=keyboard
                    )
            except Exception as fallback_error:
                logger.error(f"Fallback send also failed: {fallback_error}")
    except Exception as e:
        logger.error(f"Unexpected error sending message: {e}")

    return None


async def edit_or_reply(
        update: Update,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Edit message for callback queries or reply for regular messages.
    Convenience wrapper around send_message.
    """
    return await send_message(
        update,
        text,
        keyboard,
        parse_mode,
        disable_web_page_preview=disable_web_page_preview
    )


async def answer_callback(
        update: Update,
        text: Optional[str] = None,
        show_alert: bool = False,
        cache_time: int = 0
) -> bool:
    """
    Answer a callback query with optional text.
    """
    if update.callback_query:
        try:
            await update.callback_query.answer(
                text=text[:200] if text else None,
                show_alert=show_alert,
                cache_time=cache_time
            )
            return True
        except Exception as e:
            logger.error(f"Error answering callback query: {str(e)}")
    return False


async def fixup_message_text(text: str, parse_mode: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Fix up message text to avoid formatting issues.
    """
    if not parse_mode:
        return text, None

    # Try to detect unclosed formatting
    if parse_mode.lower() == "markdown":
        # Check for unclosed formatting markers
        marker_counts = {
            '*': text.count('*'),
            '_': text.count('_'),
            '`': text.count('`'),
            '[': text.count('['),
            ']': text.count(']')
        }

        if marker_counts['*'] % 2 != 0 or marker_counts['_'] % 2 != 0 or marker_counts['`'] % 2 != 0 or marker_counts[
            '['] != marker_counts[']']:
            # Unbalanced formatting, escape the problematic characters
            return await escape_markdown(text), None

    elif parse_mode.lower() == "html":
        # Simple check for unbalanced HTML tags
        if text.count('<') != text.count('>'):
            return await escape_html(text), None

    return text, parse_mode


async def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown formatting."""
    if not text:
        return ""

    # Escape special Markdown characters
    escape_chars = r'_*`[]()~>#+-=|{}.!'
    return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', text)


async def escape_html(text: str) -> str:
    """Escape special characters for HTML formatting."""
    if not text:
        return ""

    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


async def create_error_message(error: Exception, language: str, operation: str = "") -> str:
    """
    Create a user-friendly error message based on the exception.
    """
    # Import _ function here to avoid circular imports
    from utils.i18n import _

    error_text = str(error).lower()

    # Create appropriate user-facing message based on error type
    if "permission denied" in error_text or "not authorized" in error_text:
        return _("You don't have permission to perform this action.", language)
    elif "connection" in error_text or "timeout" in error_text:
        return _("Server connection issue. Please try again later.", language)
    elif "not enough" in error_text or "resource" in error_text:
        return _("You don't have enough resources for this action.", language)
    elif "not found" in error_text:
        if "player" in error_text:
            return _("Player not found. Please check the name.", language)
        elif "district" in error_text:
            return _("District not found. Please check the name.", language)
        elif "politician" in error_text:
            return _("Politician not found. Please check the name.", language)
        else:
            return _("The requested item was not found.", language)
    elif "deadline" in error_text or "closed" in error_text:
        return _("The submission deadline for this cycle has passed.", language)
    elif "already exists" in error_text:
        return _("This already exists.", language)
    else:
        # Generic error message
        if operation:
            return _("Error during {operation}: {error}", language).format(
                operation=operation,
                error=str(error)
            )
        return _("An error occurred. Please try again later.", language)