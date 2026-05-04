import json
import logging
import os
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "bot.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    category    TEXT NOT NULL,
    emotion     TEXT NOT NULL,
    name        TEXT NOT NULL,
    raw         TEXT NOT NULL,
    saved       INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rec_user ON recommendations(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_rec_saved ON recommendations(user_id, saved);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    event_type  TEXT NOT NULL,
    payload     TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evt_user ON events(user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_evt_type ON events(event_type);
"""


async def init_db() -> None:
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("DB initialized at %s", DB_PATH)


async def log_event(user_id: int, event_type: str, payload: dict | None = None) -> None:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO events (user_id, event_type, payload) VALUES (?, ?, ?)",
                (user_id, event_type, json.dumps(payload, ensure_ascii=False) if payload else None),
            )
            await db.commit()
    except Exception:
        logger.exception("log_event failed")


async def save_recommendation(
    user_id: int, category: str, emotion: str, name: str, raw: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO recommendations (user_id, category, emotion, name, raw) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, category, emotion, name, raw),
        )
        await db.commit()
        return cur.lastrowid


async def mark_saved(rec_id: int) -> tuple[str, str] | None:
    """Returns (name, raw) of the saved recommendation or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE recommendations SET saved = 1 WHERE id = ?", (rec_id,))
        await db.commit()
        async with db.execute(
            "SELECT name, raw FROM recommendations WHERE id = ?", (rec_id,)
        ) as cur:
            row = await cur.fetchone()
            return (row[0], row[1]) if row else None


async def get_saved(user_id: int, limit: int = 50) -> list[tuple[str, str, str]]:
    """Returns list of (category, name, raw) tuples for saved recommendations."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT category, name, raw FROM recommendations "
            "WHERE user_id = ? AND saved = 1 ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            return [(r[0], r[1], r[2]) async for r in cur]


async def get_recent_names(user_id: int, limit: int = 30) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name FROM recommendations "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            return [r[0] async for r in cur]


async def stats() -> dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        async def scalar(sql: str, params: tuple = ()) -> Any:
            async with db.execute(sql, params) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

        async def rows(sql: str, params: tuple = ()) -> list[tuple]:
            async with db.execute(sql, params) as cur:
                return [r async for r in cur]

        users_total = await scalar(
            "SELECT COUNT(DISTINCT user_id) FROM events"
        )
        users_today = await scalar(
            "SELECT COUNT(DISTINCT user_id) FROM events WHERE created_at >= date('now')"
        )
        recs_total = await scalar("SELECT COUNT(*) FROM recommendations")
        saved_total = await scalar("SELECT COUNT(*) FROM recommendations WHERE saved = 1")

        top_categories = await rows(
            "SELECT category, COUNT(*) c FROM recommendations "
            "GROUP BY category ORDER BY c DESC LIMIT 6"
        )
        top_emotions = await rows(
            "SELECT emotion, COUNT(*) c FROM recommendations "
            "GROUP BY emotion ORDER BY c DESC LIMIT 6"
        )
        top_events = await rows(
            "SELECT event_type, COUNT(*) c FROM events "
            "GROUP BY event_type ORDER BY c DESC LIMIT 10"
        )

        return {
            "users_total": users_total,
            "users_today": users_today,
            "recs_total": recs_total,
            "saved_total": saved_total,
            "top_categories": top_categories,
            "top_emotions": top_emotions,
            "top_events": top_events,
        }
