from aiogram.fsm.state import State, StatesGroup


class Flow(StatesGroup):
    WaitingEmotion = State()
    WaitingFeedback = State()
