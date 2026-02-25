"""Unit tests for calendar module with mocked Google API."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Import after patching auth
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@patch("calendar_mcp.calendar.get_credentials")
@patch("calendar_mcp.calendar.build")
def test_create_event_success(mock_build, mock_get_creds):
    from calendar_mcp import calendar
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_get_creds.return_value = MagicMock()

    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    mock_service.events().insert().execute.return_value = {
        "id": "ev123",
        "summary": "Test Meeting",
        "start": {"dateTime": future},
        "end": {"dateTime": future},
        "location": "",
    }

    result = calendar.create_event(
        title="Test Meeting",
        start_time=future,
        duration_minutes=60,
    )
    assert "Created event" in result
    assert "ev123" in result
    assert "Test Meeting" in result


@patch("calendar_mcp.calendar.get_credentials")
@patch("calendar_mcp.calendar.build")
def test_create_event_past(mock_build, mock_get_creds):
    from calendar_mcp import calendar
    mock_get_creds.return_value = MagicMock()

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    result = calendar.create_event(
        title="Past Meeting",
        start_time=past,
        duration_minutes=60,
    )
    assert "Error" in result
    assert "past" in result.lower()


@patch("calendar_mcp.calendar.get_credentials")
def test_create_event_no_credentials(mock_get_creds):
    from calendar_mcp import calendar
    mock_get_creds.side_effect = FileNotFoundError("No credentials")

    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    result = calendar.create_event(
        title="Test",
        start_time=future,
    )
    assert "Authentication expired" in result


@patch("calendar_mcp.calendar.get_credentials")
@patch("calendar_mcp.calendar.build")
def test_list_events_success(mock_build, mock_get_creds):
    from calendar_mcp import calendar
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_get_creds.return_value = MagicMock()

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    mock_service.events().list().execute.return_value = {
        "items": [
            {
                "id": "ev1",
                "summary": "Meeting 1",
                "start": {"dateTime": future},
                "end": {"dateTime": future},
                "location": "",
            }
        ]
    }

    result = calendar.list_events(max_results=5)
    assert "ev1" in result
    assert "Meeting 1" in result


@patch("calendar_mcp.calendar.get_credentials")
@patch("calendar_mcp.calendar.build")
def test_list_events_empty(mock_build, mock_get_creds):
    from calendar_mcp import calendar
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_get_creds.return_value = MagicMock()
    mock_service.events().list().execute.return_value = {"items": []}

    result = calendar.list_events(max_results=5)
    assert "No upcoming events" in result


@patch("calendar_mcp.calendar.get_credentials")
@patch("calendar_mcp.calendar.build")
def test_get_free_slots(mock_build, mock_get_creds):
    from calendar_mcp import calendar
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_get_creds.return_value = MagicMock()
    mock_service.settings().get().execute.return_value = {"value": "UTC"}
    mock_service.freebusy().query().execute.return_value = {
        "calendars": {
            "primary": {"busy": []}
        }
    }

    start = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=2)
    result = calendar.get_free_slots(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        min_duration_minutes=30,
    )
    assert "Free slots" in result or "free" in result.lower()


@patch("calendar_mcp.calendar.get_credentials")
@patch("calendar_mcp.calendar.build")
def test_update_event_not_found(mock_build, mock_get_creds):
    from googleapiclient.errors import HttpError
    from calendar_mcp import calendar

    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_get_creds.return_value = MagicMock()
    error = HttpError(MagicMock(status=404), b"Not Found")
    mock_service.events().get().execute.side_effect = error

    result = calendar.update_event(event_id="nonexistent", title="New Title")
    assert "Error" in result
    assert "not found" in result.lower()
