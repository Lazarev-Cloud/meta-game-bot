#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Internationalization (i18n) utilities for the Meta Game bot with improved caching and error handling.
"""
import json
import logging
import os
import time  # Add explicit import for time module
from typing import Dict, Optional, Any, Callable, Awaitable
from functools import lru_cache

# Initialize logger
logger = logging.getLogger(__name__)

# Translation dictionaries
_translations: Dict[str, Dict[str, str]] = {
    "en_US": {},
    "ru_RU": {}
}

# User language preferences cache with expiration time (30 minutes)
_user_languages: Dict[str, Dict[str, Any]] = {}
_CACHE_EXPIRATION = 1800  # 30 minutes in seconds


async def handle_async_operation(operation_name: str, func: Callable[..., Awaitable[Any]],
                                 *args, default_return: Any = None, **kwargs) -> Any:
    """Generic error handler for async operations"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {operation_name}: {str(e)}")
        return default_return


async def load_translations() -> None:
    """Load translations from both files and database in proper sequence, with improved error handling."""
    try:
        # First load from files as fallback
        await load_translations_from_file()

        # Then try to load from database, which may override file translations
        await load_translations_from_db()

        logger.info(
            f"Loaded translations successfully: {len(_translations['en_US'])} English, {len(_translations['ru_RU'])} Russian keys")
    except Exception as e:
        logger.error(f"Error loading translations: {str(e)}")
        logger.info("Continuing with default translations only")


async def load_translations_from_db() -> None:
    """Load translations from the database with improved error handling and retry logic."""
    # Try using get_translations function
    db_translations = await _load_translations_via_function()
    if db_translations:
        return

    # Fallback to direct table query
    await _load_translations_via_table()


async def _load_translations_via_function() -> bool:
    """Load translations using the get_translations RPC function."""
    try:
        from db.supabase_client import get_supabase
        client = get_supabase()

        # Try the public helper function
        response = client.rpc("get_translations").execute()
        if hasattr(response, 'data') and response.data:
            translations_dict = response.data
            loaded_count = 0

            for key, value in translations_dict.items():
                _translations["en_US"][key] = value.get("en_US", key)
                _translations["ru_RU"][key] = value.get("ru_RU", key)
                loaded_count += 1

            logger.info(f"Loaded {loaded_count} translations using get_translations function")
            return True
        return False
    except Exception as e:
        logger.warning(f"Error using get_translations function: {e}, will try direct table access")
        return False


async def _load_translations_via_table() -> None:
    """Load translations directly from the translations table."""
    try:
        from db.supabase_client import get_supabase
        client = get_supabase()

        # Use the correct schema reference
        response = client.from_("translations").schema("game").select("translation_key,en_US,ru_RU").execute()

        if hasattr(response, 'data') and response.data:
            translations_data = response.data
            loaded_count = 0

            for translation in translations_data:
                key = translation.get("translation_key", "")
                if key:
                    _translations["en_US"][key] = translation.get("en_US", key)
                    _translations["ru_RU"][key] = translation.get("ru_RU", key)
                    loaded_count += 1

            logger.info(f"Loaded {loaded_count} translations from database")
        else:
            logger.warning("No translations found or unexpected response format")
    except Exception as e:
        logger.warning(f"Error accessing translations table: {e}")


async def load_translations_from_file() -> None:
    """Load translations from JSON files with improved error handling."""
    # Path to translations directory
    translations_dir = os.path.join(os.path.dirname(__file__), "../translations")

    # Create the directory if it doesn't exist
    os.makedirs(translations_dir, exist_ok=True)

    # Load for each supported language
    for lang_code in ["en_US", "ru_RU"]:
        lang_path = os.path.join(translations_dir, f"{lang_code}.json")

        # Load existing file or create new one
        await _load_or_create_translation_file(lang_path, lang_code)


async def _load_or_create_translation_file(filepath: str, lang_code: str) -> None:
    """Load a translation file or create it if it doesn't exist."""
    try:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    _translations[lang_code].update(json.load(f))
                    logger.info(f"Loaded {lang_code} translations from file: {len(_translations[lang_code])} keys")
            except json.JSONDecodeError:
                logger.warning(f"Error parsing JSON in {filepath}, creating a new file")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4)
        else:
            # Create an empty translations file for future use
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
                logger.info(f"Created empty {lang_code} translations file")
    except Exception as e:
        logger.error(f"Error loading/creating translation file {filepath}: {str(e)}")


@lru_cache(maxsize=1000)
def _(key: str, language: str = "en_US") -> str:
    """Translate a key into the specified language with caching for performance."""
    # Default to English if language not supported
    if language not in _translations:
        language = "en_US"

    # Get translation or default to key
    return _translations[language].get(key, key)


async def get_user_language(telegram_id: str) -> str:
    """Get the user's preferred language with caching and improved error handling."""
    # Check cache first
    current_time = int(time.time())

    if telegram_id in _user_languages:
        cache_entry = _user_languages[telegram_id]
        # Check if cache is still valid
        if current_time - cache_entry['timestamp'] < _CACHE_EXPIRATION:
            return cache_entry['language']

    # Cache missed or expired, fetch from database
    try:
        # Use enhanced db_client
        try:
            from db.db_client import get_player_language as db_get_player_language
            language = await db_get_player_language(telegram_id)
        except (ImportError, Exception):
            # Fallback to direct database query
            from db.supabase_client import get_supabase
            client = get_supabase()
            # FIX: Correct schema reference
            response = client.from_("players").schema("game").select("language").eq("telegram_id", telegram_id).execute()
            language = response.data[0]["language"] if hasattr(response, 'data') and response.data and response.data[0].get("language") else "en_US"

        # Cache the result with timestamp
        _user_languages[telegram_id] = {
            'language': language,
            'timestamp': current_time
        }
        return language
    except Exception as e:
        logger.error(f"Error getting user language: {str(e)}")
        return "en_US"

async def set_user_language(telegram_id: str, language: str) -> bool:
    """Set user's preferred language with improved error handling and caching."""
    if language not in _translations:
        logger.warning(f"Unsupported language: {language}")
        return False

    try:
        # Try using the enhanced db_client
        updated = False
        try:
            from db.db_client import set_player_language
            updated = await set_player_language(telegram_id, language)
        except (ImportError, Exception) as e:
            logger.debug(f"Error using set_player_language: {e}")

            # Direct database approach as fallback
            from db.supabase_client import get_player_by_telegram_id, get_supabase
            player = await get_player_by_telegram_id(telegram_id)

            if player:
                # Player exists, update their language
                client = get_supabase()
                client.from_("players").schema("game").update({"language": language}).eq("telegram_id", telegram_id).execute()
                updated = True
                logger.info(f"Updated language for existing player {telegram_id} to {language}")
            else:
                logger.info(f"Player {telegram_id} not registered yet, caching language preference")

        # Update cache regardless of database update result
        current_time = int(time.time())
        _user_languages[telegram_id] = {
            'language': language,
            'timestamp': current_time
        }

        return True
    except Exception as e:
        logger.error(f"Error setting user language: {str(e)}")
        # Still update the cache even if there was an error
        _user_languages[telegram_id] = {
            'language': language,
            'timestamp': int(time.time() if not hasattr(os, 'time') else os.time())
        }
        return False

def get_available_languages() -> Dict[str, str]:
    """Get list of available languages."""
    return {
        "en_US": "English",
        "ru_RU": "Русский"
    }


def clear_language_cache(telegram_id: Optional[str] = None) -> None:
    """Clear language cache for a user or all users."""
    global _user_languages

    if telegram_id:
        if telegram_id in _user_languages:
            del _user_languages[telegram_id]
    else:
        _user_languages = {}


def setup_i18n() -> None:
    """Initialize the internationalization system."""
    logger.info("Initializing internationalization system")

    # We don't call the async functions directly here anymore
    # They will be called from main.py in the initialization sequence