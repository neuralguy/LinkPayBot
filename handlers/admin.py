from datetime import datetime, timedelta, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Payment, User, BotSettings
from states.payment import AdminStates
from keyboards.inline import get_admin_settings_keyboard, get_cancel_keyboard
from config import settings

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\n"
        "Выберите параметр для редактирования:",
        reply_markup=get_admin_settings_keyboard()
    )


@router.callback_query(F.data == "edit_card")
async def edit_card_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    result = await session.execute(select(BotSettings).where(BotSettings.key == "card_number"))
    setting = result.scalar_one_or_none()
    current = setting.value if setting else "не задано"
    
    await state.set_state(AdminStates.editing_card)
    await callback.message.answer(
        f"💳 <b>Текущий номер карты:</b>\n<code>{current}</code>\n\n"
        "Отправьте новый номер карты:",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "edit_phone")
async def edit_phone_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    result = await session.execute(select(BotSettings).where(BotSettings.key == "phone_number"))
    setting = result.scalar_one_or_none()
    current = setting.value if setting else "не задано"
    
    await state.set_state(AdminStates.editing_phone)
    await callback.message.answer(
        f"📱 <b>Текущий номер телефона:</b>\n<code>{current}</code>\n\n"
        "Отправьте новый номер телефона:",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "edit_amount")
async def edit_amount_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await callback.answer()
    
    result = await session.execute(select(BotSettings).where(BotSettings.key == "amount"))
    setting = result.scalar_one_or_none()
    current = setting.value if setting else "не задано"
    
    await state.set_state(AdminStates.editing_amount)
    await callback.message.answer(
        f"💰 <b>Текущая сумма:</b> {current} ₽\n\n"
        "Отправьте новую сумму (только число):",
        reply_markup=get_cancel_keyboard()
    )


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("❌ Действие отменено.")


async def update_setting(session: AsyncSession, key: str, value: str):
    result = await session.execute(select(BotSettings).where(BotSettings.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = value
    else:
        session.add(BotSettings(key=key, value=value))
    
    await session.commit()


@router.message(AdminStates.editing_card)
async def process_edit_card(message: Message, session: AsyncSession, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await update_setting(session, "card_number", message.text.strip())
    await state.clear()
    
    await message.answer(
        f"✅ <b>Номер карты обновлён:</b>\n<code>{message.text.strip()}</code>",
        reply_markup=get_admin_settings_keyboard()
    )


@router.message(AdminStates.editing_phone)
async def process_edit_phone(message: Message, session: AsyncSession, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    await update_setting(session, "phone_number", message.text.strip())
    await state.clear()
    
    await message.answer(
        f"✅ <b>Номер телефона обновлён:</b>\n<code>{message.text.strip()}</code>",
        reply_markup=get_admin_settings_keyboard()
    )


@router.message(AdminStates.editing_amount)
async def process_edit_amount(message: Message, session: AsyncSession, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("⚠️ Введите корректное число.")
        return
    
    await update_setting(session, "amount", str(amount))
    await state.clear()
    
    await message.answer(
        f"✅ <b>Сумма обновлена:</b> {amount} ₽",
        reply_markup=get_admin_settings_keyboard()
    )


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[1])
    
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    
    if payment.status != "pending":
        await callback.answer("Платёж уже обработан", show_alert=True)
        return
    
    payment.status = "approved"

    # Получаем пользователя
    result = await session.execute(select(User).where(User.id == payment.user_id))
    user = result.scalar_one()

    # === ПРОДЛЕНИЕ ПОДПИСКИ ===
    now = datetime.now(timezone.utc)

    # Если подписка ещё активна — продлеваем от текущего конца, иначе от сейчас
    if user.subscription_until and user.subscription_until > now:
        new_until = user.subscription_until + timedelta(days=settings.subscription_days)
    else:
        new_until = now + timedelta(days=settings.subscription_days)

    user.subscription_until = new_until

    # === РАЗБАН, если пользователь был забанен ===
    if user.is_banned:
        try:
            await bot.unban_chat_member(
                chat_id=settings.channel_id,
                user_id=user.telegram_id,
                only_if_banned=True,
            )
            user.is_banned = False
        except Exception as e:
            await callback.message.answer(
                f"⚠️ Не удалось разбанить пользователя в канале: {e}"
            )

    await session.commit()

    await callback.answer("✅ Платёж одобрен!")

    # Обновляем сообщение у админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>"
    )

    # Отправляем пользователю ссылку и информацию о подписке
    expire_str = new_until.strftime("%d.%m.%Y %H:%M UTC")
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                "🎉 <b>Ваш платёж подтверждён!</b>\n\n"
                f"Подписка активна до: <b>{expire_str}</b>\n\n"
                f"Добро пожаловать! Вот ваша ссылка для доступа:\n"
                f"{settings.invite_link}"
            ),
        )
    except Exception as e:
        await callback.message.answer(
            f"⚠️ Не удалось отправить сообщение пользователю: {e}"
        )


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[1])
    
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    
    if payment.status != "pending":
        await callback.answer("Платёж уже обработан", show_alert=True)
        return
    
    payment.status = "rejected"
    await session.commit()
    
    # Получаем пользователя
    result = await session.execute(select(User).where(User.id == payment.user_id))
    user = result.scalar_one()
    
    await callback.answer("❌ Платёж отклонён!")
    
    # Обновляем сообщение у админа
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>"
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                "❌ <b>Ваш платёж отклонён.</b>\n\n"
                "Пожалуйста, проверьте правильность оплаты и попробуйте снова.\n"
                "Используйте /start для повторной попытки."
            )
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ Не удалось отправить сообщение пользователю: {e}")
