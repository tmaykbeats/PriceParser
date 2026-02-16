# # ~/PriceParser/main.py
# Основной файл для запуска Grok Insights Bot.
# Python 3.8.10
# для корректной работы этого бота я загнузил эти пакеты
# pip install aiogram==2.21 aiohttp==3.8.1
# содержит только тот код который нужен для старта и управления ботом.
#

# Комментарии:

# logging: Помогает видеть, что происходит (ошибки, старт бота).
# Bot, Dispatcher: Основные объекты aiogram для работы бота.
# MemoryStorage: Хранит состояния (например, текущую тему анализа).
# register_handlers: Подключает команды и кнопки из handlers.py.
# start_polling: Запускает бота, чтобы он слушал сообщения.

import asyncio
import logging
import time

import schedule
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import register_handlers
from services.notifier import notify_subscribers
from services.parser import scrape_prices
from services.pit_db import save_pit_results
from services.pit_parser import run_pit_parsing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting PriceParser...")
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    register_handlers(dp)

    # Schedule hourly price scraping and notifications
    # schedule.every().hour.do(lambda: asyncio.create_task(scrape_and_notify(bot)))
    schedule.every(1).minutes.do(lambda: asyncio.create_task(scrape_and_notify(bot)))

    # Schedule PIT parsing daily at 02:00
    schedule.every().day.at("02:00").do(
        lambda: asyncio.create_task(pit_parse_and_save())
    )

    # Run scheduler in background
    async def run_scheduler():
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)

    # Start polling and scheduler
    await asyncio.gather(dp.start_polling(), run_scheduler())


async def scrape_and_notify(bot):
    try:
        prices = await scrape_prices()
        await notify_subscribers(bot, prices)
    except Exception as e:
        logger.error(f"Error in scrape_and_notify: {str(e)}")


async def pit_parse_and_save():
    """
    Запускает парсинг магазинов через PIT и сохраняет результаты в БД.
    """
    try:
        logger.info("Starting PIT parsing...")
        results = await run_pit_parsing()
        if results:
            stats = save_pit_results(results)
            logger.info(f"PIT parsing completed: {stats}")
        else:
            logger.warning("PIT parsing returned no results")
    except Exception as e:
        logger.error(f"Error in PIT parsing: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
