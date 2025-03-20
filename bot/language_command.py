#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language command implementation for Belgrade Game Bot
Handles language switching and related functionality
"""

import logging
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from languages import get_text, get_player_language, set_player_language
from language_utils import (
    SUPPORTED_LANGUAGES,
    create_language_keyboard,
    get_language_name,
    detect_user_language
)
from database.utils import update_user_activity, get_user

logger = logging.getLogger(__name__)

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /language command to change interface language."""
    try:
        user = update.effective_user
        
        # Check if user exists in database
        db_user = get_user(user.id)
        if not db_user:
            await update.message.reply_text(
                get_text("not_registered", "en")
            )
            return

        # Get current language
        current_lang = get_player_language(user.id)
        
        # Update user's activity timestamp
        await update_user_activity(user.id)

        # Create language selection keyboard
        reply_markup = create_language_keyboard(current_lang)

        # Show current language and selection options
        await update.message.reply_text(
            get_text("language_current", current_lang, language=get_language_name(current_lang)) + "\n\n" +
            get_text("language_select", current_lang),
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in language command: {e}")
        await update.message.reply_text(
            get_text("error_message", get_player_language(update.effective_user.id))
        )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    user = query.from_user
    
    try:
        # Check if user exists in database
        db_user = get_user(user.id)
        if not db_user:
            await query.answer(get_text("not_registered", "en"))
            return

        # Extract language code from callback data
        try:
            new_lang = query.data.split(":")[1]
        except (IndexError, ValueError):
            logger.error(f"Invalid callback data format: {query.data}")
            await query.answer(get_text("error_invalid_input", get_player_language(user.id)))
            return

        current_lang = get_player_language(user.id)
        
        # Validate language selection
        if new_lang not in SUPPORTED_LANGUAGES:
            logger.warning(f"Invalid language selection attempt: {new_lang}")
            await query.answer(get_text("language_invalid", current_lang))
            return

        # Don't update if the same language is selected
        if new_lang == current_lang:
            await query.answer(get_text("language_current", current_lang, language=get_language_name(current_lang)))
            return

        # Update user's language preference
        if set_player_language(user.id, new_lang):
            # Update activity timestamp
            await update_user_activity(user.id)
            
            # Confirm language change
            await query.answer(get_text("language_changed", new_lang))
            
            # Update message with new keyboard
            reply_markup = create_language_keyboard(new_lang)
            await query.edit_message_text(
                get_text("language_current", new_lang, language=get_language_name(new_lang)) + "\n\n" +
                get_text("language_select", new_lang),
                reply_markup=reply_markup
            )
            
            logger.info(f"Language changed to {new_lang} for user {user.id}")
        else:
            # Handle database update failure
            await query.answer(get_text("language_change_failed", current_lang))
            logger.error(f"Failed to update language for user {user.id}")

    except Exception as e:
        logger.error(f"Error in language callback: {e}")
        try:
            current_lang = get_player_language(user.id)
            await query.answer(get_text("error_message", current_lang))
        except:
            await query.answer(get_text("error_message", "en")) 