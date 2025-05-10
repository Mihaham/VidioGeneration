import bot.main as bot_starter
import asyncio
from loguru import logger

if __name__ == "__main__":
    try:
        asyncio.run(bot_starter.main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")