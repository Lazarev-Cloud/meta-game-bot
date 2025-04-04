"""
Bot routes for handling incoming messages and callbacks.

Defines entry points to start and interact with the flow engine
based on user inputs and callback queries.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.flow_engine.manager import FlowManager

# FlowManager instance initialized with the flow configuration file.
flow = FlowManager("config/flow.json")

# Aiogram Router instance for registering flow-related handlers.
router = Router()


@router.message(F.text == "/start")
async def start_flow(message: Message, state: FSMContext):
    """
    Start the flow engine from the initial step.

    Triggered when the user sends the "/start" command.

    Args:
        message (Message): Incoming message from the user.
        state (FSMContext): Current FSM context.
    """
    await flow.start(message, state)


@router.message()
async def handle_message(message: Message, state: FSMContext):
    """
    Handle a regular text message and delegate processing to the flow engine.

    Args:
        message (Message): Incoming message from the user.
        state (FSMContext): Current FSM context.
    """
    await flow.handle(message, state)


@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    """
    Handle a callback query and delegate processing to the flow engine.

    Args:
        callback (CallbackQuery): Incoming callback query from an inline button.
        state (FSMContext): Current FSM context.
    """
    await flow.handle(callback, state)
