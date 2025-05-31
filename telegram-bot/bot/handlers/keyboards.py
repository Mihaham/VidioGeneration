"""
Модуль управления клавиатурами бота

Содержит фабричные функции для создания:
- Основной пользовательской клавиатуры
- Административной панели управления
"""

from typing import List, Tuple

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Константы текстов кнопок
BTN_MEMORY_STATS = "📊 Статистика памяти"
BTN_ADMIN_PANEL = "👑 Админ-панель"
BTN_SYS_STATS = "📊 Системная статистика"
BTN_ACTION_LOGS = "📝 Логи действий"
BTN_USERS_LIST = "👥 Пользователи"
BTN_MAIN_MENU = "🔙 На главную"
BTN_GEN_VIDEO_UPLOAD = "🎥 Сгенерировать видео (с загрузкой)"
BTN_GEN_VIDEO_LOCAL = "🎥 Сгенерировать видео (без загрузки)"
BTN_EXCEL_LIST = "📚 Экспорт в Excel"
BTN_CSV_LISTS = "📚 Экспорт в CSV файлы"
BTN_GENERATE = "💫 Хочу Сгенерировать что-нибудь..."
BTN_SOUND_GENERATION = "🔊 Хочу преобразовать текст в аудио!"

def user_main_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру пользователя с учетом прав администратора.
    
    Args:
        is_admin: Флаг наличия административных прав
        
    Returns:
        ReplyKeyboardMarkup: Настроенная клавиатура
    """
    # Базовые кнопки для всех пользователей
    base_buttons: List[Tuple[KeyboardButton]] = [
        (KeyboardButton(text=BTN_MEMORY_STATS),)
    ]
    
    # Кнопки администратора
    admin_buttons: List[Tuple[KeyboardButton]] = [
        (KeyboardButton(text=BTN_ADMIN_PANEL),)
    ]
    
    # Компоновка клавиатуры
    keyboard_layout = base_buttons
    if is_admin:
        keyboard_layout += admin_buttons

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

def admin_panel_kb() -> ReplyKeyboardMarkup:
    """Генерирует клавиатуру административной панели.
    
    Returns:
        ReplyKeyboardMarkup: Клавиатура с инструментами управления
    """
    # Группировка кнопок по функциональности
    management_buttons: List[Tuple[KeyboardButton]] = [
        (KeyboardButton(text=BTN_SYS_STATS),),
        (KeyboardButton(text=BTN_ACTION_LOGS),),
        (KeyboardButton(text=BTN_USERS_LIST),),
        (KeyboardButton(text=BTN_EXCEL_LIST),),
        (KeyboardButton(text=BTN_CSV_LISTS),),
        (KeyboardButton(text=BTN_GENERATE),),

    ]
    
    video_controls: List[Tuple[KeyboardButton]] = [
        (KeyboardButton(text=BTN_GEN_VIDEO_UPLOAD),),
        (KeyboardButton(text=BTN_GEN_VIDEO_LOCAL),)
    ]
    
    navigation_buttons: List[Tuple[KeyboardButton]] = [
        (KeyboardButton(text=BTN_MAIN_MENU),)
    ]

    return ReplyKeyboardMarkup(
        keyboard=[
            *management_buttons,
            *video_controls,
            *navigation_buttons
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите команду управления",
        selective=True
    )