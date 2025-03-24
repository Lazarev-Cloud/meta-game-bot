#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified message handling utilities for the Meta Game bot.
"""

import logging
from typing import Optional, Dict, Any, List, Union, Tuple

from telegram import Update, InlineKeyboardMarkup, Message, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.i18n import _

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


async def create_keyboard(
        buttons: List[List[Dict[str, str]]],
        language: str
) -> InlineKeyboardMarkup:
    """
    Create an inline keyboard from a list of button definitions.

    Args:
        buttons: List of button rows, each containing dicts with 'text' and 'callback_data'
        language: User's language for translation

    Returns:
        The created InlineKeyboardMarkup
    """
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button in row:
            text = _(button["text"], language) if isinstance(button["text"], str) else button["text"]

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
    from utils.formatting import format_action_confirmation

    # Format the action confirmation text
    confirmation_text = await format_action_confirmation(action_data, language)

    # Send the message
    return await send_message(update, confirmation_text)


async def send_paginated_content(
        update: Update,
        content_items: List[Dict[str, Any]],
        page: int,
        format_func: callable,
        language: str,
        page_size: int = 5,
        navigation_callback_prefix: str = "page:",
        additional_buttons: Optional[List[List[Dict[str, str]]]] = None
) -> Optional[Message]:
    """
    Send paginated content with navigation buttons.

    Args:
        update: The update object
        content_items: List of content items to paginate
        page: Current page number (0-indexed)
        format_func: Function to format the content items for display
        language: User's language code
        page_size: Number of items per page
        navigation_callback_prefix: Prefix for navigation callbacks
        additional_buttons: Additional buttons to add to the keyboard

    Returns:
        The sent message object, or None if sending failed
    """
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
            )
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
    return await send_message(update, content_text, keyboard=keyboard)


async def split_long_message(
        text: str,
        max_length: int = 4000
) -> List[str]:
    """
    Split a long message into multiple parts that respect message length limits.

    Args:
        text: The text to split
        max_length: Maximum length per message

    Returns:
        List of message parts
    """
    if len(text) <= max_length:
        return [text]

    parts = []

    # Try to split on double newlines to keep paragraphs together
    paragraphs = text.split('\n\n')
    current_part = ""

    for paragraph in paragraphs:
        # If adding this paragraph would exceed the limit
        if len(current_part) + len(paragraph) + 2 > max_length:
            # If current_part is not empty, add it to parts
            if current_part:
                parts.append(current_part)
                current_part = ""

            # If paragraph itself is too long, split it further
            if len(paragraph) > max_length:
                # Split on single newlines
                lines = paragraph.split('\n')
                for line in lines:
                    if len(current_part) + len(line) + 1 > max_length:
                        if current_part:
                            parts.append(current_part)
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
        parts.append(current_part)

    return parts


async def send_long_message(
        update: Update,
        text: str,
        keyboard: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "Markdown",
        max_length: int = 4000,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> Optional[Message]:
    """
    Send a long message, splitting it into multiple messages if needed.

    Args:
        update: The update object
        text: Message text to send
        keyboard: Optional inline keyboard markup (only added to last part)
        parse_mode: Message parsing mode
        max_length: Maximum length per message
        context: PTB context object (optional)

    Returns:
        The last sent message object, or None if sending failed
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
            context=context
        )

        if message:
            last_message = message

    return last_message