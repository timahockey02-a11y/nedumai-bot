from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import CATEGORY_QUESTIONS, FEEDBACK_NO, FEEDBACK_YES
from handlers.emotion import send_recommendation
from handlers.states import Flow
from keyboards.emotions import emotions_kb

router = Router()


@router.callback_query(F.data == "change_mood")
async def on_change_mood(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    category = data.get("category")
    if not category:
        await callback.answer()
        return
    await state.update_data(history=[])
    question = CATEGORY_QUESTIONS.get(category, "Какое настроение?")
    await state.set_state(Flow.WaitingEmotion)
    await callback.message.answer(question, reply_markup=emotions_kb())
    await callback.answer()


@router.callback_query(F.data == "another")
async def on_another(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.answer()
    await send_recommendation(callback, state, bot)


@router.callback_query(F.data == "fb_yes")
async def on_fb_yes(callback: CallbackQuery) -> None:
    await callback.message.answer(FEEDBACK_YES)
    await callback.answer()


@router.callback_query(F.data == "fb_no")
async def on_fb_no(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await callback.message.answer(FEEDBACK_NO)
    await callback.answer()
    await send_recommendation(callback, state, bot)
