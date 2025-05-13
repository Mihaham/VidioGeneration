"""
Модуль обработки запросов статистики памяти

Содержит хендлеры для:
- Сохранения активности пользователей
- Сбора статистики использования памяти
- Интеграции с внешними сервисами мониторинга
"""

from datetime import datetime
from typing import Any, Dict, Optional

from aiogram import Router, types, F
from aiogram.filters import Command
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Message, User
from database.db import async_session
from videogeneration.sdapi_cleared import AsyncSDClient

memory_router = Router()

async def update_user_and_message(
    user_data: types.User, 
    message_text: str
) -> None:
    """Обновляет информацию о пользователе и сохраняет сообщение в БД.
    
    Args:
        user_data: Данные пользователя из Telegram
        message_text: Текст сообщения для сохранения
    """
    logger.info("Обновление данных для пользователя {}", user_data.id)
    
    try:
        async with async_session.begin() as session:
            # Получение или создание пользователя
            result = await session.execute(
                select(User)
                .where(User.telegram_id == user_data.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    telegram_id=user_data.id,
                    username=user_data.username[:50] if user_data.username else None
                )
                session.add(user)
                logger.debug("Создан новый пользователь: {}", user_data.id)
            else:
                user.username = user_data.username
                user.last_activity = datetime.utcnow()
                logger.debug("Обновлен пользователь: {}", user_data.id)

            # Сохранение сообщения
            message = Message(
                user=user,
                text=message_text[:4096]  # Ограничение длины текста
            )
            session.add(message)
            
        logger.success("Данные успешно сохранены для {}", user_data.id)
    except Exception as exc:
        logger.critical(
            "Ошибка сохранения данных для {}: {}",
            user_data.id,
            exc
        )
        raise

def format_memory_value(value: float) -> str:
    """Форматирует значение памяти в гигабайты.
    
    Args:
        value: Значение в байтах
        
    Returns:
        Строка с отформатированным значением в GB
    """
    if value <= 0:
        return "N/A"
    return f"{value / (1024 ** 3):.2f} GB"

@memory_router.message(F.text == "📊 Статистика памяти")
@memory_router.message(Command("memory"))
async def handle_memory_command(message: types.Message) -> None:
    """Обрабатывает запросы статистики использования памяти."""
    user = message.from_user
    logger.info("Запрос статистики памяти от пользователя {}", user.id)
    
    try:
        # Сохранение активности
        await update_user_and_message(user, message.text)
        
        # Получение данных о памяти
        async with AsyncSDClient() as sd:
            memory_stats: Dict[str, Any] = await sd.get_memory_stats()
        
        # Форматирование ответа
        response = ["📊 Статистика памяти:"]
        
        # Обработка RAM данных
        ram_data = memory_stats.get('ram', {})
        response.extend([
            f"• Использовано: {format_memory_value(ram_data.get('used', 0))}",
            f"• Свободно: {format_memory_value(ram_data.get('free', 0))}",
            f"• Всего: {format_memory_value(ram_data.get('total', 0))}"
        ])
        
        # Обработка VRAM данных
        cuda_data = memory_stats.get('cuda', {})
        response.extend([
            "\n💻 VRAM статистика:",
            f"• Выделено: {format_memory_value(cuda_data.get('allocated', {}).get('current', 0))}",
            f"• Зарезервировано: {format_memory_value(cuda_data.get('reserved', {}).get('current', 0))}"
        ])
        
        await message.answer("\n".join(response))
        logger.success("Статистика отправлена пользователю {}", user.id)
        
    except Exception as exc:
        logger.error(
            "Ошибка получения статистики для {}: {}",
            user.id,
            exc
        )
        await message.answer("⚠️ Не удалось получить данные о памяти")