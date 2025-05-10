"""
Модуль фильтров и утилит для проверки прав администратора

Содержит:
- Функцию проверки административных прав пользователя
- Кастомный фильтр для обработчиков Aiogram
"""

from typing import Any, Optional, cast

from aiogram import Router, types
from aiogram.filters import Filter
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import User
from database.db import async_session

class AdminFilter(Filter):
    """Фильтр проверки административных прав пользователя.
    
    Использование:
    @router.message(AdminFilter())
    async def admin_handler(message: types.Message):
        ...
    """

    async def __call__(self, update: Any) -> bool:
        """Проверяет наличие административных прав у отправителя сообщения.
        
        Args:
            update: Объект входящего обновления от Telegram
            
        Returns:
            bool: True если пользователь имеет права администратора
        """
        if not isinstance(update, types.Message):
            return False
            
        user_id = update.from_user.id
        return await is_admin(user_id)

async def is_admin(user_id: int) -> bool:
    """Проверяет наличие административных прав у пользователя.
    
    Args:
        user_id: Telegram ID пользователя для проверки
        
    Returns:
        bool: Статус администратора пользователя
        
    Raises:
        RuntimeError: При критических ошибках подключения к БД
    """
    logger.debug("Проверка прав администратора для пользователя {}", user_id)
    
    try:
        async with async_session() as session:
            session = cast(AsyncSession, session)
            result = await session.execute(
                select(User.is_admin)
                .where(User.telegram_id == user_id)
                .limit(1)
            )
            user: Optional[bool] = result.scalar_one_or_none()
            
            if user is None:
                logger.warning("Пользователь {} не найден", user_id)
                return False
                
            logger.info(
                "Статус администратора для {}: {}",
                user_id,
                "GRANTED" if user else "DENIED"
            )
            return user
            
    except Exception as exc:
        logger.opt(exception=True).critical(
                "КРИТИЧЕСКАЯ ОШИБКА при проверке прав администратора\n"
                "User ID: {}\n"
                "Exception Type: {}\n"
                "Exception Message: {}\n"
                "Stack Trace:",
                user_id,
                type(exc).__name__,
                str(exc)
            )
        return False