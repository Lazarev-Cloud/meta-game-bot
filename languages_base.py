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
        
        # Properly formatted quick start guide texts (flattened structure)
        "welcome_en": "Welcome to Belgrade Game!",
        "welcome_sr": "Добродошли у Београдску игру!",
        "quick_start_guide_en": "Quick Start Guide:",
        "quick_start_guide_sr": "Водич за брзи почетак:",
        "quick_start_1_en": "Type /start to register and begin playing",
        "quick_start_1_sr": "Укуцајте /start да се региструјете и почнете да играте",
        "quick_start_2_en": "Choose your language using /language",
        "quick_start_2_sr": "Изаберите свој језик користећи /language",
        "quick_start_3_en": "Set your character name when prompted",
        "quick_start_3_sr": "Поставите име свог лика када вам буде затражено",
        "quick_start_4_en": "Use /status to view your resources",
        "quick_start_4_sr": "Користите /status да видите своје ресурсе",
        "quick_start_5_en": "Start playing with /act to perform actions",
        "quick_start_5_sr": "Почните да играте са /act да бисте извршили акције",
        "need_more_help_en": "Need more help?",
        "need_more_help_sr": "Потребна вам је додатна помоћ?",
        "contact_admin_en": "Contact the game administrator for assistance.",
        "contact_admin_sr": "Контактирајте администратора игре за помоћ.",
        "basic_commands_en": "Basic Commands:",
        "basic_commands_sr": "Основне команде:",
        "start_command_help_en": "Register or check your status",
        "start_command_help_sr": "Региструјте се или проверите свој статус",
        "help_command_help_en": "Show this help message",
        "help_command_help_sr": "Прикажи ову поруку помоћи",
        "status_command_help_en": "View your character status and resources",
        "status_command_help_sr": "Погледајте статус свог лика и ресурсе",
        "language_command_help_en": "Change your language settings",
        "language_command_help_sr": "Промените своја језичка подешавања",
        "game_actions_en": "Game Actions:",
        "game_actions_sr": "Акције игре:",
        "act_command_help_en": "Perform game actions",
        "act_command_help_sr": "Извршите акције игре",
        "join_command_help_en": "Join coordinated actions",
        "join_command_help_sr": "Придружите се координисаним акцијама",
        "information_commands_en": "Information Commands:",
        "information_commands_sr": "Информационе команде:",
        "districts_command_help_en": "View district information",
        "districts_command_help_sr": "Погледајте информације о дистриктима",
        "politicians_command_help_en": "View politician information",
        "politicians_command_help_sr": "Погледајте информације о политичарима",
        "news_command_help_en": "Check latest game news",
        "news_command_help_sr": "Проверите најновије вести из игре",
        "resources_heading_en": "Resources:",
        "resources_heading_sr": "Ресурси:",
        "resources_help_text_en": "• You get resources from districts you control\n• Different actions require different resources\n• Plan your resource usage carefully",
        "resources_help_text_sr": "• Добијате ресурсе из дистрикта које контролишете\n• Различите акције захтевају различите ресурсе\n• Пажљиво планирајте коришћење ресурса",
        "game_cycles_heading_en": "Game Cycles:",
        "game_cycles_heading_sr": "Циклуси игре:",
        "game_cycles_help_text_en": "• The game has morning and evening cycles\n• Your actions refresh at the start of each cycle\n• Resources are distributed at the start of each cycle",
        "game_cycles_help_text_sr": "• Игра има јутарње и вечерње циклусе\n• Ваше акције се обнављају на почетку сваког циклуса\n• Ресурси се дистрибуирају на почетку сваког циклуса",
        "admin_commands_en": "Admin Commands:",
        "admin_commands_sr": "Админ команде:",
        "admin_help_hint_en": "Use /admin_help to see all admin commands.",
        "admin_help_hint_sr": "Користите /admin_help да видите све админ команде.",
        "tips_heading_en": "Helpful Tips:",
        "tips_heading_sr": "Корисни савети:",
        "help_tips_en": "• Form alliances with other players\n• Watch the news for important events\n• Balance your resource usage carefully",
        "help_tips_sr": "• Формирајте савезе са другим играчима\n• Пратите вести за важне догађаје\n• Пажљиво балансирајте коришћење ресурса",
        "help_footer_en": "If you need assistance, contact the game administrator.",
        "help_footer_sr": "Ако вам је потребна помоћ, контактирајте администратора игре.",
        "cycle_morning_en": "🌅 Good morning! A new cycle has begun. Your operations have been reset and resources replenished.",
        "cycle_morning_sr": "🌅 Добро јутро! Започео је нови циклус. Ваше операције су ресетоване и ресурси допуњени.",
        "cycle_evening_en": "🌃 Good evening! A new cycle has begun. Your operations have been reset and resources replenished.",
        "cycle_evening_sr": "🌃 Добро вече! Започео је нови циклус. Ваше операције су ресетоване и ресурси допуњени.",
        "action_expired_en": "⌛ Your coordinated action has expired. You can start a new one using the /act command.",
        "action_expired_sr": "⌛ Ваша координисана акција је истекла. Можете започети нову помоћу команде /act."
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
        "player_joined_your_action": "{player} присоединился к вашему {action_type} действию на {target} с {resources}!",

        # Russian translations for flattened help keys
        "welcome_en": "Welcome to Belgrade Game!",
        "welcome_ru": "Добро пожаловать в Белградскую Игру!",
        "quick_start_guide_en": "Quick Start Guide:",
        "quick_start_guide_ru": "Краткое руководство:",
        "quick_start_1_en": "Type /start to register and begin playing",
        "quick_start_1_ru": "Напишите /start, чтобы зарегистрироваться и начать игру",
        "quick_start_2_en": "Choose your language using /language",
        "quick_start_2_ru": "Выберите язык с помощью команды /language",
        "quick_start_3_en": "Set your character name when prompted",
        "quick_start_3_ru": "Установите имя вашего персонажа, когда появится запрос",
        "quick_start_4_en": "Use /status to view your resources",
        "quick_start_4_ru": "Используйте /status для просмотра ваших ресурсов",
        "quick_start_5_en": "Start playing with /act to perform actions",
        "quick_start_5_ru": "Начните играть с помощью /act для выполнения действий",
        "need_more_help_en": "Need more help?",
        "need_more_help_ru": "Нужна дополнительная помощь?",
        "contact_admin_en": "Contact the game administrator for assistance.",
        "contact_admin_ru": "Свяжитесь с администратором игры для получения помощи.",
        "basic_commands_en": "Basic Commands:",
        "basic_commands_ru": "Основные команды:",
        "start_command_help_en": "Register or check your status",
        "start_command_help_ru": "Зарегистрироваться или проверить свой статус",
        "help_command_help_en": "Show this help message",
        "help_command_help_ru": "Показать это сообщение помощи",
        "status_command_help_en": "View your character status and resources",
        "status_command_help_ru": "Посмотреть статус вашего персонажа и ресурсы",
        "language_command_help_en": "Change your language settings",
        "language_command_help_ru": "Изменить настройки языка",
        "game_actions_en": "Game Actions:",
        "game_actions_ru": "Игровые действия:",
        "act_command_help_en": "Perform game actions",
        "act_command_help_ru": "Выполнить игровые действия",
        "join_command_help_en": "Join coordinated actions",
        "join_command_help_ru": "Присоединиться к координированным действиям",
        "information_commands_en": "Information Commands:",
        "information_commands_ru": "Информационные команды:",
        "districts_command_help_en": "View district information",
        "districts_command_help_ru": "Просмотреть информацию о районах",
        "politicians_command_help_en": "View politician information",
        "politicians_command_help_ru": "Просмотреть информацию о политиках",
        "news_command_help_en": "Check latest game news",
        "news_command_help_ru": "Проверить последние новости игры",
        "resources_heading_en": "Resources:",
        "resources_heading_ru": "Ресурсы:",
        "resources_help_text_en": "• You get resources from districts you control\n• Different actions require different resources\n• Plan your resource usage carefully",
        "resources_help_text_ru": "• Вы получаете ресурсы из районов, которые контролируете\n• Разные действия требуют разных ресурсов\n• Тщательно планируйте использование ресурсов",
        "game_cycles_heading_en": "Game Cycles:",
        "game_cycles_heading_ru": "Игровые циклы:",
        "game_cycles_help_text_en": "• The game has morning and evening cycles\n• Your actions refresh at the start of each cycle\n• Resources are distributed at the start of each cycle",
        "game_cycles_help_text_ru": "• В игре есть утренние и вечерние циклы\n• Ваши действия обновляются в начале каждого цикла\n• Ресурсы распределяются в начале каждого цикла",
        "admin_commands_en": "Admin Commands:",
        "admin_commands_ru": "Команды администратора:",
        "admin_help_hint_en": "Use /admin_help to see all admin commands.",
        "admin_help_hint_ru": "Используйте /admin_help, чтобы увидеть все команды администратора.",
        "tips_heading_en": "Helpful Tips:",
        "tips_heading_ru": "Полезные советы:",
        "help_tips_en": "• Form alliances with other players\n• Watch the news for important events\n• Balance your resource usage carefully",
        "help_tips_ru": "• Формируйте альянсы с другими игроками\n• Следите за новостями о важных событиях\n• Тщательно балансируйте использование ресурсов",
        "help_footer_en": "If you need assistance, contact the game administrator.",
        "help_footer_ru": "Если вам нужна помощь, свяжитесь с администратором игры.",
        "cycle_morning_en": "🌅 Good morning! A new cycle has begun. Your operations have been reset and resources replenished.",
        "cycle_morning_ru": "🌅 Доброе утро! Начался новый цикл. Ваши операции были сброшены, а ресурсы пополнены.",
        "cycle_evening_en": "🌃 Good evening! A new cycle has begun. Your operations have been reset and resources replenished.",
        "cycle_evening_ru": "🌃 Добрый вечер! Начался новый цикл. Ваши операции были сброшены, а ресурсы пополнены.",
        "action_expired_en": "⌛ Your coordinated action has expired. You can start a new one using the /act command.",
        "action_expired_ru": "⌛ Срок вашего координированного действия истек. Вы можете начать новое, используя команду /act."
    },
    "sr": {
        # Serbian translations
        "welcome": "Добродошли у Београдску игру! Ово је стратешка игра улога смештена у Југославији деведесетих.",
        "not_registered": "Нисте регистровани. Користите /start да започнете игру.",
        "registration_successful": "Регистрација успешна! Добродошли у Београдску игру.",
        "help_title": "Помоћ - Бот Београдске Игре",
        "status_title": "Статус играча",
        "resources_title": "Ваши ресурси",
        "district_title": "Информације о округу",
        "politician_title": "Информације о политичару",
        "action_success": "Акција успешно завршена.",
        "action_failed": "Акција није успела.",
        "insufficient_resources": "Немате довољно {resource_type} за ову акцију.",
        "invalid_target": "Неважећа мета за ову акцију.",
        "action_cancelled": "Акција отказана.",
        "select_district": "Изаберите округ:",
        "select_politician": "Изаберите политичара:",
        "select_resources": "Изаберите ресурсе за коришћење:",
        "select_action": "Изаберите акцију:",
        "confirm_action": "Потврдите акцију?",
        "yes": "Да",
        "no": "Не",
        "cancel": "Откажи",
        "back": "Назад",
        "next": "Следеће",
        "previous": "Претходно",
        "done": "Готово",
        "none": "Ништа",
        "today": "Данас",
        "yesterday": "Јуче",
        "morning": "Јутро",
        "evening": "Вече",
        "cycle": "Циклус",
        "name_prompt": "Молимо унесите име вашег лика:",
        "name_set": "Име вашег лика је постављено на: {name}",
        "language_prompt": "Молимо изаберите ваш језик:",
        "language_set": "Језик је постављен на Српски",
        "ideology_strongly_conservative": "Изразито конзервативно",
        "ideology_conservative": "Конзервативно",
        "ideology_neutral": "Неутрално",
        "ideology_reformist": "Реформистички",
        "ideology_strongly_reformist": "Изразито реформистички",
        "select_language": "Изаберите језик:",
        "action_not_found": "Акција није пронађена.",
        "action_error": "Дошло је до грешке приликом обраде ваше акције.",
        "main_actions_left": "Преосталих главних акција: {count}",
        "quick_actions_left": "Преосталих брзих акција: {count}",
        "no_actions_left": "Нема преосталих акција. Акције ће се обновити на почетку следећег циклуса.",
        "actions_refreshed": "Ваше акције су обновљене!",
        "district_control": "Контрола: {control}%",
        "district_resources": "Доступни ресурси: {resources}",
        "start_command_help": "Започните игру и региструјте свој лик",
        "help_command_help": "Прикажи ову поруку помоћи",
        "status_command_help": "Погледајте статус свог лика и ресурсе",
        "act_command_help": "Извршите акцију у округу",
        "districts_command_help": "Погледајте све округе и њихов статус",
        "politicians_command_help": "Погледајте све политичаре и њихов статус",
        "news_command_help": "Погледајте најновије вести",
        "language_command_help": "Промените своје језичке преференције",
        "join_command_help": "Придружите се координисаној акцији",
        
        # Error and user feedback messages
        "error_message": "Жао нам је, нешто је пошло наопако. Грешка је пријављена администраторима.",
        "action_timeout": "Истекло је време за ову акцију. Молимо покушајте поново.",
        "confirm_cancel_action": "Да ли сте сигурни да желите да откажете ову акцију?",
        "network_error": "Дошло је до мрежне грешке. Молимо покушајте поново.",
        "database_error": "Дошло је до грешке у бази података. Молимо покушајте касније.",
        "loading_message": "Учитавање, молимо сачекајте...",
        "coordinated_action_expired": "Ова координисана акција је истекла.",
        "joined_coordinated_action": "Успешно сте се придружили {action_type} акцији циљајући {target} са {resources}.",
        "invalid_amount": "Неважећи износ. Молимо унесите број.",
        "amount_too_large": "Износ је превелик. Имате само {available}.",
        "transaction_successful": "Трансакција успешна!",
        "no_main_actions": "Немате више главних акција. Обновиће се у следећем циклусу.",
        "no_quick_actions": "Немате више брзих акција. Обновиће се у следећем циклусу.",
        
        # Command descriptions for help
        "action_influence": "🎯 Утицај (стицање контроле)",
        "action_attack": "🎯 Напад (преузимање контроле)",
        "action_defense": "🎯 Одбрана (заштита)",
        "action_recon": "⚡ Извиђање",
        "action_info": "⚡ Прикупљање информација",
        "action_support": "⚡ Подршка",
        "action_join": "🤝 Придружи се координисаној акцији",
        
        # Main menu translations
        "welcome_back": "Добродошли назад, {player_name}!",
        "what_next": "Шта бисте желели да урадите?",
        "action_button": "🎯 Акције",
        "status_button": "📊 Статус",
        "districts_button": "🏙️ Окрузи",
        "politicians_button": "👥 Политичари",
        "join_button": "🤝 Придружи се",
        "language_button": "🌐 Језик",
        "news_button": "📰 Вести",
        "help_button": "❓ Помоћ",
        "back_button": "↩️ Назад",
        
        # Player status
        "player_status": "Статус за {player_name}",
        "remaining_actions": "Преостале акције",
        "cycle_info": "Тренутни циклус",
        "cycle_deadline": "Рок циклуса",
        "results_time": "Резултати ће бити обрађени у",
        "main_actions_status": "🎯 Главне акције: {count}",
        "quick_actions_status": "⚡ Брзе акције: {count}",
        
        # District and politician views
        "districts_info": "Окрузи Београда",
        "politicians_info": "Политичари Београда",
        "no_open_actions": "Нема отворених координисаних акција за придруживање.",
        "available_actions": "Доступне координисане акције за придруживање:",
        "option_not_available": "Ова опција није доступна.",
        "error_occurred": "Дошло је до грешке. Молимо покушајте поново.",
        "no_news": "Нема вести за приказ.",
        "recent_news": "Недавне вести",
        "help_info": "Београдска игра је стратешка игра у којој можете утицати на округе, политичаре и координисати са другим играчима.\n\nКоманде:\n/start - Започни игру\n/status - Погледај свој статус\n/help - Прикажи ову поруку помоћи",
        
        # News and notifications
        "news_player_joined_action": "{player_name} се придружио координисаној акцији са {resource_amount} {resource_type}!",
        "attack_button": "⚔️ Напад",
        "defense_button": "🛡️ Одбрана",
        "coordinated_action_button": "🤝 Координисана акција",
        "no_resources": "Нема доступних ресурса",
        
        # District and politician action buttons
        "recon_button": "👁️ Извиђање",
        "info_button": "ℹ️ Информације",
        "info_gathering_button": "🔍 Прикупи информације",
        "influence_button": "🗣️ Утицај",
        "undermine_button": "💥 Подривање",
        "back_to_districts": "Назад на Округе",
        "back_to_politicians": "Назад на Политичаре",
        "back_to_main": "Главни мени",
        "back_to_main_menu": "Назад на главни мени",
        "view_status": "Погледај статус",
        "custom_name": "Унеси прилагођено име",
        
        # Error messages
        "district_not_found": "Округ није пронађен.",
        "politician_not_found": "Политичар није пронађен.",
        "error_retrieving_district": "Грешка при добављању информација о округу.",
        "error_retrieving_politician": "Грешка при добављању информација о политичару.",
        "target_not_found": "Циљ није пронађен.",
        "view_district_again": "Погледај округ поново",
        "language_not_supported": "Жао нам је, овај језик још није подржан.",
        "language_set_select_name": "Језик је постављен! Молимо изаберите или унесите име вашег лика:",
        
        # Action messages
        "select_resources_for_action": "Изаберите колико {resource_type} ћете користити за {action} циљајући {target}. Имате {available} доступно.",
        "confirm_action_with_resources": "Потврдите {action} на {target} коришћењем {resources}?",
        "confirm": "Потврди",
        "action_closed": "Ова акција више не прихвата учеснике.",
        "attack_effect": "Ваше снаге сада циљају {target}.",
        "defense_effect": "Појачали сте одбрану {target}.",
        "action_effect": "Ваша {action} на {target} је у току.",
        "player_joined_your_action": "{player} се придружио вашој {action_type} акцији циљајући {target} са {resources}!",
        
        # Serbian translations for flattened help keys
        "welcome_en": "Welcome to Belgrade Game!",
        "welcome_sr": "Добродошли у Београдску игру!",
        "quick_start_guide_en": "Quick Start Guide:",
        "quick_start_guide_sr": "Водич за брзи почетак:",
        "quick_start_1_en": "Type /start to register and begin playing",
        "quick_start_1_sr": "Укуцајте /start да се региструјете и почнете да играте",
        "quick_start_2_en": "Choose your language using /language",
        "quick_start_2_sr": "Изаберите свој језик користећи /language",
        "quick_start_3_en": "Set your character name when prompted",
        "quick_start_3_sr": "Поставите име свог лика када вам буде затражено",
        "quick_start_4_en": "Use /status to view your resources",
        "quick_start_4_sr": "Користите /status да видите своје ресурсе",
        "quick_start_5_en": "Start playing with /act to perform actions",
        "quick_start_5_sr": "Почните да играте са /act да бисте извршили акције",
        "need_more_help_en": "Need more help?",
        "need_more_help_sr": "Потребна вам је додатна помоћ?",
        "contact_admin_en": "Contact the game administrator for assistance.",
        "contact_admin_sr": "Контактирајте администратора игре за помоћ.",
        "basic_commands_en": "Basic Commands:",
        "basic_commands_sr": "Основне команде:",
        "start_command_help_en": "Register or check your status",
        "start_command_help_sr": "Региструјте се или проверите свој статус",
        "help_command_help_en": "Show this help message",
        "help_command_help_sr": "Прикажи ову поруку помоћи",
        "status_command_help_en": "View your character status and resources",
        "status_command_help_sr": "Погледајте статус свог лика и ресурсе",
        "language_command_help_en": "Change your language settings",
        "language_command_help_sr": "Промените своја језичка подешавања",
        "game_actions_en": "Game Actions:",
        "game_actions_sr": "Акције игре:",
        "act_command_help_en": "Perform game actions",
        "act_command_help_sr": "Извршите акције игре",
        "join_command_help_en": "Join coordinated actions",
        "join_command_help_sr": "Придружите се координисаним акцијама",
        "information_commands_en": "Information Commands:",
        "information_commands_sr": "Информационе команде:",
        "districts_command_help_en": "View district information",
        "districts_command_help_sr": "Погледајте информације о дистриктима",
        "politicians_command_help_en": "View politician information",
        "politicians_command_help_sr": "Погледајте информације о политичарима",
        "news_command_help_en": "Check latest game news",
        "news_command_help_sr": "Проверите најновије вести из игре",
        "resources_heading_en": "Resources:",
        "resources_heading_sr": "Ресурси:",
        "resources_help_text_en": "• You get resources from districts you control\n• Different actions require different resources\n• Plan your resource usage carefully",
        "resources_help_text_sr": "• Добијате ресурсе из дистрикта које контролишете\n• Различите акције захтевају различите ресурсе\n• Пажљиво планирајте коришћење ресурса",
        "game_cycles_heading_en": "Game Cycles:",
        "game_cycles_heading_sr": "Циклуси игре:",
        "game_cycles_help_text_en": "• The game has morning and evening cycles\n• Your actions refresh at the start of each cycle\n• Resources are distributed at the start of each cycle",
        "game_cycles_help_text_sr": "• Игра има јутарње и вечерње циклусе\n• Ваше акције се обнављају на почетку сваког циклуса\n• Ресурси се дистрибуирају на почетку сваког циклуса",
        "admin_commands_en": "Admin Commands:",
        "admin_commands_sr": "Админ команде:",
        "admin_help_hint_en": "Use /admin_help to see all admin commands.",
        "admin_help_hint_sr": "Користите /admin_help да видите све админ команде.",
        "tips_heading_en": "Helpful Tips:",
        "tips_heading_sr": "Корисни савети:",
        "help_tips_en": "• Form alliances with other players\n• Watch the news for important events\n• Balance your resource usage carefully",
        "help_tips_sr": "• Формирајте савезе са другим играчима\n• Пратите вести за важне догађаје\n• Пажљиво балансирајте коришћење ресурса",
        "help_footer_en": "If you need assistance, contact the game administrator.",
        "help_footer_sr": "Ако вам је потребна помоћ, контактирајте администратора игре.",
        "cycle_morning_en": "🌅 Good morning! A new cycle has begun. Your operations have been reset and resources replenished.",
        "cycle_morning_sr": "🌅 Добро јутро! Започео је нови циклус. Ваше операције су ресетоване и ресурси допуњени.",
        "cycle_evening_en": "🌃 Good evening! A new cycle has begun. Your operations have been reset and resources replenished.",
        "cycle_evening_sr": "🌃 Добро вече! Започео је нови циклус. Ваше операције су ресетоване и ресурси допуњени.",
        "action_expired_en": "⌛ Your coordinated action has expired. You can start a new one using the /act command.",
        "action_expired_sr": "⌛ Ваша координисана акција је истекла. Можете започети нову помоћу команде /act.",
        
        # Additional translations
        "insufficient_resources_for_main_action": "Главне акције захтевају најмање 2 ресурса. Молимо изаберите више ресурса.",
        "insufficient_resources_for_action": "Морате изабрати бар један ресурс за ову акцију.",
        "coordinated_actions_heading": "Координисане акције:",
        "coordinated_actions_help_text": "• Користите опцију \"Придружи се\" из главног менија акција да бисте се придружили акцији неког другог\n• Креирајте координисану акцију користећи опције менија \"Напад\" или \"Одбрана\"\n• Што више играча се придружи, то ће акција бити јача",
        "your_resources": "Ваши ресурси",
        
        # District report translations
        "district_report_title": "Извештај о статусу округа",
        "controlled_by": "Контролише",
        "contested_by": "Оспорава",
        "not_controlled": "Није контролисано",
        "players": "играча",
        "high_importance": "Висока важност",
        "medium_importance": "Средња важност",
        "low_importance": "Ниска важност",
        "error_generating_report": "Грешка при генерисању извештаја",
        
        # Politician action translations
        "politician_influence_title": "Извештај о утицају политичара",
        "high_influence": "Висок утицај",
        "medium_influence": "Средњи утицај",
        "low_influence": "Низак утицај",
        "international_politicians": "Међународни политичари",
        
        # Politician action button labels
        "action_pol_info": "Прикупи информације",
        "action_pol_info_desc": "Сазнајте више о овом политичару",
        "action_pol_influence": "Утицај",
        "action_pol_influence_desc": "Покушајте да побољшате свој однос",
        "action_pol_collaborate": "Сарадња",
        "action_pol_collaborate_desc": "Радите заједно на политичкој иницијативи",
        "action_pol_request": "Затражи ресурсе",
        "action_pol_request_desc": "Тражите политичку подршку и ресурсе",
        "action_pol_power": "Користи политичку моћ",
        "action_pol_power_desc": "Користите њихов политички утицај за притисак на друге",
        "action_pol_undermine": "Подривање",
        "action_pol_undermine_desc": "Ослабите њихов утицај",
        "action_pol_rumors": "Ширење гласина",
        "action_pol_rumors_desc": "Оштетите њихову јавну репутацију",
        "action_pol_scandal": "Креирање скандала",
        "action_pol_scandal_desc": "Раскринкајте их у великом политичком скандалу",
        "action_pol_diplomatic": "Дипломатски канал",
        "action_pol_diplomatic_desc": "Успоставите дипломатску везу",
        "action_pol_pressure": "Међународни притисак",
        "action_pol_pressure_desc": "Користите међународни притисак против ваших противника",
        
        # Special event translations
        "event_govt_reshuffle": "Реорганизација владе",
        "event_demonstration": "Масовна демонстрација",
        "event_investment": "Страна инвестиција",
        "event_sanctions": "Економске санкције",
        "event_police_raid": "Полицијска рација",
        "event_smuggling": "Операција швјерца",
        "event_diplomatic": "Дипломатски пријем",
        "event_military": "Војна вежба",
        "event_strike": "Штрајк радника",
        "event_student": "Студентски протест",
        "event_festival": "Културни фестивал",
        
        # Response messages for politician actions
        "politician_info_success": "Прикупили сте вредне информације о {name}.",
        "politician_info_title": "Обавештајни извештај: {name}",
        "politician_info_no_resources": "Потребан вам је најмање 1 ресурс Информација за прикупљање података о политичару. Акција отказана.",
        "politician_info_no_action": "Потребна вам је брза акција за прикупљање података о политичару. Акција отказана.",
        "politician_collaborate_success": "Успешно сте сарађивали са {name} на политичкој иницијативи.",
        "politician_request_success": "Примили сте ресурсе од {name}.",
        "politician_power_success": "Искористили сте политички утицај {name} за притисак на ваше противнике.",
        "politician_undermine_success": "Успешно сте подрили утицај {name}.",
        "politician_undermine_no_resources": "Потребно вам је најмање 2 ресурса Информација за подривање политичара. Акција отказана.",
        "politician_undermine_no_action": "Потребна вам је главна акција за подривање политичара. Акција отказана.",
        "politician_influence_no_resources": "Потребно вам је најмање 2 ресурса Утицаја за утицање на политичара. Акција отказана.",
        "politician_influence_no_action": "Потребна вам је главна акција за утицање на политичара. Акција отказана.",
        "politician_influence_success": "Искористили сте свој утицај на {name}. Ваш однос са њим се може побољшати. Резултати ће бити обрађени на крају циклуса.",
        "politician_rumors_success": "Проширили сте гласине о {name}, оштетивши њихову репутацију.",
        "politician_scandal_success": "Раскринкали сте {name} у политичком скандалу, озбиљно наштетивши њиховој позицији.",
        "politician_diplomatic_success": "Успоставили сте дипломатски канал са {name}.",
        "politician_pressure_success": "Искористили сте међународни притисак {name} против ваших противника.",
        
        # Enhanced error messages
        "db_connection_error": "Грешка у вези са базом података. Молимо покушајте касније.",
        "invalid_district_error": "Неважећи округ. Молимо изаберите важећи округ.",
        "invalid_politician_error": "Неважећи политичар. Молимо изаберите важећег политичара.",
        "insufficient_resources_detailed": "Недовољно ресурса. Потребно вам је {required} {resource_type}, али имате само {available}.",
        "invalid_action_error": "Неважећа акција. Молимо изаберите важећи тип акције.",
        "language_detection_error": "Није могуће открити ваш језик. Постављено на енглески.",
        "error_district_selection": "Грешка при приказивању избора округа. Молимо покушајте поново.",
        "error_resource_selection": "Грешка при приказивању избора ресурса. Молимо покушајте поново.",
        "error_district_info": "Грешка при добављању информација о округу.",
        "error_politician_info": "Грешка при добављању информација о политичару.",
        "role": "Улога",
        "district": "Округ",
        "key_relationships": "Кључни односи",
        
        # Admin translations
        "admin_error": "Грешка администратора: {error}",
        "admin_player_resources_not_found": "Играч {player_id} постоји али нема запис о ресурсима.",
        "admin_help_title": "Административне команде",
        "admin_reset_actions_usage": "Употреба: /admin_reset_actions [ИД играча]",
        "admin_reset_actions_success": "Акције ресетоване за играча {player_id}.",
        "admin_reset_all_actions_success": "Акције ресетоване за {count} играча.",
        "admin_set_ideology_usage": "Употреба: /admin_set_ideology [ИД играча] [оцена идеологије]",
        "admin_set_ideology_success": "Оцена идеологије за играча {player_id} постављена на {score}.",
        "admin_set_ideology_invalid": "Оцена идеологије мора бити између -5 и +5.",
        "admin_player_not_found": "Играч {player_id} није пронађен.",
        "admin_list_players_none": "Нема регистрованих играча.",
        "admin_list_players_title": "Регистровани играчи",
        "admin_help_desc": "Прикажи ову поруку административне помоћи",
        "admin_news_desc": "Додај вест",
        "admin_cycle_desc": "Ручно обради циклус игре"
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
    """Get the localized name for a specific action."""
    if action in ACTION_NAMES and lang in ACTION_NAMES[action]:
        return ACTION_NAMES[action][lang]
    elif action in ACTION_NAMES:
        return ACTION_NAMES[action].get("en", action)
    return action

def get_district_name(district_id, lang="en"):
    """Get the localized name for a district."""
    try:
        import sqlite3
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM districts WHERE district_id = ?", (district_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            # Currently, we don't have localized district names, just return the name from the database
            return result[0]
        return district_id
    except Exception as e:
        logger.error(f"Error getting district name for {district_id}: {e}")
        return district_id 