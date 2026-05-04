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
from services.kudago import Event

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


_PICKER_SYSTEM = (
    "Ты — друг в Москве, который помогает выбрать одно событие из списка реальных. "
    "Ты не выдумываешь — ты выбираешь из того, что дано. "
    "Отвечаешь строго в формате — никаких вступлений."
)

_PICKER_USER_TEMPLATE = (
    "Категория: {category_name}\n"
    "Настроение пользователя: {emotion_description}\n"
    "Сейчас в Москве: {time_context}\n"
    "{skip_note}\n\n"
    "Выбери ОДНО событие из списка ниже, которое лучше всего подходит под настроение. "
    "Опирайся только на эти данные, ничего не придумывай.\n\n"
    "{events}\n\n"
    "Формат ответа — РОВНО так:\n"
    "ID: <id выбранного события из списка выше>\n"
    "ОБОСНОВАНИЕ: 2–3 живых предложения, почему именно это под настроение"
)


async def pick_event(
    category: str,
    emotion: str,
    events: list[Event],
    skip_titles: list[str] | None = None,
) -> tuple[Event, str] | None:
    """Передаёт реальные события в DeepSeek, получает выбранный id + обоснование."""
    if not events:
        return None

    skip_titles = skip_titles or []
    available = [e for e in events if e.title not in skip_titles]
    if not available:
        available = events  # если всё в скипе — берём что есть

    category_name = CATEGORY_NAMES.get(category, category)
    emotion_description = EMOTION_DESCRIPTIONS.get(emotion, emotion)

    skip_note = f"Уже видел — старайся не повторять: {', '.join(skip_titles)}" if skip_titles else ""

    events_block = "\n".join(e.to_prompt_line() for e in available)

    user_prompt = _PICKER_USER_TEMPLATE.format(
        category_name=category_name,
        emotion_description=emotion_description,
        time_context=_time_context(),
        skip_note=skip_note,
        events=events_block,
    )

    response = await _client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": _PICKER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=300,
    )
    raw = (response.choices[0].message.content or "").strip()
    logger.info("KudaGo-picker %s/%s -> %s", category, emotion, raw[:120].replace("\n", " "))

    id_match = re.search(r"ID\s*[::]\s*#?(\d+)", raw, re.IGNORECASE)
    reason_match = re.search(
        r"ОБОСНОВАНИЕ\s*[::]\s*(.+)", raw, re.IGNORECASE | re.DOTALL,
    )
    if not id_match:
        return None
    chosen_id = int(id_match.group(1))
    reason = (reason_match.group(1).strip() if reason_match else "").strip()

    chosen = next((e for e in available if e.id == chosen_id), None)
    if not chosen:
        chosen = available[0]
    return chosen, reason


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
