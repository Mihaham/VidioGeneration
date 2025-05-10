"""
Модуль утилит для работы с системной статистикой и пользователями

Содержит функции для:
- Сбора информации о системе и оборудовании
- Форматирования данных пользователей
- Экспорта данных в структурированные форматы
"""

import os
import platform
from datetime import datetime
from textwrap import dedent
from typing import List, Optional, Dict, Any
import tempfile

import GPUtil
import pandas as pd
import psutil
from loguru import logger

from bot.models import User


def bytes_to_gb(bytes_value: int) -> float:
    """Конвертирует байты в гигабайты.
    
    Args:
        bytes_value: Значение в байтах
        
    Returns:
        Значение в гигабайтах с плавающей точкой
    """
    return bytes_value / (1024 ** 3)


def get_gpu_info() -> Optional[str]:
    """Получает и форматирует информацию о GPU.
    
    Returns:
        Строка с информацией о видеокартах или None при ошибке
    """
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
            
        gpu_info = []
        for i, gpu in enumerate(gpus):
            gpu_info.append(
                f"🎮 GPU {i} ({gpu.name}):\n"
                f"   ▪️Load: {gpu.load*100:.1f}% | 🌡️Temp: {gpu.temperature}°C\n"
                f"   ▪️VRAM: {gpu.memoryUsed:.1f}/{gpu.memoryTotal:.1f} GB"
            )
        return "\n".join(gpu_info)
    except Exception as exc:
        logger.error(f"Ошибка получения данных GPU: {exc}")
        return None


def get_system_stats() -> str:
    """Собирает и форматирует комплексную статистику системы.
    
    Returns:
        Строка с отформатированной статистикой в Markdown
    """
    stats: List[str] = []
    
    try:
        # CPU Information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        cpu_cores = psutil.cpu_count(logical=False) or 0
        cpu_threads = psutil.cpu_count(logical=True) or 0

        # Memory Information
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk Information
        disk = psutil.disk_usage('/')

        # Network Information
        net_io = psutil.net_io_counters()

        # System Information
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        os_info = f"{platform.system()} {platform.release()}"

        # Формирование базовой статистики
        stats = [
            "🖥️ *System Statistics* 🖥️",
            f"⏰ Boot Time: `{boot_time.strftime('%Y-%m-%d %H:%M:%S')}`",
            f"🔧 OS: `{os_info}`",
            "",
            "🔥 *CPU Usage* 🔥",
            f"▪️ Total Usage: `{cpu_percent}%`",
            f"▪️ Cores: `{cpu_cores}` | Threads: `{cpu_threads}`",
            f"▪️ Frequency: `{cpu_freq.current:.2f} MHz`" if cpu_freq else "",
        ]

        # Добавление секций данных
        sections: List[Dict[str, Any]] = [
            {
                "title": "💾 Memory Usage",
                "items": [
                    ("Total", mem.total),
                    ("Used", mem.used),
                    ("Available", mem.available)
                ]
            },
            {
                "title": "💽 Disk Usage",
                "items": [
                    ("Total", disk.total),
                    ("Used", disk.used),
                    ("Free", disk.free)
                ]
            },
            {
                "title": "🌐 Network",
                "items": [
                    ("Sent", net_io.bytes_sent),
                    ("Received", net_io.bytes_recv)
                ]
            }
        ]

        # Обработка секций
        for section in sections:
            stats.extend(["", f"{section['title']} {section['title'][0]}"])
            for label, value in section["items"]:
                stats.append(
                    f"▪️ {label}: `{bytes_to_gb(value):.2f} GB`"
                )

        # GPU Information
        if gpu_stats := get_gpu_info():
            stats.extend(["", "🎮 *GPU Info* 🎮", gpu_stats])

        # Temperature Information
        if temps := psutil.sensors_temperatures():
            stats.extend(["", "🌡️ *Temperatures* 🌡️"])
            for name, entries in temps.items():
                for entry in entries:
                    stats.append(f"▪️ {entry.label or name}: `{entry.current}°C`")

    except Exception as exc:
        logger.error(f"Ошибка сбора статистики: {exc}")
        return "⚠️ Ошибка получения системной информации"

    return "\n".join(filter(None, stats))


async def format_users_table(users: List[User]) -> str:
    """Форматирует список пользователей в текстовую таблицу.
    
    Args:
        users: Список объектов User
        
    Returns:
        Отформатированная таблица в Markdown
    """
    logger.info("Форматирование таблицы пользователей")
    
    columns = [
        ("ID", 4, lambda u: str(u.id)),
        ("Telegram ID", 12, lambda u: str(u.telegram_id)),
        ("Username", 15, lambda u: (u.username or "-")[:14]),
        ("Admin", 5, lambda u: "✓" if u.is_admin else "✗"),
        ("Created", 19, lambda u: u.created_at.strftime("%Y-%m-%d %H:%M")),
        ("Last Active", 19, lambda u: u.last_activity.strftime("%Y-%m-%d %H:%M") 
            if u.last_activity else "Never")
    ]

    # Создание заголовков
    header = "|".join(f" {col[0].ljust(col[1])} " for col in columns)
    separator = "+".join("-" * (col[1] + 2) for col in columns)
    
    # Генерация строк
    rows = []
    for user in users:
        row = "|".join(
            f" {str(col[2](user)).ljust(col[1])} " 
            for col in columns
        )
        rows.append(row)
        
    data = "\n".join(rows)

    return dedent(f"""
        ```
        Пользователи системы ({len(users)})
        {separator}
        {header}
        {separator}
        {data}
        {separator}
        ```
    """).strip()


def generate_users_dataframe(users: List[User]) -> pd.DataFrame:
    """Генерирует DataFrame из списка пользователей.
    
    Args:
        users: Список объектов User
        
    Returns:
        DataFrame с данными пользователей
    """
    logger.info("Создание DataFrame для {} пользователей", len(users))
    
    data = [{
        "ID": user.id,
        "Telegram ID": user.telegram_id,
        "Username": user.username or "-",
        "Admin": "Да" if user.is_admin else "Нет",
        "Created At": user.created_at.strftime("%Y-%m-%d %H:%M"),
        "Last Activity": user.last_activity.strftime("%Y-%m-%d %H:%M") 
            if user.last_activity else "Никогда"
    } for user in users]

    return pd.DataFrame(data)


def save_users_to_csv(df: pd.DataFrame) -> str:
    """Сохраняет DataFrame в CSV файл.
    
    Args:
        df: DataFrame для сохранения
        
    Returns:
        Путь к сохраненному файлу
        
    Raises:
        IOError: При ошибках записи файла
    """
    fd, path = None, None
    try:
        fd, path = tempfile.mkstemp(suffix=".csv")
        df.to_csv(path, index=False, encoding='utf-8-sig')
        logger.success("CSV сохранен: {}", path)
        return path
    except Exception as exc:
        logger.error("Ошибка сохранения CSV: {}", exc)
        raise IOError("Ошибка записи CSV файла") from exc
    finally:
        if fd:
            os.close(fd)