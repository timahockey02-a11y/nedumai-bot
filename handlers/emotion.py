import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import (
    CATEGORY_EMOJI,
    EMOTION_REACTIONS,
    ERROR_TEXT,
    FEEDBACK_QUESTION,
)
from handlers.states import Flow
from keyboards.emotions import feedback_kb, result_kb
from services.deepseek import get_recommendation

logger = logging.getLogger(__name__)

router = Router()


def format_card(category: str, raw: str) -> str:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return ERROR_TEXT

    emoji = CATEGORY_EMOJI.get(category, "✨")
    name = lines[0]

    if len(lines) == 1:
        return f"{emoji} {name}"
    if len(lines) == 2:
        return f"{emoji} {name}\n\n{lines[1]}"

    details = lines[-1]
    description = "\n".join(lines[1:-1])
    return f"{emoji} {name}\n\n{description}\n\n📍 {details}"


async def send_recommendation(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    previous: str = "",
) -> None:
    data = await state.get_data()
    category = data.get("category")
    emotion = data.get("emotion")
    if not category or not emotion:
        await callback.message.answer(ERROR_TEXT)
        return

    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    await asyncio.sleep(1.5)

    try:
        raw = await get_recommendation(category, emotion, previous=previous)
    except Exception:
        logger.exception("DeepSeek request failed")
        await callback.message.answer(ERROR_TEXT)
        return

    card = format_card(category, raw)
    await state.update_data(last_result=raw)
    await state.set_state(Flow.WaitingFeedback)

    await callback.message.answer(card, reply_markup=result_kb())
    await callback.message.answer(FEEDBACK_QUESTION, reply_markup=feedback_kb())


@router.callback_query(Flow.WaitingEmotion, F.data.startswith("em_"))
async def on_emotion(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    emotion = callback.data
    reaction = EMOTION_REACTIONS.get(emotion)
    if not reaction:
        await callback.answer()
        return

    await state.update_data(emotion=emotion)
    await callback.message.answer(reaction)
    await callback.answer()

    await send_recommendation(callback, state, bot, previous="")
