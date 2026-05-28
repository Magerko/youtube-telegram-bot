"""FSM-состояния для диалогов админки."""

from aiogram.fsm.state import State, StatesGroup


class AddChannel(StatesGroup):
    waiting_input = State()
