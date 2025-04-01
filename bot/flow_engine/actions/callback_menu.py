from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from .base import FlowActionType
from app.translator import t


class CallbackMenuAction(FlowActionType):
    """
    Показывает список кнопок с вариантами выбора.
    Переход зависит от выбранной опции.
    """

    async def render(self, event: Message | CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()

        # Локализованный prompt
        prompt = t(f"{self.step_id}.prompt", **data)

        # Опции с локализацией label
        options = self.config.get("options", {})
        max_in_row = self.config.get("max_in_row", 1)

        # Формируем кнопки
        button_list = [
            InlineKeyboardButton(
                text=t(f"{self.step_id}.options.{key}", **data),
                callback_data=key,
            )
            for key in options
        ]

        # Разбиваем кнопки на строки
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
