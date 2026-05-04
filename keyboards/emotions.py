from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def emotions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🫁 Расслабиться",   callback_data="em_exhale"),
                InlineKeyboardButton(text="😈 Поугарать",      callback_data="em_lol"),
            ],
            [
                InlineKeyboardButton(text="🔮 Открыть новое",  callback_data="em_new"),
                InlineKeyboardButton(text="🫀 Прочувствовать", callback_data="em_feel"),
            ],
            [
                InlineKeyboardButton(text="⚡ Зарядиться",     callback_data="em_charge"),
                InlineKeyboardButton(text="🤯 Удивиться",      callback_data="em_wow"),
            ],
        ]
    )


def result_kb(map_url: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if map_url:
        rows.append([InlineKeyboardButton(text="🗺 Открыть на карте", url=map_url)])
    rows.append([
        InlineKeyboardButton(text="🔄 Другое",            callback_data="another"),
        InlineKeyboardButton(text="🔀 Сменить настроение", callback_data="change_mood"),
    ])
    rows.append([
        InlineKeyboardButton(text="📤 Поделиться", switch_inline_query="Зацени бота «Не думай» — он подсказывает одно место под настроение."),
        InlineKeyboardButton(text="🏠 В начало",   callback_data="home"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def feedback_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Да",     callback_data="fb_yes"),
                InlineKeyboardButton(text="👎 Не то",  callback_data="fb_no"),
            ],
        ]
    )
