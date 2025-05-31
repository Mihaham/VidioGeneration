import asyncio
from pathlib import Path
from typing import Tuple, Optional, List
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from loguru import logger
from videogeneration.utils import get_next_free_path
from videogeneration.config import GIGACHAT_CREDENTIALS, CA_BUNDLE_FILE
# В начале файла добавим необходимые импорты для GigaChat
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import time
import re
import emoji
import numpy as np
import requests
import unicodedata
import random

class CoverGenerator:
    def __init__(self):
        self.credentials = GIGACHAT_CREDENTIALS
        self.ca_bundle = CA_BUNDLE_FILE
        self.font_path = "fonts/Roboto-Medium.ttf"  # Укажите путь к шрифту
        self.emoji_mapping = {
            "sea": "🌊",
            "mountain": "⛰️",
            "space": "🚀",
            "future": "🔮",
            "nature": "🌿"
        }

    def _construct_system_prompt(self) -> str:
        return """Ты профессиональный копирайтер для YouTube-роликов. Соблюдай правила:
    1. Анализируй суть промпта
    2. Генерируй яркий заголовок строго из 3-5 слов
    3. Используй: Цифры, вопросы, эмоциональные прилагательные
    4. Добавляй 1-3 релевантных эмодзи в конце
    5. Запрещены: Переносы слов, слэши, сложные термины

    Формат: [Заголовок] [Эмодзи]
    Примеры:
    - "ШОК! 5 секретов ИИ, которые изменят всё 🤯💻"
    - "Как нейросети видят будущее? 🔮👁️"
    - "2077: Квантовый прорыв в 3D 💥🚀"
    """

    def extract_text_and_emojis(self, input_str: str) -> Tuple[str, str]:
        """Разделяет строку на текст и последовательность эмодзи"""
        # Получаем все эмодзи с их позициями
        emoji_info = emoji.emoji_list(input_str)
        
        # Собираем отдельно текст и эмодзи
        text_chars = []
        emoji_chars = []
        
        last_position = 0
        for info in emoji_info:
            start = info['match_start']
            end = info['match_end']
            
            # Добавляем текст до эмодзи
            text_chars.append(input_str[last_position:start])
            # Добавляем эмодзи
            emoji_chars.append(input_str[start:end])
            
            last_position = end
        
        # Добавляем оставшийся текст после последнего эмодзи
        text_chars.append(input_str[last_position:])
        
        # Формируем результат
        clean_text = ''.join(text_chars).strip()
        all_emojis = "🔥" + ''.join(emoji_chars)
        
        # Чистим текст от лишних пробелов
        clean_text = ' '.join(clean_text.split())
        
        return clean_text[1:-1], all_emojis

    def generate_clickbait_title(self, prompt: str) -> Tuple[str, str]:
        """Генерация короткого кликбейтного заголовка"""
        logger.info("Starting title generation for prompt: {}", prompt[:50])
        
        try:
            with GigaChat(
                credentials=self.credentials,
                ca_bundle_file=self.ca_bundle,
                verify_ssl_certs=True
            ) as model:
                chat = Chat(
                    messages=[
                        Messages(role=MessagesRole.SYSTEM, content=self._construct_system_prompt()),
                        Messages(role=MessagesRole.USER, content=f"Создать заголовок для: {prompt}")
                    ],
                    temperature=0.9,  # Больше креативности
                    max_tokens=80     # Жесткое ограничение длины
                )
                
                response = model.chat(chat)
                full_text = response.choices[0].message.content.strip()
                logger.success("Generated title: {}", full_text)
                
                return self.extract_text_and_emojis(full_text)
                
        except Exception as e:
            logger.error("GigaChat error: {}", str(e))
            return ("ИИ Революция: " + prompt[:12], "✨")

    def _load_and_process_image(self, image_path: str) -> Image.Image:
        """Загрузка и предобработка изображения."""
        logger.debug("Processing image: {}", image_path)
        
        try:
            img = Image.open(image_path)
            # Применяем размытие
            return img.filter(ImageFilter.GaussianBlur(radius=5))
        except Exception as e:
            logger.critical("Image processing failed: {}", str(e))
            raise

    def _add_text_to_image(
        self, 
        image: Image.Image,
        title: str,
        emoji: str
    ) -> Image.Image:
        """Добавление текста и декоративных элементов на изображение."""
        try:
            draw = ImageDraw.Draw(image)
            
            # Настройки шрифта
            font_size = 48
            try:
                font = ImageFont.truetype(self.font_path, font_size)
            except IOError:
                font = ImageFont.load_default()
                logger.warning("Using fallback font")

            # Рассчитываем позиционирование
            text = f"{title}\n{emoji}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (image.width - text_width) // 2
            y = image.height // 8

            # Текстовый контур
            stroke_width = 3
            draw.text(
                (x, y), text, font=font, fill="white",
                stroke_width=stroke_width, stroke_fill="black"
            )
            
            return image
        except Exception as e:
            logger.error("Text rendering error: {}", str(e))
            return image

    def _save_cover(
        self,
        image: Image.Image,
        output_dir: str = "output/covers"
    ) -> str:
        """Сохранение готовой обложки."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        save_path = get_next_free_path(output_dir, prefix="cover_")
        with open(save_path, "wb") as f:
            f.write(buffer.getvalue())
            
        logger.info("Cover saved to: {}", save_path)
        return save_path

    async def generate_first_page(
        self,
        prompt: str,
        initial_photo: str
    ) -> Optional[str]:
        """Основная функция генерации обложки."""
        try:
            # Генерация текста
            title, emoji = await self.generate_clickbait_title(prompt)
            logger.debug(f"Using title: {title} {emoji}")

            # Обработка изображения
            img = await asyncio.to_thread(self._load_and_process_image, initial_photo)
            img = await asyncio.to_thread(self._add_text_to_image, img, title, emoji)

            # Сохранение результата
            return await asyncio.to_thread(self._save_cover, img)
            
        except Exception as e:
            logger.critical("Cover generation failed: {}", str(e))
            return None
        
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor
from loguru import logger
from pathlib import Path

class CoverGeneratorEnhanced(CoverGenerator):
    def __init__(self):
        super().__init__()
        self.fonts = self._load_fonts()
        self.emoji_cache = {}
        
    def _load_fonts(self) -> dict:
        """Поиск и загрузка шрифтов с поддержкой кириллицы"""
        font_paths = {
            'Roboto': self._find_font('Roboto-Regular.ttf'),
            'Arial': self._find_font('arial.ttf'),
            'DejaVu': self._find_font('DejaVuSans-Bold.ttf')
        }
        logger.info(f"Found fonts: {font_paths}")
        return {name: path for name, path in font_paths.items() if path}

    def _find_font(self, filename: str) -> Optional[str]:
        """Поиск шрифта в стандартных директориях"""
        paths = [
            Path(__file__).parent / 'fonts' / filename,
            Path.home() / '.fonts' / filename,
            Path('/usr/share/fonts/truetype') / filename,
            Path('C:/Windows/Fonts') / filename,
            Path(f'fonts/{filename}')
        ]
        for path in paths:
            if path.exists():
                return str(path)
        return None

    def _generate_emoji(self, char: str, size: int) -> Image.Image:
        """Генерация эмодзи через Twemoji CDN"""
        try:
            # Конвертируем эмодзи в код точки Unicode
            code_point = ord(char)
            hex_code = f"{code_point:x}"
            
            # Специальная обработка вариационных последовательностей
            if unicodedata.category(char) == 'So':
                hex_code = hex_code.lstrip('0').lower()
                
            # Формируем URL для Twemoji
            url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{hex_code}.png"
            
            # Загружаем и обрабатываем изображение
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            
            emoji_img = Image.open(BytesIO(response.content)).convert("RGBA")
            return emoji_img.resize((size, size), Image.Resampling.LANCZOS)
            
        except Exception as e:
            logger.error(f"Emoji load error: {str(e)}")
            return self._create_fallback_emoji(size)

    def _create_fallback_emoji(self, size: int) -> Image.Image:
        """Резервная эмодзи-заглушка"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, size, size), fill='#FFD700')
        return img

    def _get_emoji_image(self, emoji_char: str, size: int) -> Image.Image:
        """Получение или генерация эмодзи"""
        cache_key = f"{emoji_char}_{size}"
        if cache_key not in self.emoji_cache:
            self.emoji_cache[cache_key] = self._generate_emoji(emoji_char, size)
        return self.emoji_cache[cache_key]

    def _create_gradient(self, width: int, height: int) -> Image.Image:
        """Создание градиентной подложки"""
        gradient = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(gradient)
        
        for i in range(height):
            alpha = int(255 * (1 - i/height))
            draw.line([(0, i), (width, i)], fill=(0, 0, 0, alpha))
        
        return gradient

    def _calculate_text_size(self, lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float) -> Tuple[int, int]:
        """Точный расчёт размеров текстового блока"""
        line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
        max_line_height = max(line_heights)
        total_height = int(sum([h * line_spacing for h in line_heights]))
        max_width = max(font.getlength(line) for line in lines)
        return int(max_width), int(total_height)

    def _split_long_word(self, word: str, font: ImageFont.FreeTypeFont, max_width: int, lines: List[str]):
        """Улучшенная обработка кириллицы и комбинированных строк"""
        current_part = ''
        for char in word:
            # Учитываем ширину комбинированных символов
            test_part = current_part + char
            if font.getlength(test_part) <= max_width:
                current_part = test_part
            else:
                if current_part:
                    lines.append(current_part)
                current_part = char
                
                # Экстренный случай: если символ шире max_width
                if font.getlength(char) > max_width:
                    lines.append(char)
                    current_part = ''

        if current_part:
            lines.append(current_part)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Строгий перенос только целых слов"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Проверяем ширину слова ДО добавления
            test_line = ' '.join(current_line + [word])
            test_width = font.getlength(test_line)
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                # Если слово не влезает целиком - уменьшаем шрифт
                if font.getlength(word) > max_width:
                    return self._handle_long_word(word, font, max_width)
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def _handle_long_word(self, word: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Экстренное уменьшение шрифта для длинных слов"""
        for font_size in range(font.size, 20, -2):
            new_font = self._get_best_font(font_size)
            if new_font.getlength(word) <= max_width:
                return [word]
        return [word[:15] + "…"]  # Крайний случай

    def _get_best_font(self, font_size: int) -> ImageFont.FreeTypeFont:
        """Гарантированная поддержка кириллицы"""
        fallback_fonts = [
            'arial.ttf', 
            'Roboto-Regular.ttf',
            'DejaVuSans.ttf',
            'times.ttf'
        ]
        
        for font_file in fallback_fonts:
            try:
                path = self._find_font(font_file)
                if path:
                    return ImageFont.truetype(path, font_size, encoding='unic')
            except Exception as e:
                continue
                
        return ImageFont.load_default()

    def _calculate_text_size(self, lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float) -> Tuple[int, int]:
        """Точный расчет для кириллических символов"""
        max_width = 0
        total_height = 0
        
        for line in lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            
            if line_width > max_width:
                max_width = line_width
                
            total_height += int(line_height * line_spacing)
            
        return max_width, total_height

    def _split_long_word(self, word: str, font: ImageFont.FreeTypeFont, max_width: int, lines: List[str]):
        """Разбивка слишком длинных слов"""
        current_part = ''
        for char in word:
            if font.getlength(current_part + char) <= max_width:
                current_part += char
            else:
                if current_part:
                    lines.append(current_part)
                current_part = char
        if current_part:
            lines.append(current_part)

    def _add_text_layer(self, base_image: Image.Image, text: str) -> Image.Image:
        """Финальная версия с комплексными улучшениями"""
        img = base_image.copy()
        draw = ImageDraw.Draw(img)
        
        # Параметры безопасности
        padding = 40
        max_width = img.width - 2 * padding
        max_height = img.height - 2 * padding
        line_spacing = 1.3
        min_font_size = 28
        
        # Подбор оптимального размера шрифта
        best_settings = None
        for font_size in range(72, min_font_size - 1, -2):
            font = self._get_best_font(font_size)
            lines = self._wrap_text(text, font, max_width)
            
            if not lines:
                continue
                
            text_width, text_height = self._calculate_text_size(lines, font, line_spacing)
            
            if text_width <= max_width and text_height <= max_height:
                best_settings = (font, lines, font_size)
                break

        if not best_settings:
            font = self._get_best_font(min_font_size)
            lines = self._wrap_text(text, font, max_width)
            best_settings = (font, lines, min_font_size)

        font, lines, font_size = best_settings
        
        # Расчёт позиции
        text_width, text_height = self._calculate_text_size(lines, font, line_spacing)
        x = (img.width - text_width) // 2
        y = (img.height - text_height) // 2
        
        # Фоновая подложка
        bg = Image.new('RGBA', img.size, (0, 0, 0, 120))
        img = Image.alpha_composite(img.convert('RGBA'), bg)
        draw = ImageDraw.Draw(img)
        
        # Рисование текста с контуром
        stroke_width = max(1, font_size // 25)
        line_height = font.getbbox('A')[3] * line_spacing
        
        for i, line in enumerate(lines):
            line_x = x + (max_width - font.getlength(line)) // 2
            line_y = y + i * line_height
            draw.text(
                (line_x, line_y),
                line,
                font=font,
                fill="white",
                stroke_width=stroke_width,
                stroke_fill="black"
            )

        return img
    
    def _get_contrast_color(self, image: Image.Image, text_bbox: tuple) -> tuple:
        """Определение контрастного цвета"""
        region = image.crop(text_bbox)
        np_region = np.array(region)
        if np_region.size == 0:
            return (255, 255, 255)  # Fallback
        
        avg_color = np.mean(np_region, axis=(0, 1))
        brightness = 0.299 * avg_color[0] + 0.587 * avg_color[1] + 0.114 * avg_color[2]
        return (0, 0, 0) if brightness > 127 else (255, 255, 255)

    def generate_cover(
        self,
        image_path: str,
        title: str,
        emoji: str = "✨"
    ) -> str:
        """Основная функция генерации обложки"""
        try:
            # Загрузка и обработка изображения
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                
                # Размытие фона
                blurred = img.filter(ImageFilter.GaussianBlur(10))
                
                # Добавление градиента
                gradient = self._create_gradient(*img.size)
                composite = Image.alpha_composite(
                    blurred.convert('RGBA'), 
                    gradient
                )
                
                # Добавление эмодзи
                emoji_size = min(img.size) // 5
                emoji_img = self._get_emoji_image(random.choice(emoji), emoji_size)
                composite.paste(
                    emoji_img,
                    ((img.width - emoji_size)//2, 20),
                    emoji_img
                )
                
                # Добавление текста
                final_image = self._add_text_layer(composite, title)
                
                # Сохранение
                output_dir = Path("output/covers")
                output_dir.mkdir(parents=True, exist_ok=True)
                save_path = output_dir / f"cover_{int(time.time())}.png"
                final_image.save(save_path, "PNG", quality=95)
                
                logger.success(f"Cover saved to: {save_path}")
                return str(save_path)
                
        except Exception as e:
            logger.critical(f"Cover generation failed: {str(e)}")
            return ""
        
    async def generate_first_page(
        self,
        prompt: str,
        initial_photo: str
    ) -> Optional[str]:
        """Основная функция генерации обложки."""
        try:
            # Генерация текста
            title, emoji = self.generate_clickbait_title(prompt)
            logger.debug(f"Using title: {title} {emoji}")

            return self.generate_cover(initial_photo, title, emoji), title
            
        except Exception as e:
            logger.critical("Cover generation failed: {}", str(e))
            return None, None
        
    def _get_emoji_font(self, font_size: int) -> ImageFont.FreeTypeFont:
        """Шрифты с поддержкой эмодзи"""
        emoji_fonts = [
            "Segoe UI Emoji.ttf",  # Windows
            "Apple Color Emoji.ttf",  # macOS
            "NotoColorEmoji.ttf",  # Linux
            "arial.ttf"  # Fallback
        ]
        for font_file in emoji_fonts:
            try:
                path = self._find_font(font_file)
                if path:
                    return ImageFont.truetype(path, font_size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _add_emoji(self, draw: ImageDraw.Draw, text: str, position: tuple, font_size: int):
        """Отрисовка эмодзи с правильным шрифтом"""
        emoji_font = self._get_emoji_font(font_size)
        draw.text(position, text, font=emoji_font, embedded_color=True)

    def _draw_text_with_emojis(self, draw: ImageDraw.Draw, text: str, x: int, y: int, main_font: ImageFont.FreeTypeFont, emoji_size: int):
        """Совмещение обычного текста и эмодзи"""
        current_x = x
        for char in text:
            if emoji.is_emoji(char):
                # Отрисовка эмодзи отдельным шрифтом
                self._add_emoji(draw, char, (current_x, y), emoji_size)
                current_x += emoji_size  # Примерная ширина
            else:
                # Отрисовка обычного текста
                draw.text((current_x, y), char, font=main_font)
                current_x += main_font.getlength(char)
        

def generate_first_page(prompt: str, initial_photo) -> str:
    """Генерирует обложку по текстовому описанию и исходному изображению и возвращает путь к файлу.
    
    Args:
        prompt: Текстовое описание для генерации изображения
        initial_photo: Путь до изображения для обложки
        
    Returns:
        str: Абсолютный путь к сгенерированному изображению
    """
    async def _async_generate(prompt : str, initial_photo : str) -> str:
            generator = CoverGeneratorEnhanced()
            return await generator.generate_first_page(prompt=prompt, initial_photo=initial_photo)

    try:
        return asyncio.run(_async_generate(prompt=prompt, initial_photo=initial_photo))
    except Exception as e:
        logger.error("Generation failed: {}", str(e))
        return "", ""