#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified internationalization module for the Meta Game bot.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

from db import player_exists

# Initialize logger
logger = logging.getLogger(__name__)

# Global translations storage
_translations = {
    "en_US": {},
    "ru_RU": {}
}


def _(text: str, language: str = "en_US") -> str:
    """
    Translate a text string to the specified language.

    Args:
        text: Text string to translate
        language: Language code (en_US or ru_RU)

    Returns:
        Translated string or original text if no translation is found
    """
    if language not in _translations:
        language = "en_US"

    # Return the translation if it exists, otherwise return the original text
    return _translations[language].get(text, text)


async def get_user_language(telegram_id: str) -> str:
    """
    Get a user's preferred language.

    Args:
        telegram_id: User's Telegram ID

    Returns:
        Language code (en_US or ru_RU)
    """
    try:
        # Check if player exists in database
        exists = await player_exists(telegram_id)

        if exists:
            # Try to get language from database
            try:
                from db.db_client import get_player_language
                language = await get_player_language(telegram_id)
                if language in ["en_US", "ru_RU"]:
                    return language
            except Exception as e:
                logger.warning(f"Error getting player language from database: {e}")

        # Default to English if not found or error occurs
        return "en_US"
    except Exception as e:
        logger.error(f"Error in get_user_language: {e}")
        return "en_US"


async def set_user_language(telegram_id: str, language: str) -> bool:
    """
    Set a user's preferred language.

    Args:
        telegram_id: User's Telegram ID
        language: Language code (en_US or ru_RU)

    Returns:
        True if successful, False otherwise
    """
    if language not in ["en_US", "ru_RU"]:
        return False

    try:
        # Check if player exists in database
        exists = await player_exists(telegram_id)

        if exists:
            # Try to set language in database
            try:
                from db.db_client import set_player_language
                return await set_player_language(telegram_id, language)
            except Exception as e:
                logger.warning(f"Error setting player language in database: {e}")
                return False
        else:
            # Store in memory for now (will be saved after registration)
            return True
    except Exception as e:
        logger.error(f"Error in set_user_language: {e}")
        return False


def setup_i18n() -> None:
    """Initialize the internationalization system with default translations."""
    # Initialize default translations for English
    _translations["en_US"].update({
        "Yes": "Yes",
        "No": "No",
        "Back": "Back",
        "Cancel": "Cancel",
        "Confirm": "Confirm",
        # More default translations can be added here
    })

    # Initialize default translations for Russian
    _translations["ru_RU"].update({
        "Yes": "Да",
        "No": "Нет",
        "Back": "Назад",
        "Cancel": "Отмена",
        "Confirm": "Подтвердить",
        # More default translations can be added here
    })

    logger.info("Basic internationalization system initialized")


async def load_translations_from_file() -> None:
    """Load translations from JSON files with improved error handling."""
    # Path to translations directory
    translations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translations")

    # Create the directory if it doesn't exist
    os.makedirs(translations_dir, exist_ok=True)

    # Load for each supported language
    for lang_code in ["en_US", "ru_RU"]:
        lang_path = os.path.join(translations_dir, f"{lang_code}.json")

        try:
            if os.path.exists(lang_path):
                with open(lang_path, "r", encoding="utf-8") as f:
                    _translations[lang_code].update(json.load(f))
                    logger.info(f"Loaded {lang_code} translations from file: {len(_translations[lang_code])} keys")
            else:
                # Create an empty translations file for future use
                with open(lang_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4)
                    logger.info(f"Created empty {lang_code} translations file")
        except Exception as e:
            logger.error(f"Error loading translation file {lang_path}: {str(e)}")


async def load_translations_from_db() -> None:
    """Load translations from the database with unified error handling."""
    try:
        # Try using the db_client method first
        from db.db_client import db_operation

        async def fetch_translations():
            from db.supabase_client import get_supabase
            client = get_supabase()
            response = client.from_("translations").schema("game").select("translation_key,en_US,ru_RU").execute()
            return response.data if hasattr(response, 'data') else None

        translations_data = await db_operation(
            "load_translations_from_db",
            fetch_translations,
            default_return=[]
        )

        # Process the translations
        if translations_data:
            loaded_count = 0
            for translation in translations_data:
                key = translation.get("translation_key", "")
                if key:
                    _translations["en_US"][key] = translation.get("en_US", key)
                    _translations["ru_RU"][key] = translation.get("ru_RU", key)
                    loaded_count += 1

            logger.info(f"Loaded {loaded_count} translations from database")
        else:
            logger.info("No translations found in database")
    except Exception as e:
        logger.warning(f"Error loading translations from database: {e}")


async def load_translations() -> None:
    """
    Unified method to load translations from all sources.

    This function loads translations in the following order:
    1. Default fallback translations (hardcoded)
    2. Local files (from translations directory)
    3. Database (overrides previous sources)

    The loading is done sequentially to ensure proper override priority.
    """
    try:
        # 1. First set up default fallback translations
        setup_i18n()

        # 2. Then load from files
        await load_translations_from_file()

        # 3. Finally, try to load from database (which may override file translations)
        await load_translations_from_db()

        logger.info(
            f"Loaded translations successfully: {len(_translations['en_US'])} English, "
            f"{len(_translations['ru_RU'])} Russian keys"
        )
    except Exception as e:
        logger.error(f"Error loading translations: {str(e)}")
        logger.info("Continuing with default translations only")