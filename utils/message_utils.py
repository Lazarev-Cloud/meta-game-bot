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

    This unified function handles both message types and provides clean error handling.
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
    if parse_mode == "Markdown":
        text, parse_mode = await fixup_message_text(text, parse_mode)

    # Safely truncate text if it's too long
    if len(text) > MAX_MESSAGE_LENGTH:
        logger.warning(f"Message too long ({len(text)} chars), truncating to {MAX_MESSAGE_LENGTH} chars")
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

    Args:
        update: The update object
        text: Optional text to show (limited to 200 characters)
        show_alert: Whether to show as alert or toast notification
        cache_time: Time in seconds for caching the response

    Returns:
        True if successful, False otherwise
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


async def create_keyboard(
        buttons: List[List[Dict[str, str]]],
        language: str
) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard from a list of button definitions.

    This helper function simplifies keyboard creation and handles translations.
    """
    # Import here to avoid circular imports
    from utils.i18n import _

    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button in row:
            text = _(button["text"], language) if "text" in button else "Button"

            # Handle different button types (callback, url, etc.)
            if "url" in button:
                keyboard_row.append(InlineKeyboardButton(text, url=button["url"]))
            elif "callback_data" in button:
                keyboard_row.append(InlineKeyboardButton(text, callback_data=button["callback_data"]))
            elif "switch_inline_query" in button:
                keyboard_row.append(InlineKeyboardButton(text, switch_inline_query=button["switch_inline_query"]))
            elif "switch_inline_query_current_chat" in button:
                keyboard_row.append(InlineKeyboardButton(
                    text,
                    switch_inline_query_current_chat=button["switch_inline_query_current_chat"]
                ))

        keyboard.append(keyboard_row)

    return InlineKeyboardMarkup(keyboard)


async def split_long_message(
        text: str,
        max_length: int = MAX_MESSAGE_LENGTH
) -> List[str]:
    """
    Split a long message into multiple parts that respect message length limits.

    Intelligently splits on paragraph boundaries when possible.
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    # Try to split on double newlines to keep paragraphs together
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if len(current_part) + len(paragraph) + 2 > max_length:
            # If current_part is not empty, add it to parts
            if current_part:
                parts.append(current_part.strip())
                current_part = ""

            # If paragraph itself is too long, split it further
            if len(paragraph) > max_length:
                # Split on single newlines
                lines = paragraph.split('\n')
                for line in lines:
                    if len(current_part) + len(line) + 1 > max_length:
                        if current_part:
                            parts.append(current_part.strip())
                            current_part = ""

                        # If even a single line is too long, split it into chunks
                        if len(line) > max_length:
                            for i in range(0, len(line), max_length):
                                parts.append(line[i:i + max_length])
                        else:
                            current_part = line
                    else:
                        if current_part:
                            current_part += "\n" + line
                        else:
                            current_part = line
            else:
                current_part = paragraph
        else:
            if current_part:
                current_part += "\n\n" + paragraph
            else:
                current_part = paragraph

    if current_part:
        parts.append(current_part.strip())

    return parts


