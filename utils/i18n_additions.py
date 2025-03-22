#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Additional translations to be added to the i18n system.
"""

# Additional English translations
EN_ADDITIONS = {
    # Error messages
    "An error occurred while processing your request.": "An error occurred while processing your request.",
    "You don't have enough resources for this action.": "You don't have enough resources for this action.",
    "You don't have permission to perform this action.": "You don't have permission to perform this action.",
    "The requested item was not found.": "The requested item was not found.",
    "The submission deadline for this cycle has passed.": "The submission deadline for this cycle has passed.",
    "Sorry, we're experiencing technical issues. Please try again later.": "Sorry, we're experiencing technical issues. Please try again later.",
    "Database connection error. Please try again later.": "Database connection error. Please try again later.",
    "Unable to process your request. The system may be temporarily unavailable.": "Unable to process your request. The system may be temporarily unavailable.",

    # Common UI strings
    "Loading...": "Loading...",
    "Processing...": "Processing...",
    "Success!": "Success!",
    "Failed!": "Failed!",
    "Canceled": "Canceled",
    "Confirm Action": "Confirm Action",
    "Are you sure?": "Are you sure?",

    # Resource related
    "Resource conversion successful": "Resource conversion successful",
    "Resource conversion failed": "Resource conversion failed",
    "Current resources": "Current resources",
    "Not enough {resource} resources": "Not enough {resource} resources",

    # Action related
    "Action submitted successfully": "Action submitted successfully",
    "Action canceled successfully": "Action canceled successfully",
    "No actions to cancel": "No actions to cancel",
    "Please select a district first": "Please select a district first",
    "Please select a resource type": "Please select a resource type",
    "Please select a resource amount": "Please select a resource amount",

    # Politician related
    "Relations improved with {politician}": "Relations improved with {politician}",
    "Failed to improve relations with {politician}": "Failed to improve relations with {politician}",
    "Resources requested from {politician}": "Resources requested from {politician}",

    # District related
    "You now control {district}": "You now control {district}",
    "Your control in {district} has increased": "Your control in {district} has increased",
    "Your control in {district} has decreased": "Your control in {district} has decreased",

    # Collective action related
    "Collective action initiated successfully": "Collective action initiated successfully",
    "Failed to initiate collective action": "Failed to initiate collective action",
    "You have joined the collective action": "You have joined the collective action",
    "Failed to join collective action": "Failed to join collective action",

    # Time related
    "{hours}h {minutes}m remaining": "{hours}h {minutes}m remaining",
    "{minutes}m {seconds}s remaining": "{minutes}m {seconds}s remaining",
    "Less than a minute remaining": "Less than a minute remaining",
    "Time expired": "Time expired",

    # Misc
    "Page {current} of {total}": "Page {current} of {total}",
    "Previous page": "Previous page",
    "Next page": "Next page",
    "Game paused": "Game paused",
    "Game resumed": "Game resumed"
}

# Additional Russian translations
RU_ADDITIONS = {
    # Error messages
    "An error occurred while processing your request.": "Произошла ошибка при обработке вашего запроса.",
    "You don't have enough resources for this action.": "У вас недостаточно ресурсов для этого действия.",
    "You don't have permission to perform this action.": "У вас нет прав для выполнения этого действия.",
    "The requested item was not found.": "Запрашиваемый элемент не найден.",
    "The submission deadline for this cycle has passed.": "Срок подачи заявок на этот цикл истек.",
    "Sorry, we're experiencing technical issues. Please try again later.": "Извините, у нас технические проблемы. Пожалуйста, попробуйте позже.",
    "Database connection error. Please try again later.": "Ошибка подключения к базе данных. Пожалуйста, попробуйте позже.",
    "Unable to process your request. The system may be temporarily unavailable.": "Невозможно обработать ваш запрос. Система может быть временно недоступна.",

    # Common UI strings
    "Loading...": "Загрузка...",
    "Processing...": "Обработка...",
    "Success!": "Успех!",
    "Failed!": "Не удалось!",
    "Canceled": "Отменено",
    "Confirm Action": "Подтвердить действие",
    "Are you sure?": "Вы уверены?",

    # Resource related
    "Resource conversion successful": "Конвертация ресурсов успешна",
    "Resource conversion failed": "Ошибка конвертации ресурсов",
    "Current resources": "Текущие ресурсы",
    "Not enough {resource} resources": "Недостаточно ресурсов {resource}",

    # Action related
    "Action submitted successfully": "Действие успешно отправлено",
    "Action canceled successfully": "Действие успешно отменено",
    "No actions to cancel": "Нет действий для отмены",
    "Please select a district first": "Пожалуйста, сначала выберите район",
    "Please select a resource type": "Пожалуйста, выберите тип ресурса",
    "Please select a resource amount": "Пожалуйста, выберите количество ресурсов",

    # Politician related
    "Relations improved with {politician}": "Отношения с {politician} улучшены",
    "Failed to improve relations with {politician}": "Не удалось улучшить отношения с {politician}",
    "Resources requested from {politician}": "Запрошены ресурсы у {politician}",

    # District related
    "You now control {district}": "Теперь вы контролируете {district}",
    "Your control in {district} has increased": "Ваш контроль в {district} увеличился",
    "Your control in {district} has decreased": "Ваш контроль в {district} уменьшился",

    # Collective action related
    "Collective action initiated successfully": "Коллективное действие успешно инициировано",
    "Failed to initiate collective action": "Не удалось инициировать коллективное действие",
    "You have joined the collective action": "Вы присоединились к коллективному действию",
    "Failed to join collective action": "Не удалось присоединиться к коллективному действию",

    # Time related
    "{hours}h {minutes}m remaining": "Осталось {hours}ч {minutes}м",
    "{minutes}m {seconds}s remaining": "Осталось {minutes}м {seconds}с",
    "Less than a minute remaining": "Осталось менее минуты",
    "Time expired": "Время истекло",

    # Misc
    "Page {current} of {total}": "Страница {current} из {total}",
    "Previous page": "Предыдущая страница",
    "Next page": "Следующая страница",
    "Game paused": "Игра приостановлена",
    "Game resumed": "Игра возобновлена"
}


def update_translations(translations_dict):
    """
    Add these translations to the main translations dictionary.
    This function should be called during setup_i18n().
    """
    translations_dict["en_US"].update(EN_ADDITIONS)
    translations_dict["ru_RU"].update(RU_ADDITIONS)