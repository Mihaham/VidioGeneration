"""
Модуль определения моделей базы данных

Содержит ORM-модели для:
- Пользователей бота (User)
- Сообщений пользователей (Message)
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей"""
    pass

class User(Base):
    """Модель пользователя Telegram бота
    
    Attributes:
        telegram_id: Уникальный идентификатор пользователя в Telegram
        username: Имя пользователя (опционально)
        is_admin: Флаг администратора системы
        created_at: Дата создания записи
        last_activity: Последняя активность пользователя
    """
    
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, 
        unique=True,
        index=True,
        comment="Уникальный Telegram ID пользователя"
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50), 
        comment="Имя пользователя в Telegram"
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, 
        default=False,
        nullable=False,
        comment="Флаг администраторских прав"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        comment="Дата регистрации пользователя"
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Время последней активности"
    )

    messages: Mapped[List[Message]] = relationship(
        "Message", 
        back_populates="user",
        cascade="all, delete-orphan"
    )

    image_requests: Mapped[List[ImageGenerationRequest]] = relationship(
        "ImageGenerationRequest",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, "
            f"telegram_id={self.telegram_id}, "
            f"username='{self.username}', "
            f"is_admin={self.is_admin})>"
        )

class Message(Base):
    """Модель сообщения пользователя
    
    Attributes:
        text: Текст сообщения
        created_at: Дата создания сообщения
        user_id: Связь с пользователем
    """
    
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(
        Text,
        comment="Текст сообщения пользователя"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        index=True,
        comment="Дата создания сообщения"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete="CASCADE"),
        index=True,
        comment="Внешний ключ к пользователю"
    )

    user: Mapped[User] = relationship(
        User, 
        back_populates="messages",
        lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, "
            f"user_id={self.user_id}, "
            f"created_at={self.created_at.isoformat()})>"
        )


class ImageGenerationRequest(Base):
    """Модель запроса на генерацию изображения"""

    __tablename__ = 'image_requests'

    class Statuses:
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, comment="Основной промпт для генерации")
    negative_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Нежелательные элементы в изображении"
    )
    width: Mapped[int] = mapped_column(
        Integer, default=512,
        comment="Ширина изображения"
    )
    height: Mapped[int] = mapped_column(
        Integer, default=512,
        comment="Высота изображения"
    )
    n_iter: Mapped[int] = mapped_column(
        Integer, default=1,
        comment="Количество изображений"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=Statuses.PENDING,
        comment="Статус обработки запроса"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow,
        comment="Дата создания запроса"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
        comment="Дата последнего обновления"
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.telegram_id', ondelete="CASCADE"),
        index=True,
        comment="Связь с пользователем"
    )

    user: Mapped[User] = relationship(User, back_populates="image_requests")