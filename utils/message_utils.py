#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified message handling utilities for the Meta Game bot.
"""

import logging
import re
from typing import Optional, Dict, Any, List, Union, Tuple

from telegram import Update, InlineKeyboardMarkup, Message, InlineKeyboardButton, ReplyMarkup, ParseMode, Bot
from telegram.ext import ContextTypes
from telegram.error import BadRequest, TimedOut, TelegramError

# Initialize logger
logger = logging.getLogger(__name__)

# Maximum message length for Telegram
MAX_MESSAGE_LENGTH = 4096


async def send_message(
        update: Update,
        text: str,
        keyboard: Optional[ReplyMarkup] = None,
        parse_mode: str = "Markdown",
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        disable_web_page_preview: bool = True,
        chat_id: Optional[int] = None,
        reply_to_message_id: Optional[int] = None
) -> Optional[Message]:
    """
    Send a message to the user, handling both regular messages and callback queries.

    Args:
        update: The update object
        text: Message text to send
        keyboard: Optional inline keyboard markup
        parse_mode: Message parsing mode ("Markdown", "HTML", or None)
        context: PTB context object (optional)
        disable_web_page_preview: Whether to disable web page previews
        chat_id: Optional chat ID to override the default
        reply_to_message_id: Optional message ID to reply to

    Returns:
        The sent message object, or None if sending failed
    """
    # Ensure text is not None or empty
    if not text:
        text = "No message content"

    # Get the chat ID if not provided
    if not chat_id and update.effective_chat:
        chat_id = update.effective_chat.id

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
            # Message is identical - not a real error
            logger.debug("Message not modified, ignoring")
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
                        text=text,
                        reply_markup=keyboard
                    )
                elif update.message and not chat_id:
                    return await update.message.reply_text(
                        text=text,
                        reply_markup=keyboard
                    )
                elif chat_id and context:
                    return await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
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
        keyboard: Optional[ReplyMarkup] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Edit message for callback queries or reply for regular messages.
    Convenience wrapper around send_message.

    Args:
        update: The update object
        text: Message text
        keyboard: Optional inline keyboard markup
        parse_mode: Message parsing mode
        disable_web_page_preview: Whether to disable web page previews

    Returns:
        The message object, or None if failed
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

    Args:
        buttons: List of button rows, each containing dicts with 'text' and
                'callback_data' or 'url' keys
        language: User's language for translation

    Returns:
        The created InlineKeyboardMarkup
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


async def send_action_confirmation(
        update: Update,
        action_data: Dict[str, Any],
        language: str,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> Optional[Message]:
    """
    Send standardized action confirmation message.

    Args:
        update: The update object
        action_data: Data about the confirmed action
        language: User's language code
        context: Optional context object

    Returns:
        The sent message object, or None if sending failed
    """
    from utils.formatting import format_action_confirmation

    # Format the action confirmation text
    confirmation_text = await format_action_confirmation(action_data, language)

    # Send the message
    return await send_message(update, confirmation_text, context=context)


async def split_long_message(
        text: str,
        max_length: int = MAX_MESSAGE_LENGTH
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
    current_part = ""

    # Try to split on double newlines to keep paragraphs together
    paragraphs = text.split('\n\n')

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
        keyboard: Optional[ReplyMarkup] = None,
        parse_mode: str = "Markdown",
        max_length: int = MAX_MESSAGE_LENGTH,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        disable_web_page_preview: bool = True
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
        disable_web_page_preview: Whether to disable web page previews

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


async def send_media_message(
        update: Update,
        media_type: str,
        media: Union[str, bytes],
        caption: Optional[str] = None,
        keyboard: Optional[ReplyMarkup] = None,
        parse_mode: str = "Markdown",
        context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> Optional[Message]:
    """
    Send a media message (photo, document, audio, etc.).

    Args:
        update: The update object
        media_type: Type of media ('photo', 'document', 'audio', 'video')
        media: File path, URL, or file_id
        caption: Optional caption text
        keyboard: Optional inline keyboard markup
        parse_mode: Message parsing mode
        context: PTB context object (optional)

    Returns:
        The sent message object, or None if sending failed
    """
    if not update.effective_chat:
        logger.error("No effective chat to send media to")
        return None

    chat_id = update.effective_chat.id
    bot = context.bot if context else update.get_bot()

    try:
        if media_type == "photo":
            return await bot.send_photo(
                chat_id=chat_id,
                photo=media,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        elif media_type == "document":
            return await bot.send_document(
                chat_id=chat_id,
                document=media,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        elif media_type == "audio":
            return await bot.send_audio(
                chat_id=chat_id,
                audio=media,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        elif media_type == "video":
            return await bot.send_video(
                chat_id=chat_id,
                video=media,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=keyboard
            )
        else:
            logger.error(f"Unsupported media type: {media_type}")
            # Fall back to regular message
            if caption:
                return await send_message(
                    update,
                    caption,
                    keyboard=keyboard,
                    parse_mode=parse_mode,
                    context=context
                )
    except Exception as e:
        logger.error(f"Error sending media message: {str(e)}")
        # Try to send just the caption as fallback
        if caption:
            return await send_message(
                update,
                f"Error sending media: {str(e)}\n\n{caption}",
                keyboard=keyboard,
                parse_mode=parse_mode,
                context=context
            )

    return None


async def delete_message(
        update: Update,
        message_id: Optional[int] = None,
        context: Optional[ContextTypes.DEFAULT_TYPE] = None
) -> bool:
    """
    Delete a message.

    Args:
        update: The update object
        message_id: Optional message ID (uses callback query message if not provided)
        context: PTB context object (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        if update.callback_query and not message_id:
            # Delete the message that contains the callback button
            await update.callback_query.message.delete()
            return True

        chat_id = update.effective_chat.id if update.effective_chat else None
        if not chat_id:
            logger.error("No chat ID available for message deletion")
            return False

        if not message_id and update.message:
            message_id = update.message.message_id

        if not message_id:
            logger.error("No message ID provided for deletion")
            return False

        bot = context.bot if context else update.get_bot()
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        return False


async def escape_markdown(text: str, version: int = 1) -> str:
    """
    Escape special characters for Markdown formatting.

    Args:
        text: Text to escape
        version: Markdown version (1 or 2)

    Returns:
        Escaped text
    """
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
    """
    Escape special characters for HTML formatting.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    if not text:
        return ""

    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


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

    Args:
        update: The update object
        content_items: List of content items to paginate
        page: Current page number (0-indexed)
        format_func: Function to format the content items for display
        language: User's language code
        page_size: Number of items per page
        navigation_callback_prefix: Prefix for navigation callbacks
        additional_buttons: Additional buttons to add to the keyboard
        context: PTB context object (optional)

    Returns:
        The sent message object, or None if sending failed
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


async def send_command_response(
        update: Update,
        text: str,
        keyboard: Optional[ReplyMarkup] = None,
        parse_mode: str = "Markdown",
        context: Optional[ContextTypes.DEFAULT_TYPE] = None,
        disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Send a response to a command message.

    This is a specialized version of send_message specifically for command responses.

    Args:
        update: The update object
        text: Message text to send
        keyboard: Optional inline keyboard markup
        parse_mode: Message parsing mode
        context: PTB context object (optional)
        disable_web_page_preview: Whether to disable web page previews

    Returns:
        The sent message object, or None if sending failed
    """
    return await send_message(
        update,
        text,
        keyboard=keyboard,
        parse_mode=parse_mode,
        context=context,
        disable_web_page_preview=disable_web_page_preview
    )


async def fixup_message_text(text: str, parse_mode: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Fix up message text to avoid formatting issues.

    Args:
        text: Original message text
        parse_mode: Original parse mode

    Returns:
        Tuple of (fixed_text, fixed_parse_mode)
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