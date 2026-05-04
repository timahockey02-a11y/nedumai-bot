from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import CATEGORY_QUESTIONS
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

    await state.update_data(category=category)
    await state.set_state(Flow.WaitingEmotion)

    await callback.message.answer(question, reply_markup=emotions_kb())
    await callback.answer()
