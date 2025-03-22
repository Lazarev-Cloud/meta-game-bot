#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Internationalization (i18n) utilities for the Meta Game bot.
"""
import logging
import json
import os
from typing import Dict

from utils.i18n_additions import update_translations

# Initialize logger
logger = logging.getLogger(__name__)

# Translation dictionaries
_translations: Dict[str, Dict[str, str]] = {
    "en_US": {},
    "ru_RU": {}
}

# User language preferences cache
_user_languages: Dict[str, str] = {}


async def load_translations_from_db() -> None:
    """Load translations from the database."""
    try:
        from db.supabase_client import get_supabase
        client = get_supabase()

        # Check if the translations table exists
        try:
            response = client.table("translations").select("*").execute()

            if not response.data:
                logger.warning("No translations found in database")
                return

            for translation in response.data:
                key = translation.get("translation_key", "")
                if key:
                    _translations["en_US"][key] = translation.get("en_US", key)
                    _translations["ru_RU"][key] = translation.get("ru_RU", key)

            logger.info(f"Loaded {len(response.data)} translations from database")
        except Exception as table_error:
            logger.warning(f"Translations table may not exist: {table_error}")
            # Continue with default translations
    except Exception as e:
        logger.error(f"Error loading translations from database: {str(e)}")
        # Continue with default translations


async def load_translations_from_file() -> None:
    """Load translations from JSON files as fallback or initial setup."""
    try:
        # Path to translations directory
        translations_dir = os.path.join(os.path.dirname(__file__), "../translations")
        os.makedirs(translations_dir, exist_ok=True)

        # Load English translations
        en_path = os.path.join(translations_dir, "en_US.json")
        if os.path.exists(en_path):
            with open(en_path, "r", encoding="utf-8") as f:
                _translations["en_US"] = json.load(f)

        # Load Russian translations
        ru_path = os.path.join(translations_dir, "ru_RU.json")
        if os.path.exists(ru_path):
            with open(ru_path, "r", encoding="utf-8") as f:
                _translations["ru_RU"] = json.load(f)

        logger.info(
            f"Loaded translations from files: EN: {len(_translations['en_US'])}, RU: {len(_translations['ru_RU'])}")
    except Exception as e:
        logger.error(f"Error loading translations from files: {str(e)}")


def _(key: str, language: str = "en_US") -> str:
    """Translate a key into the specified language."""
    # Default to English if language not supported
    if language not in _translations:
        language = "en_US"

    # Get translation or default to key
    return _translations[language].get(key, key)


async def get_user_language(telegram_id: str) -> str:
    """Get the user's preferred language."""
    # Check cache first
    if telegram_id in _user_languages:
        return _user_languages[telegram_id]

    try:
        # Get from database
        from db.supabase_client import get_supabase
        client = get_supabase()
        try:
            response = client.table("players").select("language").eq("telegram_id", telegram_id).execute()

            if response.data and response.data[0].get("language"):
                language = response.data[0]["language"]
                # Cache the result
                _user_languages[telegram_id] = language
                return language
        except Exception as table_error:
            logger.warning(f"Couldn't retrieve language preference: {table_error}")
    except Exception as e:
        logger.error(f"Error getting user language: {str(e)}")

    # Default to English
    return "en_US"


async def set_user_language(telegram_id: str, language: str) -> bool:
    """Set user's preferred language."""
    if language not in _translations:
        logger.warning(f"Unsupported language: {language}")
        return False

    try:
        # Update database
        from db.supabase_client import get_supabase
        client = get_supabase()
        client.table("players").update({"language": language}).eq("telegram_id", telegram_id).execute()

        # Update cache
        _user_languages[telegram_id] = language

        logger.info(f"Set language for user {telegram_id} to {language}")
        return True
    except Exception as e:
        logger.error(f"Error setting user language: {str(e)}")
        # Still update the cache even if DB update fails
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


