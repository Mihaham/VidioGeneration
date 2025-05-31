from videogeneration.utils import get_next_free_path
from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap
import os


def create_text_image(text, max_width, max_height, fontsize=36, font_path=None):
    """
    Создает изображение с текстом, гарантированно помещающееся в указанные размеры

    Параметры:
    text (str): Текст для отображения
    max_width (int): Максимальная ширина изображения
    max_height (int): Максимальная высота изображения
    fontsize (int): Начальный размер шрифта
    font_path (str): Путь к файлу шрифта

    Возвращает:
    np.array: Массив пикселей изображения
    """
    # Загружаем шрифт
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, fontsize)
        else:
            # Пытаемся найти стандартные шрифты
            for fname in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "Arial"
            ]:
                try:
                    font = ImageFont.truetype(fname, fontsize)
                    break
                except:
                    continue
            else:
                # Используем стандартный шрифт
                font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Адаптивный подбор размера шрифта и разбивки текста
    current_fontsize = fontsize
    wrapped_text = text
    text_width, text_height = max_width, max_height

    # Пытаемся уменьшить размер шрифта, пока текст не поместится
    while current_fontsize > 10:
        # Пробуем разбить текст на более короткие строки
        chars_per_line = max(10, int(max_width / (current_fontsize * 0.6)))
        wrapped_text = '\n'.join(textwrap.wrap(text, width=chars_per_line))

        # Создаем временное изображение для измерения текста
        test_img = Image.new('RGB', (1, 1))
        test_draw = ImageDraw.Draw(test_img)
        text_bbox = test_draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Если текст помещается, выходим из цикла
        if text_width <= max_width * 0.9 and text_height <= max_height * 0.9:
            break

        # Уменьшаем размер шрифта для следующей попытки
        current_fontsize -= 2
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, current_fontsize)
        else:
            font = ImageFont.truetype(font.path, current_fontsize)

    # Создаем изображение с отступами
    img_width = min(max_width, text_width + 40)
    img_height = min(max_height, text_height + 20)
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Рисуем текст
    draw.multiline_text(
        (img_width // 2, img_height // 2),
        wrapped_text,
        font=font,
        fill="white",
        anchor="mm",  # центр
        align="center",
        stroke_width=1,
        stroke_fill="black"
    )

    return np.array(img)


def split_into_short_phrases(text, max_words=3):
    """
    Разбивает текст на короткие фразы по 1-3 слова

    Параметры:
    text (str): Исходный текст
    max_words (int): Максимальное количество слов в фразе

    Возвращает:
    list: Список коротких фраз
    """
    # Разбиваем текст на слова
    words = [word.strip() for word in text.split() if word.strip()]
    phrases = []

    # Формируем короткие фразы
    current_phrase = []
    for word in words:
        # Если слово содержит знаки пунктуации, завершаем фразу
        if any(punct in word for punct in ['.', ',', '!', '?', ';', ':']):
            if current_phrase:
                phrases.append(" ".join(current_phrase))
                current_phrase = []
            phrases.append(word)
        # Если достигли максимальной длины фразы
        elif len(current_phrase) >= max_words:
            phrases.append(" ".join(current_phrase))
            current_phrase = [word]
        else:
            current_phrase.append(word)

    # Добавляем последнюю фразу, если осталась
    if current_phrase:
        phrases.append(" ".join(current_phrase))

    return phrases


def add_subtitles_from_text(input_video, text, output_video=None,
                            fontsize=36, color='white', bg_opacity=0.6):
    """
    Добавляет субтитры короткими фразами поверх видео

    Параметры:
    input_video (str): Путь к исходному видео
    output_video (str): Путь для сохранения результата
    text (str): Текст для субтитров
    fontsize (int): Размер шрифта
    color (str): Цвет текста
    bg_opacity (float): Прозрачность фона (0.0-1.0)
    """
    # Определяем путь для выходного файла
    if not output_video:
        output_video = get_next_free_path('output/video_with_subtitles', prefix='video_', suffix='.mp4')

    # Загружаем видео
    video = VideoFileClip(input_video)
    duration = video.duration

    # Разбиваем текст на короткие фразы
    phrases = split_into_short_phrases(text)
    if not phrases:
        raise ValueError("Текст для субтитров пуст!")

    # Рассчитываем длительность для каждой фразы
    phrase_duration = duration / len(phrases)

    # Создаем список видеоклипов
    clips = [video]

    # Максимальные размеры для субтитра
    max_sub_width = int(video.w * 0.9)  # 90% ширины видео
    max_sub_height = int(video.h * 0.15)  # 15% высоты видео

    # Генерируем субтитры для каждой фразы
    for i, phrase in enumerate(phrases):
        if not phrase:
            continue

        start_time = i * phrase_duration
        end_time = (i + 1) * phrase_duration
        clip_duration = end_time - start_time

        # Создаем текстовый клип с помощью Pillow
        text_image = create_text_image(phrase, max_sub_width, max_sub_height, fontsize)
        txt = ImageClip(text_image, duration=clip_duration)

        # Создаем фон для субтитра
        bg_height = text_image.shape[0] + 20
        bg = ColorClip(
            size=(video.w, bg_height),
            color=(0, 0, 0),
            duration=clip_duration
        ).set_opacity(bg_opacity)

        # Позиционируем элементы
        bg = bg.set_position(("center", "bottom")).set_start(start_time)
        txt = txt.set_position(("center", "bottom")).set_start(start_time)

        clips.extend([bg, txt])

    # Собираем финальное видео
    final = CompositeVideoClip(clips)

    # Сохраняем результат
    final.write_videofile(
        output_video,
        codec='libx264',
        audio_codec='aac',
        fps=video.fps,
        threads=4,
        logger=None,
        preset='ultrafast',
        ffmpeg_params=['-crf', '23']
    )

    # Закрываем клипы
    video.close()
    final.close()

    return output_video


# Пример использования
if __name__ == "__main__":
    subtitle_text = "В то время как камера плавно скользит по кристальной пещере, окутанной золотыми акцентами, в которой каждый уголок наполнен мерцающими сталагмитами и сталактитами, создающими атмосферу волшебного подземного царства."
    add_subtitles_from_text("input.mp4", subtitle_text, "output.mp4")