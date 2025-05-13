"""
Главный модуль для запуска Telegram-бота.

Модуль обеспечивает:
- Инициализацию и запуск асинхронного бота
- Обработку системных прерываний
- Логирование критических ошибок и событий жизненного цикла бота
"""

import asyncio

from loguru import logger

import bot.main as bot_starter

if __name__ == "__main__":
    """Точка входа для запуска Telegram-бота."""
    logger.info("Инициализация бота...")
    
    try:
        asyncio.run(bot_starter.main())        
    except (KeyboardInterrupt, SystemExit):
        logger.info("Корректное завершение работы по системному прерыванию")
        
    except Exception as error:
        logger.critical(
            "Критическая ошибка во время работы бота: {error}",
            error=repr(error)
        )
        logger.exception("Трассировка ошибки:")
        
    finally:
        logger.info("Работа бота завершена")