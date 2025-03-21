# languages_base.py
# Base language support for Belgrade Game Bot
import logging

logger = logging.getLogger(__name__)

# Dictionary of translations
TRANSLATIONS = {
    "en": {
        # Basic translations
        "welcome": "Welcome to the Belgrade Game! This is a strategic role-playing game set in 1990s Yugoslavia.",
        "not_registered": "You are not registered. Use /start to begin the game.",
        "registration_successful": "Registration successful! Welcome to the Belgrade Game.",
        "help_title": "Help - Belgrade Game Bot",
        "status_title": "Player Status",
        "resources_title": "Your Resources",
        "district_title": "District Information",
        "politician_title": "Politician Information",
        "action_success": "Action completed successfully.",
        "action_failed": "Action failed to complete.",
        "insufficient_resources": "You don't have enough {resource_type} for this action.",
        "invalid_target": "Invalid target for this action.",
        "action_cancelled": "Action cancelled.",
        "select_district": "Select a district:",
        "select_politician": "Select a politician:",
        "select_resources": "Select resources to use:",
        "select_action": "Select an action:",
        "confirm_action": "Confirm action?",
        "yes": "Yes",
        "no": "No",
        "cancel": "Cancel",
        "back": "Back",
        "next": "Next",
        "previous": "Previous",
        "done": "Done",
        "none": "None",
        "today": "Today",
        "yesterday": "Yesterday",
        "morning": "Morning",
        "evening": "Evening",
        "cycle": "Cycle",
        "name_prompt": "Please enter your character's name:",
        "name_set": "Your character's name has been set to: {name}",
        "language_prompt": "Please select your language:",
        "language_set": "Language set to English",
        "ideology_strongly_conservative": "Strongly Conservative",
        "ideology_conservative": "Conservative",
        "ideology_neutral": "Neutral",
        "ideology_reformist": "Reformist",
        "ideology_strongly_reformist": "Strongly Reformist",
        "select_language": "Select language:",
        "action_not_found": "Action not found.",
        "action_error": "An error occurred while processing your action.",
        "main_actions_left": "Main actions left: {count}",
        "quick_actions_left": "Quick actions left: {count}",
        "no_actions_left": "No actions left. Actions will refresh at the start of the next cycle.",
        "actions_refreshed": "Your actions have been refreshed!",
        "district_control": "Control: {control}%",
        "district_resources": "Resources available: {resources}",
        "start_command_help": "Start the game and register your character",
        "help_command_help": "Show this help message",
        "status_command_help": "View your character status and resources",
        "act_command_help": "Perform an action in a district",
        "districts_command_help": "View all districts and their status",
        "politicians_command_help": "View all politicians and their status",
        "news_command_help": "View recent news",
        "language_command_help": "Change your language preference",
        "join_command_help": "Join a coordinated action",
        
        # Error and user feedback messages
        "error_message": "Sorry, something went wrong. The error has been reported to administrators.",
        "action_timeout": "This action has timed out. Please try again.",
        "confirm_cancel_action": "Are you sure you want to cancel this action?",
        "network_error": "Network error occurred. Please try again.",
        "database_error": "Database error occurred. Please try again later.",
        "loading_message": "Loading, please wait...",
        "coordinated_action_expired": "This coordinated action has expired.",
        "joined_coordinated_action": "You've successfully joined the {action_type} action targeting {target} with {resources}.",
        "invalid_amount": "Invalid amount. Please enter a number.",
        "amount_too_large": "Amount too large. You only have {available}.",
        "transaction_successful": "Transaction successful!",
        "no_main_actions": "You have no main actions left. They will refresh in the next cycle.",
        "no_quick_actions": "You have no quick actions left. They will refresh in the next cycle.",
        
        # Command descriptions for help
        "action_influence": "🎯 Influence (gain control)",
        "action_attack": "🎯 Attack (take control)",
        "action_defense": "🎯 Defense (protect)",
        "action_recon": "⚡ Reconnaissance",
        "action_info": "⚡ Gather Information",
        "action_support": "⚡ Support",
        "action_join": "🤝 Join Coordinated Action",
        
        # Main menu translations
        "welcome_back": "Welcome back, {player_name}!",
        "what_next": "What would you like to do?",
        "action_button": "🎯 Actions",
        "status_button": "📊 Status",
        "districts_button": "🏙️ Districts",
        "politicians_button": "👥 Politicians",
        "join_button": "🤝 Join Actions",
        "language_button": "🌐 Language",
        "news_button": "📰 News",
        "help_button": "❓ Help",
        "back_button": "↩️ Back",
        
        # Player status
        "player_status": "Status for {player_name}",
        "remaining_actions": "Remaining Actions",
        "cycle_info": "Current Cycle",
        "cycle_deadline": "Cycle Deadline",
        "results_time": "Results will be processed at",
        "main_actions_status": "🎯 Main Actions: {count}",
        "quick_actions_status": "⚡ Quick Actions: {count}",
        
        # District and politician views
        "districts_info": "Districts of Belgrade",
        "politicians_info": "Politicians of Belgrade",
        "no_open_actions": "There are no open coordinated actions available to join.",
        "available_actions": "Available coordinated actions to join:",
        "option_not_available": "This option is not available.",
        "error_occurred": "An error occurred. Please try again.",
        "no_news": "There are no news items to display.",
        "recent_news": "Recent News",
        "help_info": "The Belgrade Game is a strategy game where you can influence districts, politicians, and coordinate with other players.\n\nCommands:\n/start - Start the game\n/status - View your status\n/help - Show this help message",
        
        # News and notifications
        "news_player_joined_action": "{player_name} joined a coordinated action with {resource_amount} {resource_type}!",
        "attack_button": "⚔️ Attack",
        "defense_button": "🛡️ Defense",
        "coordinated_action_button": "🤝 Coordinated Action",
        "no_resources": "No resources available",
        
        # District and politician action buttons
        "recon_button": "👁️ Reconnaissance",
        "info_button": "ℹ️ Information",
        "info_gathering_button": "🔍 Gather Intel",
        "influence_button": "🗣️ Influence",
        "undermine_button": "💥 Undermine",
        "back_to_districts": "Back to Districts",
        "back_to_politicians": "Back to Politicians",
        "back_to_main": "Main Menu",
        "back_to_main_menu": "Back to Main Menu",
        "view_status": "View Status",
        "custom_name": "Enter Custom Name",
        
        # Error messages
        "district_not_found": "District not found.",
        "politician_not_found": "Politician not found.",
        "error_retrieving_district": "Error retrieving district information.",
        "error_retrieving_politician": "Error retrieving politician information.",
        "target_not_found": "Target not found.",
        "view_district_again": "View District Again",
        "language_not_supported": "Sorry, this language is not supported yet.",
        "language_set_select_name": "Language set! Please select or enter your character name:",
        
        # Action messages
        "select_resources_for_action": "Select how much {resource_type} to use for {action} targeting {target}. You have {available} available.",
        "confirm_action_with_resources": "Confirm {action} on {target} using {resources}?",
        "confirm": "Confirm",
        "action_closed": "This action is no longer accepting participants.",
        "attack_effect": "Your forces are now targeting {target}.",
        "defense_effect": "You've enhanced the defenses of {target}.",
        "action_effect": "Your {action} on {target} is underway.",
        "player_joined_your_action": "{player} has joined your {action_type} action targeting {target} with {resources}!",
        
        # Add the new translations for help command
        "welcome": {
            "en": "Welcome to Belgrade Game!",
            "sr": "Добродошли у Београдску игру!"
        },
        "quick_start_guide": {
            "en": "Quick Start Guide:",
            "sr": "Водич за брзи почетак:"
        },
        "quick_start_1": {
            "en": "Type /start to register and begin playing",
            "sr": "Укуцајте /start да се региструјете и почнете да играте"
        },
        "quick_start_2": {
            "en": "Choose your language using /language",
            "sr": "Изаберите свој језик користећи /language"
        },
        "quick_start_3": {
            "en": "Set your character name when prompted",
            "sr": "Поставите име свог лика када вам буде затражено"
        },
        "quick_start_4": {
            "en": "Use /status to view your resources",
            "sr": "Користите /status да видите своје ресурсе"
        },
        "quick_start_5": {
            "en": "Start playing with /act to perform actions",
            "sr": "Почните да играте са /act да бисте извршили акције"
        },
        "need_more_help": {
            "en": "Need more help?",
            "sr": "Потребна вам је додатна помоћ?"
        },
        "contact_admin": {
            "en": "Contact the game administrator for assistance.",
            "sr": "Контактирајте администратора игре за помоћ."
        },
        "basic_commands": {
            "en": "Basic Commands:",
            "sr": "Основне команде:"
        },
        "start_command_help": {
            "en": "Register or check your status",
            "sr": "Региструјте се или проверите свој статус"
        },
        "help_command_help": {
            "en": "Show this help message",
            "sr": "Прикажи ову поруку помоћи"
        },
        "status_command_help": {
            "en": "View your character status and resources",
            "sr": "Погледајте статус свог лика и ресурсе"
        },
        "language_command_help": {
            "en": "Change your language settings",
            "sr": "Промените своја језичка подешавања"
        },
        "game_actions": {
            "en": "Game Actions:",
            "sr": "Акције игре:"
        },
        "act_command_help": {
            "en": "Perform game actions",
            "sr": "Извршите акције игре"
        },
        "join_command_help": {
            "en": "Join coordinated actions",
            "sr": "Придружите се координисаним акцијама"
        },
        "information_commands": {
            "en": "Information Commands:",
            "sr": "Информационе команде:"
        },
        "districts_command_help": {
            "en": "View district information",
            "sr": "Погледајте информације о дистриктима"
        },
        "politicians_command_help": {
            "en": "View politician information",
            "sr": "Погледајте информације о политичарима"
        },
        "news_command_help": {
            "en": "Check latest game news",
            "sr": "Проверите најновије вести из игре"
        },
        "resources_heading": {
            "en": "Resources:",
            "sr": "Ресурси:"
        },
        "resources_help_text": {
            "en": "• You get resources from districts you control\n• Different actions require different resources\n• Plan your resource usage carefully",
            "sr": "• Добијате ресурсе из дистрикта које контролишете\n• Различите акције захтевају различите ресурсе\n• Пажљиво планирајте коришћење ресурса"
        },
        "game_cycles_heading": {
            "en": "Game Cycles:",
            "sr": "Циклуси игре:"
        },
        "game_cycles_help_text": {
            "en": "• The game has morning and evening cycles\n• Your actions refresh at the start of each cycle\n• Resources are distributed at the start of each cycle",
            "sr": "• Игра има јутарње и вечерње циклусе\n• Ваше акције се обнављају на почетку сваког циклуса\n• Ресурси се дистрибуирају на почетку сваког циклуса"
        },
        "admin_commands": {
            "en": "Admin Commands:",
            "sr": "Админ команде:"
        },
        "admin_help_hint": {
            "en": "Use /admin_help to see all admin commands.",
            "sr": "Користите /admin_help да видите све админ команде."
        },
        "tips_heading": {
            "en": "Helpful Tips:",
            "sr": "Корисни савети:"
        },
        "help_tips": {
            "en": "• Form alliances with other players\n• Watch the news for important events\n• Balance your resource usage carefully",
            "sr": "• Формирајте савезе са другим играчима\n• Пратите вести за важне догађаје\n• Пажљиво балансирајте коришћење ресурса"
        },
        "help_footer": {
            "en": "If you need assistance, contact the game administrator.",
            "sr": "Ако вам је потребна помоћ, контактирајте администратора игре."
        },
        "cycle_morning": {
            "en": "🌅 Good morning! A new cycle has begun. Your operations have been reset and resources replenished.",
            "sr": "🌅 Добро јутро! Започео је нови циклус. Ваше операције су ресетоване и ресурси допуњени."
        },
        "cycle_evening": {
            "en": "🌃 Good evening! A new cycle has begun. Your operations have been reset and resources replenished.",
            "sr": "🌃 Добро вече! Започео је нови циклус. Ваше операције су ресетоване и ресурси допуњени."
        },
        "action_expired": {
            "en": "⌛ Your coordinated action has expired. You can start a new one using the /act command.",
            "sr": "⌛ Ваша координисана акција је истекла. Можете започети нову помоћу команде /act."
        }
    },
    "ru": {
        # Russian translations
        "welcome": "Добро пожаловать в Белградскую Игру! Это стратегическая ролевая игра, действие которой происходит в Югославии 1990-х годов.",
        "not_registered": "Вы не зарегистрированы. Используйте /start, чтобы начать игру.",
        "registration_successful": "Регистрация успешна! Добро пожаловать в Белградскую Игру.",
        "help_title": "Помощь - Бот Белградской Игры",
        "status_title": "Статус игрока",
        "resources_title": "Ваши ресурсы",
        "district_title": "Информация о районе",
        "politician_title": "Информация о политике",
        "action_success": "Действие успешно выполнено.",
        "action_failed": "Не удалось выполнить действие.",
        "insufficient_resources": "У вас недостаточно {resource_type} для этого действия.",
        "invalid_target": "Недопустимая цель для этого действия.",
        "action_cancelled": "Действие отменено.",
        "select_district": "Выберите район:",
        "select_politician": "Выберите политика:",
        "select_resources": "Выберите ресурсы для использования:",
        "select_action": "Выберите действие:",
        "confirm_action": "Подтвердить действие?",
        "yes": "Да",
        "no": "Нет",
        "cancel": "Отмена",
        "back": "Назад",
        "next": "Далее",
        "previous": "Предыдущий",
        "done": "Готово",
        "none": "Нет",
        "today": "Сегодня",
        "yesterday": "Вчера",
        "morning": "Утренний",
        "evening": "Вечерний",
        "cycle": "Цикл",
        "name_prompt": "Пожалуйста, введите имя вашего персонажа:",
        "name_set": "Имя вашего персонажа установлено: {name}",
        "language_prompt": "Пожалуйста, выберите ваш язык:",
        "language_set": "Язык установлен на Русский",
        "ideology_strongly_conservative": "Крайне консервативный",
        "ideology_conservative": "Консервативный",
        "ideology_neutral": "Нейтральный",
        "ideology_reformist": "Реформистский",
        "ideology_strongly_reformist": "Крайне реформистский",
        "select_language": "Выберите язык:",
        "action_not_found": "Действие не найдено.",
        "action_error": "Произошла ошибка при обработке вашего действия.",
        "main_actions_left": "Осталось основных действий: {count}",
        "quick_actions_left": "Осталось быстрых действий: {count}",
        "no_actions_left": "Не осталось действий. Действия будут обновлены в начале следующего цикла.",
        "actions_refreshed": "Ваши действия были обновлены!",
        "district_control": "Контроль: {control}%",
        "district_resources": "Доступные ресурсы: {resources}",
        "start_command_help": "Начать игру и зарегистрировать персонажа",
        "help_command_help": "Показать это сообщение помощи",
        "status_command_help": "Посмотреть статус персонажа и ресурсы",
        "act_command_help": "Выполнить действие в районе",
        "districts_command_help": "Просмотреть все районы и их статус",
        "politicians_command_help": "Просмотреть всех политиков и их статус",
        "news_command_help": "Просмотреть последние новости",
        "language_command_help": "Изменить языковые предпочтения",
        "join_command_help": "Присоединиться к координированному действию",
        
        # Error and user feedback messages
        "error_message": "Извините, что-то пошло не так. Ошибка была передана администраторам.",
        "action_timeout": "Время действия истекло. Пожалуйста, попробуйте снова.",
        "confirm_cancel_action": "Вы уверены, что хотите отменить это действие?",
        "network_error": "Произошла сетевая ошибка. Пожалуйста, попробуйте снова.",
        "database_error": "Произошла ошибка базы данных. Пожалуйста, попробуйте позже.",
        "loading_message": "Загрузка, пожалуйста, подождите...",
        "coordinated_action_expired": "Это координированное действие истекло.",
        "joined_coordinated_action": "Вы успешно присоединились к действию {action_type}, направленному на {target} с {resources}.",
        "invalid_amount": "Недопустимая сумма. Пожалуйста, введите число.",
        "amount_too_large": "Слишком большая сумма. У вас есть только {available}.",
        "transaction_successful": "Транзакция успешна!",
        "no_main_actions": "У вас не осталось основных действий. Они обновятся в следующем цикле.",
        "no_quick_actions": "У вас не осталось быстрых действий. Они обновятся в следующем цикле.",
        
        # Command descriptions for help
        "action_influence": "🎯 Влияние (получить контроль)",
        "action_attack": "🎯 Атака (захватить контроль)",
        "action_defense": "🎯 Защита (защитить)",
        "action_recon": "⚡ Разведка",
        "action_info": "⚡ Сбор информации",
        "action_support": "⚡ Поддержка",
        "action_join": "🤝 Присоединиться к координированному действию",
        
        # Main menu translations
        "welcome_back": "С возвращением, {player_name}!",
        "what_next": "Что бы вы хотели сделать?",
        "action_button": "🎯 Действия",
        "status_button": "📊 Статус",
        "districts_button": "🏙️ Районы",
        "politicians_button": "👥 Политики",
        "join_button": "🤝 Присоединиться",
        "language_button": "🌐 Язык",
        "news_button": "📰 Новости",
        "help_button": "❓ Помощь",
        "back_button": "↩️ Назад",
        
        # Player status
        "player_status": "Статус для {player_name}",
        "remaining_actions": "Оставшиеся действия",
        "cycle_info": "Текущий цикл",
        "cycle_deadline": "Крайний срок цикла",
        "results_time": "Результаты будут обработаны в",
        "main_actions_status": "🎯 Основные действия: {count}",
        "quick_actions_status": "⚡ Быстрые действия: {count}",
        
        # District and politician views
        "districts_info": "Районы Белграда",
        "politicians_info": "Политики Белграда",
        "no_open_actions": "Нет доступных координированных действий для присоединения.",
        "available_actions": "Доступные координированные действия для присоединения:",
        "option_not_available": "Эта опция недоступна.",
        "error_occurred": "Произошла ошибка. Пожалуйста, попробуйте снова.",
        "no_news": "Нет новостей для отображения.",
        "recent_news": "Последние новости",
        "help_info": "Белградская игра — это стратегическая игра, где вы можете влиять на районы, политиков и координировать действия с другими игроками.\n\nКоманды:\n/start - Начать игру\n/status - Просмотреть свой статус\n/help - Показать это сообщение помощи",
        
        # News and notifications
        "news_player_joined_action": "{player_name} присоединился к координированному действию с {resource_amount} {resource_type}!",
        "attack_button": "⚔️ Атака",
        "defense_button": "🛡️ Защита",
        "coordinated_action_button": "🤝 Координированное действие",
        "no_resources": "Нет доступных ресурсов",
        
        # District and politician action buttons
        "recon_button": "👁️ Разведка",
        "info_button": "ℹ️ Информация",
        "info_gathering_button": "🔍 Собирать Разведку",
        "influence_button": "🗣️ Влияние",
        "undermine_button": "💥 Подрывать",
        "back_to_districts": "Вернуться к Районам",
        "back_to_politicians": "Вернуться к Политикам",
        "back_to_main": "Главное Меню",
        "back_to_main_menu": "Вернуться в Главное Меню",
        "view_status": "Посмотреть Статус",
        "custom_name": "Введите Название",
        
        # Error messages
        "district_not_found": "Район не найден.",
        "politician_not_found": "Политик не найден.",
        "error_retrieving_district": "Ошибка получения информации о районе.",
        "error_retrieving_politician": "Ошибка получения информации о политике.",
        "target_not_found": "Цель не найдена.",
        "view_district_again": "Посмотреть Район Снова",
        "language_not_supported": "Извините, этот язык еще не поддерживается.",
        "language_set_select_name": "Язык установлен! Пожалуйста, выберите или введите имя вашего персонажа:",
        
        # Action messages
        "select_resources_for_action": "Выберите, сколько {resource_type} использовать для {action} на {target}. У вас есть {available} доступно.",
        "confirm_action_with_resources": "Подтвердить {action} на {target} с использованием {resources}?",
        "confirm": "Подтвердить",
        "action_closed": "Это действие больше не принимает участников.",
        "attack_effect": "Ваши силы теперь нацелены на {target}.",
        "defense_effect": "Вы усилили оборону {target}.",
        "action_effect": "Ваше {action} на {target} продолжается.",
        "player_joined_your_action": "{player} присоединился к вашему {action_type} действию на {target} с {resources}!"
    }
}

# Resource names translation
RESOURCE_NAMES = {
    "en": {
        "influence": "Influence",
        "resources": "Resources",
        "information": "Information",
        "force": "Force"
    },
    "ru": {
        "influence": "Влияние",
        "resources": "Ресурсы",
        "information": "Информация",
        "force": "Сила"
    }
}

# Cycle names translation
CYCLE_NAMES = {
    "en": {
        "morning": "Morning",
        "evening": "Evening"
    },
    "ru": {
        "morning": "Утренний",
        "evening": "Вечерний"
    }
}

# Action names translation
ACTION_NAMES = {
    "en": {
        "influence": "Influence",
        "attack": "Attack",
        "defense": "Defense",
        "recon": "Reconnaissance",
        "info": "Intelligence",
        "support": "Support"
    },
    "ru": {
        "influence": "Влияние",
        "attack": "Атака",
        "defense": "Оборона",
        "recon": "Разведка",
        "info": "Сбор информации",
        "support": "Поддержка"
    }
}

def get_text(key, lang="en", default=None, **kwargs):
    """
    Get text in the specified language with optional formatting
    
    Parameters:
    key (str): The translation key
    lang (str): Language code (en/ru)
    default (str): Default text if translation is missing
    **kwargs: Variables to format the text with
    
    Returns:
    str: Translated and formatted text
    """
    # Ensure lang is a valid string
    if not isinstance(lang, str) or lang.strip() == "":
        lang = "en"
        logger.warning(f"Invalid language code, defaulting to English")
        
    # Default to English if the language is not supported
    if lang not in TRANSLATIONS:
        lang = "en"

    # Get the text for the key
    try:
        text = TRANSLATIONS[lang].get(key)
    except Exception as e:
        logger.error(f"Error accessing translation: {e}")
        text = None

    # If not found in the requested language, try English as fallback
    if text is None:
        try:
            text = TRANSLATIONS["en"].get(key)
            # Log missing translation
            logger.warning(f"Missing translation for key '{key}' in language '{lang}'")
        except Exception as e:
            logger.error(f"Error accessing English fallback translation: {e}")
            text = None

    # If still not found, use the provided default or return an error message
    if text is None:
        if default is not None:
            text = default
        else:
            return f"[Missing translation: {key}]"

    # Format the text with the provided variables
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError as e:
            # Log formatting error
            logger.error(f"Translation format error: {e} in '{text}' for key '{key}'")
            # Try to provide a somewhat useful output despite the error
            return f"{text} [Format error: {e}]"
        except Exception as e:
            logger.error(f"Unexpected error formatting text: {e}")
            return f"{text} [Format error]"

    return text

def get_resource_name(resource, lang="en"):
    """Get the translated name of a resource"""
    if not isinstance(lang, str) or lang not in RESOURCE_NAMES:
        lang = "en"

    # Handle case where resource doesn't exist in the dictionary
    return RESOURCE_NAMES[lang].get(resource, resource)

def get_cycle_name(cycle, lang="en"):
    """Get the translated name of a cycle"""
    if not isinstance(lang, str) or lang not in CYCLE_NAMES:
        lang = "en"

    # Handle case where cycle doesn't exist in the dictionary
    return CYCLE_NAMES[lang].get(cycle, cycle)

def get_action_name(action, lang="en"):
    """Get the translated name of an action"""
    if not isinstance(lang, str) or lang not in ACTION_NAMES:
        lang = "en"

    # Handle case where action doesn't exist in the dictionary
    return ACTION_NAMES[lang].get(action, action) 