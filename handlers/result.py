from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import FEEDBACK_NO, FEEDBACK_YES
from handlers.emotion import send_recommendation

router = Router()


@router.callback_query(F.data == "another")
async def on_another(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    previous = data.get("last_result", "")
    await callback.answer()
    await send_recommendation(callback, state, bot, previous=previous)


@router.callback_query(F.data == "fb_yes")
async def on_fb_yes(callback: CallbackQuery) -> None:
    await callback.message.answer(FEEDBACK_YES)
    await callback.answer()


@router.callback_query(F.data == "fb_no")
async def on_fb_no(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    previous = data.get("last_result", "")
    await callback.message.answer(FEEDBACK_NO)
    await callback.answer()
    await send_recommendation(callback, state, bot, previous=previous)
