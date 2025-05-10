import os
import sys
from loguru import logger

def setup_logger():
    logger.remove()
    
    # Консольный формат с цветами
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name: <35}</cyan>:<cyan>{function: <25}</cyan>:<cyan>{line: <5}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Файловый формат
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # Создаем папку для логов
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Добавляем обработчики
    logger.add(
        sink=sys.stdout,
        format=console_format,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    logger.add(
        sink=os.path.join(logs_dir, "bot.log"),
        format=file_format,
        level="DEBUG",
        rotation="1 week",
        compression="zip",
        enqueue=True
    )

# Инициализируем логгер при импорте
setup_logger()