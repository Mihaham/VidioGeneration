"""
Модуль обработчиков административных команд

Содержит хендлеры для:
- Управления правами пользователей
- Просмотра системной статистики
- Генерации отчетов
- Управления задачами планировщика
- Работы с системными логами
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Optional

import pandas as pd
from aiogram import Bot, Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from bot.config import USER_ID
from bot.handlers.filters import AdminFilter, is_admin
from bot.handlers.keyboards import admin_panel_kb, user_main_kb
from bot.handlers.utils import (format_users_table, generate_users_dataframe,
                               get_system_stats, save_users_to_csv)
from bot.models import User
from bot.scheduler import send_scheduled_message
from database.db import async_session, get_db
from videogeneration.sdapi_cleared import AsyncSDClient

router = Router()
router.message.filter(AdminFilter())

@router.message(F.text == "👑 Админ-панель")
async def admin_panel(message: types.Message) -> None:
    """Отображает панель управления администратора.
    
    Args:
        message: Объект входящего сообщения
    """
    user_id = message.from_user.id
    logger.info("Admin panel request from user {}", user_id)
    
    try:
        await message.answer(
            text="⚙️ Панель управления администратора:",
            reply_markup=admin_panel_kb()
        )
        logger.success("Admin panel displayed for user {}", user_id)
    except Exception as exc:
        logger.error("Failed to show admin panel to user {}: {}", user_id, exc)
        await message.answer("❌ Ошибка отображения панели управления")

@router.message(F.text == "📊 Системная статистика")
async def system_stats(message: types.Message) -> None:
    """Предоставляет системную статистику в формате Markdown."""
    user_id = message.from_user.id
    logger.info("System stats request from user {}", user_id)
    
    try:
        stats = get_system_stats()
        await message.answer(f"```\n{stats}\n```", parse_mode="MarkdownV2")
        logger.success("Stats sent to user {}", user_id)
    except Exception as exc:
        logger.error("Stats error for user {}: {}", user_id, exc)
        await message.answer("❌ Ошибка получения статистики")

@router.message(F.text == "🔙 На главную")
async def back_to_main(message: types.Message) -> None:
    """Возвращает пользователя в главное меню."""
    user_id = message.from_user.id
    logger.debug("Main menu request from user {}", user_id)
    
    try:
        show_admin_buttons = await is_admin(user_id)
            
        await message.answer(
                text="Главное меню:",
                reply_markup=user_main_kb(show_admin_buttons)
            )
        logger.success("Main menu shown to user {}", user_id)
    except Exception as exc:
        logger.error("Menu error for user {}: {}", user_id, exc)
        await message.answer("❌ Ошибка отображения меню")

@router.message(F.text == "🎥 Сгенерировать видео (с загрузкой)")
@router.message(F.text == "🎥 Сгенерировать видео (без загрузки)")
async def handle_video_generation(message: types.Message, bot: Bot) -> None:
    """Обрабатывает запросы на генерацию видео."""
    user_id = message.from_user.id
    upload = "загрузкой" in message.text
    logger.info("Video generation request from user {} (upload={})", user_id, upload)
    
    try:
        await send_scheduled_message(bot=bot, user_id=USER_ID, upload=upload)
        status = "запущена" if upload else "запущена без загрузки"
        await message.answer(f"✅ Генерация видео {status}")
        logger.success("Video generation started by user {}", user_id)
    except Exception as exc:
        logger.error("Video generation failed for user {}: {}", user_id, exc)
        await message.answer("❌ Ошибка запуска генерации видео")

@router.message(Command("grant_admin"))
async def grant_admin_access(
    message: types.Message,
    command: CommandObject,
    bot: Bot
) -> None:
    """Предоставляет права администратора указанному пользователю."""
    user_id = message.from_user.id
    logger.info("Admin grant attempt by user {}", user_id)
    
    if not command.args:
        logger.warning("Empty arguments in grant_admin command")
        return await message.answer("❌ Укажите ID пользователя: /grant_admin <user_id>")
    
    try:
        target_user_id = int(command.args)
    except ValueError:
        logger.error("Invalid user ID format: {}", command.args)
        return await message.answer("❌ Некорректный формат ID пользователя")
    
    try:
        async with async_session.begin() as session:
            result = await session.execute(
                select(User)
                .where(User.telegram_id == target_user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning("User {} not found", target_user_id)
                return await message.answer("❌ Пользователь не найден")
            
            if user.is_admin:
                logger.info("User {} already admin", target_user_id)
                return await message.answer("ℹ️ Пользователь уже имеет права администратора")
            
            user.is_admin = True
            await session.commit()
            
            await message.answer(f"✅ Пользователь @{user.username} получил права администратора")
            await bot.send_message(
                chat_id=target_user_id,
                text="🎉 Вам выданы права администратора!"
            )
            logger.success("Admin rights granted to user {} by {}", target_user_id, user_id)
    except Exception as exc:
        logger.error("Admin grant error: {}", exc)
        await message.answer("❌ Ошибка выполнения команды")

@router.message(F.text == "👥 Пользователи")
async def handle_users_list(message: Message) -> None:
    """Генерирует и отправляет список пользователей в виде таблицы и CSV-файла."""
    user_id = message.from_user.id
    logger.info("Users list request from user {}", user_id)
    csv_path: Optional[Path] = None
    
    try:
        async with async_session() as session:
            result = await session.execute(
                select(User).order_by(User.created_at.desc())
            )
            users = result.scalars().all()
            
            if not users:
                return await message.answer("📭 В системе пока нет пользователей")
            
            table = await format_users_table(users)
            await message.answer(table, parse_mode="MarkdownV2")
            
            try:
                df = generate_users_dataframe(users)
                csv_path = save_users_to_csv(df)
                
                await message.answer_document(
                    document=FSInputFile(csv_path, filename="users.csv"),
                    caption="📊 Полный список пользователей"
                )
                logger.success("CSV report sent to user {}", user_id)
            except pd.errors.EmptyDataError:
                logger.error("Empty users dataframe")
                await message.answer("❌ Нет данных для экспорта")
    except Exception as exc:
        logger.error("Users list error: {}", exc)
        await message.answer("❌ Ошибка получения списка пользователей")
    finally:
        if csv_path and Path(csv_path).exists():
            Path(csv_path).unlink(missing_ok=True)
            logger.debug("Temporary CSV file removed")

@router.message(F.text == "📝 Логи действий")
async def logs_handler(message: types.Message) -> None:
    """Обрабатывает запросы на получение логов работы системы."""
    user_id = message.from_user.id
    logger.info("Logs request from user {}", user_id)
    
    log_file = Path("logs/bot.log")
    tmp_path: Optional[Path] = None
    
    try:
        if not log_file.exists():
            raise FileNotFoundError("Log file not found")
        
        since_time = datetime.now() - timedelta(days=3)
        stats = defaultdict(int)
        error_logs = []
        buffer = []
        
        with log_file.open(encoding="utf-8") as f:
            for line in f:
                if len(buffer) >= 1000:
                    buffer.pop(0)
                buffer.append(line)
                
                try:
                    log_time_str = line.split(" | ")[0]
                    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S")
                    log_level = line.split(" | ")[1].strip()
                    
                    if log_time >= since_time:
                        stats[log_level] += 1
                        if log_level in {"ERROR", "CRITICAL"}:
                            error_logs.append(line)
                except Exception:
                    continue
        
        with NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp:
            tmp.writelines(buffer[-1000:])
            tmp_path = Path(tmp.name)
        
        stats_text = (
            "📊 Статистика логов за последние 3 дня:\n"
            + "\n".join(f"• {k}: {v}" for k, v in stats.items())
            + (f"\n\n🚨 Последние ошибки:\n{''.join(error_logs[-5])}" if error_logs else "")
        )
        
        await message.answer(f"<code>{stats_text}</code>", parse_mode="HTML")
        await message.answer_document(
            document=FSInputFile(tmp_path, filename="recent.log"),
            caption="📎 Последние логи системы"
        )
        logger.success("Logs sent to user {}", user_id)
    except FileNotFoundError:
        logger.error("Log file not found")
        await message.answer("⚠️ Файл логов не найден")
    except Exception as exc:
        logger.error("Log processing error: {}", exc)
        await message.answer(f"❌ Ошибка обработки логов: {exc}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)