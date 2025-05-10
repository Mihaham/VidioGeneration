from aiogram import Router, types
from aiogram.filters import Command
from bot.models import User
from database.db import async_session
from bot.handlers.keyboards import user_main_kb
from sqlalchemy import select

router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
            session.add(user)
            await session.commit()
        await message.answer(
            f"Добро пожаловать, {user.username}!",
            reply_markup=user_main_kb(user.is_admin)
        )