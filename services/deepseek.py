import logging
import re
from dataclasses import dataclass
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

_FIELD_KEYS = ("НАЗВАНИЕ", "ОПИСАНИЕ", "АДРЕС", "СТОИМОСТЬ", "ССЫЛКА", "УВЕРЕННОСТЬ")
_FIELD_RE = re.compile(
    r"^\s*(" + "|".join(_FIELD_KEYS) + r")\s*[::]\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class Recommendation:
    name: str = ""
    description: str = ""
    address: str = ""
    price: str = ""
    link: str = ""
    confidence: str = ""
    raw: str = ""


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


def parse_recommendation(raw: str) -> Recommendation:
    rec = Recommendation(raw=raw.strip())
    matches = list(_FIELD_RE.finditer(raw))
    for i, m in enumerate(matches):
        key = m.group(1).upper()
        same_line = (m.group(2) or "").strip()
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        between = raw[m.end():next_start].strip()
        value = (same_line + ("\n" + between if between else "")).strip().strip("«»\"'")
        if not value or value.lower() in {"нет", "—", "-", "пусто", "не указано"}:
            continue
        if key == "НАЗВАНИЕ":
            rec.name = value
        elif key == "ОПИСАНИЕ":
            rec.description = value
        elif key == "АДРЕС":
            rec.address = value
        elif key == "СТОИМОСТЬ":
            rec.price = value
        elif key == "ССЫЛКА":
            rec.link = value
        elif key == "УВЕРЕННОСТЬ":
            rec.confidence = value.lower()

    if not rec.name:
        # fallback: первая непустая строка
        first = next((ln.strip() for ln in raw.splitlines() if ln.strip()), "")
        rec.name = first[:120]
    return rec


async def _ask_deepseek(category: str, emotion: str, previous_list: list[str]) -> str:
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
        temperature=1.0,
        max_tokens=500,
    )
    return (response.choices[0].message.content or "").strip()


async def get_recommendation(
    category: str,
    emotion: str,
    previous_list: list[str] | None = None,
    blocked: list[str] | None = None,
    max_retries: int = 1,
) -> Recommendation:
    skip = list(previous_list or []) + list(blocked or [])
    last_rec: Recommendation | None = None

    for attempt in range(max_retries + 1):
        raw = await _ask_deepseek(category, emotion, skip)
        rec = parse_recommendation(raw)
        last_rec = rec
        logger.info(
            "DeepSeek %s/%s try=%d skip=%d conf=%s -> %s",
            category, emotion, attempt, len(skip), rec.confidence,
            rec.name[:80],
        )
        if rec.confidence != "низкая" and rec.name:
            return rec
        if rec.name:
            skip.append(rec.name)

    return last_rec or Recommendation(raw="", name="")
