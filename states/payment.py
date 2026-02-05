from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    waiting_for_photo = State()


class AdminStates(StatesGroup):
    editing_card = State()
    editing_phone = State()
    editing_amount = State()
