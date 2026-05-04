import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI

from config import DEEPSEEK_API_KEY
from data.texts import (
    CATEGORY_EXTRA,
    CATEGORY_NAMES,
    EMOTION_DESCRIPTIONS,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

_MOSCOW = ZoneInfo("Europe/Moscow")
_WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def _time_context() -> str:
    now = datetime.now(_MOSCOW)
    h = now.hour
    if 5 <= h < 11:
        part = "утро"
    elif 11 <= h < 17:
        part = "день"
    elif 17 <= h < 23:
        part = "вечер"
    else:
        part = "поздняя ночь"
    weekday = _WEEKDAYS[now.weekday()]
    return f"{weekday}, {part}, {h:02d}:{now.minute:02d}"


async def get_recommendation(
    category: str,
    emotion: str,
    previous_list: list[str] | None = None,
) -> str:
    category_name = CATEGORY_NAMES.get(category, category)
    emotion_description = EMOTION_DESCRIPTIONS.get(emotion, emotion)

    if previous_list:
        previous_note = "Уже предлагал — НЕ повторяй: " + "; ".join(previous_list)
    else:
        previous_note = ""

    extra = CATEGORY_EXTRA.get(category, "")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        category_name=category_name,
        emotion_description=emotion_description,
        time_context=_time_context(),
        extra=extra,
        previous_note=previous_note,
    )

    response = await _client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1.1,
        max_tokens=400,
    )

    text = response.choices[0].message.content or ""
    logger.info(
        "DeepSeek %s/%s (skip=%d) -> %s",
        category, emotion, len(previous_list or []),
        text[:100].replace("\n", " "),
    )
    return text.strip()
