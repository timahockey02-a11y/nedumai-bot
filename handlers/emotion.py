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
    FEEDBACK_QUESTION,
)
from handlers.states import Flow
from keyboards.emotions import feedback_kb, result_kb
from services.deepseek import get_recommendation

logger = logging.getLogger(__name__)

router = Router()


SKIP_MAP_CATEGORIES = {"cat_cinema"}


def format_card(category: str, raw: str) -> tuple[str, str | None]:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return ERROR_TEXT, None

    emoji = CATEGORY_EMOJI.get(category, "✨")
    name = lines[0]

    if len(lines) == 1:
        return f"{emoji} {name}", _maybe_map_url(category, name, "")
    if len(lines) == 2:
        return f"{emoji} {name}\n\n{lines[1]}", _maybe_map_url(category, name, "")

    details = lines[-1]
    description = "\n".join(lines[1:-1])
    text = f"{emoji} {name}\n\n{description}\n\n📍 {details}"
    return text, _maybe_map_url(category, name, details)


def _maybe_map_url(category: str, name: str, details: str) -> str | None:
    if category in SKIP_MAP_CATEGORIES:
        return None
    query_parts = [name]
    if details:
        query_parts.append(details)
    query = " ".join(query_parts).strip()
    if not query:
        return None
    return f"https://yandex.ru/maps/?text={quote(query)}"


async def send_recommendation(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    reset_history: bool = False,
) -> None:
    data = await state.get_data()
    category = data.get("category")
    emotion = data.get("emotion")
    if not category or not emotion:
        await callback.message.answer(ERROR_TEXT)
        return

    history: list[str] = [] if reset_history else list(data.get("history", []))

    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    await asyncio.sleep(1.5)

    try:
        raw = await get_recommendation(category, emotion, previous_list=history)
    except Exception:
        logger.exception("DeepSeek request failed")
        await callback.message.answer(ERROR_TEXT)
        return

    card, map_url = format_card(category, raw)

    name = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
    if name:
        history.append(name)

    await state.update_data(last_result=raw, history=history)
    await state.set_state(Flow.WaitingFeedback)

    await callback.message.answer(card, reply_markup=result_kb(map_url=map_url))
    await callback.message.answer(FEEDBACK_QUESTION, reply_markup=feedback_kb())


@router.callback_query(Flow.WaitingEmotion, F.data.startswith("em_"))
async def on_emotion(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    emotion = callback.data
    reaction = EMOTION_REACTIONS.get(emotion)
    if not reaction:
        await callback.answer()
        return

    await state.update_data(emotion=emotion, history=[])
    await callback.message.answer(reaction)
    await callback.answer()

    await send_recommendation(callback, state, bot, reset_history=True)
