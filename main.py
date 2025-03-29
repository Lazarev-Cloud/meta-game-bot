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
    from bot.dispatcher import get_dispatcher
    dp = get_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
