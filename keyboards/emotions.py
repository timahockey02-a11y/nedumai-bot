from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def emotions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🫁 Хочу выдохнуть",   callback_data="em_exhale"),
                InlineKeyboardButton(text="😈 Хочу угореть",     callback_data="em_lol"),
            ],
            [
                InlineKeyboardButton(text="🔮 Хочу что-то новое", callback_data="em_new"),
                InlineKeyboardButton(text="🫀 Хочу почувствовать", callback_data="em_feel"),
            ],
            [
                InlineKeyboardButton(text="⚡ Хочу зарядиться",   callback_data="em_charge"),
                InlineKeyboardButton(text="🤯 Хочу удивиться",    callback_data="em_wow"),
            ],
        ]
    )


def result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Другое",   callback_data="another"),
                InlineKeyboardButton(text="🏠 В начало", callback_data="home"),
            ],
        ]
    )


def feedback_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Да",     callback_data="fb_yes"),
                InlineKeyboardButton(text="👎 Не то",  callback_data="fb_no"),
            ],
        ]
    )
