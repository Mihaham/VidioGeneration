import tempfile
import zipfile
from pathlib import Path
from typing import List, Type

import pandas as pd
from aiogram.types import Message, FSInputFile
from aiogram import Router, F
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeMeta
from loguru import logger

# Импортируйте ваши зависимости
from bot.models import Base  # Ваша декларативная база
from bot.handlers.filters import AdminFilter
from database.db import async_session  # Асинхронная сессия
from bot.handlers.keyboards import BTN_EXCEL_LIST, BTN_CSV_LISTS

router = Router()
router.message.filter(AdminFilter())


def get_all_models() -> List[Type[DeclarativeMeta]]:
    """Возвращает список всех ORM-моделей с таблицами."""
    return [
        mapper.class_
        for mapper in Base.registry.mappers
        if hasattr(mapper.class_, '__tablename__')
    ]

def model_to_dataframe(model_class: Type[DeclarativeMeta], records: list) -> pd.DataFrame:
    """Конвертирует записи ORM в DataFrame."""
    return pd.DataFrame(
        {col.name: [getattr(r, col.name) for r in records]
        for col in model_class.__table__.columns}
    )


@router.message(F.text == BTN_CSV_LISTS)
async def export_all_tables_csv(message: Message):
    """Экспорт всех таблиц в ZIP-архив с CSV файлами."""
    user_id = message.from_user.id
    logger.info("Запрос на экспорт CSV от пользователя {}", user_id)

    try:
        models = get_all_models()
        if not models:
            return await message.answer("❌ Нет доступных таблиц")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            zip_file = tmp_path / "all_tables.zip"

            with zipfile.ZipFile(zip_file, 'w') as zipf:
                for model in models:
                    async with async_session() as session:
                        result = await session.execute(select(model))
                        records = result.scalars().all()

                        df = model_to_dataframe(model, records)
                        csv_path = tmp_path / f"{model.__tablename__}.csv"
                        df.to_csv(csv_path, index=False)
                        zipf.write(csv_path, arcname=csv_path.name)

            await message.answer_document(
                FSInputFile(zip_file, filename="tables.zip"),
                caption="📦 Все таблицы в CSV"
            )
            logger.success("CSV архив отправлен пользователю {}", user_id)

    except Exception as e:
        logger.error("Ошибка: {}", e)
        await message.answer("❌ Ошибка экспорта")


@router.message(F.text == BTN_EXCEL_LIST)
async def export_all_tables_excel(message: Message):
    """Экспорт всех таблиц в многостраничный Excel."""
    user_id = message.from_user.id
    logger.info("Запрос на экспорт Excel от пользователя {}", user_id)
    excel_path = None

    try:
        models = get_all_models()
        if not models:
            return await message.answer("❌ Нет доступных таблиц")

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            excel_path = Path(tmp.name)

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for model in models:
                    async with async_session() as session:
                        result = await session.execute(select(model))
                        records = result.scalars().all()

                        df = model_to_dataframe(model, records)
                        df.to_excel(
                            writer,
                            sheet_name=model.__tablename__[:31],
                            index=False
                        )

            await message.answer_document(
                FSInputFile(excel_path, filename="tables.xlsx"),
                caption="📊 Все таблицы в Excel"
            )
            logger.success("Excel файл отправлен пользователю {}", user_id)

    except Exception as e:
        logger.error("Ошибка: {}", e)
        await message.answer("❌ Ошибка экспорта")
    finally:
        if excel_path and excel_path.exists():
            excel_path.unlink()
