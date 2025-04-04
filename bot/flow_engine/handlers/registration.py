"""
Flow engine handlers for registration validation and processing.

Defines asynchronous handlers used to validate user-provided names
and update FSM state based on the input.
"""
from bot.flow_engine.exceptions.base import NameTooShortError


async def validate_name(event, state, context):
    """
    Validate the user-provided name.

    Args:
        event: Incoming user event (Message or CallbackQuery).
        state (FSMContext): Current FSM context.
        context (dict): Contextual data passed to the handler.

    Raises:
        NameTooShortError: If the name is shorter than 3 characters.
        ValueError: If the name exceeds 8 characters (uses a localized error key).
    """
    data = await state.get_data()
    name = data.get("name", "")
    if len(name) < 3:
        raise NameTooShortError("Name too short")
    elif len(name) > 8:
        raise ValueError("__system__.invalid_text")


async def save_name_to_state(event, state, context):
    """
    Save the validated name into the FSM context.

    Args:
        event: Incoming user event (Message or CallbackQuery).
        state (FSMContext): Current FSM context.
        context (dict): Contextual data passed to the handler.

    Behavior:
        Stores the name under the key 'validated_name' in the FSM state.
    """
    data = await state.get_data()
    name = data.get("name")
    await state.update_data(validated_name=name)
