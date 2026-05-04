import os

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from data.texts import MAIN_TEXT, START_TEXT
from keyboards.categories import categories_kb, start_kb

router = Router()

_WELCOME_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "welcome.jpg")


async def _send_start(message: Message) -> None:
    if os.path.exists(_WELCOME_IMAGE_PATH):
        await message.answer_photo(
            FSInputFile(_WELCOME_IMAGE_PATH),
            caption=START_TEXT,
            reply_markup=start_kb(),
        )
    else:
        await message.answer(START_TEXT, reply_markup=start_kb())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_start(message)


@router.callback_query(F.data == "go")
async def go_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(MAIN_TEXT, reply_markup=categories_kb())
    await callback.answer()


@router.callback_query(F.data == "home")
async def go_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(MAIN_TEXT, reply_markup=categories_kb())
    await callback.answer()
