#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language utilities for Belgrade Game Bot
Extends the base language.py functionality with additional utilities
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import List, Dict, Optional, Union, Any
from database.utils import get_user_language, update_user_language, update_detected_language
from database.schema import Language
from languages import get_text

logger = logging.getLogger(__name__)

# Supported languages with their display names
SUPPORTED_LANGUAGES = ["en", "ru"]
LANGUAGE_NAMES = {
    "en": "English",
    "ru": "Русский"
}

def get_language_name(lang_code: str) -> str:
    """Get the display name of a language code."""
    return LANGUAGE_NAMES.get(lang_code, lang_code.upper())

def get_nested_translation(key_path: str, lang: str = "en", **kwargs) -> str:
    """
    Get a nested translation using dot notation
    Example: get_nested_translation("resource_types.money", "en")
    """
    try:
        keys = key_path.split('.')
        text = get_text(keys[0], lang)
        
        if not isinstance(text, dict):
            return text
            
        for key in keys[1:]:
            if not isinstance(text, dict) or key not in text:
                logger.warning(f"Invalid nested key path: {key_path}")
                return f"[Invalid key: {key_path}]"
            text = text[key]
            
        if kwargs and isinstance(text, str):
            try:
                return text.format(**kwargs)
            except KeyError as e:
                logger.error(f"Format error in nested translation: {e}")
                return text
                
        return text
        
    except Exception as e:
        logger.error(f"Error in get_nested_translation: {e}")
        return f"[Error: {key_path}]"

async def detect_user_language(update: Update) -> str:
    """
    Attempt to detect the user's preferred language based on their settings

    Args:
        update: The telegram update object

    Returns:
        str: Detected language code ('en' or 'ru')
    """
    try:
        user = update.effective_user

        # If the user already has a language preference in our database, use that
        current_lang = get_user_language(user.id)
        if current_lang in SUPPORTED_LANGUAGES:
            logger.debug(f"Using stored language preference for user {user.id}: {current_lang}")
            return current_lang

        # Check if Telegram provides the user's language
        user_language = user.language_code
        if user_language:
            # Extract base language code (e.g., 'ru-RU' -> 'ru')
            base_lang = user_language.split('-')[0].lower()
            
            if base_lang in SUPPORTED_LANGUAGES:
                logger.info(f"Detected language from Telegram for user {user.id}: {base_lang}")
                # Update detected language in the database
                await update_detected_language(user.id, base_lang)
                return base_lang
            else:
                logger.debug(f"Unsupported Telegram language for user {user.id}: {user_language}")

        # Default to English
        logger.debug(f"Using default language (en) for user {user.id}")
        return "en"

    except Exception as e:
        logger.error(f"Error in detect_user_language: {e}")
        return "en"

def create_language_keyboard(current_lang: str) -> InlineKeyboardMarkup:
    """
    Create a keyboard for language selection

    Args:
        current_lang: Current language code

    Returns:
        InlineKeyboardMarkup: Keyboard with language options
    """
    try:
        keyboard = []
        for lang in SUPPORTED_LANGUAGES:
            button_text = get_text(f"language_button_{lang}", current_lang)
            # Add a marker to show current language
            if lang == current_lang:
                button_text += " ✓"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"lang:{lang}")])
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"Error creating language keyboard: {e}")
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("English", callback_data="lang:en"),
            InlineKeyboardButton("Русский", callback_data="lang:ru")
        ]])

async def create_localized_keyboard(
    items: List[Dict[str, Any]],
    lang: str = "en",
    row_width: int = 1
) -> InlineKeyboardMarkup:
    """
    Create a localized keyboard where button labels are translated

    Args:
        items: List of items with 'text' and 'callback_data' keys
        lang: Language code
        row_width: Number of buttons per row

    Returns:
        InlineKeyboardMarkup: Keyboard with translated buttons
    """
    try:
        keyboard = []
        row = []
        
        for item in items:
            # Get translation key if provided, otherwise use text as is
            text = item.get('text', '')
            if 'translation_key' in item:
                text = get_text(item['translation_key'], lang, text)
                
            button = InlineKeyboardButton(
                text=text,
                callback_data=item.get('callback_data', '')
            )
            row.append(button)
            
            if len(row) >= row_width:
                keyboard.append(row)
                row = []
        
        if row:  # Add any remaining buttons
            keyboard.append(row)
            
        return InlineKeyboardMarkup(keyboard)

    except Exception as e:
        logger.error(f"Error creating localized keyboard: {e}")
        # Return a single button with error message
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(
                get_text("error_message", lang, "Error"),
                callback_data="error"
            )
        ]])

def format_command_description(command: str, description_key: str, lang: str = "en") -> str:
    """
    Format a command and its description for help messages

    Args:
        command: Command name (e.g., '/start')
        description_key: Translation key for command description
        lang: Language code

    Returns:
        str: Formatted command description
    """
    try:
        desc = get_text(description_key, lang)
        return f"{command} - {desc}"
    except Exception as e:
        logger.error(f"Error formatting command description: {e}")
        return f"{command} - {description_key}"

def format_resource_name(resource_type: str, lang: str = "en") -> str:
    """
    Get the localized name of a resource type

    Args:
        resource_type: Resource type key
        lang: Language code

    Returns:
        str: Localized resource name
    """
    try:
        return get_nested_translation(f"resource_types.{resource_type}", lang)
    except Exception as e:
        logger.error(f"Error formatting resource name: {e}")
        return resource_type.title()

def format_district_name(district_code: str, lang: str = "en") -> str:
    """
    Get the localized name of a district

    Args:
        district_code: District code
        lang: Language code

    Returns:
        str: Localized district name
    """
    try:
        return get_nested_translation(f"districts.{district_code}", lang)
    except Exception as e:
        logger.error(f"Error formatting district name: {e}")
        return district_code.replace('_', ' ').title()

def format_action_name(action_type: str, lang: str = "en") -> str:
    """
    Get the localized name of an action type

    Args:
        action_type: Action type key
        lang: Language code

    Returns:
        str: Localized action name
    """
    try:
        return get_nested_translation(f"action_types.{action_type}", lang)
    except Exception as e:
        logger.error(f"Error formatting action name: {e}")
        return action_type.replace('_', ' ').title()