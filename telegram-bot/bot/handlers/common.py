"""
Модуль обработки стартовых команд пользователя

Содержит хендлеры для:
- Первичной регистрации пользователей
- Отображения главного меню
- Инициализации пользовательской сессии
"""

from typing import Optional

from aiogram import Router, types
from aiogram.filters import Command
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.keyboards import user_main_kb
from bot.models import User
from database.db import async_session

router = Router()

@router.message(Command("start"))
async def start(message: types.Message) -> None:
    """Обрабатывает команду /start, регистрируя нового пользователя или приветствуя существующего.
    
    Args:
        message: Объект входящего сообщения с данными пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username or "Анонимный пользователь"
    logger.info("Обработка команды /start для пользователя {}", user_id)

    try:
        async with async_session.begin() as session:
            # Поиск существующего пользователя
            result = await session.execute(
                select(User)
                .where(User.telegram_id == user_id)
            )
            user: Optional[User] = result.scalar_one_or_none()

            # Регистрация нового пользователя
            if not user:
                user = User(
                    telegram_id=user_id,
                    username=username[:50]  # Обрезка до 50 символов
                )
                session.add(user)
                logger.success("Зарегистрирован новый пользователь: {}", username)
            else:
                logger.debug("Пользователь уже существует: {}", username)

            # Формирование ответа
            welcome_text = (
                f"🎉 Добро пожаловать, {user.username}!\n\n"
                "🛠 Выберите нужное действие в меню ниже:"
            )
            
            await message.answer(
                text=welcome_text,
                reply_markup=user_main_kb(user.is_admin)
            )
            logger.success("Главное меню отправлено пользователю {}", user_id)

    except Exception as exc:
        logger.critical(
            "Ошибка обработки команды /start для пользователя {}: {}",
            user_id,
            exc
        )
        await message.answer("⚠️ Произошла ошибка при обработке запроса. Попробуйте позже.")