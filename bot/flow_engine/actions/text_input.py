"""
Flow action for receiving and processing text input from the user.

This action prompts the user for text input, saves the response into FSM state,
and transitions to the next step based on the input.
"""
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from .base import FlowActionType
from app.translator import t
from ..reply_factory import ReplyFactory


class TextInputAction(FlowActionType):
    """
    Action type that expects text input from the user.

    After receiving the text, it saves the result to the FSM state and moves to the next flow step.

    Configuration Options:
        field (str, optional): The name of the field to store the user input under. Defaults to "value".
    """

    async def render(self, event: Message | CallbackQuery, state: FSMContext) -> None:
        """
        Render a prompt asking the user for text input.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): Current FSM context.

        Behavior:
            - Sends or edits a localized prompt message based on the event type.
            - Resets the "__preserve_previous" flag in the FSM context after use.
        """
        data = await state.get_data()

        flow_config = self.config.copy()
        flow_config["prompt"] = t(f"{self.step_id}.prompt", **data)

        preserve_previous = data.pop("__preserve_previous", False)
        await state.update_data(__preserve_previous=False)

        if flow_config.get("reply_type") is None:
            flow_config["reply_type"] = "edit" if not preserve_previous else "new"

        await ReplyFactory.send(event, state, flow_config, step_id=self.step_id)

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
