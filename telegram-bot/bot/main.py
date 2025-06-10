"""
Главный модуль для инициализации и запуска Telegram бота

Содержит:
- Конфигурацию основных компонентов приложения
- Инициализацию системы планирования задач
- Обработчики жизненного цикла приложения
- Основной цикл работы бота
"""

from bot.logger_setup import setup_logger
#Конфигурирование логгера перед запуском всех частей бота
setup_logger()

import asyncio
from contextlib import suppress
from typing import Any, cast

from aiogram import Bot, Dispatcher
from aiogram.types import User, ReplyKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.util import undefined

from bot.config import TIMEZONE, TOKEN, USER_ID, NEED_SHEDULER
from bot.handlers import admin, common, memory_handler, generation, data, user, google_auth
from bot.logger_setup import logger
from bot.scheduler import setup_scheduler, init_dispatcher
from database.db import init_db
from bot.middleware.database_middleware import DatabaseMiddleware
from bot.handlers.keyboards import user_main_kb

async def on_startup(bot: Bot, scheduler: AsyncIOScheduler, dispatcher) -> None:
    """Выполняет инициализацию приложения при старте.
    
    Args:
        bot: Экземпляр Telegram бота
        scheduler: Планировщик задач
        
    Raises:
        RuntimeError: Ошибка при отправке стартового сообщения
    """
    logger.info("Инициализация компонентов приложения")
    
    try:
        # Получаем информацию о боте для проверки токена
        bot_user = cast(User, await bot.me())
        logger.debug(
            "Инициализация бота: ID={id}, Username={username}",
            id=bot_user.id,
            username=bot_user.username
        )
        
        # Отправка стартового уведомления
        await bot.send_message(
            chat_id=USER_ID,
            text="🟢 Bot started ✔",
            reply_markup=user_main_kb(is_admin=True)
        )
        logger.debug("Стартовое уведомление отправлено")
        
    except Exception as exc:
        logger.critical("Ошибка инициализации бота: {}", exc)
        raise RuntimeError("Bot initialization failed") from exc

    if NEED_SHEDULER:
        # Настройка планировщика
        try:
            init_dispatcher(dispatcher=dispatcher)
            setup_scheduler(scheduler, bot, USER_ID)
            if scheduler.state == 0:  # type: ignore
                scheduler.start()
                logger.info(
                    "Планировщик запущен (временная зона: {tz})",
                    tz=TIMEZONE.zone
                )
        except Exception as exc:
            logger.critical("Ошибка запуска планировщика: {}", exc)
            raise

async def main() -> None:
    """Основная точка входа для запуска приложения."""

    logger.info("Подготовка к запуску приложения")
    
    try:
        # Инициализация базы данных
        await init_db()
        logger.debug("База данных инициализирована")
        
        # Создание основных компонентов
        bot = Bot(token=TOKEN)
        dp = Dispatcher()

        dp.update.middleware(DatabaseMiddleware())

        scheduler = AsyncIOScheduler(timezone=TIMEZONE)
        
        # Регистрация роутеров
        routers = (memory_handler.memory_router, admin.router, common.router, generation.image_router, data.router, user.router, google_auth.router)
        for router in routers:
            dp.include_router(router)
        logger.debug("Зарегистрировано роутеров: {}", len(routers))
        
        # Запуск процедур инициализации
        await on_startup(bot, scheduler, dp)
        
        # Основной цикл работы бота
        logger.info("Запуск основного цикла обработки сообщений")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
        
    except Exception as exc:
        logger.critical("Критическая ошибка в основном цикле: {}", exc)
        raise
    
    finally:
        logger.info("Завершение работы приложения")
        with suppress(Exception):
            if 'scheduler' in locals() and scheduler.running:
                scheduler.shutdown()
                logger.info("Планировщик остановлен")
            
        with suppress(Exception):
            if 'bot' in locals():
                await bot.close()
                logger.debug("Сессия бота закрыта")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Принудительная остановка бота")
    except Exception as exc:
        logger.critical("Непредвиденная ошибка: {}", exc)
        raise