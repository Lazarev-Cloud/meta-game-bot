#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language utilities for Belgrade Game Bot
Extends the base language.py functionality with additional utilities
"""

import logging
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from languages import get_text, set_player_language, get_player_language

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ["en", "ru"]


async def detect_user_language(update: Update) -> str:
    """
    Attempt to detect the user's preferred language based on their settings

    Args:
        update: The telegram update object

    Returns:
        str: Detected language code ('en' or 'ru')
    """
    user = update.effective_user

    # If the user already has a language preference in our database, use that
    db_language = get_player_language(user.id)
    if db_language in SUPPORTED_LANGUAGES:
        return db_language

    # Check if Telegram provides the user's language
    user_language = user.language_code
    if user_language and user_language.split('-')[0] in SUPPORTED_LANGUAGES:
        # Extract base language code (e.g., 'ru-RU' -> 'ru')
        detected_lang = user_language.split('-')[0]
        # Update in the database if the user exists
        _update_detected_language(user.id, detected_lang)
        return detected_lang

    # Default to English
    return "en"


def _update_detected_language(user_id: int, language: str) -> None:
    """
    Update the detected language for an existing user

    Args:
        user_id: Telegram user ID
        language: Language code to set
    """
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check if player exists first
        cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE players SET language = ? WHERE player_id = ?",
                (language, user_id)
            )
            conn.commit()

        conn.close()
    except Exception as e:
        logger.error(f"Error updating detected language: {e}")


async def create_localized_keyboard(keyboard_items, lang="en"):
    """
    Create a localized keyboard where button labels are translated

    Args:
        keyboard_items: List of keyboard items to translate
        lang: Language code

    Returns:
        List of translated keyboard items
    """
    translated_keyboard = []

    for row in keyboard_items:
        translated_row = []
        for button in row:
            # If button has text property, translate it
            if hasattr(button, 'text'):
                button.text = get_text(button.text, lang, button.text)
            translated_row.append(button)
        translated_keyboard.append(translated_row)

    return translated_keyboard


def format_command_description(command, description, lang="en"):
    """
    Format a command and its description for help messages

    Args:
        command: Command name (e.g., '/start')
        description: Command description key
        lang: Language code

    Returns:
        str: Formatted command description
    """
    desc = get_text(description, lang, f"Command {command}")
    return f"{command} - {desc}"