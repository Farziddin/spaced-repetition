from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⚙️ Open Settings",
        web_app=WebAppInfo(url=settings.FRONTEND_URL),
    )
    await message.answer(
        "👋 Welcome to <b>Spaced Repetition</b>!\n\n"
        "I'll help you memorize vocabulary using the scientifically proven "
        "spaced repetition method.\n\n"
        "Use /review to start your daily review session.\n"
        "Use /settings to open the WebApp and configure your preferences.",
        reply_markup=builder.as_markup(),
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⚙️ Open Settings",
        web_app=WebAppInfo(url=settings.FRONTEND_URL),
    )
    await message.answer(
        "⚙️ Open the WebApp to configure your settings and add new words:",
        reply_markup=builder.as_markup(),
    )
