from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.flow_engine.actions import action_types
from bot.flow_engine.loader import load_flow_config
from app.translator import t


class FlowManager:
    def __init__(self, config_path: str):
        self.config = load_flow_config(config_path)

    async def start(self, event: Message | CallbackQuery, state: FSMContext):
        await state.update_data(current_step="start", history=["start"])
        await self.render(event, state)

    async def render(self, event: Message | CallbackQuery, state: FSMContext):
        data = await state.get_data()
        step_id = data.get("current_step", "start")
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
        Выполняет переход в зависимости от результата действия.
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

    async def _go_to(self, step_id: str, state: FSMContext):
        data = await state.get_data()
        history = data.get("history", [])
        history.append(step_id)
        await state.update_data(current_step=step_id, history=history)

    async def _go_back(self, event: Message | CallbackQuery, state: FSMContext):
        data = await state.get_data()
        history = data.get("history", [])

        if len(history) < 2:
            await self._answer(event, t("__system__.cannot_go_back"))
            return

        history.pop()
        prev_step = history[-1]
        await state.update_data(current_step=prev_step, history=history)
        await self.render(event, state)

    async def _get_current_step(self, state: FSMContext) -> str:
        data = await state.get_data()
        return data.get("current_step", "start")

    async def _get_previous_step(self, state: FSMContext) -> str | None:
        data = await state.get_data()
        history = data.get("history", [])
        if len(history) >= 2:
            return history[-2]
        return None

    async def _set_preserve_flag(self, state: FSMContext, step_id: str | None):
        """
        Устанавливает флаг preserve_message от указанного шага.
        """
        if not step_id:
            return
        cfg = self.config.get(step_id, {})
        preserve = cfg.get("preserve_message", False)
        await state.update_data(__preserve_previous=preserve)

    async def _answer(self, event: Message | CallbackQuery, text: str):
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
        else:
            await event.answer(text)
