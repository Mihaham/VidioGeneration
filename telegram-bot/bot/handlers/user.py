from aiogram import Bot, Router, types, F

import os
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pathlib import Path

from bot.handlers.filters import is_admin
from bot.handlers.keyboards import admin_panel_kb, user_main_kb, BTN_SOUND_GENERATION
from videogeneration.sound_generation import generate_audio_file

# Роутер для обработки сообщений
router = Router()


# Состояния FSM
class AudioStates(StatesGroup):
    waiting_for_text = State()


@router.message(F.text == BTN_SOUND_GENERATION)
async def start_command(message: Message, state: FSMContext):
    await message.answer("Отправь мне текст для преобразования в аудио", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AudioStates.waiting_for_text)


@router.message(AudioStates.waiting_for_text)
async def process_text(message: Message, state: FSMContext):
    user_text = message.text

    try:
        # Генерируем аудио
        audio_path = generate_audio_file(user_text)

        # Проверяем существование файла
        if not os.path.exists(audio_path):
            raise FileNotFoundError("Аудиофайл не был создан")

        # Отправляем аудио
        audio = FSInputFile(audio_path)
        await message.answer_audio(audio, caption="Ваше аудио готово!", reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))

    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))
    finally:
        # Очищаем состояние
        await state.clear()