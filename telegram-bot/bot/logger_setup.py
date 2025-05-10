"""
Модуль конфигурации системы логирования

Обеспечивает:
- Настройку форматов вывода логов
- Создание директории для хранения логов
- Раздельные обработчики для консоли и файлов
- Автоматическую ротацию и архивацию логов
"""

import os
import sys
from pathlib import Path
from typing import NoReturn

from loguru import logger


def setup_logger() -> None:
    """Инициализирует и настраивает логгер приложения.
    
    Выполняет:
    - Очистку дефолтных обработчиков
    - Создание директории для логов
    - Добавление консольного и файлового обработчиков
    - Настройку форматов и уровней логирования
    """
    logger.remove()
    
    # Форматы сообщений
    console_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name: <35}</cyan>:<cyan>{function: <25}</cyan>:<cyan>{line: <5}</cyan> | "
        "<level>{message}</level>"
    )
    
    file_format: str = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Создание директории для логов
    logs_dir: Path = Path("logs")
    try:
        logs_dir.mkdir(exist_ok=True)
        logger.debug(f"Директория для логов: {logs_dir.resolve()}")
    except PermissionError as exc:
        logger.critical(f"Ошибка доступа к директории логов: {exc}")
        sys.exit(1)

    # Параметры обработчиков
    console_handler: dict = {
        "sink": sys.stdout,
        "format": console_format,
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "colorize": True,
        "backtrace": True,
        "diagnose": True
    }
    
    file_handler: dict = {
        "sink": logs_dir / "bot.log",
        "format": file_format,
        "level": "DEBUG",
        "rotation": "1 week",
        "compression": "zip",
        "enqueue": True,
        "encoding": "utf-8"
    }

    try:
        logger.add(**console_handler)
        logger.add(**file_handler)
    except Exception as exc:
        logger.critical(f"Ошибка инициализации логгера: {exc}")
        raise

    finally:
        logger.success("Логгер сконфигурирован")


# Инициализация при импорте модуля
try:
    setup_logger()
except Exception as exc:
    logger.critical(f"Критическая ошибка при настройке логгера: {exc}")
    sys.exit(1)