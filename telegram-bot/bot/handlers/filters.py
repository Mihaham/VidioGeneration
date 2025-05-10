from aiogram import Router, types
from aiogram.filters import Filter
from aiogram.filters.command import Command

from loguru import logger
from sqlalchemy import select
from database.db import get_db
from bot.models import User

async def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором
    """
    logger.debug(f"Начало проверки прав администратора для user_id: {user_id}")
    
    async for session in get_db():
        try:
            logger.info(f"Выполнение запроса к БД для user_id: {user_id}")
            
            # Выполняем запрос к БД
            result = await session.execute(
                select(User)
                .where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"Пользователь {user_id} не найден в базе данных")
                return False
                
            logger.debug(f"Найден пользователь: {user.id} (telegram_id: {user.telegram_id})")
            logger.info(f"Статус администратора для {user_id}: {user.is_admin}")
            
            return user.is_admin
            
        except Exception as e:
            logger.exception(f"Ошибка при проверке прав администратора для {user_id}:")
            logger.error(f"Тип ошибки: {type(e).__name__}, сообщение: {str(e)}")
            return False
            
    logger.error("Не удалось получить сессию базы данных")
    return False


# Создаем кастомный фильтр
class AdminFilter(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return await is_admin(message.from_user.id)