import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

logger = logging.getLogger(__name__)

KUDAGO_API = "https://kudago.com/public-api/v1.5"

# Соответствие наших категорий → slugs KudaGo.
CATEGORY_MAP = {
    "cat_theatre":     ["theater"],
    "cat_exhibitions": ["exhibition"],
    "cat_cinema":      ["cinema"],
}

CACHE_TTL = 3600  # 1 час
_cache: dict[str, tuple[float, list]] = {}

_MOSCOW = ZoneInfo("Europe/Moscow")
_RU_MONTHS = [
    "", "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Event:
    id: int
    title: str
    description: str
    place: str
    address: str
    price: str
    url: str
    dates_str: str
    age_restriction: str = ""

    def to_prompt_line(self) -> str:
        chunks = [f"#{self.id}", self.title]
        if self.dates_str:
            chunks.append(f"({self.dates_str})")
        if self.place:
            chunks.append(f"@ {self.place}")
        if self.price and self.price != "—":
            chunks.append(f"[{self.price}]")
        if self.age_restriction:
            chunks.append(self.age_restriction)
        line = " ".join(chunks)
        if self.description:
            short = self.description.replace("\n", " ").strip()[:220]
            line += f" — {short}"
        return line


def is_supported(category: str) -> bool:
    return category in CATEGORY_MAP


async def fetch_events(category: str, limit: int = 25) -> list[Event]:
    if category not in CATEGORY_MAP:
        return []
    cache_key = category
    now_ts = time.time()
    cached = _cache.get(cache_key)
    if cached and now_ts - cached[0] < CACHE_TTL:
        return cached[1]

    cats = ",".join(CATEGORY_MAP[category])
    actual_since = int(now_ts)
    actual_until = int(now_ts) + 14 * 24 * 3600  # ближайшие 2 недели

    params = {
        "location": "msk",
        "categories": cats,
        "actual_since": actual_since,
        "actual_until": actual_until,
        "fields": "id,title,description,body_text,place,dates,price,site_url,age_restriction",
        "expand": "place",
        "page_size": limit,
        "order_by": "-publication_date",
    }
    headers = {"User-Agent": "nedumai-bot/1.0 (+telegram)"}

    timeout = aiohttp.ClientTimeout(total=8)
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(f"{KUDAGO_API}/events/", params=params) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("KudaGo %s -> %s: %s", category, resp.status, body[:200])
                    return []
                data = await resp.json()
    except Exception:
        logger.exception("KudaGo fetch failed for %s", category)
        return []

    events: list[Event] = []
    for item in data.get("results", []):
        e = _parse_event(item)
        if e:
            events.append(e)

    logger.info("KudaGo %s -> %d events", category, len(events))
    _cache[cache_key] = (now_ts, events)
    return events


def _parse_event(item: dict) -> Event | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None
    desc = _strip_html(item.get("description") or item.get("body_text") or "")

    place_obj = item.get("place") or {}
    if isinstance(place_obj, int):
        place_obj = {}
    place = (place_obj.get("title") or "").strip() if isinstance(place_obj, dict) else ""
    address = (place_obj.get("address") or "").strip() if isinstance(place_obj, dict) else ""

    price = (item.get("price") or "").strip()
    if not price:
        price = "бесплатно" if item.get("is_free") else "—"

    url = item.get("site_url") or ""
    dates_str = _format_dates(item.get("dates") or [])
    age = (item.get("age_restriction") or "").strip()
    if age and not age.endswith("+"):
        age = f"{age}+" if age.isdigit() else age

    return Event(
        id=int(item.get("id") or 0),
        title=_capitalize(title),
        description=desc,
        place=place,
        address=address,
        price=price,
        url=url,
        dates_str=dates_str,
        age_restriction=age,
    )


def _capitalize(s: str) -> str:
    if not s:
        return s
    return s[0].upper() + s[1:]


def _strip_html(s: str) -> str:
    text = _HTML_TAG_RE.sub("", s)
    text = text.replace("&nbsp;", " ").replace("&mdash;", "—").replace("&ndash;", "–")
    text = text.replace("&laquo;", "«").replace("&raquo;", "»").replace("&hellip;", "…")
    text = text.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
    return re.sub(r"\s+", " ", text).strip()


def _format_dates(dates: list) -> str:
    """Compact human date string. Берёт ближайшую будущую дату из множества."""
    if not dates:
        return ""
    now = datetime.now(_MOSCOW)
    upcoming: list[tuple[datetime, datetime | None]] = []
    for d in dates:
        try:
            start_ts = int(d.get("start") or 0)
            end_ts = int(d.get("end") or 0)
        except (TypeError, ValueError):
            continue
        # KudaGo иногда возвращает -62135433000 как «дата неизвестна»
        if start_ts < 946684800:  # < 2000-01-01
            start_ts = 0
        if end_ts < 946684800:
            end_ts = 0
        if not start_ts and not end_ts:
            continue
        try:
            start = datetime.fromtimestamp(start_ts, tz=_MOSCOW) if start_ts else None
            end = datetime.fromtimestamp(end_ts, tz=_MOSCOW) if end_ts else None
        except Exception:
            continue
        # фильтр: либо начало в будущем, либо диапазон ещё не закончился
        ref = start or end
        if not ref:
            continue
        if end and end < now:
            continue
        if start and start < now and not end:
            continue
        upcoming.append((start or end, end))

    if not upcoming:
        return ""
    upcoming.sort(key=lambda t: t[0])
    start, end = upcoming[0]
    s = f"{start.day} {_RU_MONTHS[start.month]}"
    if end and end.date() != start.date():
        s += f" — {end.day} {_RU_MONTHS[end.month]}"
    elif start.hour or start.minute:
        s += f", {start.hour:02d}:{start.minute:02d}"
    return s
