import logging
from uuid import uuid4

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from data.texts import INLINE_DESCRIPTION, INLINE_MESSAGE, INLINE_TITLE
from services.db import log_event

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def inline_share(query: InlineQuery) -> None:
    await log_event(query.from_user.id, "inline_share")
    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title=INLINE_TITLE,
        description=INLINE_DESCRIPTION,
        input_message_content=InputTextMessageContent(
            message_text=INLINE_MESSAGE,
            disable_web_page_preview=False,
        ),
    )
    await query.answer([result], cache_time=60, is_personal=False)