async def send_long_message(
        update: Update,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        max_length: int = MAX_MESSAGE_LENGTH,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Send a long message, splitting it into multiple messages if needed.

    Returns the last message sent, which contains any keyboard attachments.
    """
    parts = await split_long_message(text, max_length)

    last_message = None

    for i, part in enumerate(parts):
        # Only add keyboard to the last part
        part_keyboard = keyboard if i == len(parts) - 1 else None

        # Send this part
        message = await send_message(
            update,
            part,
            keyboard=part_keyboard,
            parse_mode=parse_mode,
            context=context,
            disable_web_page_preview=disable_web_page_preview
        )

        if message:
            last_message = message

        # Add a small delay if sending multiple messages to avoid rate limiting
        if i < len(parts) - 1:
            import asyncio
            await asyncio.sleep(0.5)

    return last_message


async def escape_markdown(text: str, version: int = 1) -> str:
    """Escape special characters for Markdown formatting."""
    if not text:
        return ""

    if version == 1:
        # Markdown v1
        escape_chars = r'_*`['
        return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', text)
    else:
        # Markdown v2
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', text)


async def escape_html(text: str) -> str:
    """Escape special characters for HTML formatting."""
    if not text:
        return ""

    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


async def fixup_message_text(text: str, parse_mode: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Fix up message text to avoid formatting issues.

    This crucial utility prevents common Markdown/HTML formatting errors.
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


async def send_paginated_content(
        update: Update,
        content_items: List[Dict[str, Any]],
        page: int,
        format_func: callable,
        language: str,
        page_size: int = 5,
        navigation_callback_prefix: str = "page:",
        additional_buttons: Optional[List[List[Dict[str, str]]]] = None,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> Optional[Message]:
    """
    Send paginated content with navigation buttons.

    Perfect for news, lists of politicians, districts, etc.
    """
    from utils.i18n import _

    # Calculate pagination info
    total_items = len(content_items)
    total_pages = (total_items + page_size - 1) // page_size  # Ceiling division

    if total_items == 0:
        # No items to display
        return await send_message(
            update,
            _("No items to display.", language),
            keyboard=await create_keyboard(
                [
                    [{"text": _("Back", language), "callback_data": "back_to_menu"}]
                ],
                language
            ),
            context=context
        )

    # Ensure page is within valid range
    page = max(0, min(page, total_pages - 1))

    # Get items for current page
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)
    current_items = content_items[start_idx:end_idx]

    # Format content
    content_text = await format_func(current_items, language)

    # Add pagination info
    content_text += f"\n\n{_('Page', language)} {page + 1}/{total_pages}"

    # Create navigation buttons
    buttons = []
    nav_row = []

    if page > 0:
        nav_row.append({
            "text": f"◀️ {_('Previous', language)}",
            "callback_data": f"{navigation_callback_prefix}prev"
        })

    if page < total_pages - 1:
        nav_row.append({
            "text": f"{_('Next', language)} ▶️",
            "callback_data": f"{navigation_callback_prefix}next"
        })

    if nav_row:
        buttons.append(nav_row)

    # Add additional buttons
    if additional_buttons:
        buttons.extend(additional_buttons)

    # Add back button if not already included
    if not any(any(button.get("callback_data") == "back_to_menu" for button in row) for row in buttons):
        buttons.append([{"text": _("Back", language), "callback_data": "back_to_menu"}])

    # Create keyboard
    keyboard = await create_keyboard(buttons, language)

    # Send message
    return await send_message(update, content_text, keyboard=keyboard, context=context)


# Standardized keyboards builder
async def get_standard_keyboard(keyboard_type: str, language: str, **kwargs) -> InlineKeyboardMarkup:
    """
    Get a standard keyboard based on type with proper translations.

    Centralizes keyboard creation for consistency across the bot.
    """
    from utils.i18n import _

    if keyboard_type == "yes_no":
        return await create_keyboard([
            [
                {"text": _("Yes", language), "callback_data": "yes"},
                {"text": _("No", language), "callback_data": "no"}
            ]
        ], language)

    elif keyboard_type == "back":
        callback = kwargs.get("callback_data", "back_to_menu")
        return await create_keyboard([
            [{"text": _("Back", language), "callback_data": callback}]
        ], language)

    elif keyboard_type == "confirmation":
        return await create_keyboard([
            [
                {"text": _("Confirm", language), "callback_data": "confirm"},
                {"text": _("Cancel", language), "callback_data": "cancel_selection"}
            ]
        ], language)

    # Add more standard keyboards as needed

    # Default fallback to simple back button
    return await create_keyboard([
        [{"text": _("Back", language), "callback_data": "back_to_menu"}]
    ], language)