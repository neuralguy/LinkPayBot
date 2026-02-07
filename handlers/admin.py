from datetime import datetime, timedelta, timezone
from html import escape as html_escape

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Payment, User, BotSettings, Admin
from states.payment import AdminStates
from keyboards.inline import (
    get_admin_settings_keyboard,
    get_cancel_keyboard,
    get_admin_manage_keyboard,
    get_confirm_delete_admin_keyboard,
    get_start_message_keyboard,
)
from config import settings

router = Router()

# Шаблон по умолчанию (используется при сбросе)
DEFAULT_START_MESSAGE = (
    "👋 Привет, {first_name}!\n\n"
    "{sub_info}\n"
    "📋 <b>Информация для оплаты подписки на месяц:</b>\n\n"
    "💳 <b>Номер карты:</b>\n<code>{card_number}</code>\n\n"
    "📱 <b>Номер телефона:</b>\n<code>{phone_number}</code>\n\n"
    "💰 <b>Сумма к оплате:</b> <b>{amount} ₽</b>\n\n"
    "После оплаты нажмите кнопку ниже и отправьте скриншот/фото чека."
)


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


def is_main_admin(user_id: int) -> bool:
    return user_id == settings.main_admin_id


# ─────────────────────────────────────────────
# /admin — главное меню
# ─────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\n"
        "Выберите параметр для редактирования:",
        reply_markup=get_admin_settings_keyboard()
    )


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "⚙️ <b>Панель администратора</b>\n\n"
        "Выберите параметр для редактирования:",
        reply_markup=get_admin_settings_keyboard()
    )


# ─────────────────────────────────────────────
# Редактирование карты / телефона / суммы
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# Редактирование сообщения /start
# ─────────────────────────────────────────────

