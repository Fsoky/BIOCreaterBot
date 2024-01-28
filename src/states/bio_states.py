from aiogram.fsm.state import StatesGroup, State


class BIOTextForm(StatesGroup):
    text = State()


class BIOButtonForm(StatesGroup):
    text = State()
    url = State()