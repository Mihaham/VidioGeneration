"""
Модуль конфигурации приложения

Обеспечивает:
- Загрузку переменных окружения из .env файла
- Валидацию обязательных параметров
- Инициализацию временной зоны
- Централизованное хранение настроек
"""

import os

from dotenv import load_dotenv
from loguru import logger
from pytz import timezone
from pytz.exceptions import UnknownTimeZoneError

# Загрузка переменных окружения
env_loaded = load_dotenv()
if env_loaded:
    logger.info("Найдены локальные переменные окружения (.env)")
else:
    logger.warning("Локальный .env файл не обнаружен, используются системные переменные")

# Основные конфигурационные параметры
TOKEN: str = os.getenv('BOT_TOKEN')
USER_ID: str = os.getenv('USER_ID')
DEFAULT_TZ = 'Europe/Moscow'
TIMEZONE_NAME: str = os.getenv('TZ', DEFAULT_TZ)
NEED_SHEDULER: bool = True

# Валидация обязательных параметров
missing_vars = []
if not TOKEN:
    missing_vars.append('BOT_TOKEN')
if not USER_ID:
    missing_vars.append('USER_ID')

if missing_vars:
    error_msg = f"Отсутствуют обязательные переменные: {', '.join(missing_vars)}"
    logger.critical(error_msg)
    raise EnvironmentError(error_msg)

# Инициализация временной зоны
try:
    TIMEZONE = timezone(TIMEZONE_NAME)
    logger.debug(f"Временная зона установлена: {TIMEZONE_NAME}")
except UnknownTimeZoneError as exc:
    logger.error(
        "Некорректная временная зона в конфигурации: {}",
        TIMEZONE_NAME
    )
    TIMEZONE = timezone(DEFAULT_TZ)
    logger.warning("Используется временная зона по умолчанию: {}", DEFAULT_TZ)

logger.success("Конфигурация приложения успешно загружена")