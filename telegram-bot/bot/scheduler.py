from apscheduler.triggers.cron import CronTrigger
from bot.config import TIMEZONE
from loguru import logger
import asyncio
from moviepy.editor import VideoFileClip
from aiogram.types import FSInputFile
from videogeneration.main import generate_video
from aiogram.utils.media_group import MediaGroupBuilder
import time
from videogeneration.upload_video import upload_video

async def get_video_duration(video_path):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: VideoFileClip(video_path).duration)

async def send_photos_group(bot, user_id, photos_paths):
    for i in range(0, len(photos_paths), 10):
        chunk = photos_paths[i:i+10]
        media_group = MediaGroupBuilder(
            caption=f"Media group {i}")
        for photo in chunk :
            media_group.add_photo(type="photo", media=FSInputFile(photo))
        await bot.send_media_group(chat_id=user_id, media=media_group.build())
        time.sleep(5)

async def send_scheduled_message(bot, user_id : int, upload : bool = True):
    await bot.send_message(chat_id = user_id, text="Начинаю запланированную генерацию видео")
    video_path, photos_paths = None, None
    while True:
        video_path, photos_paths, title = await asyncio.get_event_loop().run_in_executor(None, generate_video)
        
        try:
            duration = await get_video_duration(video_path)
            duration_minutes = duration / 60
            
            # Отправка видео
            await bot.send_video(chat_id=user_id, video=FSInputFile(video_path),caption="Video generated!")
            
            # Отправка фото
            #await send_photos_group(bot, user_id, photos_paths)
            
            # Проверка длительности
            if 0.5 < duration_minutes < 1:
                break
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text="Длина видео не соответствует требованиям. Повторяю генерацию..."
                )
                
        except Exception as e:
            await bot.send_message(chat_id=user_id, text=f"Произошла ошибка: {str(e)}")
            continue
        
        finally:
            # Очистка временных файлов (реализуйте при необходимости)
            pass
    if upload:
        upload_video(video_path, title, privacy="public")

def setup_scheduler(scheduler, bot, user_id):
    scheduler.add_job(
        send_scheduled_message,
        CronTrigger(
            day_of_week='tue,fri',
            hour=12,
            minute=0,
            timezone=TIMEZONE
        ),
        args=[bot, user_id]
    )