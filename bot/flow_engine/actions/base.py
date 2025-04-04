"""
Base class for flow actions in the bot's flow engine.

Defines the abstract FlowActionType and common utility methods
for handling user input, rendering prompts, managing handlers, and exception processing.
"""
import logging
import re
from abc import ABC, abstractmethod
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.translator import t
from bot.flow_engine.handlers import handler_registry

# Импорт ошибок
from bot.flow_engine.exceptions.base import *  # noqa: F401,F403
from bot.flow_engine.reply_factory import ReplyFactory

log = logging.getLogger(__name__)


class FlowActionType(ABC):
    """
    Abstract base class for all flow action types.

    Attributes:
        step_id (str): Identifier for the current step in the flow.
        config (dict): Configuration dictionary for the action.

    Methods:
        render(event, state): Abstract method to render the step.
        handle_input(event, state): Handles user input and invokes handlers or transitions.
        _handle_user_input(event, state): Abstract method to process the user input.
    """

    def __init__(self, step_id: str, config: dict):
        """
        Initialize a FlowActionType.

        Args:
            step_id (str): Identifier of the flow step.
            config (dict): Step-specific configuration.
        """
        self.step_id = step_id
        self.config = config

    @abstractmethod
    async def render(self, event: Message | CallbackQuery, state: FSMContext) -> None:
        """
        Abstract method to render the action's initial prompt or view.

        Must be implemented by subclasses.
        """
        data = await state.get_data()

        flow_config = self.config.copy()
        flow_config["prompt"] = t(f"{self.step_id}.prompt", **data)

        preserve_previous = data.pop("__preserve_previous", False)
        await state.update_data(__preserve_previous=False)

        if flow_config.get("reply_type") is None:
            flow_config["reply_type"] = "edit" if not preserve_previous else "new"

        await ReplyFactory.send(event, state, flow_config, step_id=self.step_id)

    @abstractmethod
    async def _handle_user_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        """
        Abstract method to process the user's input.

        Must be implemented by subclasses.
        """
        ...

    async def handle_input(self, event: Message | CallbackQuery, state: FSMContext) -> str | None:
        """
        Handle the user input, process the action, manage exceptions, and invoke custom handlers if needed.

        Args:
            event (Message | CallbackQuery): Incoming event from the user.
            state (FSMContext): Current FSM context.

        Returns:
            str | None: The next step identifier, or None if the flow should terminate.
        """
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
            data.pop("lang", None)

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
        Send a localized prompt to the user.

        Args:
            event (Message | CallbackQuery): Incoming event.
            prompt_key (str): Key to fetch the localized prompt.
            lang (str): Language code.
            **kwargs: Data for rendering template variables.
        """
        message = t(prompt_key, lang=lang, **kwargs)
        if isinstance(event, CallbackQuery):
            await event.message.answer(message)
        else:
            await event.answer(message)

    @staticmethod
    async def __check_special_command(event: Message | CallbackQuery) -> str | None:
        """
        Check if the user input corresponds to a special command.

        Special commands include back, menu, and repeat actions.

        Args:
            event (Message | CallbackQuery): Incoming event.

        Returns:
            str | None: Special command identifier if matched, otherwise None.
        """
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
        Retrieve the rendered prompt string with variable substitution from the state.

        Args:
            state (FSMContext): Current FSM context.
            placeholder (str, optional): Fallback text if no prompt is configured.

        Returns:
            str: Rendered prompt text.
        """
        template = self.config.get("prompt", placeholder)
        data = await state.get_data()
        return self._render_template(template, data)

    @staticmethod
    def _render_template(template: str, data: dict) -> str:
        """
        Replace template placeholders {{variable}} with corresponding values from a dictionary.

        Args:
            template (str): Template string containing placeholders.
            data (dict): Data to substitute into the template.

        Returns:
            str: Rendered string.
        """
        def replacer(match):
            """
            Replace a template placeholder with the corresponding value from the data dictionary.

            Args:
                match (re.Match): A regex match object capturing a placeholder key.

            Returns:
                str: The corresponding value from the data dictionary,
                     or the original placeholder if the key is not found.
            """
            key = match.group(1)
            return str(data.get(key, f"{{{{{key}}}}}"))

        return re.sub(r"{{\s*(\w+)\s*}}", replacer, template)

    def _get_next_step(self, result: str | None) -> str | None:
        """
        Determine the next step based on the user input result and action configuration.

        Args:
            result (str | None): The processed user input result.

        Returns:
            str | None: Identifier of the next step, or None if not defined.
        """
        # Если есть options — ищем в них
        if "options" in self.config and result:
            option = self.config["options"].get(result)
            if option:
                return option.get("next")

        # Иначе — универсальное поле
        return self.config.get("next")
