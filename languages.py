#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language support for Belgrade Game Bot
This file contains all translations and language-related utilities
"""

import logging
from typing import Dict, Any, Optional, Union
from db.queries import get_player_language, set_player_language

logger = logging.getLogger(__name__)

# Dictionary of translations
TRANSLATIONS = {
    "en": {
        # Language settings
        "language_current": "Your current language is: {language}",
        "language_select": "Please select your preferred language:",
        "language_changed": "Language changed to English",
        "language_button_en": "English",
        "language_button_ru": "Русский",
        "language_invalid": "Invalid language selection",
        "language_change_failed": "Failed to change language. Please try again.",
        "language_detection_error": "Could not detect your language. Defaulting to English.",

        # Basic commands and responses
        "welcome": "Welcome to the Belgrade Game, {user_name}! This game simulates the political struggle in 1998 Yugoslavia through control of Belgrade's districts.\n\nPlease enter your character's name:",
        "name_set": "Welcome, {character_name}! You are now a political player in 1998 Belgrade.\n\nUse /help to see available commands and /status to check your current situation.",
        "invalid_name": "Please enter a valid name.",
        "operation_cancelled": "Operation cancelled.",
        "not_registered": "You are not registered. Use /start to begin the game.",

        # Help and documentation
        "help_title": "Belgrade Game Command Guide",
        "help_basic": "*Basic Commands:*\n• /start - Begin the game and register your character\n• /help - Display this command list\n• /status - Check your resources and district control\n• /map - View the current control map\n• /time - Show current game cycle and time until next\n• /news - Display recent news\n• /language - Change interface language",
        "help_action": "*Action Commands:*\n• /action - Submit a main action (influence, attack, defense)\n• /quick_action - Submit a quick action (recon, spread info, support)\n• /cancel_action - Cancel your last pending action\n• /actions_left - Check your remaining actions\n• /view_district [district] - View information about a district",
        "help_resource": "*Resource Commands:*\n• /resources - View your current resources\n• /convert_resource [type] [amount] - Convert resources\n• /check_income - Check your expected resource income",
        "help_trade": "*Trade Commands:*\n• /trade - Create a new trade offer\n• /accept_trade [id] - Accept a trade offer\n• /cancel_trade [id] - Cancel your trade offer",
        "help_political": "*Political Commands:*\n• /politicians - View active politicians\n• /politician_status - Check your political status\n• /international - View international relations",
        "help_admin": "*Admin Commands:*\n• /admin_help - Show admin command list\n• /broadcast - Send message to all players\n• /set_cycle - Set game cycle manually\n• /reset_player [id] - Reset player data",

        # Game mechanics
        "cycle_info": "Current game cycle: {cycle}\nTime until next cycle: {time}",
        "cycle_start": "New game cycle has started! Cycle {cycle} begins.",
        "cycle_end": "Game cycle {cycle} has ended.",
        "cycle_update": "Game cycle update: {message}",
        "cycle_reminder": "Reminder: {time} until cycle {cycle} ends.",
        "resource_info": "Your resources:\n{resources}",
        "district_info": "District: {district}\nControl: {control}%\nInfluence: {influence}",
        "action_submit": "Action submitted: {action}",
        "action_cancel": "Action cancelled: {action}",
        "action_complete": "Action completed: {action}",
        "action_failed": "Action failed: {action}",
        "actions_remaining": "Actions remaining this cycle: {count}",

        # Resources and economy
        "resource_types": {
            "money": "Money",
            "influence": "Influence",
            "manpower": "Manpower",
            "intel": "Intelligence",
            "supplies": "Supplies"
        },
        "resource_convert": "Converting {amount} {from_type} to {to_type}",
        "resource_insufficient": "Insufficient {resource} (needed: {amount})",
        "income_report": "Expected income next cycle:\n{income}",
        "resource_gain": "You gained {amount} {resource}",
        "resource_loss": "You lost {amount} {resource}",
        "resource_transfer": "Transferred {amount} {resource} to {target}",

        # Districts
        "districts": {
            "stari_grad": "Stari Grad",
            "savski_venac": "Savski Venac",
            "vracar": "Vračar",
            "palilula": "Palilula",
            "zvezdara": "Zvezdara",
            "rakovica": "Rakovica",
            "cukarica": "Čukarica",
            "novi_beograd": "Novi Beograd",
            "zemun": "Zemun",
            "surcin": "Surčin"
        },
        "district_status": {
            "controlled": "Under your control",
            "contested": "Contested",
            "enemy": "Enemy controlled",
            "neutral": "Neutral"
        },

        # Actions
        "action_types": {
            "influence": "Increase Influence",
            "attack": "Launch Attack",
            "defend": "Strengthen Defense",
            "recon": "Gather Intelligence",
            "propaganda": "Spread Propaganda",
            "support": "Support Allies"
        },
        "action_descriptions": {
            "influence": "Increase your influence in a district",
            "attack": "Attack opponent's position",
            "defend": "Strengthen your defenses",
            "recon": "Gather intelligence about a district",
            "propaganda": "Spread propaganda in your favor",
            "support": "Support your allies"
        },
        "action_results": {
            "success": "Action successful: {details}",
            "partial": "Partial success: {details}",
            "failure": "Action failed: {details}",
            "interrupted": "Action interrupted: {details}"
        },

        # Trading
        "trade_new": "New trade offer created: {offer}",
        "trade_accept": "Trade offer accepted: {offer}",
        "trade_cancel": "Trade offer cancelled: {offer}",
        "trade_complete": "Trade completed: {offer}",
        "trade_failed": "Trade failed: {reason}",
        "trade_not_found": "Trade offer not found",
        "trade_expired": "Trade offer has expired",
        "trade_invalid": "Invalid trade offer",

        # Politics
        "politician_new": "New politician registered: {name}",
        "politician_status": "Political status:\nInfluence: {influence}\nParty: {party}\nStatus: {status}",
        "international_relations": "International relations report:\n{relations}",
        "political_event": "Political event: {event}",
        "political_alliance": "Alliance formed with {party}",
        "political_rivalry": "Rivalry declared with {party}",

        # Events and notifications
        "event_district_captured": "District captured: {district}",
        "event_resource_found": "Resources found: {resources}",
        "event_political_change": "Political change: {description}",
        "notification_attack": "Your district is under attack: {district}",
        "notification_spy": "Spy activity detected in {district}",
        "notification_trade": "New trade offer available",
        "notification_cycle": "New game cycle starting in {time}",
        "notification_action": "Action required: {action}",
        "notification_update": "Game update: {message}",
        "notification_achievement": "Achievement unlocked: {achievement}",
        "notification_warning": "Warning: {message}",
        "notification_error": "Error: {message}",

        # Error messages
        "error_message": "Sorry, something went wrong. The error has been reported.",
        "error_db_connection": "Database connection error. Please try again later.",
        "error_invalid_input": "Invalid input. Please check your command and try again.",
        "error_permission": "You don't have permission to perform this action.",
        "error_timeout": "Operation timed out. Please try again.",
        "error_rate_limit": "You're doing that too often. Please wait a moment.",
        "error_maintenance": "The game is currently under maintenance. Please try again later.",
        "error_invalid_state": "Invalid game state. Please contact support if this persists.",
        "error_not_found": "The requested item was not found.",
        "error_already_exists": "This item already exists.",
        "error_insufficient_resources": "You don't have enough resources for this action.",
        "error_invalid_target": "Invalid target for this action.",
        "error_cooldown": "This action is still on cooldown. Try again in {time}.",

        # Success messages
        "success_generic": "Operation completed successfully.",
        "success_saved": "Changes have been saved.",
        "success_updated": "Information has been updated.",
        "success_deleted": "Item has been deleted.",
        "success_created": "New item has been created.",
        "success_action": "Action completed successfully.",
        "success_purchase": "Purchase completed successfully.",
        "success_trade": "Trade completed successfully.",
        "ideology_far_right": "Far Right",
        "ideology_right": "Right",
        "ideology_center": "Center",
        "ideology_left": "Left",
        "ideology_far_left": "Far Left"
    },

    "ru": {
        # Language settings
        "language_current": "Ваш текущий язык: {language}",
        "language_select": "Пожалуйста, выберите предпочитаемый язык:",
        "language_changed": "Язык изменён на русский",
        "language_button_en": "English",
        "language_button_ru": "Русский",
        "language_invalid": "Неверный выбор языка",
        "language_change_failed": "Не удалось изменить язык. Пожалуйста, попробуйте снова.",
        "language_detection_error": "Не удалось определить ваш язык. Используется английский по умолчанию.",

        # Basic commands and responses
        "welcome": "Добро пожаловать в Белградскую Игру, {user_name}! Эта игра моделирует политическую борьбу в Югославии 1998 года через контроль над районами Белграда.\n\nПожалуйста, введите имя вашего персонажа:",
        "name_set": "Добро пожаловать, {character_name}! Теперь вы политический игрок в Белграде 1998 года.\n\nИспользуйте /help для просмотра доступных команд и /status для проверки вашей текущей ситуации.",
        "invalid_name": "Пожалуйста, введите корректное имя.",
        "operation_cancelled": "Операция отменена.",
        "not_registered": "Вы не зарегистрированы. Используйте /start, чтобы начать игру.",

        # Help and documentation
        "help_title": "Руководство по командам Белградской Игры",
        "help_basic": "*Основные команды:*\n• /start - Начать игру и зарегистрировать персонажа\n• /help - Показать список команд\n• /status - Проверить ресурсы и контроль районов\n• /map - Посмотреть карту контроля\n• /time - Показать текущий цикл и время до следующего\n• /news - Показать последние новости\n• /language - Изменить язык интерфейса",
        "help_action": "*Команды действий:*\n• /action - Отправить основное действие (влияние, атака, защита)\n• /quick_action - Отправить быстрое действие (разведка, информация, поддержка)\n• /cancel_action - Отменить последнее ожидающее действие\n• /actions_left - Проверить оставшиеся действия\n• /view_district [район] - Посмотреть информацию о районе",
        "help_resource": "*Команды ресурсов:*\n• /resources - Посмотреть текущие ресурсы\n• /convert_resource [тип] [количество] - Конвертировать ресурсы\n• /check_income - Проверить ожидаемый доход",
        "help_trade": "*Торговые команды:*\n• /trade - Создать новое торговое предложение\n• /accept_trade [id] - Принять торговое предложение\n• /cancel_trade [id] - Отменить торговое предложение",
        "help_political": "*Политические команды:*\n• /politicians - Просмотр активных политиков\n• /politician_status - Проверить политический статус\n• /international - Просмотр международных отношений",
        "help_admin": "*Команды администратора:*\n• /admin_help - Показать список команд администратора\n• /broadcast - Отправить сообщение всем игрокам\n• /set_cycle - Установить игровой цикл вручную\n• /reset_player [id] - Сбросить данные игрока",

        # Game mechanics
        "cycle_info": "Текущий игровой цикл: {cycle}\nВремя до следующего цикла: {time}",
        "cycle_start": "Начался новый игровой цикл! Цикл {cycle} начинается.",
        "cycle_end": "Игровой цикл {cycle} завершен.",
        "cycle_update": "Обновление игрового цикла: {message}",
        "cycle_reminder": "Напоминание: {time} до окончания цикла {cycle}.",
        "resource_info": "Ваши ресурсы:\n{resources}",
        "district_info": "Район: {district}\nКонтроль: {control}%\nВлияние: {influence}",
        "action_submit": "Действие отправлено: {action}",
        "action_cancel": "Действие отменено: {action}",
        "action_complete": "Действие завершено: {action}",
        "action_failed": "Действие не удалось: {action}",
        "actions_remaining": "Осталось действий в этом цикле: {count}",

        # Resources and economy
        "resource_types": {
            "money": "Деньги",
            "influence": "Влияние",
            "manpower": "Людские ресурсы",
            "intel": "Разведданные",
            "supplies": "Припасы"
        },
        "resource_convert": "Конвертация {amount} {from_type} в {to_type}",
        "resource_insufficient": "Недостаточно {resource} (требуется: {amount})",
        "income_report": "Ожидаемый доход в следующем цикле:\n{income}",
        "resource_gain": "Вы получили {amount} {resource}",
        "resource_loss": "Вы потеряли {amount} {resource}",
        "resource_transfer": "Передано {amount} {resource} игроку {target}",

        # Districts
        "districts": {
            "stari_grad": "Стари-Град",
            "savski_venac": "Савски-Венац",
            "vracar": "Врачар",
            "palilula": "Палилула",
            "zvezdara": "Звездара",
            "rakovica": "Раковица",
            "cukarica": "Чукарица",
            "novi_beograd": "Нови-Београд",
            "zemun": "Земун",
            "surcin": "Сурчин"
        },
        "district_status": {
            "controlled": "Под вашим контролем",
            "contested": "Оспариваемый",
            "enemy": "Под контролем противника",
            "neutral": "Нейтральный"
        },

        # Actions
        "action_types": {
            "influence": "Увеличить влияние",
            "attack": "Начать атаку",
            "defend": "Усилить оборону",
            "recon": "Собрать разведданные",
            "propaganda": "Распространить пропаганду",
            "support": "Поддержать союзников"
        },
        "action_descriptions": {
            "influence": "Увеличить ваше влияние в районе",
            "attack": "Атаковать позиции противника",
            "defend": "Усилить вашу оборону",
            "recon": "Собрать разведданные о районе",
            "propaganda": "Распространить пропаганду в вашу пользу",
            "support": "Поддержать ваших союзников"
        },
        "action_results": {
            "success": "Действие успешно: {details}",
            "partial": "Частичный успех: {details}",
            "failure": "Действие не удалось: {details}",
            "interrupted": "Действие прервано: {details}"
        },

        # Trading
        "trade_new": "Создано новое торговое предложение: {offer}",
        "trade_accept": "Торговое предложение принято: {offer}",
        "trade_cancel": "Торговое предложение отменено: {offer}",
        "trade_complete": "Торговля завершена: {offer}",
        "trade_failed": "Торговля не удалась: {reason}",
        "trade_not_found": "Торговое предложение не найдено",
        "trade_expired": "Срок торгового предложения истек",
        "trade_invalid": "Недействительное торговое предложение",

        # Politics
        "politician_new": "Зарегистрирован новый политик: {name}",
        "politician_status": "Политический статус:\nВлияние: {influence}\nПартия: {party}\nСтатус: {status}",
        "international_relations": "Отчет о международных отношениях:\n{relations}",
        "political_event": "Политическое событие: {event}",
        "political_alliance": "Сформирован альянс с {party}",
        "political_rivalry": "Объявлено соперничество с {party}",

        # Events and notifications
        "event_district_captured": "Район захвачен: {district}",
        "event_resource_found": "Найдены ресурсы: {resources}",
        "event_political_change": "Политическое изменение: {description}",
        "notification_attack": "Ваш район атакован: {district}",
        "notification_spy": "Обнаружена шпионская деятельность в {district}",
        "notification_trade": "Доступно новое торговое предложение",
        "notification_cycle": "Новый игровой цикл начнется через {time}",
        "notification_action": "Требуется действие: {action}",
        "notification_update": "Обновление игры: {message}",
        "notification_achievement": "Достижение разблокировано: {achievement}",
        "notification_warning": "Предупреждение: {message}",
        "notification_error": "Ошибка: {message}",

        # Error messages
        "error_message": "Извините, что-то пошло не так. Об ошибке сообщено.",
        "error_db_connection": "Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.",
        "error_invalid_input": "Неверный ввод. Пожалуйста, проверьте команду и попробуйте снова.",
        "error_permission": "У вас нет прав для выполнения этого действия.",
        "error_timeout": "Время операции истекло. Пожалуйста, попробуйте снова.",
        "error_rate_limit": "Вы делаете это слишком часто. Пожалуйста, подождите.",
        "error_maintenance": "Игра находится на техническом обслуживании. Пожалуйста, попробуйте позже.",
        "error_invalid_state": "Неверное состояние игры. Пожалуйста, свяжитесь с поддержкой, если это повторится.",
        "error_not_found": "Запрошенный элемент не найден.",
        "error_already_exists": "Этот элемент уже существует.",
        "error_insufficient_resources": "У вас недостаточно ресурсов для этого действия.",
        "error_invalid_target": "Неверная цель для этого действия.",
        "error_cooldown": "Это действие все еще на перезарядке. Попробуйте снова через {time}.",

        # Success messages
        "success_generic": "Операция успешно завершена.",
        "success_saved": "Изменения сохранены.",
        "success_updated": "Информация обновлена.",
        "success_deleted": "Элемент удален.",
        "success_created": "Новый элемент создан.",
        "success_action": "Действие успешно выполнено.",
        "success_purchase": "Покупка успешно завершена.",
        "success_trade": "Торговля успешно завершена.",
        "ideology_far_right": "Далеко правый",
        "ideology_right": "Право",
        "ideology_center": "Центр",
        "ideology_left": "Лево",
        "ideology_far_left": "Далеко лево"
    }
}

def get_text(key: str, lang: str = "en", default: Optional[str] = None, **kwargs) -> str:
    """Get text in the specified language with optional formatting"""
    try:
        # Default to English if the language is not supported
        if lang not in TRANSLATIONS:
            logger.warning(f"Unsupported language: {lang}, falling back to English")
            lang = "en"

        # Get the text for the key
        text = TRANSLATIONS[lang].get(key)

        # If not found in the requested language, try English as fallback
        if text is None:
            text = TRANSLATIONS["en"].get(key)
            if text is None:
                logger.warning(f"Missing translation for key '{key}' in both {lang} and English")
                return default if default is not None else f"[Missing translation: {key}]"
            else:
                logger.debug(f"Using English fallback for key '{key}' in language '{lang}'")

        # Format the text with the provided variables
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                logger.error(f"Translation format error: {e} in '{text}' for key '{key}'")
                return f"[Format error in translation: {key}]"
            except Exception as e:
                logger.error(f"Unexpected error formatting translation: {e}")
                return text

        return text

    except Exception as e:
        logger.error(f"Error in get_text: {e}")
        return default if default is not None else f"[Error: {key}]"

def get_player_language(player_id: int) -> str:
    """Get player's language preference from database"""
    return get_player_language(player_id)

