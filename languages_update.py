#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced language support for Belgrade Game Bot
Extends the base languages.py with additional translations and utilities
"""

import logging
import sqlite3
import re
from typing import Dict, Any, Optional, Union, List, Tuple

logger = logging.getLogger(__name__)

# Additional translations to add to the existing language dictionary
ADDITIONAL_TRANSLATIONS = {
    "en": {
        # Action result translations
        "action_detail_attack_success": "Your attack was successful! You've weakened enemy control in {district}.",
        "action_detail_attack_partial": "Your attack was partially successful. Some impact on enemy control in {district}.",
        "action_detail_attack_failure": "Your attack failed. Enemy defenses in {district} were too strong.",

        "action_detail_influence_success": "Your influence efforts in {district} were highly effective!",
        "action_detail_influence_partial": "Your influence in {district} has grown, but less than expected.",
        "action_detail_influence_failure": "Your influence attempt in {district} failed to gain traction.",

        "action_detail_defense_success": "Your defenses in {district} held strong against all attacks!",
        "action_detail_defense_partial": "Your defenses in {district} partially mitigated incoming attacks.",
        "action_detail_defense_failure": "Your defenses in {district} were overwhelmed.",

        # International politics
        "international_active": "International politician {name} ({role}) has taken action!",
        "international_sanctions": "Sanctions have been imposed on {district}!",
        "international_support": "International support has arrived for {district}!",
        "international_diplomatic": "Diplomatic pressure is affecting relations in {district}.",

        # Extended resource descriptions
        "influence_desc": "Political capital and ability to sway others",
        "resources_desc": "Economic and material assets",
        "information_desc": "Intelligence, secrets, and knowledge",
        "force_desc": "Military, police, and armed groups",

        # Detailed district descriptions
        "district_desc_stari_grad": "The political heart of Belgrade, where government offices are located",
        "district_desc_novi_beograd": "Modern business district with international connections",
        "district_desc_zemun": "Historical district with strong criminal elements",
        "district_desc_savski_venac": "Diplomatic quarter with many foreign embassies",
        "district_desc_vozdovac": "Military base and security headquarters",
        "district_desc_cukarica": "Industrial area with factories and working-class population",
        "district_desc_palilula": "University district with student activism",
        "district_desc_vracar": "Cultural and religious center",

        # Detailed politician descriptions
        "politician_desc_milosevic": "As President of Yugoslavia, Milošević maintains tight control over state institutions and security forces.",
        "politician_desc_djindjic": "A progressive reformist pushing for democratic changes and closer ties with the West.",
        "politician_desc_arkan": "A paramilitary leader with strong connections to organized crime and nationalist groups.",
        "politician_desc_pavkovic": "The military commander loyal to the regime, controlling army deployments.",

        # Detailed joint action descriptions
        "joint_action_influence_desc": "A coordinated influence campaign across multiple fronts",
        "joint_action_attack_desc": "A multi-pronged attack operation",
        "joint_action_defense_desc": "A unified defensive strategy",

        # Detailed resource distribution messages
        "resource_distribution_success": "Your controlled districts have generated resources!",
        "resource_distribution_none": "You didn't receive any resources this cycle. Control more districts to generate income.",

        # Detailed trade system messages
        "trade_system_info": "The trading system allows you to exchange resources with other players.",
        "trade_how_to": "To create a trade, use: /trade <player_id> offer <resource> <amount> request <resource> <amount>",
        "trade_complete_details": "Trade #{trade_id} completed. You received: {received} and gave: {given}",

        # Enhanced help categories
        "help_category_basic": "Basic Commands",
        "help_category_action": "Action Commands",
        "help_category_resource": "Resource Commands",
        "help_category_political": "Political Commands",
        "help_category_advanced": "Advanced Features",

        # Advanced feature descriptions
        "feature_joint_actions": "Joint Actions: Coordinate with other players for stronger effects",
        "feature_trade": "Trading: Exchange resources with other players",
        "feature_politician_abilities": "Politician Abilities: Use special actions through allied politicians",

        # New user tips
        "tip_first_steps": "First steps: Focus on gaining control in one district. Use influence actions to establish presence.",
        "tip_resources": "Resource tip: Convert general Resources to specialized ones based on your strategy.",
        "tip_politicians": "Politician tip: Build relationships with politicians who match your ideology.",
        "tip_defense": "Defense tip: Defend territories you want to keep, not every place you have presence.",

        # More detailed error messages
        "error_action_timeout": "Action timed out. Please try again.",
        "error_invalid_resource_combination": "Invalid resource combination for this action type.",
        "error_politician_unavailable": "This politician is not available for interaction at this time.",
        "error_district_contested": "This district is heavily contested right now. Your action faces strong opposition.",

        # Welcome back message
        "welcome_back": "Welcome back, {character_name}! You've been away for {days} days. Here's what's changed:",

        # Detailed game mechanics for help command
        "mechanics_control": "District Control: Control points represent your influence in a district. 60+ points = full control with resource generation.",
        "mechanics_actions": "Actions: You have 1 main action and 2 quick actions every 3 hours. Main actions have stronger effects.",
        "mechanics_resources": "Resources: Generated from controlled districts. Each district produces different resource types.",
        "mechanics_ideology": "Ideology: Your position on the reform-conservative scale (-5 to +5) affects compatibility with politicians.",

        # Command helpers
        "command_helper_action": "For best results with /action, target districts where you already have some presence or that match your ideology.",
        "command_helper_quick_action": "Quick actions are good for reconnaissance before committing main actions.",
        "command_helper_view_district": "Use /view_district without arguments to see all districts first.",

        # Status messages
        "player_joined": "New player joined: {username} as {character_name}",
        "player_left": "Player {character_name} has left the game",
        "player_active": "Player activity: {active_count} active in the last 24 hours, {total_count} total",

        # Achievement notifications
        "achievement_first_control": "Achievement: First District Control! You now fully control {district}.",
        "achievement_international": "Achievement: International Recognition! Your first alliance with international politician {name}.",

        # Pluralization templates
        "points_count": "{count} point|{count} points",
        "players_count": "{count} player|{count} players",
        "resources_count": "{count} resource|{count} resources",
        "actions_count": "{count} action|{count} actions",
    },

    "ru": {
        # Action result translations
        "action_detail_attack_success": "Ваша атака была успешной! Вы ослабили контроль противника в районе {district}.",
        "action_detail_attack_partial": "Ваша атака была частично успешной. Некоторое влияние на контроль противника в районе {district}.",
        "action_detail_attack_failure": "Ваша атака провалилась. Защита противника в районе {district} оказалась слишком сильной.",

        "action_detail_influence_success": "Ваши усилия по влиянию в районе {district} были очень эффективны!",
        "action_detail_influence_partial": "Ваше влияние в районе {district} выросло, но меньше, чем ожидалось.",
        "action_detail_influence_failure": "Ваша попытка влияния в районе {district} не получила развития.",

        "action_detail_defense_success": "Ваша защита в районе {district} выдержала все атаки!",
        "action_detail_defense_partial": "Ваша защита в районе {district} частично смягчила входящие атаки.",
        "action_detail_defense_failure": "Ваша защита в районе {district} была подавлена.",

        # International politics
        "international_active": "Международный политик {name} ({role}) предпринял действие!",
        "international_sanctions": "На {district} наложены санкции!",
        "international_support": "В {district} пришла международная поддержка!",
        "international_diplomatic": "Дипломатическое давление влияет на отношения в {district}.",

        # Extended resource descriptions
        "influence_desc": "Политический капитал и способность влиять на других",
        "resources_desc": "Экономические и материальные активы",
        "information_desc": "Разведданные, секреты и знания",
        "force_desc": "Военные, полиция и вооруженные группы",

        # Detailed district descriptions
        "district_desc_stari_grad": "Политическое сердце Белграда, где расположены правительственные учреждения",
        "district_desc_novi_beograd": "Современный деловой район с международными связями",
        "district_desc_zemun": "Исторический район с сильными криминальными элементами",
        "district_desc_savski_venac": "Дипломатический квартал со многими иностранными посольствами",
        "district_desc_vozdovac": "Военная база и штаб-квартиры безопасности",
        "district_desc_cukarica": "Промышленная зона с фабриками и рабочим населением",
        "district_desc_palilula": "Университетский район со студенческим активизмом",
        "district_desc_vracar": "Культурный и религиозный центр",

        # Detailed politician descriptions
        "politician_desc_milosevic": "Как президент Югославии, Милошевич поддерживает жесткий контроль над государственными институтами и силами безопасности.",
        "politician_desc_djindjic": "Прогрессивный реформатор, выступающий за демократические изменения и более тесные связи с Западом.",
        "politician_desc_arkan": "Лидер военизированных формирований с сильными связями с организованной преступностью и националистическими группами.",
        "politician_desc_pavkovic": "Военный командир, верный режиму, контролирующий развертывание армии.",

        # Detailed joint action descriptions
        "joint_action_influence_desc": "Скоординированная кампания влияния по нескольким направлениям",
        "joint_action_attack_desc": "Многосторонняя наступательная операция",
        "joint_action_defense_desc": "Единая оборонительная стратегия",

        # Detailed resource distribution messages
        "resource_distribution_success": "Ваши контролируемые районы сгенерировали ресурсы!",
        "resource_distribution_none": "Вы не получили ресурсов в этом цикле. Контролируйте больше районов для получения дохода.",

        # Detailed trade system messages
        "trade_system_info": "Система торговли позволяет обмениваться ресурсами с другими игроками.",
        "trade_how_to": "Чтобы создать обмен, используйте: /trade <id_игрока> offer <ресурс> <количество> request <ресурс> <количество>",
        "trade_complete_details": "Обмен #{trade_id} завершен. Вы получили: {received} и отдали: {given}",

        # Enhanced help categories
        "help_category_basic": "Основные команды",
        "help_category_action": "Команды действий",
        "help_category_resource": "Команды ресурсов",
        "help_category_political": "Политические команды",
        "help_category_advanced": "Продвинутые функции",

        # Advanced feature descriptions
        "feature_joint_actions": "Совместные действия: Координируйтесь с другими игроками для более сильных эффектов",
        "feature_trade": "Торговля: Обменивайтесь ресурсами с другими игроками",
        "feature_politician_abilities": "Способности политиков: Используйте специальные действия через союзных политиков",

        # New user tips
        "tip_first_steps": "Первые шаги: Сосредоточьтесь на получении контроля в одном районе. Используйте действия влияния для установления присутствия.",
        "tip_resources": "Совет по ресурсам: Конвертируйте общие Ресурсы в специализированные в зависимости от вашей стратегии.",
        "tip_politicians": "Совет по политикам: Стройте отношения с политиками, которые соответствуют вашей идеологии.",
        "tip_defense": "Совет по защите: Защищайте территории, которые вы хотите сохранить, а не каждое место, где у вас есть присутствие.",

        # More detailed error messages
        "error_action_timeout": "Время действия истекло. Пожалуйста, попробуйте снова.",
        "error_invalid_resource_combination": "Недопустимая комбинация ресурсов для этого типа действия.",
        "error_politician_unavailable": "Этот политик недоступен для взаимодействия в данный момент.",
        "error_district_contested": "Этот район сейчас сильно оспаривается. Ваше действие сталкивается с сильной оппозицией.",

        # Welcome back message
        "welcome_back": "С возвращением, {character_name}! Вы отсутствовали {days} дней. Вот что изменилось:",

        # Detailed game mechanics for help command
        "mechanics_control": "Контроль района: Очки контроля представляют ваше влияние в районе. 60+ очков = полный контроль с генерацией ресурсов.",
        "mechanics_actions": "Действия: У вас есть 1 основное действие и 2 быстрых действия каждые 3 часа. Основные действия имеют более сильные эффекты.",
        "mechanics_resources": "Ресурсы: Генерируются из контролируемых районов. Каждый район производит разные типы ресурсов.",
        "mechanics_ideology": "Идеология: Ваша позиция по шкале реформы-консерватизма (от -5 до +5) влияет на совместимость с политиками.",

        # Command helpers
        "command_helper_action": "Для лучших результатов с /action, выбирайте районы, где у вас уже есть присутствие или которые соответствуют вашей идеологии.",
        "command_helper_quick_action": "Быстрые действия хороши для разведки перед совершением основных действий.",
        "command_helper_view_district": "Используйте /view_district без аргументов, чтобы сначала увидеть все районы.",

        # Status messages
        "player_joined": "Новый игрок присоединился: {username} как {character_name}",
        "player_left": "Игрок {character_name} покинул игру",
        "player_active": "Активность игроков: {active_count} активны за последние 24 часа, {total_count} всего",

        # Achievement notifications
        "achievement_first_control": "Достижение: Первый контроль района! Теперь вы полностью контролируете {district}.",
        "achievement_international": "Достижение: Международное признание! Ваш первый союз с международным политиком {name}.",

        # Pluralization templates
        "points_count": "{count} очко|{count} очка|{count} очков",
        "players_count": "{count} игрок|{count} игрока|{count} игроков",
        "resources_count": "{count} ресурс|{count} ресурса|{count} ресурсов",
        "actions_count": "{count} действие|{count} действия|{count} действий",
    }
}

# Admin-specific translations
ADMIN_TRANSLATIONS = {
    "en": {
        # Extended admin command descriptions
        "admin_resource_detailed": "Add resources to a player's inventory",
        "admin_set_control_detailed": "Set a player's control points in a district",
        "admin_reset_actions_detailed": "Reset a player's available actions to full",
        "admin_process_cycle_detailed": "Manually trigger cycle processing (results calculation)",
        "admin_add_news_detailed": "Add a custom news item visible to all or specific players",
        "admin_set_ideology_detailed": "Set a player's ideology score (affects politician compatibility)",

        # Admin resource management
        "admin_resources_added_detailed": "Added {amount} {resource_type} to player {player_id}. Previous: {previous}, New: {new_amount}",
        "admin_resources_removed": "Removed {amount} {resource_type} from player {player_id}. Previous: {previous}, New: {new_amount}",
        "admin_resources_view": "Resources for player {player_id}: Influence: {influence}, Resources: {resources}, Information: {information}, Force: {force}",

        # Admin district control management
        "admin_control_added": "Added {points} control points to player {player_id} in district {district_id}. New total: {new_total}",
        "admin_control_removed": "Removed {points} control points from player {player_id} in district {district_id}. New total: {new_total}",
        "admin_control_view": "Control status for district {district_id}:",

        # Admin player management
        "admin_player_rename": "Renamed player {player_id} from '{old_name}' to '{new_name}'",
        "admin_player_list_detailed": "Detailed player list (including activity and resources)",
        "admin_player_reset": "Reset player {player_id} data (control points and resources)",

        # Admin international politics
        "admin_intl_activate": "Manually activated international politician {name}",
        "admin_intl_deactivate": "Deactivated international politician {name}",
        "admin_intl_view": "Active international politicians this cycle:",

        # Advanced admin actions
        "admin_force_action": "Force an action for player {player_id} in district {district_id}",
        "admin_block_action": "Blocked pending action {action_id} from player {player_id}",
        "admin_modify_action": "Modified action {action_id} parameters",
    },

    "ru": {
        # Extended admin command descriptions
        "admin_resource_detailed": "Добавить ресурсы в инвентарь игрока",
        "admin_set_control_detailed": "Установить очки контроля игрока в районе",
        "admin_reset_actions_detailed": "Сбросить доступные действия игрока до полных",
        "admin_process_cycle_detailed": "Вручную запустить обработку цикла (расчет результатов)",
        "admin_add_news_detailed": "Добавить пользовательскую новость, видимую всем или конкретным игрокам",
        "admin_set_ideology_detailed": "Установить идеологический показатель игрока (влияет на совместимость с политиками)",

        # Admin resource management
        "admin_resources_added_detailed": "Добавлено {amount} {resource_type} игроку {player_id}. Ранее: {previous}, Новое: {new_amount}",
        "admin_resources_removed": "Удалено {amount} {resource_type} у игрока {player_id}. Ранее: {previous}, Новое: {new_amount}",
        "admin_resources_view": "Ресурсы игрока {player_id}: Влияние: {influence}, Ресурсы: {resources}, Информация: {information}, Сила: {force}",

        # Admin district control management
        "admin_control_added": "Добавлено {points} очков контроля игроку {player_id} в районе {district_id}. Новый итог: {new_total}",
        "admin_control_removed": "Удалено {points} очков контроля у игрока {player_id} в районе {district_id}. Новый итог: {new_total}",
        "admin_control_view": "Статус контроля для района {district_id}:",

        # Admin player management
        "admin_player_rename": "Переименован игрок {player_id} с '{old_name}' на '{new_name}'",
        "admin_player_list_detailed": "Подробный список игроков (включая активность и ресурсы)",
        "admin_player_reset": "Сброшены данные игрока {player_id} (очки контроля и ресурсы)",

        # Admin international politics
        "admin_intl_activate": "Вручную активирован международный политик {name}",
        "admin_intl_deactivate": "Деактивирован международный политик {name}",
        "admin_intl_view": "Активные международные политики в этом цикле:",

        # Advanced admin actions
        "admin_force_action": "Принудительное действие для игрока {player_id} в районе {district_id}",
        "admin_block_action": "Заблокировано ожидающее действие {action_id} от игрока {player_id}",
        "admin_modify_action": "Изменены параметры действия {action_id}",
    }
}


def update_translations(translations_dict=None):
    """
    Update the main translations dictionary with additional translations

    This function must be called during initialization to ensure all
    new translations are available in the main dictionary

    Args:
        translations_dict: Optional dictionary to update directly (for testing)
    """
    try:
        if translations_dict is None:
            from languages import TRANSLATIONS
        else:
            TRANSLATIONS = translations_dict

        for lang in ADDITIONAL_TRANSLATIONS:
            if lang in TRANSLATIONS:
                # Update existing language with new translations
                for key, value in ADDITIONAL_TRANSLATIONS[lang].items():
                    TRANSLATIONS[lang][key] = value
            else:
                # Add new language (unlikely case)
                logger.warning(f"Adding new language {lang} to TRANSLATIONS")
                TRANSLATIONS[lang] = ADDITIONAL_TRANSLATIONS[lang]

        logger.info("Translations updated with additional entries")
        return True
    except ImportError as e:
        logger.error(f"Failed to import TRANSLATIONS from languages.py: {e}")
        return False
    except Exception as e:
        logger.error(f"Error in update_translations: {e}")
        return False


def update_admin_translations(translations_dict=None):
    """
    Update the main translations dictionary with admin translations

    Args:
        translations_dict: Optional dictionary to update directly (for testing)
    """
    try:
        if translations_dict is None:
            from languages import TRANSLATIONS
        else:
            TRANSLATIONS = translations_dict

        for lang in ADMIN_TRANSLATIONS:
            if lang in TRANSLATIONS:
                # Update existing language with admin translations
                for key, value in ADMIN_TRANSLATIONS[lang].items():
                    TRANSLATIONS[lang][key] = value

        logger.info("Admin translations added")
        return True
    except ImportError as e:
        logger.error(f"Failed to import TRANSLATIONS from languages.py: {e}")
        return False
    except Exception as e:
        logger.error(f"Error in update_admin_translations: {e}")
        return False


def init_admin_language_support():
    """Initialize admin language support by updating admin translations"""
    update_admin_translations()
    logger.info("Admin language support initialized")
    return True


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
    try:
        from languages import get_resource_name, get_text

        formatted_parts = []
        for resource_type, amount in resources.items():
            if amount != 0:
                resource_name = get_resource_name(resource_type, lang)
                formatted_parts.append(f"{amount} {resource_name}")

        if not formatted_parts:
            return get_text("none", lang, default="None")

        return ", ".join(formatted_parts)
    except ImportError:
        logger.error("Failed to import functions from languages.py")
        # Fallback simple formatting
        return ", ".join(
            f"{amount} {resource_type}" for resource_type, amount in resources.items() if amount != 0) or "None"
    except Exception as e:
        logger.error(f"Error in format_resource_list: {e}")
        return "Error formatting resources"


def get_translated_keyboard(keyboard_items: List[Dict[str, str]], lang: str = "en") -> List[Dict[str, str]]:
    """
    Translate a list of keyboard items

    Args:
        keyboard_items: List of keyboard items with 'text' keys
        lang: Language code

    Returns:
        List of translated keyboard items
    """
    try:
        from languages import get_text

        translated_items = []
        for item in keyboard_items:
            translated_item = item.copy()
            if 'text' in item:
                # If text is a translation key, translate it
                translated_item['text'] = get_text(item['text'], lang, item['text'])
            translated_items.append(translated_item)

        return translated_items
    except ImportError:
        logger.error("Failed to import get_text from languages.py")
        return keyboard_items
    except Exception as e:
        logger.error(f"Error in get_translated_keyboard: {e}")
        return keyboard_items


# Pluralization support for different languages
def format_plurals(key: str, count: int, lang: str = "en") -> str:
    """
    Format pluralized text based on count

    Args:
        key: Translation key for text with plural forms
        count: Count number to determine which form to use
        lang: Language code

    Returns:
        Formatted text with correct plural form
    """
    try:
        from languages import TRANSLATIONS, get_text

        if lang not in TRANSLATIONS or key not in TRANSLATIONS[lang]:
            # Fall back to English or default
            return get_text(key, "en", default=f"{count}").format(count=count)

        # Get the pluralization template
        template = TRANSLATIONS[lang][key]

        # Split the template into plural forms
        forms = template.split("|")

        # For English (and most languages with 2 forms)
        if lang == "en" or len(forms) == 2:
            form_index = 0 if count == 1 else 1
            return forms[min(form_index, len(forms) - 1)].format(count=count)

        # For Russian and other languages with complex pluralization
        elif lang == "ru" and len(forms) >= 3:
            # Russian pluralization rules
            if count % 10 == 1 and count % 100 != 11:
                form_index = 0  # 1, 21, 31, ...
            elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                form_index = 1  # 2-4, 22-24, ...
            else:
                form_index = 2  # 0, 5-20, 25-30, ...

            return forms[min(form_index, len(forms) - 1)].format(count=count)

        # Generic fallback for other languages
        else:
            # Just use the first form as fallback
            return forms[0].format(count=count)

    except Exception as e:
        logger.error(f"Error formatting plurals: {e}")
        return f"{count}"


def has_translation(key: str, lang: str = "en") -> bool:
    """
    Check if a translation key exists for the specified language

    Args:
        key: Translation key to check
        lang: Language code

    Returns:
        bool: True if translation exists, False otherwise
    """
    try:
        from languages import TRANSLATIONS

        return lang in TRANSLATIONS and key in TRANSLATIONS[lang]
    except ImportError:
        logger.error("Failed to import TRANSLATIONS from languages.py")
        return False
    except Exception as e:
        logger.error(f"Error checking translation: {e}")
        return False


def check_format_strings(text: str) -> List[str]:
    """
    Extract format string parameters from a text

    Args:
        text: Text to check for format strings

    Returns:
        List of format string parameter names
    """
    pattern = re.compile(r'\{([^{}]+)}')
    return pattern.findall(text)