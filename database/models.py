from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Text, Boolean, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Дата окончания подписки (None = нет активной подписки)
    subscription_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Забанен ли в канале (чтобы знать, что надо разбанить при новой оплате)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    payments: Mapped[list["Payment"]] = relationship(back_populates="user")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    photo_file_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by: Mapped[int] = mapped_column(BigInteger)  # кто добавил
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