def setup_i18n() -> None:
    """Initialize the internationalization system."""
    logger.info("Initializing internationalization system")

    # Initialize with default translations
    _translations["en_US"] = {
        # Common terms
        "Influence": "Influence",
        "Money": "Money",
        "Information": "Information",
        "Force": "Force",
        "None": "None",
        "Yes": "Yes",
        "No": "No",
        "Back": "Back",
        "Cancel": "Cancel",
        "Confirm": "Confirm",
        "Join Action": "Join Action",

        # Menu items
        "Status": "Status",
        "Map": "Map",
        "News": "News",
        "Main Action": "Main Action",
        "Quick Action": "Quick Action",
        "Resources": "Resources",
        "Politicians": "Politicians",
        "Collective Actions": "Collective Actions",
        "Help": "Help",

        # Actions
        "influence": "Influence",
        "attack": "Attack",
        "defense": "Defense",
        "reconnaissance": "Reconnaissance",
        "information_spread": "Information Spread",
        "support": "Support",
        "politician_influence": "Politician Influence",
        "politician_reputation_attack": "Reputation Attack",
        "politician_displacement": "Politician Displacement",
        "international_negotiations": "International Negotiations",
        "kompromat_search": "Kompromat Search",
        "lobbying": "Lobbying",

        # Status-related
        "Action Submitted": "Action Submitted",
        "You are not registered as a player. Please use the /start command to register.": "You are not registered as a player. Please use the /start command to register.",
        "You don't have permission to use admin commands.": "You don't have permission to use admin commands.",

        # Collective actions
        "Active Collective Actions": "Active Collective Actions",
        "Join collective action": "Join collective action",
        "There are no active collective actions at the moment.": "There are no active collective actions at the moment.",
        "You are joining collective action {action_id}.\n\nWhat resource would you like to contribute?": "You are joining collective action {action_id}.\n\nWhat resource would you like to contribute?",

        # Resources
        "You don't have enough resources for this action.": "You don't have enough resources for this action.",
        "Resource conversion successful": "Resource conversion successful",
        "Resource conversion failed": "Resource conversion failed",

        # Districts
        "Please select a district to view:": "Please select a district to view:",
        "Error retrieving district information for {district}. The district may not exist or there was a server error.": "Error retrieving district information for {district}. The district may not exist or there was a server error.",

        # Error messages
        "An error occurred while processing your request.": "An error occurred while processing your request.",
        "Database connection error. Please try again later.": "Database connection error. Please try again later.",
        "Invalid action format. Please try again.": "Invalid action format. Please try again.",

        # Conversation prompts
        "What type of main action would you like to take?": "What type of main action would you like to take?",
        "What type of quick action would you like to take?": "What type of quick action would you like to take?",
        "Please select a resource type to use for this action:": "Please select a resource type to use for this action:",
        "How much {resource} do you want to use for this action?": "How much {resource} do you want to use for this action?",
        "Will you be physically present for this action? Being present gives +20 control points.": "Will you be physically present for this action? Being present gives +20 control points.",
        "Please confirm your action:": "Please confirm your action:",
        "Action canceled.": "Action canceled.",
    }

    # Initialize Russian translations with some basic terms
    _translations["ru_RU"] = {
        # Common terms
        "Influence": "Влияние",
        "Money": "Деньги",
        "Information": "Информация",
        "Force": "Сила",
        "None": "Нет",
        "Yes": "Да",
        "No": "Нет",
        "Back": "Назад",
        "Cancel": "Отмена",
        "Confirm": "Подтвердить",
        "Join Action": "Присоединиться к действию",

        # Menu items
        "Status": "Статус",
        "Map": "Карта",
        "News": "Новости",
        "Main Action": "Основное действие",
        "Quick Action": "Быстрое действие",
        "Resources": "Ресурсы",
        "Politicians": "Политики",
        "Collective Actions": "Коллективные действия",
        "Help": "Помощь",

        # Actions
        "influence": "Влияние",
        "attack": "Атака",
        "defense": "Защита",
        "reconnaissance": "Разведка",
        "information_spread": "Распространение информации",
        "support": "Поддержка",
        "politician_influence": "Влияние на политика",
        "politician_reputation_attack": "Атака на репутацию",
        "politician_displacement": "Вытеснение политика",
        "international_negotiations": "Международные переговоры",
        "kompromat_search": "Поиск компромата",
        "lobbying": "Лоббирование",

        # Status-related
        "Action Submitted": "Заявка отправлена",
        "You are not registered as a player. Please use the /start command to register.": "Вы не зарегистрированы как игрок. Используйте команду /start для регистрации.",
        "You don't have permission to use admin commands.": "У вас нет прав для использования команд администратора.",

        # Collective actions
        "Active Collective Actions": "Активные коллективные действия",
        "Join collective action": "Присоединиться к коллективному действию",
        "There are no active collective actions at the moment.": "В настоящее время нет активных коллективных действий.",
        "You are joining collective action {action_id}.\n\nWhat resource would you like to contribute?": "Вы присоединяетесь к коллективному действию {action_id}.\n\nКакой ресурс вы хотите внести?",

        # Resources
        "You don't have enough resources for this action.": "У вас недостаточно ресурсов для этого действия.",
        "Resource conversion successful": "Конвертация ресурсов успешна",
        "Resource conversion failed": "Ошибка конвертации ресурсов",

        # Districts
        "Please select a district to view:": "Выберите район для просмотра:",
        "Error retrieving district information for {district}. The district may not exist or there was a server error.": "Ошибка получения информации о районе {district}. Район может не существовать или произошла ошибка сервера.",

        # Error messages
        "An error occurred while processing your request.": "Произошла ошибка при обработке вашего запроса.",
        "Database connection error. Please try again later.": "Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.",
        "Invalid action format. Please try again.": "Неверный формат действия. Пожалуйста, попробуйте снова.",

        # Conversation prompts
        "What type of main action would you like to take?": "Какой тип основного действия вы хотите предпринять?",
        "What type of quick action would you like to take?": "Какой тип быстрого действия вы хотите предпринять?",
        "Please select a resource type to use for this action:": "Выберите тип ресурса для этого действия:",
        "How much {resource} do you want to use for this action?": "Сколько {resource} вы хотите использовать для этого действия?",
        "Will you be physically present for this action? Being present gives +20 control points.": "Будете ли вы физически присутствовать при этом действии? Присутствие дает +20 очков контроля.",
        "Please confirm your action:": "Пожалуйста, подтвердите свое действие:",
        "Action canceled.": "Действие отменено.",
    }

    # Add additional translations from i18n_additions.py
    update_translations(_translations)

    # We don't call the async functions directly here anymore
    # They will be called from main.py in the initialization sequence