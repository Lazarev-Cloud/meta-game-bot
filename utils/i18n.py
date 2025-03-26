#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced internationalization module for the Meta Game bot.
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, Callable, Awaitable

# Import core functionality without database dependencies
from utils.i18n_core import _, load_default_translations, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, _translations, load_translations_from_file

# Initialize logger
logger = logging.getLogger(__name__)

# Using dependency injection to avoid circular imports
_player_exists_func = None
_get_supabase_func = None


def init_i18n(player_exists_func=None, get_supabase_func=None):
    """Initialize i18n module with database functions to avoid circular imports."""
    global _player_exists_func, _get_supabase_func
    _player_exists_func = player_exists_func
    _get_supabase_func = get_supabase_func
    logger.info("i18n module initialized with database functions")


# Helper functions for consistent translation patterns
async def translate_resource(resource_type: str, language: str) -> str:
    """Translate a resource type consistently."""
    # Ensure consistent capitalization
    resource_type = resource_type.lower()
    return _(resource_type.capitalize(), language)


async def translate_action(action_type: str, language: str) -> str:
    """Translate an action type consistently."""
    return _(action_type, language)


async def translate_district(district_name: str, language: str) -> str:
    """Translate a district name if a translation exists."""
    district_key = f"district.{district_name}"
    translation = _(district_key, language)
    return district_name if translation == district_key else translation


async def get_user_language(telegram_id: str) -> str:
    """Get user language with memory fallback."""
    # Check memory cache first
    from utils.context_manager import context_manager
    cached_language = context_manager.get(telegram_id, "language")
    if cached_language in SUPPORTED_LANGUAGES:
        return cached_language

    # Try database as fallback
    try:
        if _get_supabase_func is not None:
            client = _get_supabase_func
            response = client.table("players").select("language")
            response = response.eq("telegram_id", telegram_id).limit(1)
            data = response.execute().data

            if data and len(data) > 0 and data[0].get("language") in SUPPORTED_LANGUAGES:
                language = data[0].get("language")
                context_manager.set(telegram_id, "language", language)
                return language
    except Exception as e:
        logger.warning(f"Database language lookup failed: {e}")

    return DEFAULT_LANGUAGE


async def set_user_language(telegram_id: str, language: str) -> bool:
    """Set language with memory-first approach."""
    if language not in SUPPORTED_LANGUAGES:
        return False

    # Update memory cache immediately
    from utils.context_manager import context_manager
    context_manager.set(telegram_id, "language", language)

    # Try database update
    try:
        if _get_supabase_func is not None and _player_exists_func is not None:
            client = _get_supabase_func()
            exists = await _player_exists_func(telegram_id)

            if exists:
                client.table("players").update({"language": language})
                client = client.eq("telegram_id", telegram_id)
                client.execute()
        # If player doesn't exist, language will be saved during registration
    except Exception as e:
        logger.warning(f"Database language update failed: {e}")

    return True


async def load_translations_from_db() -> None:
    """Load translations from the database with unified error handling."""
    try:
        # Use a direct SQL query for reliability
        if _get_supabase_func is not None:
            from db.supabase_client import execute_sql

            # Direct SQL query to fetch translations
            query = "SELECT translation_key, en_US, ru_RU FROM translations;"
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
    """
    try:
        # 1. First set up default fallback translations
        load_default_translations()

        # 2. Then load from files
        await load_translations_from_file()

        # 3. Finally, try to load from database (which may override file translations)
        try:
            if _get_supabase_func is not None:
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


# Track missing translations for future improvement
def save_missing_translations() -> None:
    """Save list of missing translations to a file for future additions."""
    try:
        from utils.i18n_core import _missing_translation_log
        missing_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "translations",
            "missing_translations.txt"
        )

        with open(missing_file, "w", encoding="utf-8") as f:
            for key in sorted(_missing_translation_log):
                f.write(f"{key}\n")

        logger.info(f"Saved {len(_missing_translation_log)} missing translations to {missing_file}")
    except Exception as e:
        logger.error(f"Error saving missing translations: {e}")


# Decorator for automatic language handling in handlers
def with_language(handler_func: Callable) -> Callable:
    """
    Decorator to automatically get language for a handler function.

    This decorator detects the user's language and provides it to the handler.
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