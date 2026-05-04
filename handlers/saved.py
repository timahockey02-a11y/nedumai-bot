import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from data.texts import (
    CATEGORY_EMOJI,
    SAVED_EMPTY,
    SAVED_HEADER,
    STATS_FORBIDDEN,
)
from services.db import get_saved, log_event, stats
from services.deepseek import parse_recommendation

router = Router()

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


@router.message(Command("saved"))
async def cmd_saved(message: Message) -> None:
    user_id = message.from_user.id
    await log_event(user_id, "open_saved")

    items = await get_saved(user_id, limit=30)
    if not items:
        await message.answer(SAVED_EMPTY)
        return

    chunks = [f"<b>{SAVED_HEADER}</b>", ""]
    for category, name, raw in items:
        emoji = CATEGORY_EMOJI.get(category, "✨")
        rec = parse_recommendation(raw)
        title = rec.name or name
        block = f"{emoji} <b>{_esc(title)}</b>"
        if rec.address:
            block += f"\n📍 {_esc(rec.address)}"
        if rec.price:
            block += f"\n💰 {_esc(rec.price)}"
        chunks.append(block)
        chunks.append("")

    text = "\n".join(chunks).strip()
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not ADMIN_CHAT_ID or str(message.from_user.id) != str(ADMIN_CHAT_ID):
        await message.answer(STATS_FORBIDDEN)
        return

    s = await stats()

    def fmt_rows(rows: list[tuple], emoji_map: dict | None = None) -> str:
        if not rows:
            return "—"
        out = []
        for key, count in rows:
            label = key
            if emoji_map and key in emoji_map:
                label = f"{emoji_map[key]} {key}"
            out.append(f"  {label}: {count}")
        return "\n".join(out)

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"Пользователей всего: <b>{s['users_total']}</b>\n"
        f"Сегодня: <b>{s['users_today']}</b>\n"
        f"Рекомендаций: <b>{s['recs_total']}</b>\n"
        f"Сохранений: <b>{s['saved_total']}</b>\n\n"
        f"<b>Категории:</b>\n{fmt_rows(s['top_categories'], CATEGORY_EMOJI)}\n\n"
        f"<b>Эмоции:</b>\n{fmt_rows(s['top_emotions'])}\n\n"
        f"<b>События:</b>\n{fmt_rows(s['top_events'])}"
    )
    await message.answer(text, parse_mode="HTML")
