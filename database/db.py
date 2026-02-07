from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from config import settings
from database.models import Base, BotSettings, Admin


async def init_db() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        await init_default_settings(session)
        await init_admins(session)

    return session_maker


async def init_default_settings(session: AsyncSession):
    defaults = {
        "card_number": "0000 0000 0000 0000",
        "phone_number": "+7 (000) 000-00-00",
        "amount": "1000",
        "start_message": (
            "👋 Привет, {first_name}!\n\n"
            "{sub_info}\n"
            "📋 <b>Информация для оплаты подписки на месяц:</b>\n\n"
            "💳 <b>Номер карты:</b>\n<code>{card_number}</code>\n\n"
            "📱 <b>Номер телефона:</b>\n<code>{phone_number}</code>\n\n"
            "💰 <b>Сумма к оплате:</b> <b>{amount} ₽</b>\n\n"
            "После оплаты нажмите кнопку ниже и отправьте скриншот/фото чека."
        ),
    }

    for key, value in defaults.items():
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == key)
        )
        if not result.scalar_one_or_none():
            session.add(BotSettings(key=key, value=value))

    await session.commit()


async def init_admins(session: AsyncSession):
    """
    Добавляет главного админа из .env в таблицу admins (если ещё нет)
    и загружает всех админов в settings.admin_ids.
    """
    main_id = settings.main_admin_id
    if not main_id:
        return

    result = await session.execute(
        select(Admin).where(Admin.telegram_id == main_id)
    )
    main_admin = result.scalar_one_or_none()

    if not main_admin:
        session.add(Admin(
            telegram_id=main_id,
            username=None,
            added_by=main_id,
            is_main=True,
        ))
        await session.commit()

    result = await session.execute(select(Admin))
    all_admins = result.scalars().all()

    settings.admin_ids.clear()
    for adm in all_admins:
        if adm.telegram_id not in settings.admin_ids:
            settings.admin_ids.append(adm.telegram_id)

    if main_id not in settings.admin_ids:
        settings.admin_ids.append(main_id)


def get_session_maker():
    pass

