import json
import logging
import random

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from data.texts import (
    CATEGORY_NAMES,
    EMOTION_DESCRIPTIONS,
    EMOTION_REACTIONS,
    SURPRISE_REACTION,
)
from handlers.emotion import send_recommendation
from handlers.states import Flow
from services.db import log_event

logger = logging.getLogger(__name__)
router = Router()


async def _run_flow(message: Message, state: FSMContext, bot: Bot, category: str, emotion: str) -> None:
    reaction = EMOTION_REACTIONS.get(emotion, "Сейчас всё будет ✨")

    await state.update_data(category=category, emotion=emotion)
    await state.set_state(Flow.WaitingEmotion)
    await message.answer(reaction)

    fake_callback = _MessageAsCallback(message)
    await send_recommendation(fake_callback, state, bot)


class _MessageAsCallback:
    """Адаптер: send_recommendation ждёт CallbackQuery, но из WebApp прилетает Message."""

    def __init__(self, message: Message):
        self.message = message
        self.from_user = message.from_user

    async def answer(self, *args, **kwargs):
        return None


@router.message(F.web_app_data)
async def on_webapp_data(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = message.web_app_data.data if message.web_app_data else ""
    try:
        payload = json.loads(raw)
    except Exception:
        logger.warning("Bad web_app_data: %s", raw[:200])
        return

    user_id = message.from_user.id
    await log_event(user_id, "miniapp_choice", payload)

    if payload.get("surprise"):
        category = random.choice(list(CATEGORY_NAMES.keys()))
        emotion = random.choice(list(EMOTION_DESCRIPTIONS.keys()))
        await message.answer(SURPRISE_REACTION)
        await _run_flow(message, state, bot, category, emotion)
        return

    category = payload.get("category")
    emotion = payload.get("emotion")
    if not category or not emotion:
        return
    await _run_flow(message, state, bot, category, emotion)
