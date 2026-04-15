import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot import services
from bot.keyboards.inline import grade_keyboard

logger = logging.getLogger(__name__)
router = Router()


class ReviewState(StatesGroup):
    waiting_for_answer = State()
    waiting_for_grade = State()


@router.message(Command("review"))
async def cmd_review(message: Message, state: FSMContext):
    await state.clear()

    telegram_id = message.from_user.id
    username = message.from_user.username

    # Ensure user exists
    await services.get_or_create_user(telegram_id, username)

    items = await services.start_review(telegram_id)
    if not items:
        await message.answer("🎉 No words are due for review right now! Come back later.")
        return

    await state.update_data(
        items=items,
        current_index=0,
        session_id=items[0]["session_id"],
    )
    await _ask_word(message, state)


async def _ask_word(message_or_callback, state: FSMContext):
    data = await state.get_data()
    items = data["items"]
    idx = data["current_index"]

    if idx >= len(items):
        await _finish_session(message_or_callback, state)
        return

    item = items[idx]
    direction = item["direction"]

    if direction == "target_to_native":
        direction_hint = "Translate to your native language"
    else:
        direction_hint = "Translate to the target language"

    text = (
        f"📚 Word <b>{idx + 1}</b> of <b>{len(items)}</b>\n\n"
        f"<b>{item['prompt']}</b> {item['hint']}\n\n"
        f"<i>{direction_hint}</i>"
    )

    if hasattr(message_or_callback, "message"):
        await message_or_callback.message.answer(text)
    else:
        await message_or_callback.answer(text)

    await state.set_state(ReviewState.waiting_for_answer)
    await state.update_data(current_item=item)


@router.message(ReviewState.waiting_for_answer)
async def handle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    item = data["current_item"]

    result = await services.submit_answer(item["id"], message.text.strip())
    if not result:
        await message.answer("⚠️ Error submitting answer. Please try again with /review.")
        await state.clear()
        return

    if result["is_correct"]:
        feedback = "✅ <b>Correct!</b>"
    else:
        feedback = f"❌ <b>Incorrect.</b>\nCorrect answer: <b>{result['correct_answer']}</b>"

    await message.answer(
        f"{feedback}\n\nRate your recall quality:",
        reply_markup=grade_keyboard(item["id"]),
    )
    await state.set_state(ReviewState.waiting_for_grade)


@router.callback_query(F.data.startswith("grade:"))
async def handle_grade(callback: CallbackQuery, state: FSMContext):
    _, item_id_str, grade_str = callback.data.split(":")
    item_id = int(item_id_str)
    grade = int(grade_str)

    result = await services.submit_grade(item_id, grade)
    if result:
        next_review = result.get("next_review", "soon")
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"📅 Next review: <b>{next_review[:10] if next_review else 'soon'}</b>")

    await callback.answer()

    data = await state.get_data()
    await state.update_data(current_index=data["current_index"] + 1)
    await _ask_word(callback, state)


async def _finish_session(event, state: FSMContext):
    data = await state.get_data()
    session_id = data.get("session_id")

    report = await services.finish_session(session_id) if session_id else None

    text_parts = ["🎊 <b>Review session complete!</b>\n"]

    if report:
        remembered = report.get("remembered", [])
        forgotten = report.get("forgotten", [])

        if forgotten:
            text_parts.append("❌ <b>Words to review again:</b>")
            for w in forgotten:
                text_parts.append(f"  • {w['word']} ({w['context']}) → {w['correct_answer']}")

        if remembered:
            text_parts.append("\n✅ <b>Words you remembered:</b>")
            for w in remembered:
                text_parts.append(f"  • {w['word']} ({w['context']})")

    msg = "\n".join(text_parts)

    if hasattr(event, "message"):
        await event.message.answer(msg)
    else:
        await event.answer(msg)

    await state.clear()
