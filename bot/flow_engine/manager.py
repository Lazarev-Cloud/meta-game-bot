"""
FlowManager class for managing flow-based interactions.

Handles flow initialization, rendering steps, processing user inputs,
managing history, and controlling transitions between steps based on flow configuration.
"""
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.flow_engine.actions import action_types
from bot.flow_engine.loader import load_flow_config
from app.translator import t


class FlowManager:
    """
    Central controller for managing flow steps and user interactions.

    Attributes:
        config (dict): Loaded flow configuration mapping step IDs to their definitions.

    Methods:
        start(event, state): Start a new flow from the 'start' step.
        render(event, state): Render the current step's action.
        handle(event, state): Handle user input for the current step and process transitions.
    """

    def __init__(self, config_path: str):
        """
        Initialize FlowManager by loading flow configuration from a file.

        Args:
            config_path (str): Path to the JSON flow configuration file.
        """
        self.config = load_flow_config(config_path)

    async def start(self, event: Message | CallbackQuery, state: FSMContext):
        """
        Start the flow by setting the initial state and rendering the start step.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): FSM context.
        """
        await state.update_data(current_step="start", history=["start"])
        await self.render(event, state)

    async def render(self, event: Message | CallbackQuery, state: FSMContext):
        """
        Render the current step by instantiating and executing its associated action.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): FSM context.
        """
        data = await state.get_data()
        step_id = data.get("current_step", "start")
        # TODO: Make duplicate as protected function
        step_cfg = self.config.get(step_id)

        if not step_cfg:
            await self._answer(event, t("__system__.step_not_found"))
            return

        action_cls = action_types.get(step_cfg.get("type"))
        if not action_cls:
            await self._answer(event, t("__system__.unknown_action_type"))
            return

        action = action_cls(step_id, step_cfg)
        await action.render(event, state)

    async def handle(self, event: Message | CallbackQuery, state: FSMContext):
        """
        Handle user input at the current step, invoke the action, and process the next transition.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): FSM context.
        """
        data = await state.get_data()
        step_id = data.get("current_step")
        step_cfg = self.config.get(step_id)

        if not step_cfg:
            await self._answer(event, t("__system__.step_not_found"))
            return

        action_cls = action_types.get(step_cfg.get("type"))
        if not action_cls:
            await self._answer(event, t("__system__.unknown_action_type"))
            return

        action = action_cls(step_id, step_cfg)
        next_step = await action.handle_input(event, state)
        await self._process_transition(event, state, next_step)

    async def _process_transition(self, event: Message | CallbackQuery, state: FSMContext, next_step: str | None):
        """
        Process transition to the next step based on the result of the current action.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): FSM context.
            next_step (str | None): Identifier of the next step or control command.
        """
        current_step = await self._get_current_step(state)
        await self._set_preserve_flag(state, current_step)

        if next_step is None or next_step == "__repeat__":
            await self.render(event, state)

        elif next_step == "__menu__":
            await self.start(event, state)

        elif next_step == "__back__":
            await self._go_back(event, state)

        else:
            await self._go_to(next_step, state)
            await self.render(event, state)

    async def _set_preserve_flag(self, state: FSMContext, step_id: str | None):
        """
        Set the __preserve_previous flag in the FSM context based on the step configuration.

        Args:
            state (FSMContext): FSM context.
            step_id (str | None): Step identifier to retrieve preservation settings from.
        """
        if not step_id:
            return
        cfg = self.config.get(step_id, {})
        preserve = cfg.get("preserve_message", False)
        await state.update_data(__preserve_previous=preserve)

    async def _go_back(self, event: Message | CallbackQuery, state: FSMContext):
        """
        Return to the previous step based on the history.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): FSM context.
        """
        data = await state.get_data()
        history = data.get("history", [])

        if len(history) < 2:
            await self._answer(event, t("__system__.cannot_go_back"))
            return

        history.pop()
        prev_step = history[-1]
        await state.update_data(current_step=prev_step, history=history)
        await self.render(event, state)

    @staticmethod
    async def _go_to(step_id: str, state: FSMContext):
        """
        Move to a specific step and update the history.

        Args:
            step_id (str): Identifier of the target step.
            state (FSMContext): FSM context.
        """
        data = await state.get_data()
        history = data.get("history", [])
        history.append(step_id)
        await state.update_data(current_step=step_id, history=history)

    @staticmethod
    async def _get_current_step(state: FSMContext) -> str:
        """
        Retrieve the current step from the FSM state.

        Args:
            state (FSMContext): FSM context.

        Returns:
            str: Current step identifier.
        """
        data = await state.get_data()
        return data.get("current_step", "start")

    @staticmethod
    async def _get_previous_step(state: FSMContext) -> str | None:
        """
        Retrieve the previous step from the history.

        Args:
            state (FSMContext): FSM context.

        Returns:
            str | None: Previous step identifier or None if not available.
        """
        data = await state.get_data()
        history = data.get("history", [])
        if len(history) >= 2:
            return history[-2]
        return None

    @staticmethod
    async def _answer(event: Message | CallbackQuery, text: str):
        """
        Send a text message to the user based on the event type.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            text (str): Text message to send.
        """
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
        else:
            await event.answer(text)
