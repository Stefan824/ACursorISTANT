"""Structured error types for tool responses."""

AUTH_EXPIRED = "Error: Authentication expired. Please re-run OAuth flow."
EVENT_NOT_FOUND = "Error: Event ID '{event_id}' not found."
QUOTA_EXCEEDED = "Error: Google Calendar API quota exceeded. Try again later."
EVENT_IN_PAST = "Error: Cannot create event in the past. Start time {start_time} is before now."
NETWORK_FAILURE = "Error: Could not reach Google Calendar API. Check network connection."
UNEXPECTED_FAILURE = "Error: Unexpected failure — {message}"


def event_not_found(event_id: str) -> str:
    return EVENT_NOT_FOUND.format(event_id=event_id)


def event_in_past(start_time: str) -> str:
    return EVENT_IN_PAST.format(start_time=start_time)


def unexpected_failure(message: str) -> str:
    return UNEXPECTED_FAILURE.format(message=message)
