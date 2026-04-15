"""SM-2 Spaced Repetition System algorithm implementation."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class SRSResult:
    interval: int          # days until next review
    repetition_count: int
    easiness_factor: float
    next_review: datetime


def calculate_next_review(
    grade: int,
    repetition_count: int,
    easiness_factor: float,
    interval: int,
) -> SRSResult:
    """
    Implementation of the SM-2 algorithm.

    Grade scale:
        5 – perfect recall
        4 – correct with minor hesitation
        3 – correct with serious difficulty
        2 – incorrect but correct answer was easy to recall
        1 – incorrect; correct answer was hard to recall
        0 – complete blackout

    Returns updated SRS parameters and the next review date.
    """
    if grade < 3:
        # Incorrect – restart repetition count, keep EF
        new_repetition_count = 0
        new_interval = 1
    else:
        if repetition_count == 0:
            new_interval = 1
        elif repetition_count == 1:
            new_interval = 6
        else:
            new_interval = round(interval * easiness_factor)

        new_repetition_count = repetition_count + 1

    # Update easiness factor (clamped to minimum 1.3)
    new_ef = easiness_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    new_ef = max(1.3, new_ef)

    next_review = datetime.now(timezone.utc) + timedelta(days=new_interval)

    return SRSResult(
        interval=new_interval,
        repetition_count=new_repetition_count,
        easiness_factor=new_ef,
        next_review=next_review,
    )


def get_review_direction(repetition_count: int) -> str:
    """
    Determine the direction of a review prompt.

    For the first 3 repetitions: always show target language word.
    After 3 repetitions: 50/50 chance of either direction.
    """
    import random

    if repetition_count < 3:
        return "target_to_native"
    return random.choice(["target_to_native", "native_to_target"])
