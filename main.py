"""
Entry point for running the bot application.

Initializes logging, loads translations, sets up the dispatcher, and starts polling updates.
"""
import logging

from app.logger import configure_logging

from app.translator import load_translations
import asyncio
from bot.bot import bot

configure_logging()
log = logging.getLogger(__name__)
log.info("Logger configuration successful")

load_translations()
log.info("Translations loaded successfully")


async def main():
    """
    Initialize the dispatcher and start polling for updates.

    Sets up all handlers and begins listening for incoming bot events.
    """
    from bot.dispatcher import get_dispatcher
    dp = get_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
