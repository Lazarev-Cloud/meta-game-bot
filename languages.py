# Language support for Belgrade Game Bot
# This file contains translations for all bot messages
import sqlite3

# Dictionary of translations
TRANSLATIONS = {
    "en": {
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
        "help_political": "*Political Commands:*\n• /politicians - List available politicians\n• /politician_status [name] - Get information about a specific politician\n• /international - Information about international politicians",
        "help_footer": "For detailed game rules, refer to the game document.",

        # Status information
        "status_title": "Status of {character_name}",
        "status_ideology": "Ideology: {ideology} ({score})",
        "status_resources": "*Resources:*\n🔵 Influence: {influence}\n💰 Resources: {resources}\n🔍 Information: {information}\n👊 Force: {force}",
        "status_actions": "*Actions Remaining:*\nMain Actions: {main}\nQuick Actions: {quick}",
        "status_districts": "*Controlled Districts:*",
        "status_no_districts": "*Controlled Districts:* None",

        # Map and districts
        "map_title": "Current Control Map of Belgrade",
        "map_legend": "Legend:\n🔒 Strong control (80+ points)\n✅ Controlled (60-79 points)\n⚠️ Contested (20-59 points)\n❌ Weak presence (<20 points)",
        "map_no_control": "No control established",
        "map_too_large": "The map is being generated. Check the web UI for details.",
        "district_not_found": "District '{district_name}' not found. Use /view_district without arguments to see a list of districts.",
        "select_district": "Select a district to view:",

        # Time information
        "time_info": "*Game Time Information*",
        "time_current": "Current Cycle: *{cycle}*",
        "time_deadlines": "Time until submission deadline: *{deadline}*\nTime until results: *{results}*",
        "time_schedule": "*Daily Schedule:*\nMorning Cycle: 6:00 - 12:00 (submissions), 13:00 (results)\nEvening Cycle: 13:01 - 18:00 (submissions), 19:00 (results)",
        "time_refresh": "Remember: Actions refresh every 3 hours!",
        "deadline_passed": "Deadline passed",
        "minutes": "minutes",

        # News
        "news_title": "Recent News",
        "no_news": "There is no news to report at this time.",

        # Actions
        "no_main_actions": "You have no main actions left. Actions refresh every 3 hours or at the start of a new cycle.",
        "no_quick_actions": "You have no quick actions left. Actions refresh every 3 hours or at the start of a new cycle.",
        "select_action_type": "Select the type of main action you want to perform:",
        "select_quick_action": "Select the type of quick action you want to perform:",
        "action_cancelled": "Your last pending action has been cancelled and resources refunded.",
        "no_pending_actions": "You have no pending actions to cancel.",
        "actions_refreshed": "Your actions have been refreshed!\n\nMain Actions: {main}\nQuick Actions: {quick}",
        "current_actions": "Current Actions Remaining:\n\nMain Actions: {main}\nQuick Actions: {quick}",

        # Resource management
        "resources_title": "Your Current Resources",
        "resources_guide": "*Resource Usage Guide:*\n• *Influence* - Used for political maneuvers, gaining additional actions\n• *Resources* - Economy, finances, connections. Can be converted to other resources\n• *Information* - Intelligence, rumors. Used for reconnaissance\n• *Force* - Military, police, criminal structures. Effective for attacks and defense",
        "convert_usage": "Usage: /convert_resource [type] [amount]\nExample: /convert_resource influence 2\n\nThis will convert 2 'resources' into 1 of the specified type.",
        "amount_not_number": "Amount must be a number.",
        "amount_not_positive": "Amount must be positive.",
        "invalid_resource_type": "Invalid resource type. Valid types: {valid_types}",
        "not_enough_resources": "You don't have enough resources. Need {needed}, have {available}.",
        "conversion_success": "Converted {resources_used} resources into {amount} {resource_type}.",
        "no_districts_controlled": "You don't control any districts yet, so you won't receive any resource income.\n\nControl districts (60+ control points) to receive resources each cycle.",
        "income_controlled_districts": "*Controlled Districts:*",
        "income_total": "*Total Per Cycle:*\n🔵 Influence: +{influence}\n💰 Resources: +{resources}\n🔍 Information: +{information}\n👊 Force: +{force}",
        "income_note": "*Note:* Resources are distributed at the end of each cycle.",
        "income_no_full_control": "You have districts with some presence, but none are fully controlled yet.\n\nYou need 60+ control points in a district to receive resources from it.",

        # Politicians
        "politicians_title": "Key Politicians in Belgrade",
        "no_politicians": "No politicians found in the database.",
        "select_politician": "Select a politician to view:",
        "politician_not_found": "Politician '{name}' not found. Use /politician_status without arguments to see a list.",
        "international_title": "International Politicians",
        "no_international": "No international politicians found in the database.",
        "international_note": "*Note:* International politicians can activate randomly each cycle. Their actions can significantly impact the political landscape in Belgrade. Use /news to stay informed about their latest activities.",

        # Ideology descriptions
        "ideology_strongly_conservative": "Strongly Conservative",
        "ideology_conservative": "Conservative",
        "ideology_neutral": "Neutral",
        "ideology_reformist": "Reformist",
        "ideology_strongly_reformist": "Strongly Reformist",

        # Relationship descriptions
        "compatibility_good": "Good ideological compatibility",
        "compatibility_moderate": "Moderate ideological differences",
        "compatibility_poor": "Significant ideological differences",

        # Actions on politicians
        "politician_influence_no_resources": "You need at least 2 Influence resources to influence a politician. Action cancelled.",
        "politician_influence_no_action": "You need a main action to influence a politician. Action cancelled.",
        "politician_influence_success": "You have used your influence on {name}. Your relationship with them may improve. Results will be processed at the end of the cycle.",
        "politician_info_no_resources": "You need at least 1 Information resource to gather info on a politician. Action cancelled.",
        "politician_info_no_action": "You need a quick action to gather info on a politician. Action cancelled.",
        "politician_info_title": "Intelligence Report: {name}",
        "politician_undermine_no_resources": "You need at least 2 Information resources to undermine a politician. Action cancelled.",
        "politician_undermine_no_action": "You need a main action to undermine a politician. Action cancelled.",
        "politician_undermine_success": "You have started undermining {name}'s influence. This may weaken their position in their district. Results will be processed at the end of the cycle.",

        # Cycle results
        "cycle_results_title": "📊 *{cycle} Cycle Results*",
        "your_actions": "*Your Actions:*",
        "no_details": "No details available",
        "your_districts": "*Your Districts:*",
        "recent_news": "*Recent News:*",
        "current_resources": "*Current Resources:*",

        # Control status
        "control_strong": "🔒 Strong control",
        "control_full": "✅ Controlled",
        "control_contested": "⚠️ Contested",
        "control_weak": "❌ Weak presence",
        "control_points": "points",

        # Language settings
        "language_current": "Your current language is: {language}",
        "language_select": "Please select your preferred language:",
        "language_changed": "Language changed to English",
        "language_button_en": "English",
        "language_button_ru": "Русский",

        # Action types
        "action_influence": "Influence",
        "action_attack": "Attack",
        "action_defense": "Defense",
        "action_recon": "Reconnaissance",
        "action_info": "Spread Information",
        "action_support": "Support",
        "action_cancel": "Cancel",

        # Resources used in actions
        "select_resources": "Select resources to use for {action_type} action in {district_name}:",
        "insufficient_resources": "You don't have enough {resource_type} resources. Action cancelled.",
        "action_submitted": "Your {action_type} action in {target_name} has been submitted using {resources}. Results will be processed at the end of the cycle.",
        "info_spreading": "Your information has been spread through the news network. It will appear in the next news cycle.",
        "enter_info_content": "What information do you want to spread? Please type your message:",
        "invalid_info_content": "Please provide valid information content.",
        "action_error": "Something went wrong. Please try again with /quick_action.",
        "info_from_user": "Information from {user}",

        # Status indicators for results
        "status_success": "✅",
        "status_partial": "⚠️",
        "status_failure": "❌",
        "status_info": "ℹ️",

        # Admin commands
        "admin_only": "This command is for administrators only.",
        "admin_news_usage": "Usage: /admin_add_news [title] [content]",
        "admin_news_added": "News added with ID: {news_id}",
        "admin_cycle_processed": "Game cycle processed.",
        "admin_resources_usage": "Usage: /admin_add_resources [player_id] [resource_type] [amount]",
        "admin_invalid_args": "Invalid arguments.",
        "admin_invalid_resource": "Invalid resource type.",
        "admin_player_not_found": "Player {player_id} not found.",
        "admin_resources_added": "Added {amount} {resource_type} to player {player_id}. New total: {new_amount}",
        "admin_control_usage": "Usage: /admin_set_control [player_id] [district_id] [control_points]",
        "admin_district_not_found": "District {district_id} not found.",
        "admin_control_updated": "Updated control for player {player_id} in district {district_id} to {control_points} points.",

        # Notifications
        "actions_refreshed_notification": "Your actions have been refreshed! You now have 1 main action and 2 quick actions available."
    },

    "ru": {
        # Basic commands and responses
        "welcome": "Добро пожаловать в Белградскую Игру, {user_name}! Эта игра моделирует политическую борьбу в Югославии 1998 года через контроль над районами Белграда.\n\nПожалуйста, введите имя вашего персонажа:",
        "name_set": "Добро пожаловать, {character_name}! Теперь вы политический игрок в Белграде 1998 года.\n\nИспользуйте /help для просмотра доступных команд и /status для проверки вашей текущей ситуации.",
        "invalid_name": "Пожалуйста, введите корректное имя.",
        "operation_cancelled": "Операция отменена.",
        "not_registered": "Вы не зарегистрированы. Используйте /start, чтобы начать игру.",

        # Help and documentation
        "help_title": "Руководство по командам Белградской Игры",
        "help_basic": "*Основные команды:*\n• /start - Начать игру и зарегистрировать персонажа\n• /help - Показать список команд\n• /status - Проверить ресурсы и контроль районов\n• /map - Просмотреть текущую карту контроля\n• /time - Показать текущий игровой цикл и время до следующего\n• /news - Показать последние новости\n• /language - Изменить язык интерфейса",
        "help_action": "*Команды действий:*\n• /action - Подать основную заявку (влияние, атака, защита)\n• /quick_action - Подать быструю заявку (разведка, информация, поддержка)\n• /cancel_action - Отменить последнюю заявку\n• /actions_left - Проверить оставшиеся заявки\n• /view_district [район] - Просмотр информации о районе",
        "help_resource": "*Команды ресурсов:*\n• /resources - Просмотр имеющихся ресурсов\n• /convert_resource [тип] [количество] - Конвертация ресурсов\n• /check_income - Проверка ожидаемого прихода ресурсов",
        "help_political": "*Политические команды:*\n• /politicians - Список доступных политиков\n• /politician_status [имя] - Информация о конкретном политике\n• /international - Информация о международных политиках",
        "help_footer": "Для подробных правил игры обратитесь к игровому документу.",

        # Status information
        "status_title": "Статус персонажа {character_name}",
        "status_ideology": "Идеология: {ideology} ({score})",
        "status_resources": "*Ресурсы:*\n🔵 Влияние: {influence}\n💰 Ресурсы: {resources}\n🔍 Информация: {information}\n👊 Сила: {force}",
        "status_actions": "*Оставшиеся действия:*\nОсновные заявки: {main}\nБыстрые заявки: {quick}",
        "status_districts": "*Контролируемые районы:*",
        "status_no_districts": "*Контролируемые районы:* Отсутствуют",

        # Map and districts
        "map_title": "Текущая карта контроля Белграда",
        "map_legend": "Обозначения:\n🔒 Сильный контроль (80+ очков)\n✅ Контролируется (60-79 очков)\n⚠️ Оспаривается (20-59 очков)\n❌ Слабое присутствие (<20 очков)",
        "map_no_control": "Контроль не установлен",
        "map_too_large": "Карта генерируется. Проверьте веб-интерфейс для подробностей.",
        "district_not_found": "Район '{district_name}' не найден. Используйте /view_district без аргументов для просмотра списка.",
        "select_district": "Выберите район для просмотра:",

        # Time information
        "time_info": "*Информация об игровом времени*",
        "time_current": "Текущий цикл: *{cycle}*",
        "time_deadlines": "Время до окончания подачи заявок: *{deadline}*\nВремя до результатов: *{results}*",
        "time_schedule": "*Ежедневное расписание:*\nУтренний цикл: 6:00 - 12:00 (подача заявок), 13:00 (результаты)\nВечерний цикл: 13:01 - 18:00 (подача заявок), 19:00 (результаты)",
        "time_refresh": "Напоминание: Действия обновляются каждые 3 часа!",
        "deadline_passed": "Срок подачи истёк",
        "minutes": "минут",

        # News
        "news_title": "Последние новости",
        "no_news": "На данный момент новостей нет.",

        # Actions
        "no_main_actions": "У вас не осталось основных заявок. Заявки обновляются каждые 3 часа или в начале нового цикла.",
        "no_quick_actions": "У вас не осталось быстрых заявок. Заявки обновляются каждые 3 часа или в начале нового цикла.",
        "select_action_type": "Выберите тип основной заявки, которую хотите выполнить:",
        "select_quick_action": "Выберите тип быстрой заявки, которую хотите выполнить:",
        "action_cancelled": "Ваша последняя заявка отменена, ресурсы возвращены.",
        "no_pending_actions": "У вас нет ожидающих заявок для отмены.",
        "actions_refreshed": "Ваши заявки обновлены!\n\nОсновные заявки: {main}\nБыстрые заявки: {quick}",
        "current_actions": "Текущие оставшиеся заявки:\n\nОсновные заявки: {main}\nБыстрые заявки: {quick}",

        # Resource management
        "resources_title": "Ваши текущие ресурсы",
        "resources_guide": "*Руководство по использованию ресурсов:*\n• *Влияние* - Используется для политических манёвров, получения дополнительных заявок\n• *Ресурсы* - Экономика, финансы, связи. Можно конвертировать в другие ресурсы\n• *Информация* - Разведданные, слухи. Используется для разведки\n• *Сила* - Военные, полиция, криминальные структуры. Эффективны для атак и защиты",
        "convert_usage": "Использование: /convert_resource [тип] [количество]\nПример: /convert_resource influence 2\n\nЭто конвертирует 2 'resources' в 1 указанного типа.",
        "amount_not_number": "Количество должно быть числом.",
        "amount_not_positive": "Количество должно быть положительным.",
        "invalid_resource_type": "Недопустимый тип ресурса. Допустимые типы: {valid_types}",
        "not_enough_resources": "У вас недостаточно ресурсов. Нужно {needed}, у вас есть {available}.",
        "conversion_success": "Конвертировано {resources_used} ресурсов в {amount} {resource_type}.",
        "no_districts_controlled": "Вы пока не контролируете ни одного района, поэтому не будете получать ресурсы.\n\nКонтролируйте районы (60+ очков контроля) для получения ресурсов каждый цикл.",
        "income_controlled_districts": "*Контролируемые районы:*",
        "income_total": "*Всего за цикл:*\n🔵 Влияние: +{influence}\n💰 Ресурсы: +{resources}\n🔍 Информация: +{information}\n👊 Сила: +{force}",
        "income_note": "*Примечание:* Ресурсы распределяются в конце каждого цикла.",
        "income_no_full_control": "У вас есть районы с некоторым присутствием, но ни один не контролируется полностью.\n\nДля получения ресурсов из района нужно 60+ очков контроля.",

        # Politicians
        "politicians_title": "Ключевые политики Белграда",
        "no_politicians": "В базе данных не найдено политиков.",
        "select_politician": "Выберите политика для просмотра:",
        "politician_not_found": "Политик '{name}' не найден. Используйте /politician_status без аргументов для просмотра списка.",
        "international_title": "Международные политики",
        "no_international": "В базе данных не найдены международные политики.",
        "international_note": "*Примечание:* Международные политики могут активироваться случайным образом в каждом цикле. Их действия могут существенно повлиять на политический ландшафт Белграда. Используйте /news для получения актуальной информации об их деятельности.",

        # Ideology descriptions
        "ideology_strongly_conservative": "Крайне консервативный",
        "ideology_conservative": "Консервативный",
        "ideology_neutral": "Нейтральный",
        "ideology_reformist": "Реформистский",
        "ideology_strongly_reformist": "Крайне реформистский",

        # Relationship descriptions
        "compatibility_good": "Хорошая идеологическая совместимость",
        "compatibility_moderate": "Умеренные идеологические различия",
        "compatibility_poor": "Существенные идеологические различия",

        # Actions on politicians
        "politician_influence_no_resources": "Вам нужно минимум 2 единицы Влияния для воздействия на политика. Действие отменено.",
        "politician_influence_no_action": "Вам нужна основная заявка для воздействия на политика. Действие отменено.",
        "politician_influence_success": "Вы использовали своё влияние на {name}. Ваши отношения с ним могут улучшиться. Результаты будут обработаны в конце цикла.",
        "politician_info_no_resources": "Вам нужна минимум 1 единица Информации для сбора данных о политике. Действие отменено.",
        "politician_info_no_action": "Вам нужна быстрая заявка для сбора данных о политике. Действие отменено.",
        "politician_info_title": "Разведывательный отчёт: {name}",
        "politician_undermine_no_resources": "Вам нужно минимум 2 единицы Информации для подрыва влияния политика. Действие отменено.",
        "politician_undermine_no_action": "Вам нужна основная заявка для подрыва влияния политика. Действие отменено.",
        "politician_undermine_success": "Вы начали подрывать влияние {name}. Это может ослабить его позиции в его районе. Результаты будут обработаны в конце цикла.",

        # Cycle results
        "cycle_results_title": "📊 *Результаты {cycle} цикла*",
        "your_actions": "*Ваши действия:*",
        "no_details": "Нет доступных деталей",
        "your_districts": "*Ваши районы:*",
        "recent_news": "*Недавние новости:*",
        "current_resources": "*Текущие ресурсы:*",

        # Control status
        "control_strong": "🔒 Сильный контроль",
        "control_full": "✅ Контролируется",
        "control_contested": "⚠️ Оспаривается",
        "control_weak": "❌ Слабое присутствие",
        "control_points": "очков",

        # Language settings
        "language_current": "Ваш текущий язык: {language}",
        "language_select": "Пожалуйста, выберите предпочитаемый язык:",
        "language_changed": "Язык изменён на русский",
        "language_button_en": "English",
        "language_button_ru": "Русский",

        # Action types
        "action_influence": "Влияние",
        "action_attack": "Атака",
        "action_defense": "Защита",
        "action_recon": "Разведка",
        "action_info": "Распространение информации",
        "action_support": "Поддержка",
        "action_cancel": "Отмена",

        # Resources used in actions
        "select_resources": "Выберите ресурсы для {action_type} действия в районе {district_name}:",
        "insufficient_resources": "У вас недостаточно ресурсов типа {resource_type}. Действие отменено.",
        "action_submitted": "Ваше действие {action_type} в {target_name} было подано с использованием {resources}. Результаты будут обработаны в конце цикла.",
        "info_spreading": "Ваша информация распространена через новостную сеть. Она появится в следующем новостном цикле.",
        "enter_info_content": "Какую информацию вы хотите распространить? Пожалуйста, напишите сообщение:",
        "invalid_info_content": "Пожалуйста, предоставьте корректное содержание информации.",
        "action_error": "Что-то пошло не так. Пожалуйста, попробуйте снова с /quick_action.",
        "info_from_user": "Информация от {user}",

        # Status indicators for results
        "status_success": "✅",
        "status_partial": "⚠️",
        "status_failure": "❌",
        "status_info": "ℹ️",

        # Admin commands
        "admin_only": "Эта команда только для администраторов.",
        "admin_news_usage": "Использование: /admin_add_news [заголовок] [содержание]",
        "admin_news_added": "Новость добавлена с ID: {news_id}",
        "admin_cycle_processed": "Игровой цикл обработан.",
        "admin_resources_usage": "Использование: /admin_add_resources [ID игрока] [тип ресурса] [количество]",
        "admin_invalid_args": "Недопустимые аргументы.",
        "admin_invalid_resource": "Недопустимый тип ресурса.",
        "admin_player_not_found": "Игрок {player_id} не найден.",
        "admin_resources_added": "Добавлено {amount} {resource_type} игроку {player_id}. Новый итог: {new_amount}",
        "admin_control_usage": "Использование: /admin_set_control [ID игрока] [ID района] [очки контроля]",
        "admin_district_not_found": "Район {district_id} не найден.",
        "admin_control_updated": "Обновлён контроль для игрока {player_id} в районе {district_id} до {control_points} очков.",

        # Notifications
        "actions_refreshed_notification": "Ваши заявки обновлены! Теперь у вас есть 1 основная заявка и 2 быстрые заявки."
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


# Helper function to get text in the correct language
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
    # Default to English if the language is not supported
    if lang not in TRANSLATIONS:
        lang = "en"

    # Get the text for the key
    text = TRANSLATIONS[lang].get(key)

    # If not found in the requested language, try English as fallback
    if text is None:
        text = TRANSLATIONS["en"].get(key)
        # Log missing translation
        import logging
        logging.warning(f"Missing translation for key '{key}' in language '{lang}'")

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
            import logging
            logging.error(f"Translation format error: {e} in '{text}' for key '{key}'")
            return f"[Format error in translation: {key}]"

    return text


def get_cycle_name(cycle, lang="en"):
    """Get the translated name of a cycle"""
    if lang not in CYCLE_NAMES:
        lang = "en"

    return CYCLE_NAMES[lang].get(cycle, cycle)


def get_action_name(action_type, lang="en"):
    """Get the translated name of an action type"""
    action_translations = {
        "en": {
            "influence": "Influence",
            "attack": "Attack",
            "defense": "Defense",
            "recon": "Reconnaissance",
            "info": "Information Spreading",
            "support": "Support"
        },
        "ru": {
            "influence": "Влияние",
            "attack": "Атака",
            "defense": "Защита",
            "recon": "Разведка",
            "info": "Распространение информации",
            "support": "Поддержка"
        }
    }

    if lang not in action_translations:
        lang = "en"

    return action_translations[lang].get(action_type, action_type)


# Player language retrieval function for main.py

def get_player_language(player_id):
    """Get player's preferred language"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()

    cursor.execute("SELECT language FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        return "en"  # Default to English


def set_player_language(player_id, language):
    """Set player's preferred language"""
    conn = sqlite3.connect('belgrade_game.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE players SET language = ? WHERE player_id = ?",
        (language, player_id)
    )

    conn.commit()
    conn.close()


def get_resource_name(resource, lang="en"):
    """Get the translated name of a resource"""
    if lang not in RESOURCE_NAMES:
        lang = "en"

    return RESOURCE_NAMES[lang].get(resource, resource)


def format_ideology(ideology_score, lang="en"):
    """Get formatted ideology description based on score"""
    if ideology_score > 3:
        return get_text("ideology_strongly_conservative", lang)
    elif ideology_score > 0:
        return get_text("ideology_conservative", lang)
    elif ideology_score == 0:
        return get_text("ideology_neutral", lang)
    elif ideology_score > -3:
        return get_text("ideology_reformist", lang)
    else:
        return get_text("ideology_strongly_reformist", lang)
