import random

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import (
    CATEGORY_NAMES,
    CATEGORY_QUESTIONS,
    EMOTION_DESCRIPTIONS,
    SURPRISE_REACTION,
)
from handlers.emotion import send_recommendation
from handlers.states import Flow
from keyboards.emotions import emotions_kb

router = Router()


@router.callback_query(F.data.startswith("cat_"))
async def on_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data
    question = CATEGORY_QUESTIONS.get(category)
    if not question:
        await callback.answer()
        return

    await state.update_data(category=category, history=[])
    await state.set_state(Flow.WaitingEmotion)

    await callback.message.answer(question, reply_markup=emotions_kb())
    await callback.answer()


@router.callback_query(F.data == "surprise")
async def on_surprise(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    category = random.choice(list(CATEGORY_NAMES.keys()))
    emotion = random.choice(list(EMOTION_DESCRIPTIONS.keys()))

    await state.update_data(category=category, emotion=emotion, history=[])
    await callback.message.answer(SURPRISE_REACTION)
    await callback.answer()

    await send_recommendation(callback, state, bot, reset_history=True)
