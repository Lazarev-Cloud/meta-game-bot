"""
Flow action for receiving and processing text input from the user.

This action prompts the user for text input, saves the response into FSM state,
and transitions to the next step based on the input.
"""
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from .base import FlowActionType
from app.translator import t


class TextInputAction(FlowActionType):
    """
    Action type that expects text input from the user.

    After receiving the text, it saves the result to the FSM state and moves to the next flow step.

    Configuration Options:
        field (str, optional): The name of the field to store the user input under. Defaults to "value".
    """

    async def _handle_user_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        """
        Handle and validate the received text input.

        Args:
            event (Message | CallbackQuery): Incoming user input event.
            state (FSMContext): Current FSM context.

        Returns:
            str | None: The received text if valid, otherwise None.

        Behavior:
            - If the input is invalid (e.g., non-text for Message), sends an error message.
            - Saves the text into the FSM context under the configured field name.
        """
        data = await state.get_data()
        lang = data.get("lang", "ru")

        if not isinstance(event, Message) or not event.text:
            if isinstance(event, CallbackQuery):
                await event.answer(t("__system__.invalid_text", lang))
            return None

        field_name = self.config.get("field", "value")
        await state.update_data({field_name: event.text})
        return event.text
