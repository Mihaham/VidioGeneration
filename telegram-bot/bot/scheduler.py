"""
Модуль планировщика задач и обработки видео

Содержит:
- Задачи для cron-расписания
- Генерацию и отправку видео контента
- Управление медиагруппами
- Интеграцию с внешними хранилищами
"""

import asyncio
import time
from pathlib import Path
from typing import List, Optional, Tuple

from aiogram import Bot
from aiogram.types import FSInputFile, Message
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.context import FSMContext
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from moviepy.editor import VideoFileClip

from bot.config import TIMEZONE
from bot.handlers.google_auth import upload_video_wrapper
from videogeneration.main import generate_video
from videogeneration.upload_video import upload_video

from tests.test_notebook import TOKEN_FILE


async def get_video_duration(video_path: Path) -> float:
    """Получает продолжительность видеофайла в секундах.
    
    Args:
        video_path: Путь к видеофайлу
        
    Returns:
        Продолжительность видео в секундах
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, 
        lambda: VideoFileClip(str(video_path)).duration
    )

async def send_photos_group(bot: Bot, user_id: int, photos_paths: List[Path]) -> None:
    """Отправляет группу фотографий с интервалами.
    
    Args:
        bot: Экземпляр Telegram бота
        user_id: ID пользователя для отправки
        photos_paths: Список путей к изображениям
    """
    for i in range(0, len(photos_paths), 10):
        chunk = photos_paths[i:i+10]
        media_group = MediaGroupBuilder(caption=f"Медиагруппа {i//10 + 1}")
        
        for photo in chunk:
            media_group.add_photo(media=FSInputFile(photo))
        
        try:
            await bot.send_media_group(
                chat_id=user_id,
                media=media_group.build()
            )
            await asyncio.sleep(5)  # Асинхронная задержка
        except Exception as exc:
            logger.error("Ошибка отправки медиагруппы: {}", exc)


async def send_scheduled_message(bot: Bot, user_id: int, upload: bool = True) -> None:
    """Основная задача для генерации и отправки видео.
    
    Args:
        bot: Экземпляр Telegram бота
        user_id: ID пользователя для отправки
        upload: Флаг загрузки на внешнее хранилище
    """
    logger.info("Начало запланированной генерации видео")
    await bot.send_message(chat_id=user_id, text="⏳ Начинаю генерацию видео...")
    
    video_path: Optional[Path] = None
    photos_paths: List[Path] = []
    title, description = "", ""
    
    try:
        while True:
            # Генерация видео
            result = await asyncio.to_thread(generate_video)
            video_path, photos_paths, title, description = result
            video_path = Path(video_path)
            
            if not video_path.exists():
                raise FileNotFoundError(f"Видео файл не найден: {video_path}")
            
            # Проверка продолжительности
            duration = await get_video_duration(video_path)
            duration_minutes = duration / 60
            
            try:
                # Отправка видео
                await bot.send_video(
                    chat_id=user_id,
                    video=FSInputFile(video_path),
                    caption="🎥 Видео сгенерировано!"
                )
                
                # Отправка фотографий (раскомментировать при необходимости)
                # await send_photos_group(bot, user_id, photos_paths)
                
                if 0.5 < duration_minutes < 1:
                    logger.success("Видео соответствует требованиям по длительности")
                    break
                
                await bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Длина видео не соответствует требованиям. Повторяю генерацию..."
                )
                
            except Exception as send_exc:
                logger.error("Ошибка отправки контента: {}", send_exc)
                continue

    except Exception as gen_exc:
        # Логируем исключение с полным трейсбэком
        logger.opt(exception=True).critical(
            "Критическая ошибка генерации (user_id={})",
            user_id
        )

        # Формируем сообщение об ошибке
        error_message = (
            f"🚨 Критическая ошибка генерации:\n"
            f"• Тип: {type(gen_exc).__name__}\n"
            f"• Сообщение: {str(gen_exc)}\n"
            f"• Файл: {gen_exc.__traceback__.tb_frame.f_code.co_filename}\n"
            f"• Строка: {gen_exc.__traceback__.tb_lineno}"
        )

        await bot.send_message(
            chat_id=user_id,
            text=error_message
        )
                
    if upload and video_path:
        await upload_video_wrapper(
            bot=bot,
            user_id=user_id,
            state=state,
            video_path=video_path,
            title=title,
            description=description
        )

def setup_scheduler(scheduler: AsyncIOScheduler, bot: Bot, user_id: int) -> Job:
    """Настраивает и добавляет задание в планировщик.
    
    Args:
        scheduler: Экземпляр планировщика
        bot: Экземпляр Telegram бота
        user_id: ID пользователя для отправки
        
    Returns:
        Созданное задание планировщика
    """
    return scheduler.add_job(
        send_scheduled_message,
        trigger=CronTrigger(
            day_of_week="tue,fri",
            hour=12,
            minute=0,
            timezone=TIMEZONE
        ),
        args=[bot, user_id],
        max_instances=1,
        coalesce=True,
        replace_existing=True
    )