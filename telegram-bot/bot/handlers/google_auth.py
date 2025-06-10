import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup

from bot.handlers.filters import OwnerFilter
from bot.handlers.keyboards import BTN_AUTHORIZATION
from videogeneration.config import TOKEN_FILE
from videogeneration.upload_video import upload_video
from loguru import logger

# Конфигурация
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']  # Ваши scopes
TOKEN_DIR = "tokens"
os.makedirs(TOKEN_DIR, exist_ok=True)

router = Router()
router.message.filter(OwnerFilter())

class AuthStates(StatesGroup):
    waiting_auth_code = State()


async def get_authenticated_service(user_id: int, state: FSMContext = None) -> Credentials:
    """Получение авторизованного сервиса с обработкой через FSM"""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Если есть валидные учетные данные - возвращаем
    if creds and creds.valid:
        return creds

    # Если требуется полная авторизация
    if state:
        await start_auth_flow(user_id, state)
    return None


async def start_auth_flow(user_id: int, state: FSMContext):
    """Инициирует процесс OAuth аутентификации"""
    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    auth_url, _ = flow.authorization_url(prompt='consent')

    await state.set_state(AuthStates.waiting_auth_code)
    await state.update_data(flow=flow, user_id=user_id)

    # Отправляем пользователю ссылку для авторизации
    message = await state.bot.send_message(
        chat_id=user_id,
        text=f"🔑 [Авторизация] Пожалуйста, перейдите по ссылке:\n{auth_url}\n\n"
             "После разрешения доступа введите полученный код:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Открыть ссылку", url=auth_url)
        ]])
    )
    await state.update_data(auth_message_id=message.message_id)


@router.message(F.text == BTN_AUTHORIZATION)
async def auth_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    creds = await get_authenticated_service(user_id, state)

    if creds:
        await message.answer("✅ Вы уже авторизованы!")
    # Если не авторизованы - процесс продолжится в start_auth_flow


@router.message(AuthStates.waiting_auth_code)
async def handle_auth_code(message: types.Message, state: FSMContext):
    try:
        user_data = await state.get_data()
        flow = user_data['flow']
        user_id = user_data['user_id']
        auth_message_id = user_data.get('auth_message_id', 0)

        # Получаем токен по коду
        flow.fetch_token(code=message.text.strip())
        creds = flow.credentials

        # Сохраняем токен
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

        # Удаляем сообщение с инструкцией
        await message.bot.delete_message(chat_id=user_id, message_id=auth_message_id)
        await message.answer("✅ Авторизация успешно завершена!")

        # Проверяем, есть ли ожидающее видео для загрузки
        if 'pending_video' in user_data:
            video_data = user_data['pending_video']
            await upload_video_wrapper(
                bot=message.bot,
                user_id=user_id,
                state=state,
                video_path=video_data['video_path'],
                title=video_data['title'],
                description=video_data['description']
            )

        await state.clear()

    except Exception as e:
        logger.exception("Auth code processing error")
        await message.answer(f"❌ Ошибка: Неверный код или проблема с подключением. Попробуйте снова командой /auth")
        await state.clear()

async def upload_video_wrapper(
        bot: Bot,
        user_id: int,
        state: FSMContext,
        video_path: str,
        title: str,
        description: str
):
    """Обертка для загрузки видео с проверкой аутентификации"""
    # Получаем учетные данные
    creds = await get_authenticated_service(user_id, state)

    if not creds:
        # Сохраняем данные видео в состоянии для последующего использования
        await state.update_data({
            "pending_video": {
                "video_path": video_path,
                "title": title,
                "description": description
            }
        })
        await bot.send_message(
            chat_id=user_id,
            text="🔑 Требуется авторизация YouTube. Пожалуйста, пройдите процесс авторизации."
        )
        return

    # Если есть действительные учетные данные - загружаем видео
    try:
        video_id = upload_video(
            creds=creds,
            video_path=video_path,
            title=title,
            privacy="public",
            description=description
        )
        await bot.send_message(
            chat_id=user_id,
            text=f"🎥 Видео успешно загружено: https://www.youtube.com/watch?v={video_id}"
        )
        logger.success(f"Видео {video_id} успешно загружено на YouTube")
    except Exception as upload_exc:
        logger.error("Ошибка загрузки видео: {}", upload_exc)
        await bot.send_message(
            chat_id=user_id,
            text=f"❌ Ошибка при загрузке видео: {str(upload_exc)}"
        )