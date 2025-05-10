from aiogram import Router, types
from aiogram.filters import Command
from database.db import get_db
from bot.models import User, Message
from videogeneration.sdapi_cleared import AsyncSDClient
from sqlalchemy import select
from datetime import datetime
from loguru import logger
from aiogram import Router, types, F

memory_router = Router()

async def update_user_and_message(user_data: types.User, message_text: str):
    async for session in get_db():
        # Обновляем или создаем пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == user_data.id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=user_data.id,
                username=user_data.username
            )
            session.add(user)
        else:
            user.username = user_data.username
            user.last_activity = datetime.utcnow()
        
        # Сохраняем сообщение
        message = Message(
            user=user,
            text=message_text
        )
        session.add(message)
        
        await session.commit()


@memory_router.message(F.text == "📊 Статистика памяти")
@memory_router.message(Command("memory"))
async def handle_memory_command(message: types.Message):
    # Сохраняем пользователя и сообщение
    await update_user_and_message(message.from_user, message.text)
    
    # Получаем данные о памяти
    memory_stats = None
    async with AsyncSDClient() as sd:
        memory_stats = await sd.get_memory_stats()
    
    def format_memory(value: float) -> str:
        # Конвертируем байты в гигабайты (1 GB = 1024^3 bytes)
        gb = value / (1024 ** 3)
        return f"{gb:.2f} GB" if gb else "N/A"

    try:
        ram_data = memory_stats.get('ram', {})
        response_text = (
            "📊 Статистика памяти:\n"
            f"• Использовано: {format_memory(ram_data.get('used', 0))}\n"
            f"• Свободно: {format_memory(ram_data.get('free', 0))}\n"
            f"• Всего: {format_memory(ram_data.get('total', 0))}\n"
            "\n💻 VRAM статистика:\n"
            f"• Выделено: {format_memory(memory_stats.get('cuda', {}).get('allocated', {}).get('current', 0))}\n"
            f"• Зарезервировано: {format_memory(memory_stats.get('cuda', {}).get('reserved', {}).get('current', 0))}"
        )
    except Exception as e:
        logger.error(f"Error parsing memory data: {str(e)}")
        response_text = "⚠️ Ошибка обработки данных от сервера"

    await message.answer(response_text)