# -*- coding: utf-8 -*-
"""
Enhanced language support for Belgrade Game Bot
Extends the base languages.py with additional translations and utilities
"""

import logging
import sqlite3
from typing import Dict, Any, Optional, Union, List

# Import only constants from languages_base to avoid circular imports
from languages_base import TRANSLATIONS

logger = logging.getLogger(__name__)

# Additional translations to add to the existing language dictionary
ADDITIONAL_TRANSLATIONS = {
    "en": {
        "insufficient_resources_for_main_action": "Main actions require at least 2 resources. Please select more resources.",
        "insufficient_resources_for_action": "You need to select at least one resource for this action.",
        "joined_coordinated_action": "You have joined the {action_type} action targeting {target}. Contributing resources: {resources}",
        "coordinated_actions_heading": "Coordinated Actions:",
        "coordinated_actions_help_text": "• Use the \"Join\" option from the main action menu to join someone's action\n• Create a coordinated action using \"Attack\" or \"Defense\" menu options\n• The more players join, the stronger the action will be",
        "your_resources": "Your Resources",
        # District report translations
        "district_report_title": "District Status Report",
        "controlled_by": "Controlled by",
        "contested_by": "Contested by",
        "not_controlled": "Not controlled",
        "players": "players",
        "high_importance": "High importance",
        "medium_importance": "Medium importance",
        "low_importance": "Low importance",
        "error_generating_report": "Error generating report",

        # Politician action translations
        "politician_influence_title": "Politician Influence Report",
        "high_influence": "High influence",
        "medium_influence": "Medium influence",
        "low_influence": "Low influence",
        "international_politicians": "International Politicians",

        # Politician action button labels
        "action_pol_info": "Gather Information",
        "action_pol_info_desc": "Learn more about this politician",
        "action_pol_influence": "Influence",
        "action_pol_influence_desc": "Try to improve your relationship",
        "action_pol_collaborate": "Collaborate",
        "action_pol_collaborate_desc": "Work together on a political initiative",
        "action_pol_request": "Request Resources",
        "action_pol_request_desc": "Ask for political support and resources",
        "action_pol_power": "Use Political Power",
        "action_pol_power_desc": "Use their political influence to pressure others",
        "action_pol_undermine": "Undermine",
        "action_pol_undermine_desc": "Weaken their influence",
        "action_pol_rumors": "Spread Rumors",
        "action_pol_rumors_desc": "Damage their public reputation",
        "action_pol_scandal": "Create Scandal",
        "action_pol_scandal_desc": "Expose them in a major political scandal",
        "action_pol_diplomatic": "Diplomatic Channel",
        "action_pol_diplomatic_desc": "Establish a diplomatic connection",
        "action_pol_pressure": "International Pressure",
        "action_pol_pressure_desc": "Use international pressure against your opponents",

        # Special event translations
        "event_govt_reshuffle": "Government Reshuffle",
        "event_demonstration": "Mass Demonstration",
        "event_investment": "Foreign Investment",
        "event_sanctions": "Economic Sanctions",
        "event_police_raid": "Police Raid",
        "event_smuggling": "Smuggling Operation",
        "event_diplomatic": "Diplomatic Reception",
        "event_military": "Military Exercise",
        "event_strike": "Worker Strike",
        "event_student": "Student Protest",
        "event_festival": "Cultural Festival",

        # Response messages for politician actions
        "politician_info_success": "You have gathered valuable information about {name}.",
        "politician_info_title": "Intelligence Report: {name}",
        "politician_info_no_resources": "You need at least 1 Information resource to gather info on a politician. Action cancelled.",
        "politician_info_no_action": "You need a quick action to gather info on a politician. Action cancelled.",
        "politician_collaborate_success": "You have successfully collaborated with {name} on a political initiative.",
        "politician_request_success": "You have received resources from {name}.",
        "politician_power_success": "You have used {name}'s political influence to pressure your opponents.",
        "politician_undermine_success": "You have successfully undermined {name}'s influence.",
        "politician_undermine_no_resources": "You need at least 2 Information resources to undermine a politician. Action cancelled.",
        "politician_undermine_no_action": "You need a main action to undermine a politician. Action cancelled.",
        "politician_influence_no_resources": "You need at least 2 Influence resources to influence a politician. Action cancelled.",
        "politician_influence_no_action": "You need a main action to influence a politician. Action cancelled.",
        "politician_influence_success": "You have used your influence on {name}. Your relationship with them may improve. Results will be processed at the end of the cycle.",
        "politician_rumors_success": "You have spread rumors about {name}, damaging their reputation.",
        "politician_scandal_success": "You have exposed {name} in a political scandal, severely damaging their position.",
        "politician_diplomatic_success": "You have established a diplomatic channel with {name}.",
        "politician_pressure_success": "You have used {name}'s international pressure against your opponents.",

        # Enhanced error messages
        "db_connection_error": "Database connection error. Please try again later.",
        "invalid_district_error": "Invalid district. Please select a valid district.",
        "invalid_politician_error": "Invalid politician. Please select a valid politician.",
        "insufficient_resources_detailed": "Insufficient resources. You need {required} {resource_type}, but you only have {available}.",
        "invalid_action_error": "Invalid action. Please select a valid action type.",
        "language_detection_error": "Could not detect your language. Defaulting to English.",
        "error_message": "Sorry, something went wrong. The error has been reported.",
        "error_district_selection": "Error showing district selection. Please try again.",
        "error_resource_selection": "Error showing resource selection. Please try again.",
        "error_district_info": "Error retrieving district information.",
        "error_politician_info": "Error retrieving politician information.",
        "action_error": "Something went wrong with your action. Please try again.",

        # Role text
        "role": "Role",
        "district": "District",
        "key_relationships": "Key Relationships",
    },

    "ru": {
        "insufficient_resources_for_main_action": "Основные действия требуют как минимум 2 ресурса. Пожалуйста, выберите больше ресурсов.",
        "insufficient_resources_for_action": "Вам нужно выбрать хотя бы один ресурс для этого действия.",
        "joined_coordinated_action": "Вы присоединились к действию {action_type}, нацеленному на {target}. Выделенные ресурсы: {resources}",
        "coordinated_actions_heading": "Координированные действия:",
        "coordinated_actions_help_text": "• Используйте опцию \"Присоединиться\" в меню основных действий, чтобы присоединиться к действию другого игрока\n• Создайте координированное действие, используя опции меню \"Атака\" или \"Защита\"\n• Чем больше игроков присоединятся, тем сильнее будет действие",
        "your_resources": "Ваши ресурсы",
        # District report translations
        "district_report_title": "Отчет о состоянии районов",
        "controlled_by": "Контролируется",
        "contested_by": "Оспаривается",
        "not_controlled": "Не контролируется",
        "players": "игроками",
        "high_importance": "Высокая важность",
        "medium_importance": "Средняя важность",
        "low_importance": "Низкая важность",
        "error_generating_report": "Ошибка при создании отчета",

        # Politician action translations
        "politician_influence_title": "Отчет о влиянии политиков",
        "high_influence": "Высокое влияние",
        "medium_influence": "Среднее влияние",
        "low_influence": "Низкое влияние",
        "international_politicians": "Международные политики",

        # Politician action button labels
        "action_pol_info": "Собрать информацию",
        "action_pol_info_desc": "Узнать больше об этом политике",
        "action_pol_influence": "Влияние",
        "action_pol_influence_desc": "Попытаться улучшить ваши отношения",
        "action_pol_collaborate": "Сотрудничество",
        "action_pol_collaborate_desc": "Работать вместе над политической инициативой",
        "action_pol_request": "Запросить ресурсы",
        "action_pol_request_desc": "Попросить политическую поддержку и ресурсы",
        "action_pol_power": "Использовать влияние",
        "action_pol_power_desc": "Использовать их политическое влияние для давления на оппонентов",
        "action_pol_undermine": "Подорвать влияние",
        "action_pol_undermine_desc": "Ослабить их влияние",
        "action_pol_rumors": "Распространить слухи",
        "action_pol_rumors_desc": "Нанести урон их репутации",
        "action_pol_scandal": "Создать скандал",
        "action_pol_scandal_desc": "Разоблачить их в крупном политическом скандале",
        "action_pol_diplomatic": "Дипломатический канал",
        "action_pol_diplomatic_desc": "Установить дипломатическую связь",
        "action_pol_pressure": "Международное давление",
        "action_pol_pressure_desc": "Использовать международное давление против ваших оппонентов",

        # Special event translations
        "event_govt_reshuffle": "Перестановки в правительстве",
        "event_demonstration": "Массовая демонстрация",
        "event_investment": "Иностранные инвестиции",
        "event_sanctions": "Экономические санкции",
        "event_police_raid": "Полицейский рейд",
        "event_smuggling": "Контрабандная операция",
        "event_diplomatic": "Дипломатический прием",
        "event_military": "Военные учения",
        "event_strike": "Забастовка рабочих",
        "event_student": "Студенческий протест",
        "event_festival": "Культурный фестиваль",

        # Response messages for politician actions
        "politician_info_success": "Вы собрали ценную информацию о {name}.",
        "politician_info_title": "Разведывательный отчёт: {name}",
        "politician_info_no_resources": "Вам нужна минимум 1 единица Информации для сбора данных о политике. Действие отменено.",
        "politician_info_no_action": "Вам нужна быстрая заявка для сбора данных о политике. Действие отменено.",
        "politician_collaborate_success": "Вы успешно сотрудничали с {name} по политической инициативе.",
        "politician_request_success": "Вы получили ресурсы от {name}.",
        "politician_power_success": "Вы использовали политическое влияние {name} для давления на оппонентов.",
        "politician_undermine_success": "Вы успешно подорвали влияние {name}.",
        "politician_undermine_no_resources": "Вам нужно минимум 2 единицы Информации для подрыва влияния политика. Действие отменено.",
        "politician_undermine_no_action": "Вам нужна основная заявка для подрыва влияния политика. Действие отменено.",
        "politician_influence_no_resources": "Вам нужно минимум 2 единицы Влияния для воздействия на политика. Действие отменено.",
        "politician_influence_no_action": "Вам нужна основная заявка для воздействия на политика. Действие отменено.",
        "politician_influence_success": "Вы использовали своё влияние на {name}. Ваши отношения с ним могут улучшиться. Результаты будут обработаны в конце цикла.",
        "politician_rumors_success": "Вы распространили слухи о {name}, нанеся урон их репутации.",
        "politician_scandal_success": "Вы разоблачили {name} в политическом скандале, серьезно подорвав их позицию.",
        "politician_diplomatic_success": "Вы установили дипломатический канал с {name}.",
        "politician_pressure_success": "Вы использовали международное давление {name} против ваших оппонентов.",

        # Enhanced error messages
        "db_connection_error": "Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.",
        "invalid_district_error": "Недействительный район. Пожалуйста, выберите правильный район.",
        "invalid_politician_error": "Недействительный политик. Пожалуйста, выберите правильного политика.",
        "insufficient_resources_detailed": "Недостаточно ресурсов. Вам нужно {required} {resource_type}, но у вас есть только {available}.",
        "invalid_action_error": "Недействительное действие. Пожалуйста, выберите правильный тип действия.",
        "language_detection_error": "Не удалось определить ваш язык. Используется английский по умолчанию.",
        "error_message": "Извините, что-то пошло не так. Об ошибке сообщено.",
        "error_district_selection": "Ошибка при показе списка районов. Пожалуйста, попробуйте снова.",
        "error_resource_selection": "Ошибка при показе выбора ресурсов. Пожалуйста, попробуйте снова.",
        "error_district_info": "Ошибка при получении информации о районе.",
        "error_politician_info": "Ошибка при получении информации о политике.",
        "action_error": "Что-то пошло не так с вашим действием. Пожалуйста, попробуйте снова.",

        # Role text
        "role": "Роль",
        "district": "Район",
        "key_relationships": "Ключевые отношения",
    }
}

