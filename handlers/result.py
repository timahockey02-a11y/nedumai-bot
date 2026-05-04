from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import CATEGORY_QUESTIONS, REJECT_TEXT, SAVED_TOAST
from handlers.emotion import send_recommendation
from handlers.states import Flow
from keyboards.emotions import emotions_kb
from services.db import block_name, log_event, mark_saved

router = Router()


@router.callback_query(F.data == "save")
async def on_save(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    rec_id = data.get("last_rec_id")
    if not rec_id:
        await callback.answer("Нечего сохранять 🤷", show_alert=False)
        return
    await mark_saved(int(rec_id))
    await log_event(callback.from_user.id, "save", {"rec_id": rec_id})
    await callback.answer(SAVED_TOAST, show_alert=False)


@router.callback_query(F.data == "change_mood")
async def on_change_mood(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    category = data.get("category")
    if not category:
        await callback.answer()
        return
    await log_event(callback.from_user.id, "change_mood", {"category": category})
    question = CATEGORY_QUESTIONS.get(category, "Какое настроение?")
    await state.set_state(Flow.WaitingEmotion)
    await callback.message.answer(question, reply_markup=emotions_kb())
    await callback.answer()


@router.callback_query(F.data == "another")
async def on_another(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await log_event(callback.from_user.id, "another")
    await callback.answer()
    await send_recommendation(callback, state, bot)


@router.callback_query(F.data == "reject")
async def on_reject(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    rejected_name = data.get("last_rec_name", "")
    if rejected_name:
        await block_name(callback.from_user.id, rejected_name)
    await log_event(callback.from_user.id, "reject", {"name": rejected_name})
    await callback.message.answer(REJECT_TEXT)
    await callback.answer()
    await send_recommendation(callback, state, bot)
