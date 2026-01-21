"""Tests for the scheduler module."""

from claude_meet.scheduler import (
    calculate_end_time,
    find_free_gaps,
    find_mutual_availability,
    merge_busy_periods,
    score_time_slot,
    time_diff_minutes,
)


class TestMergeBusyPeriods:
    """Tests for merge_busy_periods function."""

    def test_empty_list(self):
        """Empty input returns empty output."""
        result = merge_busy_periods([])
        assert result == []

    def test_single_period(self):
        """Single period returns unchanged."""
        periods = [{"start": "2026-01-20T10:00:00-08:00", "end": "2026-01-20T11:00:00-08:00"}]
        result = merge_busy_periods(periods)
        assert len(result) == 1
        assert result[0]["start"] == periods[0]["start"]

    def test_non_overlapping(self):
        """Non-overlapping periods remain separate."""
        periods = [
            {"start": "2026-01-20T10:00:00-08:00", "end": "2026-01-20T11:00:00-08:00"},
            {"start": "2026-01-20T14:00:00-08:00", "end": "2026-01-20T15:00:00-08:00"},
        ]
        result = merge_busy_periods(periods)
        assert len(result) == 2

    def test_overlapping_periods(self):
        """Overlapping periods are merged."""
        periods = [
            {"start": "2026-01-20T10:00:00-08:00", "end": "2026-01-20T11:30:00-08:00"},
            {"start": "2026-01-20T11:00:00-08:00", "end": "2026-01-20T12:00:00-08:00"},
        ]
        result = merge_busy_periods(periods)
        assert len(result) == 1
        assert result[0]["start"] == "2026-01-20T10:00:00-08:00"
        assert result[0]["end"] == "2026-01-20T12:00:00-08:00"

    def test_adjacent_periods(self):
        """Adjacent periods are merged."""
        periods = [
            {"start": "2026-01-20T10:00:00-08:00", "end": "2026-01-20T11:00:00-08:00"},
            {"start": "2026-01-20T11:00:00-08:00", "end": "2026-01-20T12:00:00-08:00"},
        ]
        result = merge_busy_periods(periods)
        assert len(result) == 1


class TestTimeDiffMinutes:
    """Tests for time_diff_minutes function."""

    def test_one_hour_diff(self):
        """One hour difference returns 60."""
        result = time_diff_minutes("2026-01-20T10:00:00-08:00", "2026-01-20T11:00:00-08:00")
        assert result == 60

    def test_30_minutes_diff(self):
        """30 minutes difference."""
        result = time_diff_minutes("2026-01-20T10:00:00-08:00", "2026-01-20T10:30:00-08:00")
        assert result == 30

    def test_zero_diff(self):
        """Same time returns 0."""
        result = time_diff_minutes("2026-01-20T10:00:00-08:00", "2026-01-20T10:00:00-08:00")
        assert result == 0

    def test_negative_diff_returns_zero(self):
        """End before start returns 0."""
        result = time_diff_minutes("2026-01-20T11:00:00-08:00", "2026-01-20T10:00:00-08:00")
        assert result == 0


class TestScoreTimeSlot:
    """Tests for score_time_slot function."""

    def test_morning_preferred(self):
        """Morning slots (9-11am) get bonus."""
        score_9am = score_time_slot("2026-01-20T09:00:00-08:00")
        score_10am = score_time_slot("2026-01-20T10:00:00-08:00")

        # Both should be above base score (50)
        assert score_9am > 50
        assert score_10am > 50

    def test_lunch_penalty(self):
        """Lunch time (12-1pm) gets penalty."""
        score_lunch = score_time_slot("2026-01-20T12:00:00-08:00")
        score_morning = score_time_slot("2026-01-20T10:00:00-08:00")

        assert score_lunch < score_morning

    def test_after_hours_penalty(self):
        """After 5pm gets significant penalty."""
        score_evening = score_time_slot("2026-01-20T18:00:00-08:00")
        score_afternoon = score_time_slot("2026-01-20T14:00:00-08:00")

        assert score_evening < score_afternoon

    def test_early_morning_penalty(self):
        """Before 9am gets penalty."""
        score_early = score_time_slot("2026-01-20T07:00:00-08:00")
        score_normal = score_time_slot("2026-01-20T09:00:00-08:00")

        assert score_early < score_normal

    def test_preferences_applied(self):
        """User preferences modify scores."""
        base_score = score_time_slot("2026-01-20T10:00:00-08:00")
        pref_score = score_time_slot(
            "2026-01-20T10:00:00-08:00", preferences={"prefer_morning": True}
        )

        assert pref_score > base_score


