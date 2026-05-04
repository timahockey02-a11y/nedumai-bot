import logging

from openai import AsyncOpenAI

from config import DEEPSEEK_API_KEY
from data.texts import (
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


async def get_recommendation(category: str, emotion: str, previous: str = "") -> str:
    category_name = CATEGORY_NAMES.get(category, category)
    emotion_description = EMOTION_DESCRIPTIONS.get(emotion, emotion)

    previous_note = f"Не повторяй: {previous}" if previous else ""

    user_prompt = USER_PROMPT_TEMPLATE.format(
        category_name=category_name,
        emotion_description=emotion_description,
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
    logger.info("DeepSeek %s/%s -> %s", category, emotion, text[:100].replace("\n", " "))
    return text.strip()
