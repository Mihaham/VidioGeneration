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

class LoguruMoviePyLogger:
    """
    Адаптер для перенаправления логов moviepy в loguru
    """

    def __init__(self):
        """Инициализация без аргументов"""
        pass

    def debug(self, msg):
        """Обработка debug-сообщений"""
        logger.debug(msg)

    def info(self, msg):
        """Обработка info-сообщений"""
        logger.info(msg)

    def warning(self, msg):
        """Обработка предупреждений"""
        logger.warning(msg)

    def error(self, msg):
        """Обработка ошибок"""
        logger.error(msg)

    def critical(self, msg):
        """Обработка критических ошибок"""
        logger.critical(msg)

    # Для совместимости с некоторыми версиями moviepy
    def write(self, buf):
        """Перехват буферизированных записей"""
        for line in buf.rstrip().splitlines():
            logger.debug(line.rstrip())

    # Метод-заглушка для обработки прогресса
    def progress(self, current, total):
        """Логирование прогресса (если требуется)"""
        logger.info(f"Прогресс рендеринга: {current}/{total} ({current/total:.1%})")

    def flush(self):
        """Метод для совместимости с файлоподобными объектами"""
        pass

    def __call__(self, *args, **kwargs):
        # Every time the logger message is updated, this function is called with
        # the `changes` dictionary of the form `parameter: new value`.
        logger.debug(f"__call__ called with {args}, {kwargs}")
        if kwargs:
            for (parameter, value) in kwargs.items():
                logger.debug('Parameter %s is now %s' % (parameter, value))
        if args:
            for parametr in args:
                logger.debug(f"Got parametr {parametr}")

    def iter_bar(self, *args, **kwargs):
        logger.debug(f"Iter_bar called with {args}, {kwargs}")
        if kwargs:
            for (parameter, value) in kwargs.items():
                logger.debug('Parameter %s is now %s' % (parameter, value))
        if args:
            for parametr in args:
                logger.debug(f"Got parametr {parametr}")


    def bars_callback(self, bar, attr, value, old_value=None):
        # Every time the logger progress is updated, this function is called
        logger.info(f"bars_callback: {bar}, {attr}, {value}, {old_value}")