class TestFindFreeGaps:
    """Tests for find_free_gaps function."""

    def test_no_busy_periods(self):
        """All time is free when no busy periods."""
        result = find_free_gaps([], "2026-01-20T09:00:00-08:00", "2026-01-20T17:00:00-08:00", 60)
        assert len(result) == 1
        assert result[0]["start"] == "2026-01-20T09:00:00-08:00"

    def test_finds_gap_before_meeting(self):
        """Finds gap before first busy period."""
        busy = [{"start": "2026-01-20T11:00:00-08:00", "end": "2026-01-20T12:00:00-08:00"}]
        result = find_free_gaps(busy, "2026-01-20T09:00:00-08:00", "2026-01-20T17:00:00-08:00", 60)

        # Should find gap 9-11am
        assert any(gap["start"] == "2026-01-20T09:00:00-08:00" for gap in result)

    def test_respects_minimum_duration(self):
        """Short gaps are filtered out."""
        busy = [{"start": "2026-01-20T09:30:00-08:00", "end": "2026-01-20T17:00:00-08:00"}]
        result = find_free_gaps(
            busy,
            "2026-01-20T09:00:00-08:00",
            "2026-01-20T17:00:00-08:00",
            60,  # Require 60 minutes
        )

        # 30 minute gap shouldn't be included
        assert len(result) == 0


class TestCalculateEndTime:
    """Tests for calculate_end_time function."""

    def test_adds_60_minutes(self):
        """Adds 60 minutes correctly."""
        result = calculate_end_time("2026-01-20T14:00:00-08:00", 60)
        assert "15:00:00" in result

    def test_adds_30_minutes(self):
        """Adds 30 minutes correctly."""
        result = calculate_end_time("2026-01-20T14:00:00-08:00", 30)
        assert "14:30:00" in result

    def test_crosses_hour(self):
        """Handles crossing hour boundary."""
        result = calculate_end_time("2026-01-20T14:45:00-08:00", 30)
        assert "15:15:00" in result


class TestFindMutualAvailability:
    """Tests for find_mutual_availability function."""

    def test_empty_busy_periods(self):
        """When everyone is free, returns full range."""
        busy = {
            "alice@example.com": [],
            "bob@example.com": [],
        }
        result = find_mutual_availability(
            busy, "2026-01-20T09:00:00-08:00", "2026-01-20T17:00:00-08:00", 60
        )
        assert len(result) > 0

    def test_overlapping_busy_periods(self):
        """Handles overlapping busy times from different people."""
        busy = {
            "alice@example.com": [
                {"start": "2026-01-20T10:00:00-08:00", "end": "2026-01-20T11:00:00-08:00"}
            ],
            "bob@example.com": [
                {"start": "2026-01-20T10:30:00-08:00", "end": "2026-01-20T11:30:00-08:00"}
            ],
        }
        result = find_mutual_availability(
            busy, "2026-01-20T09:00:00-08:00", "2026-01-20T17:00:00-08:00", 60
        )

        # Should find time before 10am and after 11:30am
        assert len(result) > 0

    def test_results_sorted_by_score(self):
        """Results are sorted with best times first."""
        busy = {
            "alice@example.com": [],
        }
        result = find_mutual_availability(
            busy, "2026-01-20T09:00:00-08:00", "2026-01-20T17:00:00-08:00", 60
        )

        # Check scores are in descending order
        scores = [slot["score"] for slot in result]
        assert scores == sorted(scores, reverse=True)
