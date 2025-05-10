from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def user_main_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        #[KeyboardButton(text="🖼 Сгенерировать изображение")],
        [KeyboardButton(text="📊 Статистика памяти")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="👑 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_panel_kb() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="📊 Системная статистика")],
        [KeyboardButton(text="📝 Логи действий")],
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="🔙 На главную")],
        [KeyboardButton(text="🎥 Сгенерируй еще видео на ютуб")],
        [KeyboardButton(text="🎥 Сгенерируй еще видео (НЕ заливать)")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)