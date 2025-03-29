from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.flow_engine.manager import FlowManager

# Указываем путь к конфигурации flow
flow = FlowManager("config/flow.json")

router = Router()


@router.message(F.text == "/start")
async def start_flow(message: Message, state: FSMContext):
    await flow.start(message, state)


@router.message()
async def handle_message(message: Message, state: FSMContext):
    await flow.handle(message, state)


@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    await flow.handle(callback, state)
