import asyncio
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.config import TOKEN, USER_ID, TIMEZONE
from bot.logger_setup import logger
from bot.scheduler import setup_scheduler, send_scheduled_message
from bot.handlers import memory_handler, admin, common
from database.db import init_db

async def on_startup(bot: Bot, scheduler: AsyncIOScheduler):
    logger.info("Бот запускается и планировщик активируется")
    # Отправляем сообщение при старте
    await bot.send_message(chat_id=USER_ID, text=f"🟢Bot started✔")
    #await send_scheduled_message(bot, USER_ID)
    
    # Настраиваем планировщик
    setup_scheduler(scheduler, bot, USER_ID)
    scheduler.start()
    logger.info("Бот запущен и планировщик активирован")

async def main():
    await init_db()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_routers(memory_handler.memory_router, admin.router, common.router)
    
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    
    try:
        await on_startup(bot, scheduler)
        await dp.start_polling(bot)
    finally:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Планировщик остановлен")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")