# Additional translations for admin commands
ADMIN_TRANSLATIONS = {
    "en": {
        "admin_error": "Admin error: {error}",
        "admin_player_resources_not_found": "Player {player_id} exists but has no resources record.",
        "admin_help_title": "Admin Commands",
        "admin_reset_actions_usage": "Usage: /admin_reset_actions [player_id]",
        "admin_reset_actions_success": "Actions reset for player {player_id}.",
        "admin_reset_all_actions_success": "Actions reset for {count} players.",
        "admin_set_ideology_usage": "Usage: /admin_set_ideology [player_id] [ideology_score]",
        "admin_set_ideology_success": "Ideology score for player {player_id} set to {score}.",
        "admin_set_ideology_invalid": "Ideology score must be between -5 and +5.",
        "admin_player_not_found": "Player {player_id} not found.",
        "admin_list_players_none": "No players registered.",
        "admin_list_players_title": "Registered Players",
        "admin_help_desc": "Show this admin help message",
        "admin_news_desc": "Add a news item",
        "admin_cycle_desc": "Manually process a game cycle"
    },
    "ru": {
        "admin_error": "Ошибка администратора: {error}",
        "admin_player_resources_not_found": "Игрок {player_id} существует, но не имеет записи ресурсов.",
        "admin_help_title": "Команды администратора",
        "admin_reset_actions_usage": "Использование: /admin_reset_actions [ID игрока]",
        "admin_reset_actions_success": "Действия сброшены для игрока {player_id}.",
        "admin_reset_all_actions_success": "Действия сброшены для {count} игроков.",
        "admin_set_ideology_usage": "Использование: /admin_set_ideology [ID игрока] [оценка идеологии]",
        "admin_set_ideology_success": "Оценка идеологии для игрока {player_id} установлена на {score}.",
        "admin_set_ideology_invalid": "Оценка идеологии должна быть от -5 до +5.",
        "admin_player_not_found": "Игрок {player_id} не найден.",
        "admin_list_players_none": "Нет зарегистрированных игроков.",
        "admin_list_players_title": "Зарегистрированные игроки",
        "admin_help_desc": "Показать это сообщение помощи администратора",
        "admin_news_desc": "Добавить новость",
        "admin_cycle_desc": "Вручную обработать игровой цикл",
    }
}

