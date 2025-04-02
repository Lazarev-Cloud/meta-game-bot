import logging
import re
from abc import ABC, abstractmethod
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.translator import t
from bot.flow_engine.exceptions.base import *
from bot.flow_engine.handlers import handler_registry

log = logging.getLogger(__name__)


class FlowActionType(ABC):
    def __init__(self, step_id: str, config: dict):
        self.step_id = step_id
        self.config = config

    @abstractmethod
    async def render(self, event: Message | CallbackQuery, state: FSMContext) -> None:
        ...

    @abstractmethod
    async def _handle_user_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        ...

    async def handle_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        special = await self.__check_special_command(event)
        if special:
            return special

        try:
            result = await self._handle_user_input(event, state)

            # 🔧 Handler — глобальный или опциональный
            handler_name = self.config.get("handler")

            if "options" in self.config and result:
                option = self.config["options"].get(result)
                if option and option.get("handler"):
                    handler_name = option["handler"]

            if handler_name:
                handler = handler_registry.get(handler_name)
                if handler:
                    context = {
                        "step_id": self.step_id,
                        "config": self.config,
                        "result": result,
                    }
                    await handler(event=event, state=state, context=context)

            return self._get_next_step(result)

        except Exception as exc:
            exc_type = type(exc).__name__
            exceptions_cfg = self.config.get("exceptions", {})
            action = exceptions_cfg.get(exc_type)
            data = await state.get_data()
            lang = data.get("lang", "ru")

            if action:
                prompt_key = action.get("prompt", exc.args[0] if not t(exc.args[0]) == exc.args[0]
                                        else "__system__.unexpected_error")
                next_step = action.get("next", "__menu__")

                await self._send_prompt(event, prompt_key, lang, **data)
                return next_step

            else:
                log.warning(f"No exception handler for {exc_type} in step {self.step_id}")
                await self._send_prompt(event, "__system__.unexpected_error", lang, **data)
                raise

    @staticmethod
    async def _send_prompt(event: Message | CallbackQuery, prompt_key: str, lang: str, **kwargs):
        """
        Утилита для отправки сообщения с ошибкой.
        """
        message = t(prompt_key, lang=lang, **kwargs)
        if isinstance(event, CallbackQuery):
            await event.message.answer(message)
        else:
            await event.answer(message)

    @staticmethod
    async def __check_special_command(event: Message | CallbackQuery) -> str | None:
        text = None
        if isinstance(event, Message):
            text = event.text
        elif isinstance(event, CallbackQuery):
            text = event.data

        if not text:
            return None

        lowered = text.lower()

        if lowered in {"__back__", "/back", "назад"}:
            return "__back__"
        if lowered in {"__menu__", "/start", "/menu" "меню"}:
            return "__menu__"
        if lowered in {"__repeat__", "/repeat", "повтор"}:
            return "__repeat__"

        return None

    async def _get_prompt(self, state: FSMContext, placeholder="") -> str:
        """
        Возвращает отрендеренный prompt с подстановкой {{переменных}} из state.
        """
        template = self.config.get("prompt", placeholder)
        data = await state.get_data()
        return self._render_template(template, data)

    @staticmethod
    def _render_template(template: str, data: dict) -> str:
        def replacer(match):
            key = match.group(1)
            return str(data.get(key, f"{{{{{key}}}}}"))

        return re.sub(r"{{\s*(\w+)\s*}}", replacer, template)

    def _get_next_step(self, result: str | None) -> str | None:
        """
        Определяет, какой шаг будет следующим после текущего ввода.
        Универсально работает как для text_input, так и для callback_menu.
        """
        # Если есть options — ищем в них
        if "options" in self.config and result:
            option = self.config["options"].get(result)
            if option:
                return option.get("next")

        # Иначе — универсальное поле
        return self.config.get("next")
