import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
import time
from urllib.parse import parse_qsl

from aiohttp import web

from config import BOT_TOKEN
from data.texts import CATEGORY_NAMES, EMOTION_DESCRIPTIONS
from services.db import (
    block_name,
    get_saved,
    log_event,
    mark_saved,
)
from services.recommender import build_recommendation, map_url_for
from services.deepseek import parse_recommendation

logger = logging.getLogger(__name__)

WEBAPP_ORIGIN = os.getenv("WEBAPP_ORIGIN", "https://timahockey02-a11y.github.io")
INIT_DATA_TTL = 3600  # 1 час
DEV_MODE = os.getenv("WEB_API_DEV_MODE", "0") == "1"


def _verify_init_data(raw: str, bot_token: str) -> dict | None:
    """Верифицирует Telegram WebApp initData. Возвращает user dict или None."""
    if not raw:
        return None
    try:
        pairs = dict(parse_qsl(raw, strict_parsing=True))
    except Exception:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    auth_date_raw = pairs.get("auth_date", "0")
    try:
        if time.time() - int(auth_date_raw) > INIT_DATA_TTL:
            return None
    except ValueError:
        return None

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        return None

    user_raw = pairs.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except Exception:
        return None


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        return _cors_response(web.Response(status=204))
    response = await handler(request)
    return _cors_response(response)


def _cors_response(response: web.StreamResponse) -> web.StreamResponse:
    response.headers["Access-Control-Allow-Origin"] = WEBAPP_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if request.method == "OPTIONS" or request.path == "/api/health":
        return await handler(request)

    raw = request.headers.get("X-Telegram-Init-Data", "")
    user = _verify_init_data(raw, BOT_TOKEN)

    if user is None and DEV_MODE:
        user = {"id": int(os.getenv("WEB_API_DEV_USER_ID", "1"))}

    if not user or "id" not in user:
        return web.json_response({"error": "unauthorized"}, status=401)

    request["user_id"] = int(user["id"])
    request["user"] = user
    return await handler(request)


def _serialize_rec(rec_id: int, category: str, name: str, raw: str) -> dict:
    parsed = parse_recommendation(raw)
    title = parsed.name or name
    map_url = None
    # Прокидываем map_url_override если он есть в raw (для Yandex Places кладём КАРТА:).
    for line in raw.splitlines():
        if line.upper().startswith("КАРТА:"):
            url = line.split(":", 1)[1].strip()
            if url.startswith("http"):
                map_url = url
                break
    if map_url is None:
        parsed.name = title
        map_url = map_url_for(category, parsed)
    return {
        "rec_id": rec_id,
        "category": category,
        "name": title,
        "description": parsed.description,
        "address": parsed.address,
        "price": parsed.price,
        "link": parsed.link,
        "map_url": map_url,
    }


async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def recommend(request: web.Request) -> web.Response:
    user_id: int = request["user_id"]
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "bad_json"}, status=400)

    if body.get("surprise"):
        category = random.choice(list(CATEGORY_NAMES.keys()))
        emotion = random.choice(list(EMOTION_DESCRIPTIONS.keys()))
        await log_event(user_id, "miniapp_surprise")
    else:
        category = body.get("category")
        emotion = body.get("emotion")
        if category not in CATEGORY_NAMES or emotion not in EMOTION_DESCRIPTIONS:
            return web.json_response({"error": "bad_params"}, status=400)

    await log_event(user_id, "miniapp_choice", {"category": category, "emotion": emotion})

    result = await build_recommendation(user_id, category, emotion)
    if result is None:
        return web.json_response({"error": "no_recommendation"}, status=502)

    rec_id, rec, map_url = result
    return web.json_response({
        "rec_id": rec_id,
        "category": category,
        "emotion": emotion,
        "name": rec.name,
        "description": rec.description,
        "address": rec.address,
        "price": rec.price,
        "link": rec.link,
        "map_url": map_url,
        "confidence": rec.confidence,
    })


async def save_handler(request: web.Request) -> web.Response:
    user_id: int = request["user_id"]
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "bad_json"}, status=400)
    rec_id = body.get("rec_id")
    if not isinstance(rec_id, int):
        return web.json_response({"error": "bad_params"}, status=400)

    saved = await mark_saved(int(rec_id))
    if saved is None:
        return web.json_response({"error": "not_found"}, status=404)
    await log_event(user_id, "save", {"rec_id": rec_id, "source": "miniapp"})
    return web.json_response({"ok": True})


async def reject_handler(request: web.Request) -> web.Response:
    user_id: int = request["user_id"]
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "bad_json"}, status=400)
    name = (body.get("name") or "").strip()
    if name:
        await block_name(user_id, name)
    await log_event(user_id, "reject", {"name": name, "source": "miniapp"})
    return web.json_response({"ok": True})


async def saved_list(request: web.Request) -> web.Response:
    user_id: int = request["user_id"]
    items = await get_saved(user_id, limit=50)
    payload = []
    for category, name, raw in items:
        payload.append(_serialize_rec(0, category, name, raw))
    return web.json_response({"items": payload})


def build_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware, auth_middleware])
    app.router.add_get("/api/health", health)
    app.router.add_post("/api/recommend", recommend)
    app.router.add_post("/api/save", save_handler)
    app.router.add_post("/api/reject", reject_handler)
    app.router.add_get("/api/saved", saved_list)

    # OPTIONS preflight для всех /api/*
    async def options_any(request: web.Request) -> web.Response:
        return web.Response(status=204)
    app.router.add_route("OPTIONS", "/api/{tail:.*}", options_any)

    return app


async def run_web_api(port: int) -> None:
    app = build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Web API listening on :%d (origin=%s, dev=%s)", port, WEBAPP_ORIGIN, DEV_MODE)
    # Держим таску живой
    while True:
        await asyncio.sleep(3600)
