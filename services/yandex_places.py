import logging
import os
import random
import time
from dataclasses import dataclass

import aiohttp

logger = logging.getLogger(__name__)

API_URL = "https://search-maps.yandex.ru/v1/"
API_KEY = os.getenv("YANDEX_PLACES_API_KEY", "")

# Bounding box Москвы (примерно).
MOSCOW_BBOX = "37.3260,55.5520~37.9676,55.9579"

CACHE_TTL = 6 * 3600  # 6 часов
_cache: dict[str, tuple[float, list]] = {}

EMOTION_ADJECTIVE = {
    "em_exhale": "тихий",
    "em_lol":    "весёлый",
    "em_new":    "необычный",
    "em_feel":   "атмосферный",
    "em_charge": "активный",
    "em_wow":    "странный",
}

# База поиска для каждой категории.
# Возвращаем варианты — для разнообразия выбираем рандомно.
CATEGORY_QUERIES = {
    "cat_restaurants": ["ресторан", "кафе", "бар"],
    "cat_sport": [
        "паддел клуб",
        "теннисный корт",
        "гольф клуб",
        "волейбольный клуб",
        "беговой клуб",
    ],
    "cat_nature": [
        "парк",
        "сквер",
        "набережная",
        "ботанический сад",
        "природный заповедник",
    ],
}

SUPPORTED = set(CATEGORY_QUERIES.keys())


@dataclass
class Place:
    id: str
    name: str
    address: str
    url: str
    phone: str
    categories: str
    hours: str
    lon: float
    lat: float

    def to_prompt_line(self) -> str:
        chunks = [f"#{self.id}", self.name]
        if self.categories:
            chunks.append(f"({self.categories})")
        if self.address:
            chunks.append(f"@ {self.address}")
        if self.hours:
            chunks.append(f"⏱ {self.hours}")
        return " ".join(chunks)

    def maps_url(self) -> str:
        return (
            f"https://yandex.ru/maps/?ll={self.lon},{self.lat}"
            f"&z=17&pt={self.lon},{self.lat},pm2rdm"
        )


def is_supported(category: str) -> bool:
    return category in SUPPORTED and bool(API_KEY)


def build_query(category: str, emotion: str) -> str:
    bases = CATEGORY_QUERIES.get(category, [])
    if not bases:
        return ""
    base = random.choice(bases)
    adj = EMOTION_ADJECTIVE.get(emotion, "")
    if adj and category == "cat_restaurants":
        # Прилагательное помогает только для ресторанов; для спорта/природы — мешает поиску.
        return f"{adj} {base} Москва"
    return f"{base} Москва"


async def fetch_places(category: str, emotion: str, limit: int = 15) -> list[Place]:
    if not is_supported(category):
        return []
    query = build_query(category, emotion)
    if not query:
        return []

    cache_key = query
    now = time.time()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_TTL:
        return cached[1]

    params = {
        "apikey": API_KEY,
        "text": query,
        "lang": "ru_RU",
        "type": "biz",
        "results": str(limit),
        "bbox": MOSCOW_BBOX,
        "rspn": "1",  # ограничивать рамкой Москвы
    }
    headers = {"User-Agent": "nedumai-bot/1.0"}
    timeout = aiohttp.ClientTimeout(total=8)

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(API_URL, params=params) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Yandex Places %s -> %s: %s", query, resp.status, body[:200])
                    return []
                data = await resp.json()
    except Exception:
        logger.exception("Yandex Places fetch failed for %s", query)
        return []

    features = data.get("features") or []
    places: list[Place] = []
    for f in features:
        place = _parse_feature(f)
        if place:
            places.append(place)

    logger.info("Yandex Places '%s' -> %d", query, len(places))
    _cache[cache_key] = (now, places)
    return places


def _parse_feature(f: dict) -> Place | None:
    geom = f.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if len(coords) != 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])

    props = f.get("properties") or {}
    meta = props.get("CompanyMetaData") or {}
    name = (meta.get("name") or "").strip()
    if not name:
        return None
    address = (meta.get("address") or "").strip()
    url = (meta.get("url") or "").strip()
    phones = meta.get("Phones") or []
    phone = phones[0].get("formatted", "") if phones else ""
    cats_raw = meta.get("Categories") or []
    cats_list = [c.get("name", "") for c in cats_raw if c.get("name")]
    categories = ", ".join(cats_list[:3])

    hours_obj = meta.get("Hours") or {}
    hours = hours_obj.get("text", "")

    place_id = str(meta.get("id") or f"{lon:.5f},{lat:.5f}")

    return Place(
        id=place_id,
        name=name,
        address=address,
        url=url,
        phone=phone,
        categories=categories,
        hours=hours,
        lon=lon,
        lat=lat,
    )
