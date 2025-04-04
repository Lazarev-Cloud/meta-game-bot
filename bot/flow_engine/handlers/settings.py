"""
Flow engine handlers for setting the user's language preference.

Defines asynchronous handlers that update the FSM state with the selected language.
"""


async def set_lang_ru(event, state, context):
    """
    Set the user's language to Russian.

    Args:
        event: Incoming user event (Message or CallbackQuery).
        state (FSMContext): Current FSM context.
        context (dict): Contextual data passed to the handler.

    Behavior:
        Updates the FSM state by setting 'lang' to "ru".
    """
    await state.update_data(lang="ru")


async def set_lang_en(event, state, context):
    """
    Set the user's language to English.

    Args:
        event: Incoming user event (Message or CallbackQuery).
        state (FSMContext): Current FSM context.
        context (dict): Contextual data passed to the handler.

    Behavior:
        Updates the FSM state by setting 'lang' to "en".
    """
    await state.update_data(lang="en")
