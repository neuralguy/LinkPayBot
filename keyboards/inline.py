from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_payment_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Я оплатил",
        callback_data="payment_confirm"
    ))
    return builder.as_markup()


def get_admin_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"approve_{payment_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"reject_{payment_id}"
        )
    )
    return builder.as_markup()


def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Номер карты", callback_data="edit_card")
    )
    builder.row(
        InlineKeyboardButton(text="📱 Номер телефона", callback_data="edit_phone")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Сумма", callback_data="edit_amount")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Сообщение /start", callback_data="edit_start_message")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def get_start_message_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить", callback_data="do_edit_start_message")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить по умолчанию", callback_data="reset_start_message")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
    )
    return builder.as_markup()


def get_admin_manage_keyboard(admins: list, main_admin_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for adm in admins:
        label = f"@{adm.username}" if adm.username else str(adm.telegram_id)
        if adm.telegram_id == main_admin_id:
            builder.row(
                InlineKeyboardButton(
                    text=f"👑 {label} (главный)",
                    callback_data="noop"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=f"🗑 Удалить {label}",
                    callback_data=f"deladmin_{adm.telegram_id}"
                )
            )

    builder.row(
        InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
    )
    return builder.as_markup()


def get_confirm_delete_admin_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"confirmdeladmin_{telegram_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="manage_admins"
        )
    )
    return builder.as_markup()

