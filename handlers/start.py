from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from data.texts import MAIN_TEXT, START_TEXT
from keyboards.categories import categories_kb, start_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_TEXT, reply_markup=start_kb())


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
