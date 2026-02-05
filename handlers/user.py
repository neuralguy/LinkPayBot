from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, Payment, BotSettings
from states.payment import PaymentStates
from keyboards.inline import get_payment_confirm_keyboard, get_admin_review_keyboard
from config import settings

router = Router()


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user


async def get_setting(session: AsyncSession, key: str) -> str:
    result = await session.execute(
        select(BotSettings).where(BotSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else ""


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    
    user = await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    
    card_number = await get_setting(session, "card_number")
    phone_number = await get_setting(session, "phone_number")
    amount = await get_setting(session, "amount")
    
    text = (
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"📋 <b>Информация для оплаты:</b>\n\n"
        f"💳 <b>Номер карты:</b>\n<code>{card_number}</code>\n\n"
        f"📱 <b>Номер телефона:</b>\n<code>{phone_number}</code>\n\n"
        f"💰 <b>Сумма к оплате:</b> <b>{amount} ₽</b>\n\n"
        f"После оплаты нажмите кнопку ниже и отправьте скриншот/фото чека."
    )
    
    await message.answer(text, reply_markup=get_payment_confirm_keyboard())


@router.callback_query(F.data == "payment_confirm")
async def payment_confirm_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PaymentStates.waiting_for_photo)
    
    await callback.message.answer(
        "📸 <b>Отправьте фото/скриншот оплаты</b>\n\n"
        "Мы проверим платёж и отправим вам ссылку на доступ."
    )


@router.message(PaymentStates.waiting_for_photo, F.photo)
async def process_payment_photo(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    user = await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    
    # Получаем file_id самого большого фото
    photo_file_id = message.photo[-1].file_id
    
    # Сохраняем платёж
    payment = Payment(user_id=user.id, photo_file_id=photo_file_id, status="pending")
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Фото получено!</b>\n\n"
        "Ваш платёж отправлен на проверку администратору.\n"
        "Ожидайте подтверждения."
    )
    
    # Отправляем админам
    admin_text = (
        f"🆕 <b>Новый платёж #{payment.id}</b>\n\n"
        f"👤 <b>Пользователь:</b> {user.full_name}\n"
        f"🆔 <b>Username:</b> @{user.username or 'нет'}\n"
        f"🔢 <b>Telegram ID:</b> <code>{user.telegram_id}</code>"
    )
    
    for admin_id in settings.admin_ids:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_file_id,
                caption=admin_text,
                reply_markup=get_admin_review_keyboard(payment.id)
            )
        except Exception as e:
            print(f"Не удалось отправить админу {admin_id}: {e}")


@router.message(PaymentStates.waiting_for_photo)
async def process_payment_not_photo(message: Message):
    await message.answer(
        "⚠️ <b>Пожалуйста, отправьте именно фото/скриншот оплаты.</b>"
    )
