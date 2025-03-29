from aiogram import Dispatcher
from bot.routes.base import router


def get_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp
