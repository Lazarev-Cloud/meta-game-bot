#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core internationalization functionality without database dependencies.
"""

import json
import logging
import os
from typing import Dict, Any, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Global translations storage with improved structure
_translations = {
    "en_US": {},
    "ru_RU": {}
}

# Supported languages
SUPPORTED_LANGUAGES = ["en_US", "ru_RU"]
DEFAULT_LANGUAGE = "en_US"

# Fallback system for missing translations
_missing_translation_log = set()  # Track missing translations to avoid log spam


def _(text: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Translate a text string to the specified language.

    Enhanced with fallback system and missing translation tracking.
    """
    if not text:
        return ""

    # Normalize language code
    language = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    # Check for translation
    translation = _translations[language].get(text)

    # If translation exists, return it
    if translation:
        return translation

    # No translation found, try fallbacks
    if language != DEFAULT_LANGUAGE:
        # Try default language
        default_translation = _translations[DEFAULT_LANGUAGE].get(text)
        if default_translation:
            return default_translation

    # Log missing translation (only once per string to avoid spam)
    cache_key = f"{language}:{text}"
    if cache_key not in _missing_translation_log and len(text) < 100:  # Don't log very long strings
        _missing_translation_log.add(cache_key)
        logger.debug(f"Missing translation for '{text}' in {language}")

    # Return original text as last resort
    return text


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
            "Permission denied": "Permission denied",
            "Connection error": "Connection error",
            "Not enough resources": "Not enough resources",

            # Languages
            "English": "English",
            "Russian": "Russian",

            # Registration/auth messages
            "You need to register first": "You need to register first",
            "You are not registered yet": "You are not registered yet",
            "Use /start to register": "Use /start to register",

            # Common game terms
            "district": "district",
            "politician": "politician",
            "action": "action",
            "cycle": "cycle",
            "control points": "control points",
            "collective action": "collective action"
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
            "Permission denied": "Доступ запрещен",
            "Connection error": "Ошибка соединения",
            "Not enough resources": "Недостаточно ресурсов",

            # Languages
            "English": "Английский",
            "Russian": "Русский",

            # Registration/auth messages
            "You need to register first": "Вам нужно сначала зарегистрироваться",
            "You are not registered yet": "Вы еще не зарегистрированы",
            "Use /start to register": "Используйте /start для регистрации",

            # Common game terms
            "district": "район",
            "politician": "политик",
            "action": "действие",
            "cycle": "цикл",
            "control points": "очки контроля",
            "collective action": "коллективное действие"
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