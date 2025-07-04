from aiogram import Bot, Router, types, F

import os
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, ReplyKeyboardRemove, BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pathlib import Path
from pydub import AudioSegment
from aiogram.types import Voice
from io import BytesIO

from loguru import logger

from bot.config import USER_ID
from bot.handlers.filters import is_admin, duplicate_to_owner, is_owner
from bot.handlers.keyboards import admin_panel_kb, user_main_kb, get_voice_keyboard, BTN_SOUND_GENERATION, BTN_PHOTO_GENERATION
from videogeneration.sound_generation import generate_audio_file
from videogeneration.sdapi_cleared import generate_photo_file
from videogeneration.config import VOICES_DICT

# Роутер для обработки сообщений
router = Router()





def convert_wav_to_ogg(wav_path: str) -> BytesIO:
    """Конвертирует WAV в OGG/OPUS формате для Telegram Voice"""
    # Загружаем WAV файл
    audio = AudioSegment.from_wav(wav_path)

    # Конвертируем в OGG с кодеком OPUS
    ogg_buffer = BytesIO()
    audio.export(ogg_buffer, format="ogg", codec="libopus")
    ogg_buffer.seek(0)

    return ogg_buffer

# Состояния FSM
class UserStates(StatesGroup):
    waiting_for_voice_choice = State()  # Новое состояние для выбора голоса
    waiting_for_audio_text = State()
    waiting_for_image_prompt = State()



@router.message(F.text == BTN_SOUND_GENERATION)
async def start_command(message: Message, state: FSMContext):
    await message.answer(
        "Сначала выберите тип голоса:",
        reply_markup=get_voice_keyboard()
    )
    await state.set_state(UserStates.waiting_for_voice_choice)


# Обработчик выбора голоса
@router.message(UserStates.waiting_for_voice_choice)
async def handle_voice_choice(message: Message, state: FSMContext):
    # Проверяем, что выбранный голос есть в нашем словаре
    if message.text not in VOICES_DICT:
        await message.answer("Пожалуйста, выберите голос из предложенных вариантов:")
        return

    # Сохраняем выбор голоса в состоянии
    voice_type = VOICES_DICT[message.text]
    await state.update_data(voice_type=voice_type)

    # Переходим к ожиданию текста
    await message.answer(
        "Отлично! Теперь отправьте текст для преобразования в голосовое сообщение",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(UserStates.waiting_for_audio_text)

@router.message(UserStates.waiting_for_audio_text)
async def process_text(message: Message, bot : Bot, state: FSMContext):
    user_text = message.text
    user_id = message.from_user.id

    try:
        data = await state.get_data()
        voice_type = data.get("voice_type", "May_24000")

        await duplicate_to_owner(
            bot=bot,
            user_id=user_id,
            method="message",
            text=f"Генерация изображения по тексту: ({user_text}) c голосом {voice_type}",
        )

        # Генерируем аудио
        audio_path = generate_audio_file(user_text, voice = voice_type)

        # Проверяем существование файла
        if not os.path.exists(audio_path):
            raise FileNotFoundError("Аудиофайл не был создан")

        # Отправляем аудио
        audio = FSInputFile(audio_path)
        await message.answer_audio(audio, caption="Ваше аудио готово!", reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))
        await duplicate_to_owner(
            bot=bot,
            user_id=user_id,
            method="audio",
            audio=audio,
            caption="Ваше аудио готово!"
        )

        # Конвертация в формат Telegram
        ogg_buffer = convert_wav_to_ogg(audio_path)

        # Создаем BufferedInputFile для отправки
        voice_file = BufferedInputFile(
            file=ogg_buffer.read(),
            filename="voice.ogg"
        )

        # Отправка голосового сообщения
        await message.answer_voice(voice=voice_file)

    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))
    finally:
        # Очищаем состояние
        await state.clear()




@router.message(F.text == BTN_PHOTO_GENERATION)
async def start_command(message: Message, state: FSMContext):
    await message.answer(
        "Напиши мне запрос на английском языке, а я тебе выдам картинку по этому запросу:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(UserStates.waiting_for_image_prompt)


@router.message(UserStates.waiting_for_image_prompt)
async def process_text(message: Message, bot: Bot, state: FSMContext):
    user_text = message.text
    user_id = message.from_user.id
    try:
        await duplicate_to_owner(
            bot=bot,
            user_id=user_id,
            method="message",
            text=f"Генерация изображения по тексту: {user_text}",
        )

        # Генерируем аудио
        photo_path = await generate_photo_file(user_text)

        # Проверяем существование файла
        if not os.path.exists(photo_path):
            raise FileNotFoundError("Фото не было создано")

        # Отправляем аудио
        photo = FSInputFile(photo_path)
        await message.answer_photo(photo, caption="Ваше фото готово!", reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))
        await duplicate_to_owner(
            bot=bot,
            user_id=user_id,
            method="photo",
            photo=photo,
            caption="Ваше фото готово!"
        )

    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}", reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))
    finally:
        # Очищаем состояние
        await state.clear()



