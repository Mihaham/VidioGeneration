from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.models import User
from database.db import get_db
from bot.handlers.keyboards import admin_panel_kb, user_main_kb
from videogeneration.sdapi_cleared import AsyncSDClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging
from aiogram import F, types
from aiogram.filters import Command, CommandObject
from sqlalchemy import update
from database.db import async_session
from bot.scheduler import send_scheduled_message
from bot.config import USER_ID
from bot.handlers.utils import get_system_stats, format_users_table, generate_users_dataframe, save_users_to_csv
from aiogram import Router, types, F
from aiogram.types import Message, FSInputFile
from sqlalchemy import select
from database.db import async_session
from bot.models import User
from bot.handlers.filters import is_admin, AdminFilter
from datetime import datetime
from loguru import logger
from bot.handlers.keyboards import user_main_kb
import pandas as pd
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
from collections import defaultdict

router = Router()

@router.message(F.text == "👑 Админ-панель", AdminFilter())
async def admin_panel(message: types.Message):
    """Хендлер админ-панели"""
    logger.info(f"Admin panel accessed by {message.from_user.id}")
    try:
        await message.answer(
            "⚙️ Панель управления администратора:",
            reply_markup=admin_panel_kb()
        )
        logger.success(f"Admin panel shown to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error showing admin panel: {e}")
        await message.answer("❌ Ошибка отображения панели")

