from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from .base import FlowActionType
from app.translator import t


class TextInputAction(FlowActionType):
    """
    Ожидает текст от пользователя, сохраняет в state, переходит на следующий шаг.
    """

    async def render(self, event: Message | CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()

        prompt = t(f"{self.step_id}.prompt", **data)

        data = await state.get_data()
        preserve_previous = data.pop("__preserve_previous", False)
        await state.update_data(__preserve_previous=False)

        if isinstance(event, CallbackQuery):
            if preserve_previous:
                # просто отправляем новое сообщение, не трогая старое
                await event.message.answer(prompt)
            else:
                # редактируем предыдущее
                await event.message.edit_text(prompt)
        else:
            await event.answer(prompt)

    async def _handle_user_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        data = await state.get_data()
        lang = data.get("lang", "ru")

        if not isinstance(event, Message) or not event.text:
            if isinstance(event, CallbackQuery):
                await event.answer(t("__system__.invalid_text", lang))
            return None

        field_name = self.config.get("field", "value")
        await state.update_data({field_name: event.text})
        return event.text
