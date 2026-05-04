import logging
import os

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from data.texts import FEEDBACK_CMD_PROMPT, FEEDBACK_THANKS

logger = logging.getLogger(__name__)
router = Router()

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


class Feedback(StatesGroup):
    WaitingMessage = State()


@router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext) -> None:
    await state.set_state(Feedback.WaitingMessage)
    await message.answer(FEEDBACK_CMD_PROMPT)


@router.message(Feedback.WaitingMessage, F.text)
async def on_feedback_text(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    user = message.from_user
    user_label = f"@{user.username}" if user and user.username else (user.full_name if user else "unknown")
    user_id = user.id if user else "?"

    payload = (
        f"📩 Feedback от {user_label} (id={user_id}):\n\n{message.text}"
    )
    logger.info("Feedback from %s (%s): %s", user_label, user_id, message.text[:200])

    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(int(ADMIN_CHAT_ID), payload)
        except Exception:
            logger.exception("Failed to forward feedback to admin")

    await message.answer(FEEDBACK_THANKS)
