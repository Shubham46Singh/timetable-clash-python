
"""Shared fixtures for integration tests."""

import pytest


@pytest.fixture
def sample_timetable():
    """Example timetable data for integration tests."""
    return [
        {
            "day": "Monday",
            "subject": "Mathematics",
            "start": "09:00",
            "end": "10:00",
            "room": "A101",
        },
        {
            "day": "Monday",
            "subject": "Physics",
            "start": "09:30",
            "end": "10:30",
            "room": "B202",
        },
        {
            "day": "Monday",
            "subject": "English",
            "start": "11:00",
            "end": "12:00",
            "room": "A101",
        },
    ]
