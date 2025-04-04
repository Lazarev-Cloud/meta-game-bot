"""
Flow action for displaying a callback menu with selectable options.

Provides a rendered list of inline buttons, where each selection determines the next flow step.
"""
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from .base import FlowActionType
from app.translator import t
from ..reply_factory import ReplyFactory


class CallbackMenuAction(FlowActionType):
    """
    Action type that displays a list of inline buttons for user selection.

    The transition to the next step is determined by the selected option.

    Configuration Options:
        options (dict): Mapping of option keys to their configurations.
        max_in_row (int, optional): Maximum number of buttons per row (default is 1).
    """

    async def render(self, event: Message | CallbackQuery, state: FSMContext) -> None:
        """
        Render the menu by sending or editing a message with inline keyboard buttons.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): Current FSM context.

        Behavior:
            - Renders a localized prompt message.
            - Dynamically generates buttons based on configured options.
            - Sends or edits the message depending on the event type and preservation settings.
        """
        data = await state.get_data()

        # Дополняем конфиг нужными runtime-полями
        flow_config = self.config.copy()
        flow_config["prompt"] = t(f"{self.step_id}.prompt", **data)

        # Учитываем preserve_previous для reply_type
        preserve_previous = data.pop("__preserve_previous", False)
        await state.update_data(__preserve_previous=False)

        if flow_config.get("reply_type") is None:
            flow_config["reply_type"] = "edit" if not preserve_previous else "new"

        await ReplyFactory.send(event, state, flow_config, step_id=self.step_id)

    async def _handle_user_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        """
        Handle user selection from the callback menu.

        Args:
            event (Message | CallbackQuery): Incoming user input event.
            state (FSMContext): Current FSM context.

        Returns:
            str | None: The selected option key if valid, otherwise None.

        Behavior:
            - Validates the selected option against the configured options.
            - Updates the FSM context with the last selected option.
            - Sends appropriate feedback if an invalid selection is made.
        """
        data = await state.get_data()
        lang = data.get("lang", "ru")

        if not isinstance(event, CallbackQuery):
            if isinstance(event, Message):
                await event.answer(t("__system__.invalid_callback", lang))
            return None

        selected = event.data
        options = self.config.get("options", {})

        if selected not in options:
            await event.answer(t("__system__.invalid_option", lang), show_alert=True)
            return None

        await state.update_data(last_selected=selected)
        return selected
