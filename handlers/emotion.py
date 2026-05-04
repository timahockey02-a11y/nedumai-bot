import asyncio
import logging
from urllib.parse import quote

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
from services.db import get_blocked_names, get_recent_names, log_event, save_recommendation
from services.deepseek import Recommendation, get_recommendation

logger = logging.getLogger(__name__)

router = Router()


SKIP_MAP_CATEGORIES = {"cat_cinema"}


def _yandex_maps_url(name: str, address: str) -> str | None:
    parts = [p for p in (name, address) if p]
    query = " ".join(parts).strip()
    if not query:
        return None
    return f"https://yandex.ru/maps/?text={quote(query)}"


def render_card(category: str, rec: Recommendation) -> tuple[str, str | None]:
    if not rec.name:
        return ERROR_TEXT, None

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

    text = "\n".join(lines)

    map_url = None
    if category not in SKIP_MAP_CATEGORIES and rec.address:
        map_url = _yandex_maps_url(rec.name, rec.address)
    elif category not in SKIP_MAP_CATEGORIES:
        map_url = _yandex_maps_url(rec.name, "")
    return text, map_url


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
    history = await get_recent_names(user_id, limit=30)
    blocked = await get_blocked_names(user_id, limit=100)

    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    await asyncio.sleep(1.2)

    try:
        rec = await get_recommendation(
            category, emotion, previous_list=history, blocked=blocked, max_retries=1
        )
    except Exception:
        logger.exception("DeepSeek request failed")
        await callback.message.answer(ERROR_TEXT)
        return

    if not rec.name:
        await callback.message.answer(ERROR_TEXT)
        return

    text, map_url = render_card(category, rec)

    rec_id = await save_recommendation(user_id, category, emotion, rec.name, rec.raw)
    await log_event(
        user_id, "recommendation",
        {"category": category, "emotion": emotion, "name": rec.name, "conf": rec.confidence},
    )

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
