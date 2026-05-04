import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from data.texts import (
    CATEGORY_EMOJI,
    EMOTION_REACTIONS,
    ERROR_TEXT,
)
from handlers.states import Flow
from keyboards.emotions import result_kb
from services.db import log_event
from services.deepseek import Recommendation
from services.recommender import build_recommendation

logger = logging.getLogger(__name__)

router = Router()


def render_card(category: str, rec: Recommendation) -> str:
    if not rec.name:
        return ERROR_TEXT

    emoji = CATEGORY_EMOJI.get(category, "✨")
    lines = [f"{emoji} <b>{_html_escape(rec.name)}</b>"]
    if rec.description:
        lines.append("")
        lines.append(_html_escape(rec.description))

    meta_lines = []
    if rec.address:
        meta_lines.append(f"📍 {_html_escape(rec.address)}")
    if rec.price:
        meta_lines.append(f"💰 {_html_escape(rec.price)}")
    if rec.link:
        meta_lines.append(f"🔗 {rec.link}")
    if meta_lines:
        lines.append("")
        lines.extend(meta_lines)

    return "\n".join(lines)


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def send_recommendation(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    data = await state.get_data()
    category = data.get("category")
    emotion = data.get("emotion")
    if not category or not emotion:
        await callback.message.answer(ERROR_TEXT)
        return

    user_id = callback.from_user.id

    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)

    result = await build_recommendation(user_id, category, emotion, typing_delay=1.2)
    if result is None:
        await callback.message.answer(ERROR_TEXT)
        return

    rec_id, rec, map_url = result
    text = render_card(category, rec)

    await state.update_data(last_rec_id=rec_id, last_rec_name=rec.name)
    await state.set_state(Flow.WaitingFeedback)

    await callback.message.answer(
        text, reply_markup=result_kb(map_url=map_url), parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.callback_query(Flow.WaitingEmotion, F.data.startswith("em_"))
async def on_emotion(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    emotion = callback.data
    reaction = EMOTION_REACTIONS.get(emotion)
    if not reaction:
        await callback.answer()
        return

    await state.update_data(emotion=emotion)
    await log_event(callback.from_user.id, "emotion", {"emotion": emotion})
    await callback.message.answer(reaction)
    await callback.answer()

    await send_recommendation(callback, state, bot)
