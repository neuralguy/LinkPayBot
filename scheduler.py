import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from config import settings
from database.models import User

logger = logging.getLogger(__name__)


async def check_expired_subscriptions(bot: Bot, session_maker: async_sessionmaker):
    """
    Проверяет всех пользователей с истёкшей подпиской.
    Кикает их из канала и помечает как забаненных.
    """
    now = datetime.now(timezone.utc)

    async with session_maker() as session:
        # Ищем пользователей, у которых подписка истекла и они ещё не забанены
        result = await session.execute(
            select(User).where(
                User.subscription_until.isnot(None),
                User.subscription_until < now,
                User.is_banned == False,
            )
        )
        expired_users = result.scalars().all()

        for user in expired_users:
            try:
                # Проверяем, состоит ли пользователь в канале
                member = await bot.get_chat_member(
                    chat_id=settings.channel_id,
                    user_id=user.telegram_id
                )

                if member.status not in (
                    ChatMemberStatus.LEFT,
                    ChatMemberStatus.KICKED,
                ):
                    # Баним пользователя из канала (кик + бан, чтобы инвайт-ссылка не работала)
                    await bot.ban_chat_member(
                        chat_id=settings.channel_id,
                        user_id=user.telegram_id,
                    )
                    logger.info(
                        f"Забанен пользователь {user.telegram_id} ({user.full_name}) — подписка истекла"
                    )

                user.is_banned = True
                user.subscription_until = None

                # Уведомляем пользователя
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "⏰ <b>Ваша подписка истекла!</b>\n\n"
                            "Доступ к каналу заблокирован.\n"
                            "Чтобы продлить подписку, нажмите /start и оплатите заново."
                        ),
                    )
                except Exception:
                    logger.warning(
                        f"Не удалось уведомить пользователя {user.telegram_id}"
                    )

            except Exception as e:
                logger.error(
                    f"Ошибка при обработке пользователя {user.telegram_id}: {e}"
                )

        await session.commit()

    if expired_users:
        logger.info(f"Обработано {len(expired_users)} истёкших подписок")
