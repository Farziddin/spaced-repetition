"""Tests for the SM-2 SRS algorithm."""

import pytest
from datetime import datetime, timedelta, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.srs import calculate_next_review, get_review_direction


class TestCalculateNextReview:
    def test_first_correct_review_grade_5(self):
        result = calculate_next_review(
            grade=5,
            repetition_count=0,
            easiness_factor=2.5,
            interval=1,
        )
        assert result.interval == 1
        assert result.repetition_count == 1
        assert result.easiness_factor > 2.5

    def test_second_correct_review(self):
        result = calculate_next_review(
            grade=4,
            repetition_count=1,
            easiness_factor=2.5,
            interval=1,
        )
        assert result.interval == 6
        assert result.repetition_count == 2

    def test_third_and_beyond_correct_review(self):
        result = calculate_next_review(
            grade=4,
            repetition_count=2,
            easiness_factor=2.5,
            interval=6,
        )
        assert result.interval == round(6 * 2.5)
        assert result.repetition_count == 3

    def test_incorrect_answer_resets(self):
        result = calculate_next_review(
            grade=1,
            repetition_count=5,
            easiness_factor=2.5,
            interval=20,
        )
        assert result.interval == 1
        assert result.repetition_count == 0

    def test_grade_2_resets(self):
        result = calculate_next_review(
            grade=2,
            repetition_count=3,
            easiness_factor=2.5,
            interval=10,
        )
        assert result.interval == 1
        assert result.repetition_count == 0

    def test_easiness_factor_minimum(self):
        """EF should not drop below 1.3."""
        result = calculate_next_review(
            grade=1,
            repetition_count=0,
            easiness_factor=1.3,
            interval=1,
        )
        assert result.easiness_factor >= 1.3

    def test_next_review_date_is_in_future(self):
        result = calculate_next_review(
            grade=4,
            repetition_count=2,
            easiness_factor=2.5,
            interval=6,
        )
        assert result.next_review > datetime.now(timezone.utc)

    def test_perfect_recall_increases_ef(self):
        result = calculate_next_review(
            grade=5,
            repetition_count=3,
            easiness_factor=2.5,
            interval=10,
        )
        assert result.easiness_factor > 2.5

    def test_difficult_recall_decreases_ef(self):
        result = calculate_next_review(
            grade=3,
            repetition_count=3,
            easiness_factor=2.5,
            interval=10,
        )
        assert result.easiness_factor < 2.5


class TestGetReviewDirection:
    def test_first_3_reps_are_always_target_to_native(self):
        for _ in range(20):
            for rep_count in range(3):
                direction = get_review_direction(rep_count)
                assert direction == "target_to_native"

    def test_after_3_reps_can_be_either_direction(self):
        directions = set()
        for _ in range(100):
            direction = get_review_direction(5)
            directions.add(direction)
        # Both directions should appear in 100 trials
        assert "target_to_native" in directions
        assert "native_to_target" in directions
