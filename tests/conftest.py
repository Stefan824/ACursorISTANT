"""Shared fixtures for tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_credentials():
    """Mock Google OAuth credentials."""
    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.refresh_token = "mock_refresh"
    return creds


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar API service."""
    service = MagicMock()
    # Settings
    service.settings().get(setting="timezone").execute.return_value = {"value": "America/New_York"}
    return service
