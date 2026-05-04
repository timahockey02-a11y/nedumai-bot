from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def categories_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
        ]
    )


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Погнали 👊", callback_data="go")]
        ]
    )
