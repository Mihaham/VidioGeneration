import psutil
import platform
from datetime import datetime
import GPUtil
from typing import Optional
from loguru import logger
import tempfile
import os
from bot.models import User
import pandas as pd
from textwrap import dedent

def bytes_to_gb(bytes: int) -> float:
    return bytes / (1024 ** 3)

def get_gpu_info() -> Optional[str]:
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
    except Exception as e:
        print(f"⚠️ Error getting GPU info: {e}")
        return None

def get_system_stats() -> str:
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    cpu_cores = psutil.cpu_count(logical=False)
    cpu_threads = psutil.cpu_count(logical=True)
    
    # Memory
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    # Disk
    disk = psutil.disk_usage('/')
    
    # Network
    net_io = psutil.net_io_counters()
    
    # Temperatures
    try:
        temps = psutil.sensors_temperatures()
    except AttributeError:
        temps = None
    
    # Boot Time
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    
    # GPU Info
    gpu_stats = get_gpu_info()
    
    # Форматирование
    stats = [
        "🖥️ *System Statistics* 🖥️",
        f"⏰ Boot Time: `{boot_time.strftime('%Y-%m-%d %H:%M:%S')}`",
        f"🔧 OS: `{platform.system()} {platform.release()}`",
        "",
        "🔥 *CPU Usage* 🔥",
        f"▪️ Total Usage: `{cpu_percent}%`",
        f"▪️ Cores: `{cpu_cores}` | Threads: `{cpu_threads}`",
        f"▪️ Frequency: `{cpu_freq.current:.2f} MHz`" if cpu_freq else "",
        "",
        "💾 *Memory Usage* 💾",
        f"▪️ Total: `{bytes_to_gb(mem.total):.2f} GB`",
        f"▪️ Used: `{bytes_to_gb(mem.used):.2f} GB` (`{mem.percent}%`)",
        f"▪️ Available: `{bytes_to_gb(mem.available):.2f} GB`",
        f"🔄 Swap: `{bytes_to_gb(swap.used):.2f}/{bytes_to_gb(swap.total):.2f} GB` (`{swap.percent}%`)",
        "",
        "💽 *Disk Usage* 💽",
        f"▪️ Total: `{bytes_to_gb(disk.total):.2f} GB`",
        f"▪️ Used: `{bytes_to_gb(disk.used):.2f} GB` (`{disk.percent}%`)",
        f"▪️ Free: `{bytes_to_gb(disk.free):.2f} GB`",
        "",
        "🌐 *Network* 🌐",
        f"📤 Sent: `{bytes_to_gb(net_io.bytes_sent):.2f} GB`",
        f"📥 Received: `{bytes_to_gb(net_io.bytes_recv):.2f} GB`",
    ]
    
    # GPU
    if gpu_stats:
        stats.extend(["", "🎮 *GPU Info* 🎮", gpu_stats])
    
    # Temperature
    if temps:
        stats.extend(["", "🌡️ *Temperatures* 🌡️"])
        for name, entries in temps.items():
            for entry in entries:
                stats.append(f"▪️ {entry.label or name}: `{entry.current}°C`")
    
    return "\n".join(stats)

async def format_users_table(users: list[User]) -> str:
    """Форматирует список пользователей в красивую текстовую таблицу"""
    # Заголовки столбцов
    headers = ["ID", "Telegram ID", "Username", "Admin", "Created", "Last Active"]
    
    # Максимальные ширины столбцов
    widths = [4, 12, 15, 5, 19, 19]
    
    # Форматирование заголовка
    header = "|".join(f" {h.ljust(w)} " for h, w in zip(headers, widths))
    separator = "+".join("-" * (w + 2) for w in widths)
    
    # Форматирование строк данных
    rows = []
    for user in users:
        created = user.created_at.strftime("%Y-%m-%d %H:%M")
        last_active = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "Never"
        
        row = (
            str(user.id).ljust(widths[0]),
            str(user.telegram_id).ljust(widths[1]),
            (user.username or "-")[:widths[2]-1].ljust(widths[2]),
            "✓" if user.is_admin else "✗".center(widths[7]),
            created.ljust(widths[4]),
            last_active.ljust(widths[5])
        )
        rows.append("|".join(f" {cell} " for cell in row))
    
    # Сборка полной таблицы
    return dedent(f"""
        ``` 
        Пользователи системы ({len(users)})
        {separator}
        {header}
        {separator}
        {chr(10).join(rows)}
        {separator}
        ```
    """).strip()

def generate_users_dataframe(users: list[User]) -> pd.DataFrame:
    """Создает DataFrame с информацией о пользователях"""
    logger.debug("Создание DataFrame пользователей")
    
    data = []
    for user in users:
        data.append({
            "ID": user.id,
            "Telegram ID": user.telegram_id,
            "Username": user.username or "-",
            "Admin": "Да" if user.is_admin else "Нет",
            "Created At": user.created_at.strftime("%Y-%m-%d %H:%M"),
            "Last Activity": user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "Никогда"
        })
    
    df = pd.DataFrame(data)
    logger.success(f"DataFrame создан с {len(df)} записями")
    return df

def save_users_to_csv(df: pd.DataFrame) -> str:
    """Сохраняет DataFrame в CSV файл и возвращает путь к файлу"""
    try:
        # Создаем временный файл
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        
        # Сохраняем в CSV с правильной кодировкой
        df.to_csv(path, index=False, encoding='utf-8-sig')
        logger.info(f"Данные сохранены в CSV файл: {path}")
        return path
        
    except Exception as e:
        logger.error(f"Ошибка сохранения CSV: {str(e)}")
        raise