def update_translations():
    """
    Update the main translations dictionary with additional translations

    This function must be called before translations are used to ensure all
    new translations are available
    """
    for lang in ADDITIONAL_TRANSLATIONS:
        if lang in TRANSLATIONS:
            # Update existing language with new translations
            for key, value in ADDITIONAL_TRANSLATIONS[lang].items():
                TRANSLATIONS[lang][key] = value
        else:
            # Add new language
            TRANSLATIONS[lang] = ADDITIONAL_TRANSLATIONS[lang]

    logger.info("Translations updated with additional entries")

def update_admin_translations():
    """Update the main translations dictionary with admin translations"""
    for lang in ADMIN_TRANSLATIONS:
        if lang in TRANSLATIONS:
            # Update existing language with admin translations
            for key, value in ADMIN_TRANSLATIONS[lang].items():
                TRANSLATIONS[lang][key] = value

    logger.info("Admin translations added")

# Define the local_get_text function at the module level
def local_get_text(key, lang="en", default=None):
    """
    Local version of get_text to avoid circular imports
    
    Args:
        key: The translation key
        lang: Language code
        default: Default text if translation is missing
    
    Returns:
        Translated text
    """
    if lang not in TRANSLATIONS:
        lang = "en"
    text = TRANSLATIONS[lang].get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key)
    if text is None:
        return default if default is not None else f"[Missing: {key}]"
    return text

