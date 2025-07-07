"""
Модуль фильтров и утилит для проверки прав администратора

Содержит:
- Функцию проверки административных прав пользователя
- Кастомный фильтр для обработчиков Aiogram
"""

from typing import Any, Optional, cast

from aiogram import Router, types, Bot
from aiogram.filters import Filter
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import User
from database.db import async_session
from bot.config import USER_ID

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


class OwnerFilter(Filter):
    """Фильтр проверки прав владельца пользователя.

    Использование:
    @router.message(OwnerFilter())
    async def owner_handler(message: types.Message):
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
        return is_owner(user_id)

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

            #Добавляем владельца, чтобы дальше он мог настраивать сессии
            user = user or (int(USER_ID) == int(user_id))
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


def is_owner(user_id: int) -> bool:
    """Does user is owner?"""
    return user_id == USER_ID


async def duplicate_to_owner(
        bot: Bot,
        user_id: int,
        method: str,
        *args: Any,
        **kwargs: Any
) -> None:
    """
    Дублирует сообщение владельцу бота, если оно отправлено не владельцу.

    Параметры:
    - bot: Экземпляр бота aiogram
    - user_id: ID пользователя-получателя сообщения
    - method: Тип сообщения ('message', 'photo', 'audio' и т.д.)
    - *args, **kwargs: Аргументы для метода отправки сообщения

    Логика:
    - Если получатель - владелец, дублирование пропускается
    - Поддерживает основные типы контента
    - Автоматически определяет метод отправки
    - Логирует успешные операции и ошибки
    """
    # Конфигурация (заменить на реальный ID владельца)

    # Проверка получателя
    if user_id == USER_ID:
        logger.debug(f"Сообщение для владельца (ID {user_id}), дублирование отменено")
        return

    # Определение метода отправки
    send_method_name = f"send_{method}"
    if not hasattr(bot, send_method_name):
        logger.error(f"Неподдерживаемый тип сообщения: '{method}'")
        return

    send_method = getattr(bot, send_method_name)

    # Формирование аргументов с заменой получателя
    send_kwargs = kwargs.copy()
    send_kwargs['chat_id'] = USER_ID

    # Добавляем информацию об исходном получателе
    caption = send_kwargs.get('caption', '')
    if caption:
        caption = f"👤 Для: {user_id}\n\n" + caption
    else:
        caption = f"👤 Сообщение для пользователя: {user_id}"

    # Для медиа-контента добавляем caption/текст
    if method in {'photo', 'audio', 'document', 'video'}:
        send_kwargs['caption'] = caption
    elif method == 'message':
        send_kwargs['text'] = f"👤 Для: {user_id}\n\n{kwargs.get('text', '')}"

    try:
        # Отправка сообщения владельцу
        await send_method(*args, **send_kwargs)
        logger.info(f"Сообщение продублировано владельцу. Тип: {method}, Получатель: {user_id}")

    except Exception as e:
        logger.error(f"Ошибка дублирования ({method} для {user_id}): {str(e)}")