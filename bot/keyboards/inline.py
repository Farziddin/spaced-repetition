from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def grade_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Returns an inline keyboard for grading a review item (1-5)."""
    builder = InlineKeyboardBuilder()
    labels = {1: "1 😞", 2: "2 😕", 3: "3 😐", 4: "4 🙂", 5: "5 😄"}
    for grade, label in labels.items():
        builder.button(text=label, callback_data=f"grade:{item_id}:{grade}")
    builder.adjust(5)
    return builder.as_markup()