def get_translated_keyboard(keyboard_items: List[Dict[str, str]], lang: str = "en") -> List[Dict[str, str]]:
    """
    Translate a list of keyboard items

    Args:
        keyboard_items: List of keyboard items with 'text' keys
        lang: Language code

    Returns:
        List of translated keyboard items
    """
    translated_items = []
    for item in keyboard_items:
        translated_item = item.copy()
        if 'text' in item:
            translated_item['text'] = local_get_text(item['text'], lang, item['text'])
        translated_items.append(translated_item)

    return translated_items

def detect_language_from_message(message_text: str) -> str:
    """
    Simple language detection based on message text

    Args:
        message_text: Message text to analyze

    Returns:
        Detected language code ('en' or 'ru')
    """
    # Count characters in Cyrillic alphabet
    cyrillic_count = sum(1 for char in message_text if 0x0400 <= ord(char) <= 0x04FF)

    # If more than 30% of characters are Cyrillic, assume Russian
    if cyrillic_count / max(1, len(message_text)) > 0.3:
        return "ru"

    return "en"

def format_resource_list(resources: Dict[str, int], lang: str = "en") -> str:
    """
    Format a dictionary of resources as a readable string

    Args:
        resources: Dictionary of resources {resource_type: amount}
        lang: Language code

    Returns:
        Formatted string
    """
    # Import locally to avoid circular imports
    from languages_base import get_resource_name

    formatted_parts = []
    for resource_type, amount in resources.items():
        if amount != 0:
            resource_name = get_resource_name(resource_type, lang)
            formatted_parts.append(f"{amount} {resource_name}")

    if not formatted_parts:
        return local_get_text("none", lang, default="None")

    return ", ".join(formatted_parts)

def get_ordinal_suffix(num: int, lang: str = "en") -> str:
    """
    Get the ordinal suffix for a number

    Args:
        num: Number
        lang: Language code

    Returns:
        String with ordinal suffix
    """
    if lang == "ru":
        # Russian doesn't use ordinal suffixes the same way
        return str(num)

    # English ordinal suffixes
    if 10 <= num % 100 <= 20:
        suffix = "th"
    else:
        suffixes = {1: "st", 2: "nd", 3: "rd"}
        suffix = suffixes.get(num % 10, "th")

    return f"{num}{suffix}"

def init_language_support():
    """Initialize language support by updating translations"""
    update_translations()
    update_admin_translations()
    logger.info("Language support initialized")