@router.message(F.text == "📊 Системная статистика", AdminFilter())
async def system_stats(message: types.Message):
    logger.info(f"System stats requested by {message.from_user.id}")
    try:
        response = get_system_stats()
        logger.success(f"Stats generated for {message.from_user.id}")
        await message.answer(f"```\n{response}\n```", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Stats error for {message.from_user.id}: {e}")
        await message.answer("❌ Ошибка получения статистики")

@router.message(F.text == "🔙 На главную", AdminFilter())
async def back_to_main(message: types.Message):
    logger.debug(f"Back to main menu by {message.from_user.id}")
    try:
        is_adm = await is_admin(message.from_user.id)
        logger.info(f"Admin check for {message.from_user.id}: {is_adm}")
        await message.answer(
            "Главное меню:",
            reply_markup=user_main_kb(is_adm)
        )
        logger.success(f"Main menu shown to {message.from_user.id}")
    except Exception as e:
        logger.error(f"Menu error for {message.from_user.id}: {e}")

@router.message(F.text == "🎥 Сгенерируй еще видео на ютуб", AdminFilter())
async def generate_video(message: types.Message, bot: Bot):
    logger.info(f"Video generation (upload) requested by {message.from_user.id}")
    try:
        await send_scheduled_message(bot=bot, user_id=USER_ID)
        logger.success(f"Video generation started by {message.from_user.id}")
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        await message.answer("❌ Ошибка генерации видео")

@router.message(F.text == "🎥 Сгенерируй еще видео (НЕ заливать)", AdminFilter())
async def generate_video_no_upload(message: types.Message, bot: Bot):
    logger.info(f"Video generation (no upload) by {message.from_user.id}")
    try:
        await send_scheduled_message(bot=bot, user_id=USER_ID, upload=False)
        logger.success(f"Video generated without upload by {message.from_user.id}")
    except Exception as e:
        logger.error(f"Video gen (no upload) error: {e}")
        await message.answer("❌ Ошибка генерации видео")

@router.message(Command("grant_admin"), AdminFilter())
async def grant_admin_access(message: types.Message, command: CommandObject):
    logger.info(f"Grant admin attempt by {message.from_user.id}")
    if not command.args:
        logger.warning("Empty args in grant_admin")
        return await message.answer("❌ Укажите ID пользователя: /grant_admin <user_id>")
    
    try:
        target_user_id = int(command.args)
        logger.debug(f"Parsed target user ID: {target_user_id}")
    except ValueError:
        logger.error(f"Invalid user ID format: {command.args}")
        return await message.answer("❌ ID должен быть числом")
    
    try:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == target_user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {target_user_id} not found")
                return await message.answer("❌ Пользователь не найден")
            
            if user.is_admin:
                logger.info(f"User {target_user_id} already admin")
                return await message.answer("ℹ️ Пользователь уже администратор")
            
            user.is_admin = True
            await session.commit()
            logger.success(f"Admin granted: {message.from_user.id} -> {target_user_id}")
            
            await message.answer(f"✅ Пользователь @{user.username} получил права администратора")
            await message.bot.send_message(
                chat_id=target_user_id,
                text="🎉 Вам выданы права администратора!"
            )
    except Exception as e:
        logger.opt(exception=True).error(f"Admin grant error: {str(e)}")
        await message.answer("❌ Ошибка при выполнении команды")

@router.message(F.text == "👥 Пользователи", AdminFilter())
async def handle_users_list(message: Message):
    """Хендлер для отображения списка пользователей и отправки CSV"""
    logger.info(f"Users list requested by {message.from_user.id}")
    csv_path = None
    try:
        async with async_session() as session:
            result = await session.execute(select(User).order_by(User.created_at.desc()))
            users = result.scalars().all()
            
            if not users:
                logger.info("Empty users list")
                return await message.answer("📭 В системе пока нет пользователей")
            
            logger.debug(f"Fetched {len(users)} users from DB")
            
            table = await format_users_table(users)
            await message.answer(
                table,
                parse_mode="MarkdownV2",
                reply_markup=user_main_kb(is_admin=is_admin(message.from_user.id)))
            
            try:
                df = generate_users_dataframe(users)
                csv_path = save_users_to_csv(df)
                
                await message.answer_document(
                    document=FSInputFile(csv_path, filename="users.csv"),
                    caption="📊 Полный список пользователей"
                )
                logger.success(f"CSV sent to {message.from_user.id}")
                
            except pd.errors.EmptyDataError:
                logger.error("Empty DataFrame in CSV generation")
                await message.answer("❌ Нет данных для экспорта")
            except Exception as csv_error:
                logger.opt(exception=True).error(f"CSV error: {csv_error}")
                await message.answer("❌ Ошибка при генерации файла")
    except Exception as e:
        logger.opt(exception=True).critical(f"Critical error: {e}")
        await message.answer("⚠️ Произошла внутренняя ошибка при обработке запроса")
        
    finally:
        if csv_path and os.path.exists(csv_path):
            os.remove(csv_path)
            logger.debug(f"Temp file removed: {csv_path}")

@router.message(F.text == "📝 Логи действий", AdminFilter())
async def logs_handler(message: types.Message):
    logger.info(f"Logs requested by {message.from_user.id}")
    log_file = Path("logs/bot.log")
    
    try:
        # Читаем все логи за последние 3 дня
        since_time = datetime.now() - timedelta(days=3)
        stats = defaultdict(int)
        error_logs = []
        recent_logs = []
        
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    # Парсим дату и уровень лога
                    log_time_str = line.split(" | ")[0]
                    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S")
                    log_level = line.split(" | ")[1].strip()
                    
                    if log_time >= since_time:
                        recent_logs.append(line)
                        stats[log_level] += 1
                        
                        if log_level in ["ERROR", "CRITICAL"]:
                            error_logs.append(line)
                            
                except Exception as e:
                    #logger.warning(f"Error parsing log line: {e}")
                    continue

        # Создаем временный файл с последними 1000 строк
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".log") as tmp:
            tmp.writelines(recent_logs[:])
            tmp_path = tmp.name

        # Формируем статистику
        stats_text = "📊 Статистика логов за последние 3 дня:\n"
        stats_text += "\n".join([f"• {level}: {count}" for level, count in stats.items()])
        
        if error_logs:
            stats_text += f"\n\n🚨 Ошибок: {len(error_logs)}\n"
            stats_text += "Последние 5 ошибок:\n" + "".join(error_logs[-5:])
        else:
            stats_text += "\n\n✅ Ошибок не обнаружено"

        # Отправляем статистику
        await message.answer(
            f"<code>{stats_text}</code>", 
            parse_mode="HTML"
        )

        # Отправляем файл с логами
        await message.answer_document(
            types.FSInputFile(tmp_path, filename=f"logs_{datetime.now().strftime('%Y-%m-%d')}.log"),
            caption="📎 Последние логи"
        )
        
        logger.success(f"Logs sent to {message.from_user.id}")

    except FileNotFoundError:
        logger.error("Log file not found")
        await message.answer("⚠️ Файл логов не найден")
    except Exception as e:
        logger.opt(exception=True).error(f"Logs error: {e}")
        await message.answer(f"🚫 Ошибка при обработке логов: {str(e)}")
    finally:
        if 'tmp_path' in locals() and Path(tmp_path).exists():
            Path(tmp_path).unlink()