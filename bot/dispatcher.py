"""
Dispatcher initialization module.

Defines a function to create and configure the Aiogram Dispatcher instance
by including all necessary routers.
"""
from aiogram import Dispatcher
from bot.routes.base import router


def get_dispatcher() -> Dispatcher:
    """
    Create and configure an Aiogram Dispatcher instance.

    Includes the base router into the dispatcher.

    Returns:
        Dispatcher: Configured Dispatcher instance ready to handle updates.
    """
    dp = Dispatcher()
    dp.include_router(router)
    return dp
