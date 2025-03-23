#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Internationalization (i18n) utilities for the Meta Game bot with improved database handling.
"""
import logging
import json
import os
from typing import Dict, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Translation dictionaries
_translations: Dict[str, Dict[str, str]] = {
    "en_US": {},
    "ru_RU": {}
}

# User language preferences cache
_user_languages: Dict[str, str] = {}


async def load_translations() -> None:
    """Load translations from both files and database in proper sequence."""
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
    """Load translations from the database with improved error handling."""
    try:
        # First try using get_translations function
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
                return
        except Exception as func_error:
            logger.warning(f"Error using get_translations function: {func_error}, trying direct table access")

        # Direct table query - use correct schema syntax
        try:
            from db.supabase_client import get_supabase
            client = get_supabase()

            # Use the correct schema reference (just "game.translations", not "public.game.translations")
            response = client.from_("game.translations").select("translation_key,en_US,ru_RU").execute()

            if hasattr(response, 'data'):
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
        except Exception as table_error:
            logger.warning(f"Error accessing translations table: {table_error}")
            # Continue with default translations
    except Exception as e:
        logger.error(f"Error loading translations from database: {str(e)}")
        # Continue with default translations

async def load_translations_from_file() -> None:
    """Load translations from JSON files as fallback or initial setup."""
    try:
        # Path to translations directory
        translations_dir = os.path.join(os.path.dirname(__file__), "../translations")

        # Create the directory if it doesn't exist
        os.makedirs(translations_dir, exist_ok=True)

        # Load English translations
        en_path = os.path.join(translations_dir, "en_US.json")
        if os.path.exists(en_path):
            try:
                with open(en_path, "r", encoding="utf-8") as f:
                    _translations["en_US"].update(json.load(f))
                    logger.info(f"Loaded English translations from file: {len(_translations['en_US'])} keys")
            except json.JSONDecodeError:
                logger.warning(f"Error parsing JSON in {en_path}, creating a new file")
                with open(en_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4)
        else:
            # Create an empty translations file for future use
            with open(en_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
                logger.info("Created empty English translations file")

        # Load Russian translations
        ru_path = os.path.join(translations_dir, "ru_RU.json")
        if os.path.exists(ru_path):
            try:
                with open(ru_path, "r", encoding="utf-8") as f:
                    _translations["ru_RU"].update(json.load(f))
                    logger.info(f"Loaded Russian translations from file: {len(_translations['ru_RU'])} keys")
            except json.JSONDecodeError:
                logger.warning(f"Error parsing JSON in {ru_path}, creating a new file")
                with open(ru_path, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=4)
        else:
            # Create an empty translations file for future use
            with open(ru_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4)
                logger.info("Created empty Russian translations file")

    except Exception as e:
        logger.error(f"Error loading translations from files: {str(e)}")


def _(key: str, language: str = "en_US") -> str:
    """Translate a key into the specified language."""
    # Default to English if language not supported
    if language not in _translations:
        language = "en_US"

    # Get translation or default to key
    return _translations[language].get(key, key)


# Standardized database access
async def get_user_language(telegram_id: str) -> str:
    """Get the user's preferred language with improved error handling."""
    # Check cache first
    if telegram_id in _user_languages:
        return _user_languages[telegram_id]

    try:
        # Use enhanced db_client instead of direct Supabase calls
        from db_client import get_player_language
        language = await get_player_language(telegram_id)
        if language:
            # Cache the result
            _user_languages[telegram_id] = language
            return language
    except Exception as e:
        logger.error(f"Error getting user language: {str(e)}")

    # Default to English
    return "en_US"

async def set_user_language(telegram_id: str, language: str) -> bool:
    """Set user's preferred language with improved error handling."""
    if language not in _translations:
        logger.warning(f"Unsupported language: {language}")
        return False

    try:
        # Try using the enhanced db_client
        try:
            from db_client import set_player_language
            success = await set_player_language(telegram_id, language)
            if success:
                # Update cache
                _user_languages[telegram_id] = language
                return True
        except ImportError:
            logger.debug("Enhanced db_client not available for language setting, using fallback")
        except Exception as e:
            logger.debug(f"Error using set_player_language from db_client: {e}")

        # Direct database approach as fallback
        try:
            # First check if the player exists
            from db.supabase_client import get_player_by_telegram_id, get_supabase

            player = await get_player_by_telegram_id(telegram_id)

            if player:
                # Player exists, update their language
                client = get_supabase()
                client.from_("game.players").update({"language": language}).eq("telegram_id", telegram_id).execute()
                logger.info(f"Updated language for existing player {telegram_id} to {language}")
            else:
                # Player does not exist yet, only update the cache
                logger.info(f"Player {telegram_id} not registered yet, caching language preference")
        except Exception as db_error:
            logger.warning(f"Error updating language in database: {db_error}")

        # Update cache even if DB update fails
        _user_languages[telegram_id] = language
        return True
    except Exception as e:
        logger.error(f"Error setting user language: {str(e)}")
        # Still update the cache even if there was an error
        _user_languages[telegram_id] = language
        return False


async def get_available_languages() -> Dict[str, str]:
    """Get list of available languages."""
    return {
        "en_US": "English",
        "ru_RU": "Русский"
    }


def clear_language_cache(telegram_id: str = None) -> None:
    """Clear language cache for a user or all users."""
    global _user_languages

    if telegram_id:
        if telegram_id in _user_languages:
            del _user_languages[telegram_id]
    else:
        _user_languages = {}


def save_translations_to_file():
    """Save current translations to JSON files for persistence."""
    try:
        # Path to translations directory
        translations_dir = os.path.join(os.path.dirname(__file__), "../translations")
        os.makedirs(translations_dir, exist_ok=True)

        # Save English translations
        en_path = os.path.join(translations_dir, "en_US.json")
        with open(en_path, "w", encoding="utf-8") as f:
            json.dump(_translations["en_US"], f, indent=4, sort_keys=True)
            logger.info(f"Saved {len(_translations['en_US'])} English translations to file")

        # Save Russian translations
        ru_path = os.path.join(translations_dir, "ru_RU.json")
        with open(ru_path, "w", encoding="utf-8") as f:
            json.dump(_translations["ru_RU"], f, indent=4, sort_keys=True)
            logger.info(f"Saved {len(_translations['ru_RU'])} Russian translations to file")
    except Exception as e:
        logger.error(f"Error saving translations to files: {str(e)}")


def setup_i18n() -> None:
    """Initialize the internationalization system."""
    logger.info("Initializing internationalization system")

    load_translations_from_file()
    # We don't call the async functions directly here anymore
    # They will be called from main.py in the initialization sequence