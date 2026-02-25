"""FastMCP server with calendar tools."""

from mcp.server.fastmcp import FastMCP

from . import calendar as cal

mcp = FastMCP("calendar-assistant", json_response=True)


@mcp.tool()
def create_calendar_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
) -> str:
    """Create a calendar event. Returns the created event ID and confirmation details.
    start_time must be ISO8601 with timezone, e.g. 2026-02-25T14:00:00+08:00"""
    return cal.create_event(
        title=title,
        start_time=start_time,
        duration_minutes=duration_minutes,
        description=description,
        location=location,
        calendar_id=calendar_id,
    )


@mcp.tool()
def update_calendar_event(
    event_id: str,
    title: str | None = None,
    start_time: str | None = None,
    duration_minutes: int | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> str:
    """Update an existing event. Only provided fields are changed.
    start_time must be ISO8601 with timezone."""
    return cal.update_event(
        event_id=event_id,
        title=title,
        start_time=start_time,
        duration_minutes=duration_minutes,
        description=description,
        location=location,
        calendar_id=calendar_id,
    )


@mcp.tool()
def get_free_slots(
    start_date: str,
    end_date: str,
    min_duration_minutes: int = 30,
    working_hours_start: int = 9,
    working_hours_end: int = 18,
    calendar_id: str = "primary",
) -> str:
    """Return available time slots within the date range, filtered by working hours and minimum duration.
    start_date and end_date must be ISO8601 date or datetime."""
    return cal.get_free_slots(
        start_date=start_date,
        end_date=end_date,
        min_duration_minutes=min_duration_minutes,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end,
        calendar_id=calendar_id,
    )


@mcp.tool()
def get_events_at_time(
    datetime_str: str,
    calendar_id: str = "primary",
) -> str:
    """Return events occurring at the given datetime. Each event includes its ID for use in update.
    datetime_str must be ISO8601. Use this to answer 'what should I do at 2pm?'"""
    return cal.get_events_at_time(
        datetime_str=datetime_str,
        calendar_id=calendar_id,
    )


@mcp.tool()
def list_upcoming_events(
    max_results: int = 10,
    calendar_id: str = "primary",
) -> str:
    """List the next N upcoming events. Each event includes its ID for use in update."""
    return cal.list_events(
        max_results=max_results,
        calendar_id=calendar_id,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