def set_player_language(player_id: int, language: str) -> bool:
    """Set player's language preference in database"""
    return set_player_language(player_id, language)

def init_language_support():
    """Initialize language support"""
    logger.info("Language support initialized")

def get_cycle_name(cycle_type: str, lang: str = "en") -> str:
    """Get the localized name of a game cycle type."""
    cycle_types = {
        "en": {
            "influence": "Influence Phase",
            "action": "Action Phase",
            "resolution": "Resolution Phase",
            "maintenance": "Maintenance Phase"
        },
        "ru": {
            "influence": "Фаза влияния",
            "action": "Фаза действий",
            "resolution": "Фаза разрешения",
            "maintenance": "Фаза обслуживания"
        }
    }
    
    if lang not in cycle_types:
        lang = "en"
    
    return cycle_types[lang].get(cycle_type, cycle_type)

def get_resource_name(resource_type: str, lang: str = "en") -> str:
    """Get the localized name of a resource type."""
    try:
        return TRANSLATIONS[lang]["resource_types"].get(resource_type, resource_type)
    except KeyError:
        return TRANSLATIONS["en"]["resource_types"].get(resource_type, resource_type)

def format_ideology(ideology_score: int, lang: str = "en") -> str:
    """Format ideology score into text description."""
    if ideology_score >= 80:
        return get_text("ideology_far_right", lang)
    elif ideology_score >= 60:
        return get_text("ideology_right", lang)
    elif ideology_score >= 40:
        return get_text("ideology_center", lang)
    elif ideology_score >= 20:
        return get_text("ideology_left", lang)
    else:
        return get_text("ideology_far_left", lang)

def get_action_name(action_type: str, lang: str = "en") -> str:
    """Get localized name for an action type."""
    action_key = f"action_types.{action_type}"
    default_name = action_type.replace("_", " ").title()
    
    # Try to get the action name from translations
    action_name = get_text(action_key, lang, default=None)
    if action_name:
        return action_name
        
    # If not found in translations, check if it's in the action_types dictionary
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    action_types = translations.get("action_types", {})
    return action_types.get(action_type, default_name)