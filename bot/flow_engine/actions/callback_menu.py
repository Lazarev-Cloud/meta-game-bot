"""
Flow action for displaying a callback menu with selectable options.

Provides a rendered list of inline buttons, where each selection determines the next flow step.
"""
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from .base import FlowActionType
from app.translator import t


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

        prompt = t(f"{self.step_id}.prompt", **data)

        options = self.config.get("options", {})
        max_in_row = self.config.get("max_in_row", 1)

        button_list = [
            InlineKeyboardButton(
                text=t(f"{self.step_id}.options.{key}", **data),
                callback_data=key,
            )
            for key in options
        ]

        buttons = [
            button_list[i:i + max_in_row]
            for i in range(0, len(button_list), max_in_row)
        ]

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        preserve_previous = data.pop("__preserve_previous", False)
        await state.update_data(__preserve_previous=False)

        if isinstance(event, CallbackQuery):
            if preserve_previous:
                await event.message.answer(prompt, reply_markup=markup)
            else:
                await event.message.edit_text(prompt, reply_markup=markup)
        else:
            await event.answer(prompt, reply_markup=markup)

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