@router.callback_query(F.data == "edit_start_message")
async def edit_start_message_callback(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.answer()

    result = await session.execute(
        select(BotSettings).where(BotSettings.key == "start_message")
    )
    setting = result.scalar_one_or_none()
    current = setting.value if setting else DEFAULT_START_MESSAGE

    # Экранируем шаблон, чтобы Telegram не пытался парсить HTML-теги из него
    safe_current = html_escape(current)

    await callback.message.answer(
        "📝 <b>Текущее сообщение /start:</b>\n\n"
        f"<pre>{safe_current}</pre>\n\n"
        "📌 <b>Доступные переменные:</b>\n"
        "<code>{first_name}</code> — имя пользователя\n"
        "<code>{sub_info}</code> — статус подписки\n"
        "<code>{card_number}</code> — номер карты\n"
        "<code>{phone_number}</code> — номер телефона\n"
        "<code>{amount}</code> — сумма оплаты\n\n"
        "Поддерживается HTML-разметка: "
        "<code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;code&gt;</code> и т.д.\n\n"
        "Выберите действие:",
        reply_markup=get_start_message_keyboard()
    )


@router.callback_query(F.data == "do_edit_start_message")
async def do_edit_start_message(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AdminStates.editing_start_message)
    await callback.message.answer(
        "✏️ <b>Отправьте новый текст сообщения /start</b>\n\n"
        "Поддерживается HTML-разметка ("
        "<code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;code&gt;</code> и т.д.)\n\n"
        "📌 <b>Доступные переменные:</b>\n"
        "<code>{first_name}</code> — имя пользователя\n"
        "<code>{sub_info}</code> — статус подписки\n"
        "<code>{card_number}</code> — номер карты\n"
        "<code>{phone_number}</code> — номер телефона\n"
        "<code>{amount}</code> — сумма оплаты",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminStates.editing_start_message)
async def process_edit_start_message(message: Message, session: AsyncSession, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    new_text = message.text
    if not new_text:
        await message.answer("⚠️ Отправьте текстовое сообщение.")
        return

    # Проверяем валидность шаблона
    try:
        preview = new_text.format(
            first_name="Иван",
            sub_info="❌ <b>У вас нет активной подписки.</b>",
            card_number="0000 0000 0000 0000",
            phone_number="+7 (000) 000-00-00",
            amount="1000",
        )
    except KeyError as e:
        await message.answer(
            f"⚠️ Неизвестная переменная в шаблоне: {e}\n\n"
            "Допустимые: <code>{{first_name}}</code>, <code>{{sub_info}}</code>, "
            "<code>{{card_number}}</code>, <code>{{phone_number}}</code>, <code>{{amount}}</code>"
        )
        return
    except (ValueError, IndexError):
        await message.answer(
            "⚠️ Ошибка в формате шаблона. Проверьте правильность фигурных скобок."
        )
        return

    await update_setting(session, "start_message", new_text)
    await state.clear()

    # Показываем предпросмотр — сначала пробуем отправить с HTML,
    # если шаблон содержит невалидный HTML — покажем экранированную версию
    try:
        await message.answer(
            "✅ <b>Сообщение /start обновлено!</b>\n\n"
            "<b>Предпросмотр:</b>\n"
            "─────────────────\n"
            f"{preview}\n"
            "─────────────────",
            reply_markup=get_admin_settings_keyboard()
        )
    except Exception:
        safe_preview = html_escape(preview)
        await message.answer(
            "✅ <b>Сообщение /start обновлено!</b>\n\n"
            "<b>Предпросмотр (исходный код):</b>\n"
            f"<pre>{safe_preview}</pre>",
            reply_markup=get_admin_settings_keyboard()
        )


@router.callback_query(F.data == "reset_start_message")
async def reset_start_message(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.answer()
    await update_setting(session, "start_message", DEFAULT_START_MESSAGE)

    await callback.message.edit_text(
        "🔄 <b>Сообщение /start сброшено на стандартное.</b>",
        reply_markup=get_admin_settings_keyboard()
    )


# ─────────────────────────────────────────────
# Управление админами
# ─────────────────────────────────────────────

@router.callback_query(F.data == "manage_admins")
async def manage_admins_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.answer()

    result = await session.execute(select(Admin))
    admins = result.scalars().all()

    text = "👥 <b>Управление админами</b>\n\n"
    for adm in admins:
        label = f"@{adm.username}" if adm.username else f"ID: <code>{adm.telegram_id}</code>"
        role = " 👑 (главный)" if adm.telegram_id == settings.main_admin_id else ""
        text += f"• {label}{role}\n"

    text += "\nВыберите действие:"

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_manage_keyboard(admins, settings.main_admin_id)
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_admin_manage_keyboard(admins, settings.main_admin_id)
        )


@router.callback_query(F.data == "add_admin")
async def add_admin_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AdminStates.adding_admin)
    await callback.message.answer(
        "➕ <b>Добавление нового админа</b>\n\n"
        "Отправьте <b>Telegram ID</b> нового админа (числом).\n\n"
        "💡 Пользователь может узнать свой ID, например, через @userinfobot",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AdminStates.adding_admin)
async def process_add_admin(message: Message, session: AsyncSession, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()

    try:
        new_admin_id = int(text)
    except ValueError:
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return

    result = await session.execute(
        select(Admin).where(Admin.telegram_id == new_admin_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await message.answer("⚠️ Этот пользователь уже является админом.")
        return

    username = None
    try:
        chat = await bot.get_chat(new_admin_id)
        username = chat.username
    except Exception:
        pass

    new_admin = Admin(
        telegram_id=new_admin_id,
        username=username,
        added_by=message.from_user.id,
        is_main=False,
    )
    session.add(new_admin)
    await session.commit()

    if new_admin_id not in settings.admin_ids:
        settings.admin_ids.append(new_admin_id)

    await state.clear()

    label = f"@{username}" if username else f"ID: <code>{new_admin_id}</code>"
    await message.answer(
        f"✅ <b>Админ добавлен:</b> {label}",
        reply_markup=get_admin_settings_keyboard()
    )

    try:
        await bot.send_message(
            chat_id=new_admin_id,
            text=(
                "🎉 <b>Вы назначены администратором бота!</b>\n\n"
                "Теперь вам будут приходить заявки на подтверждение оплаты.\n"
                "Используйте /admin для доступа к панели управления."
            )
        )
    except Exception:
        await message.answer(
            "⚠️ Не удалось отправить уведомление новому админу "
            "(возможно, он не начинал диалог с ботом)."
        )


@router.callback_query(F.data.startswith("deladmin_"))
async def delete_admin_callback(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    target_id = int(callback.data.split("_")[1])

    if target_id == settings.main_admin_id:
        await callback.answer("Нельзя удалить главного админа!", show_alert=True)
        return

    await callback.answer()

    result = await session.execute(
        select(Admin).where(Admin.telegram_id == target_id)
    )
    adm = result.scalar_one_or_none()

    if not adm:
        await callback.message.answer("⚠️ Админ не найден.")
        return

    label = f"@{adm.username}" if adm.username else f"ID: <code>{target_id}</code>"

    await callback.message.edit_text(
        f"⚠️ <b>Вы уверены, что хотите удалить админа {label}?</b>",
        reply_markup=get_confirm_delete_admin_keyboard(target_id)
    )


@router.callback_query(F.data.startswith("confirmdeladmin_"))
async def confirm_delete_admin(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    target_id = int(callback.data.split("_")[1])

    if target_id == settings.main_admin_id:
        await callback.answer("Нельзя удалить главного админа!", show_alert=True)
        return

    await callback.answer()

    result = await session.execute(
        select(Admin).where(Admin.telegram_id == target_id)
    )
    adm = result.scalar_one_or_none()

    if not adm:
        await callback.message.edit_text("⚠️ Админ не найден.")
        return

    label = f"@{adm.username}" if adm.username else f"ID: <code>{target_id}</code>"

    await session.delete(adm)
    await session.commit()

    if target_id in settings.admin_ids:
        settings.admin_ids.remove(target_id)

    await callback.message.edit_text(
        f"✅ <b>Админ {label} удалён.</b>",
        reply_markup=get_admin_settings_keyboard()
    )

    try:
        await bot.send_message(
            chat_id=target_id,
            text="ℹ️ <b>Вы были сняты с роли администратора бота.</b>"
        )
    except Exception:
        pass


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer("Это главный админ — его нельзя удалить", show_alert=True)


# ─────────────────────────────────────────────
# Одобрение / отклонение платежей
# ─────────────────────────────────────────────

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

    result = await session.execute(select(User).where(User.id == payment.user_id))
    user = result.scalar_one()

    now = datetime.now(timezone.utc)

    if user.subscription_until and user.subscription_until > now:
        new_until = user.subscription_until + timedelta(days=settings.subscription_days)
    else:
        new_until = now + timedelta(days=settings.subscription_days)

    user.subscription_until = new_until

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

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>"
    )

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

    result = await session.execute(select(User).where(User.id == payment.user_id))
    user = result.scalar_one()

    await callback.answer("❌ Платёж отклонён!")

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>ОТКЛОНЕНО</b>"
    )

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

