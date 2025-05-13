import os
from typing import List
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from videogeneration.utils import get_next_free_path
from loguru import logger
from bot.logger_setup import LoguruMoviePyLogger

def compile_video(first_page: str, photos: List[str], audio: str) -> str:
    # Константы для настройки длительности и FPS
    FIRST_DURATION = 1.0     # Длительность первого изображения (секунды)
    OTHER_DURATION = 0.5     # Длительность остальных изображений (секунды)
    FPS = 24                 # Кадров в секунду
    OUTPUT_PATH = get_next_free_path("output/video", prefix="video_", suffix=".mp4")  # Путь для сохранения видео
    logger.debug(f"Compiling video")

    # Создаем директорию, если она не существует
    output_dir = os.path.dirname(OUTPUT_PATH)
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Compile videoclips from photos")
    # Создаем видеоклипы из изображений с указанием длительности
    clips = [ImageClip(first_page).set_duration(FIRST_DURATION)]
    for photo in photos:
        clips.append(ImageClip(photo).set_duration(OTHER_DURATION))


    logger.info(f"Concating videoclips")
    # Собираем все клипы в один видеофайл
    video = concatenate_videoclips(clips, method="compose")

    # Добавляем аудиодорожку
    logger.info(f"Adding audio clip")
    audio_clip = AudioFileClip(audio)
    video = video.set_audio(audio_clip)

    logger.info(f"Saving video into path : {OUTPUT_PATH}")
    # Сохраняем результат
    video.write_videofile(OUTPUT_PATH, fps=FPS, verbose=True, logger="bar")


    logger.success(f"Compiled video!") 
    return OUTPUT_PATH