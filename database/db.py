from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from bot.config import settings
from bot.database.models import Base, BotSettings


async def init_db() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(settings.database_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Инициализация настроек по умолчанию
    async with session_maker() as session:
        await init_default_settings(session)
    
    return session_maker


async def init_default_settings(session: AsyncSession):
    defaults = {
        "card_number": "0000 0000 0000 0000",
        "phone_number": "+7 (000) 000-00-00",
        "amount": "1000",
    }
    
    for key, value in defaults.items():
        result = await session.execute(
            select(BotSettings).where(BotSettings.key == key)
        )
        if not result.scalar_one_or_none():
            session.add(BotSettings(key=key, value=value))
    
    await session.commit()


def get_session_maker():
    pass  # Placeholder, используется через middleware
