import asyncio
import logging
from urllib.parse import quote

from services import kudago, yandex_places
from services.db import get_blocked_names, get_recent_names, log_event, save_recommendation
from services.deepseek import Recommendation, get_recommendation, pick_event, pick_place

logger = logging.getLogger(__name__)


SKIP_MAP_CATEGORIES = {"cat_cinema"}


def yandex_maps_url(name: str, address: str) -> str | None:
    parts = [p for p in (name, address) if p]
    query = " ".join(parts).strip()
    if not query:
        return None
    return f"https://yandex.ru/maps/?text={quote(query)}"


def map_url_for(category: str, rec: Recommendation) -> str | None:
    override = getattr(rec, "map_url_override", None)
    if override:
        return override
    if category in SKIP_MAP_CATEGORIES:
        return None
    if rec.address:
        return yandex_maps_url(rec.name, rec.address)
    return yandex_maps_url(rec.name, "")


def _place_to_recommendation(place: yandex_places.Place, reason: str) -> Recommendation:
    description = reason.strip()
    raw_lines = [
        f"НАЗВАНИЕ: {place.name}",
        f"ОПИСАНИЕ: {description}",
    ]
    if place.address:
        raw_lines.append(f"АДРЕС: {place.address}")
    if place.hours:
        raw_lines.append(f"ЧАСЫ: {place.hours}")
    if place.url:
        raw_lines.append(f"ССЫЛКА: {place.url}")
    raw_lines.append(f"КАРТА: {place.maps_url()}")
    raw_lines.append("УВЕРЕННОСТЬ: высокая")

    rec = Recommendation(
        name=place.name,
        description=description,
        address=place.address,
        price="",
        link=place.url,
        confidence="высокая",
        raw="\n".join(raw_lines),
    )
    rec.map_url_override = place.maps_url()  # type: ignore[attr-defined]
    return rec


def _event_to_recommendation(event: kudago.Event, reason: str) -> Recommendation:
    description_parts = []
    if reason:
        description_parts.append(reason)
    if event.dates_str:
        description_parts.append(f"🗓 {event.dates_str}")

    address = event.address
    if event.place and event.place not in address:
        address = f"{event.place}, {address}".strip(", ")

    raw_lines = [
        f"НАЗВАНИЕ: {event.title}",
        f"ОПИСАНИЕ: {' '.join(description_parts).strip()}",
    ]
    if address:
        raw_lines.append(f"АДРЕС: {address}")
    if event.price and event.price != "—":
        raw_lines.append(f"СТОИМОСТЬ: {event.price}")
    if event.url:
        raw_lines.append(f"ССЫЛКА: {event.url}")
    raw_lines.append("УВЕРЕННОСТЬ: высокая")

    return Recommendation(
        name=event.title,
        description=" ".join(description_parts).strip(),
        address=address,
        price=event.price if event.price != "—" else "",
        link=event.url,
        confidence="высокая",
        raw="\n".join(raw_lines),
    )


async def build_recommendation(
    user_id: int,
    category: str,
    emotion: str,
    typing_delay: float = 0.0,
) -> tuple[int, Recommendation, str | None] | None:
    """Получить рекомендацию из лучшего источника, сохранить в БД, вернуть (rec_id, rec, map_url).

    Возвращает None если ничего не получилось (подняли уже залогированную ошибку).
    """
    history = await get_recent_names(user_id, limit=30)
    blocked = await get_blocked_names(user_id, limit=100)
    skip = list(set(history + blocked))

    if typing_delay > 0:
        await asyncio.sleep(typing_delay)

    rec: Recommendation | None = None
    source = "llm"

    if kudago.is_supported(category):
        try:
            events = await kudago.fetch_events(category)
        except Exception:
            logger.exception("KudaGo fetch error")
            events = []
        if events:
            try:
                picked = await pick_event(category, emotion, events, skip_titles=skip)
            except Exception:
                logger.exception("KudaGo picker failed")
                picked = None
            if picked:
                event, reason = picked
                rec = _event_to_recommendation(event, reason)
                source = "kudago"

    if rec is None and yandex_places.is_supported(category):
        try:
            places = await yandex_places.fetch_places(category, emotion)
        except Exception:
            logger.exception("Yandex Places fetch error")
            places = []
        if places:
            try:
                picked_place = await pick_place(category, emotion, places, skip_titles=skip)
            except Exception:
                logger.exception("Yandex Places picker failed")
                picked_place = None
            if picked_place:
                place, reason = picked_place
                rec = _place_to_recommendation(place, reason)
                source = "yandex_places"

    if rec is None:
        try:
            rec = await get_recommendation(
                category, emotion,
                previous_list=history, blocked=blocked, max_retries=1,
            )
        except Exception:
            logger.exception("DeepSeek request failed")
            return None

    if not rec.name:
        return None

    rec_id = await save_recommendation(user_id, category, emotion, rec.name, rec.raw)
    await log_event(
        user_id, "recommendation",
        {"category": category, "emotion": emotion, "name": rec.name,
         "conf": rec.confidence, "source": source},
    )

    return rec_id, rec, map_url_for(category, rec)
