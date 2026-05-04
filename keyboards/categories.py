import os

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()


def categories_kb() -> InlineKeyboardMarkup:
    rows = []
    if WEBAPP_URL:
        rows.append([
            InlineKeyboardButton(
                text="✨ Открыть в приложении",
                web_app=WebAppInfo(url=WEBAPP_URL),
            ),
        ])
    rows.extend([
        [
            InlineKeyboardButton(text="🎭 Театр",     callback_data="cat_theatre"),
            InlineKeyboardButton(text="🎬 Кино",      callback_data="cat_cinema"),
        ],
        [
            InlineKeyboardButton(text="🍽 Рестораны", callback_data="cat_restaurants"),
            InlineKeyboardButton(text="🌿 Природа",   callback_data="cat_nature"),
        ],
        [
            InlineKeyboardButton(text="🏃 Спорт",     callback_data="cat_sport"),
            InlineKeyboardButton(text="🖼 Выставки",  callback_data="cat_exhibitions"),
        ],
        [
            InlineKeyboardButton(text="🎲 Удиви меня — выбери за меня", callback_data="surprise"),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Погнали 👊", callback_data="go")]
        ]
    )
