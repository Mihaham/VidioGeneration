from aiogram import BaseMiddleware, types
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import Any, Dict, Callable, Awaitable, Optional
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from bot.models import User, Event, Message
from database.db import async_session


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        event_type = event.__class__.__name__
        logger.info(f"Processing {event_type} event")

        async with async_session.begin() as session:
            logger.debug("Database session acquired")

            try:
                # Извлекаем реальное событие из Update
                real_event = self.extract_real_event(event)
                user = await self.update_user(real_event, session)

                if user:
                    logger.debug(f"Processing user: {user.telegram_id}")
                    await self.save_event(real_event, session, user)

                    if isinstance(real_event, types.Message):
                        await self.save_message(real_event, session, user)
                else:
                    logger.warning(
                        "Event doesn't contain user information",
                        event_type=real_event.__class__.__name__ if real_event else None
                    )

            except Exception as e:
                logger.error(f"Error processing event: {e}")
                await session.rollback()
            else:
                try:
                    await session.commit()
                    logger.debug("Transaction committed successfully")
                except SQLAlchemyError as e:
                    logger.error(f"Commit failed: {e}")
                    await session.rollback()
            finally:
                await session.close()
                logger.debug("Session closed")

        return await handler(event, data)

    def extract_real_event(self, event: TelegramObject) -> Optional[TelegramObject]:
        """Извлекает вложенное событие из Update"""
        if isinstance(event, Update):
            # Проверяем все возможные типы событий в Update
            for attr in [
                'message', 'edited_message', 'channel_post',
                'edited_channel_post', 'callback_query',
                'shipping_query', 'pre_checkout_query',
                'poll', 'poll_answer', 'my_chat_member',
                'chat_member', 'chat_join_request'
            ]:
                if value := getattr(event, attr, None):
                    return value
        return event

    async def update_user(self, event: Optional[TelegramObject], session: AsyncSession) -> Optional[User]:
        if not event or not hasattr(event, 'from_user'):
            return None

        telegram_user = event.from_user
        logger.debug(f"Updating user: {telegram_user.id}")

        try:
            # Используем правильный запрос для поиска по telegram_id
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_user.id))
            user = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"User lookup failed: {repr(e)}")
            return None

        if user:
            logger.info(f"Existing user: {user.telegram_id}")
            updates = []

            if user.last_activity != datetime.utcnow():
                updates.append("last_activity")
                user.last_activity = datetime.utcnow()

            if telegram_user.username != user.username:
                updates.append("username")
                logger.info(
                    f"Updating username for {user.telegram_id}",
                    old=user.username,
                    new=telegram_user.username
                )
                user.username = telegram_user.username

            if updates:
                logger.debug(f"User updates: {', '.join(updates)}")
        else:
            logger.info(f"Creating new user: {telegram_user.id}")
            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                last_activity=datetime.utcnow()
            )
            session.add(user)
            logger.success(f"New user created: {telegram_user.id}")

        return user

    async def save_event(self, event: TelegramObject, session: AsyncSession, user: User):
        try:
            event_record = Event(
                event_type=event.__class__.__name__,
                details=self.extract_event_details(event),
                user=user,
                created_at=datetime.utcnow()
            )
            session.add(event_record)
            logger.debug(f"Event recorded: {event.__class__.__name__} for user {user.telegram_id}")
        except Exception as e:
            logger.error(f"Failed to save event: {e}")

    async def save_message(self, message: types.Message, session: AsyncSession, user: User):
        try:
            message_text = message.text or message.caption
            message_date = message.date.astimezone(timezone.utc).replace(tzinfo=None)
            message_record = Message(
                text=message_text,
                user=user,
                created_at=message_date
            )
            session.add(message_record)
            logger.info(f"Message saved: {message.message_id} ({len(message_text)} chars)")
        except Exception as e:
            logger.error(f"Failed to save message: {e}")

    def extract_event_details(self, event: TelegramObject) -> Dict:
        details = {}
        try:
            if isinstance(event, types.Message):
                details.update({
                    'text': event.text,
                    'message_id': event.message_id,
                    'chat_id': event.chat.id,
                    'content_type': event.content_type
                })
                logger.trace(f"Message details extracted: {details}")
            elif hasattr(event, 'data'):
                details['data'] = event.data
                logger.trace(f"Callback data extracted: {event.data}")
        except Exception as e:
            logger.warning(f"Failed to extract event details: {e}")

        return details