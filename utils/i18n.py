#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced internationalization module for the Meta Game.
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, Callable, Awaitable

# Initialize logger
logger = logging.getLogger(__name__)

# Global translations storage
_translations = {
    "en_US": {},
    "ru_RU": {}
}

# Supported languages
SUPPORTED_LANGUAGES = ["en_US", "ru_RU"]
DEFAULT_LANGUAGE = "en_US"

# Language cache to improve performance and reduce DB calls
_language_cache = {}
_cache_timeout = 300  # 5 minutes in seconds
_cache_timestamps = {}


def _(text: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a text string to the specified language.

    Args:
        text: Text string to translate
        language: Language code (en_US or ru_RU)

    Returns:
        Translated string or original text if no translation is found
    """
    if not text:
        return ""

    # Normalize language code
    language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    # Return the translation if it exists, otherwise return the original text
    return _translations[language].get(text, text)


# Helper functions for consistent translation patterns
async def translate_resource(resource_type: str, language: str) -> str:
    """
    Translate a resource type consistently.

    Args:
        resource_type: Resource type (influence, money, information, force)
        language: Language code

    Returns:
        Translated resource name
    """
    # Ensure consistent capitalization
    resource_type = resource_type.lower()
    return _(resource_type.capitalize(), language)


async def translate_action(action_type: str, language: str) -> str:
    """
    Translate an action type consistently.

    Args:
        action_type: Action type (attack, defense, etc.)
        language: Language code

    Returns:
        Translated action name
    """
    return _(action_type, language)


async def translate_district(district_name: str, language: str) -> str:
    """
    Translate a district name if a translation exists.

    Args:
        district_name: District name
        language: Language code

    Returns:
        Translated district name or original if no translation exists
    """
    district_key = f"district.{district_name}"
    translation = _(district_key, language)
    return district_name if translation == district_key else translation


async def get_user_language(telegram_id: str) -> str:
    """
    Get a user's preferred language with improved reliability and caching.

    Args:
        telegram_id: User's Telegram ID

    Returns:
        Language code (en_US or ru_RU)
    """
    # Check if we have a recent cached value
    current_time = time.time()
    if telegram_id in _language_cache and current_time - _cache_timestamps.get(telegram_id, 0) < _cache_timeout:
        return _language_cache[telegram_id]

    try:
        # Check if player exists in database
        from db.db_client import player_exists, get_player_by_telegram_id

        exists = await player_exists(telegram_id)

        if exists:
            # Try to get language from database
            player = await get_player_by_telegram_id(telegram_id)
            if player and "language" in player and player["language"] in SUPPORTED_LANGUAGES:
                # Cache the result
                _language_cache[telegram_id] = player["language"]
                _cache_timestamps[telegram_id] = current_time
                return player["language"]
    except Exception as e:
        logger.warning(f"Error getting player language from database: {e}")

    # Default to English if not found or error occurs
    return DEFAULT_LANGUAGE


async def set_user_language(telegram_id: str, language: str) -> bool:
    """
    Set a user's preferred language with database persistence.

    Args:
        telegram_id: User's Telegram ID
        language: Language code (en_US or ru_RU)

    Returns:
        True if successful, False otherwise
    """
    if language not in SUPPORTED_LANGUAGES:
        return False

    try:
        # Check if player exists in database
        from db.db_client import player_exists, update_record

        exists = await player_exists(telegram_id)

        if exists:
            # Update language in database
            result = await update_record("players", "telegram_id", telegram_id, {"language": language})
            success = result is not None

            if success:
                # Update cache
                _language_cache[telegram_id] = language
                _cache_timestamps[telegram_id] = time.time()
                logger.info(f"Language for {telegram_id} set to {language}")
                return True
            return False
        else:
            # Store in memory temporarily (will be saved upon registration)
            _language_cache[telegram_id] = language
            _cache_timestamps[telegram_id] = time.time()
            return True
    except Exception as e:
        logger.error(f"Error setting user language: {e}")
        return False


def load_default_translations() -> None:
    """Initialize the system with essential fallback translations."""
    # Core UI elements and commonly used strings
    essentials = {
        "en_US": {
            # Basic UI elements
            "Yes": "Yes",
            "No": "No",
            "Back": "Back",
            "Cancel": "Cancel",
            "Confirm": "Confirm",
            "Main Menu": "Main Menu",
            "Status": "Status",
            "Map": "Map",
            "News": "News",
            "Resources": "Resources",
            "Previous": "Previous",
            "Next": "Next",

            # Resource types
            "Influence": "Influence",
            "Money": "Money",
            "Information": "Information",
            "Force": "Force",

            # Common actions
            "influence": "Influence",
            "attack": "Attack",
            "defense": "Defense",
            "reconnaissance": "Reconnaissance",
            "support": "Support",
            "Politician Influence": "Politician Influence",

            # Error messages
            "Error": "Error",
            "Database error": "Database error",
            "Please try again": "Please try again",

            # Languages
            "English": "English",
            "Russian": "Russian"
        },
        "ru_RU": {
            # Basic UI elements
            "Yes": "Да",
            "No": "Нет",
            "Back": "Назад",
            "Cancel": "Отмена",
            "Confirm": "Подтвердить",
            "Main Menu": "Главное меню",
            "Status": "Статус",
            "Map": "Карта",
            "News": "Новости",
            "Resources": "Ресурсы",
            "Previous": "Предыдущий",
            "Next": "Следующий",

            # Resource types
            "Influence": "Влияние",
            "Money": "Деньги",
            "Information": "Информация",
            "Force": "Сила",

            # Common actions
            "influence": "Влияние",
            "attack": "Атака",
            "defense": "Защита",
            "reconnaissance": "Разведка",
            "support": "Поддержка",
            "Politician Influence": "Влияние на Политика",

            # Error messages
            "Error": "Ошибка",
            "Database error": "Ошибка базы данных",
            "Please try again": "Пожалуйста, попробуйте снова",

            # Languages
            "English": "Английский",
            "Russian": "Русский"
        }
    }

    # Load these essentials into the translation dictionary
    for lang in SUPPORTED_LANGUAGES:
        _translations[lang].update(essentials.get(lang, {}))

    logger.info("Loaded default translations as fallback")


async def load_translations_from_file() -> None:
    """Load translations from JSON files with improved error handling."""
    # Path to translations directory
    translations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translations")

    # Create the directory if it doesn't exist
    os.makedirs(translations_dir, exist_ok=True)

    # Load for each supported language
    for lang_code in SUPPORTED_LANGUAGES:
        lang_path = os.path.join(translations_dir, f"{lang_code}.json")

        try:
            if os.path.exists(lang_path):
                with open(lang_path, "r", encoding="utf-8") as f:
                    lang_data = json.load(f)
                    _translations[lang_code].update(lang_data)
                    logger.info(f"Loaded {len(lang_data)} {lang_code} translations from file")
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
        # Use a direct SQL query for reliability
        from db.supabase_client import execute_sql

        # Direct SQL query to fetch translations
        query = "SELECT translation_key, en_US, ru_RU FROM game.translations;"
        translations_data = await execute_sql(query)

        # Process the translations
        if translations_data and isinstance(translations_data, list):
            loaded_count = 0
            for translation in translations_data:
                if isinstance(translation, dict):
                    key = translation.get("translation_key", "")
                    if key:
                        if "en_US" in translation and translation["en_US"]:
                            _translations["en_US"][key] = translation["en_US"]
                        if "ru_RU" in translation and translation["ru_RU"]:
                            _translations["ru_RU"][key] = translation["ru_RU"]
                        loaded_count += 1

            logger.info(f"Loaded {loaded_count} translations from database")
        else:
            logger.info("No translations found in database or invalid format")
    except Exception as e:
        logger.warning(f"Error loading translations from database: {e}")
        logger.info("Continuing with file-based translations only")


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
        load_default_translations()

        # 2. Then load from files
        await load_translations_from_file()

        # 3. Finally, try to load from database (which may override file translations)
        try:
            await load_translations_from_db()
        except Exception as db_error:
            logger.error(f"Failed to load translations from database: {db_error}")
            logger.info("Continuing with file-based translations only")

        logger.info(
            f"Loaded translations successfully: {len(_translations['en_US'])} English, "
            f"{len(_translations['ru_RU'])} Russian keys"
        )
    except Exception as e:
        logger.error(f"Error loading translations: {str(e)}")
        logger.info("Continuing with default translations only")


# Decorator for automatic language handling in handlers
def with_language(handler_func: Callable) -> Callable:
    """
    Decorator to automatically get language for a handler function.

    This decorator detects the user's language and provides it to the handler.

    Args:
        handler_func: The handler function to decorate

    Returns:
        Wrapped function with language handling
    """

    async def wrapper(update, context, *args, **kwargs):
        # Get user's telegram ID
        telegram_id = str(update.effective_user.id) if update.effective_user else None

        # Get language if possible
        language = await get_user_language(telegram_id) if telegram_id else DEFAULT_LANGUAGE

        # Add language to context.user_data for convenience
        if context and hasattr(context, 'user_data'):
            context.user_data['language'] = language

        # Call the original handler with language argument
        return await handler_func(update, context, language=language, *args, **kwargs)

    return wrapper