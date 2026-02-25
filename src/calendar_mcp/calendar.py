"""Google Calendar API wrapper."""

import logging
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth import get_credentials
from . import errors

logger = logging.getLogger(__name__)

_DEFAULT_TIMEZONE = "UTC"


def _get_service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


def _get_user_timezone(service) -> str:
    """Read user's default timezone from Calendar settings."""
    try:
        setting = service.settings().get(setting="timezone").execute()
        return setting.get("value", _DEFAULT_TIMEZONE)
    except Exception:
        return _DEFAULT_TIMEZONE


def _parse_iso8601(s: str) -> datetime:
    """Parse ISO8601 string to datetime. Handles 'Z' and offset formats."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _format_event_summary(event: dict) -> str:
    """Format event for human-readable output, including ID."""
    eid = event.get("id", "?")
    summary = event.get("summary", "(No title)")
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime") or start.get("date", "?")
    end_str = end.get("dateTime") or end.get("date", "?")
    location = event.get("location", "")
    loc_part = f" @ {location}" if location else ""
    return f"ID: {eid} | {summary} | {start_str} - {end_str}{loc_part}"


def create_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    calendar_id: str = "primary",
) -> str:
    """Create a calendar event. Returns the created event ID and confirmation details."""
    try:
        service = _get_service()
        start_dt = _parse_iso8601(start_time)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=_get_tz_aware_now().tzinfo)
        if start_dt < _get_tz_aware_now():
            return errors.event_in_past(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return f"Created event: {_format_event_summary(event)}"
    except FileNotFoundError as e:
        return errors.AUTH_EXPIRED
    except HttpError as e:
        if e.resp.status == 403 and "quota" in str(e).lower():
            return errors.QUOTA_EXCEEDED
        if e.resp.status >= 500:
            return errors.NETWORK_FAILURE
        return errors.unexpected_failure(str(e))
    except Exception as e:
        logger.exception("create_event failed")
        return errors.unexpected_failure(str(e))


def _get_tz_aware_now():
    return datetime.now().astimezone()


def update_event(
    event_id: str,
    title: str | None = None,
    start_time: str | None = None,
    duration_minutes: int | None = None,
    description: str | None = None,
    location: str | None = None,
    calendar_id: str = "primary",
) -> str:
    """Update an existing event. Only provided fields are changed."""
    try:
        service = _get_service()
        existing = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    except FileNotFoundError:
        return errors.AUTH_EXPIRED
    except HttpError as e:
        if e.resp.status == 404:
            return errors.event_not_found(event_id)
        if e.resp.status == 403 and "quota" in str(e).lower():
            return errors.QUOTA_EXCEEDED
        if e.resp.status >= 500:
            return errors.NETWORK_FAILURE
        return errors.unexpected_failure(str(e))
    except Exception as e:
        logger.exception("update_event get failed")
        return errors.unexpected_failure(str(e))

    # Build patch body with only provided fields
    patch = {}
    if title is not None:
        patch["summary"] = title
    if description is not None:
        patch["description"] = description
    if location is not None:
        patch["location"] = location
    if start_time is not None:
        start_dt = _parse_iso8601(start_time)
        patch["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
        if duration_minutes is not None:
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            patch["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}
        else:
            # Preserve duration from existing
            old_start = existing.get("start", {}).get("dateTime") or existing.get("start", {}).get("date")
            old_end = existing.get("end", {}).get("dateTime") or existing.get("end", {}).get("date")
            if old_start and old_end:
                s = _parse_iso8601(old_start)
                e = _parse_iso8601(old_end)
                dur = (e - s).total_seconds() / 60
                end_dt = start_dt + timedelta(minutes=dur)
                patch["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}
    elif duration_minutes is not None:
        old_start = existing.get("start", {}).get("dateTime") or existing.get("start", {}).get("date")
        if old_start:
            start_dt = _parse_iso8601(old_start)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            patch["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "UTC"}

    if not patch:
        return f"No changes provided. Event: {_format_event_summary(existing)}"

    try:
        updated = service.events().patch(
            calendarId=calendar_id, eventId=event_id, body=patch
        ).execute()
        return f"Updated event: {_format_event_summary(updated)}"
    except HttpError as e:
        if e.resp.status == 404:
            return errors.event_not_found(event_id)
        if e.resp.status == 403 and "quota" in str(e).lower():
            return errors.QUOTA_EXCEEDED
        if e.resp.status >= 500:
            return errors.NETWORK_FAILURE
        return errors.unexpected_failure(str(e))
    except Exception as e:
        logger.exception("update_event patch failed")
        return errors.unexpected_failure(str(e))


def get_free_slots(
    start_date: str,
    end_date: str,
    min_duration_minutes: int = 30,
    working_hours_start: int = 9,
    working_hours_end: int = 18,
    calendar_id: str = "primary",
) -> str:
    """Return available time slots within the date range, filtered by working hours and minimum duration."""
    try:
        service = _get_service()
        tz = _get_user_timezone(service)
        start_dt = _parse_iso8601(start_date)
        end_dt = _parse_iso8601(end_date)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=start_dt.tzinfo)
    except FileNotFoundError:
        return errors.AUTH_EXPIRED
    except Exception as e:
        logger.exception("get_free_slots parse failed")
        return errors.unexpected_failure(str(e))

    try:
        body = {
            "timeMin": start_dt.isoformat(),
            "timeMax": end_dt.isoformat(),
            "items": [{"id": calendar_id}],
        }
        result = service.freebusy().query(body=body).execute()
        busy_list = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
    except HttpError as e:
        if e.resp.status == 403 and "quota" in str(e).lower():
            return errors.QUOTA_EXCEEDED
        if e.resp.status >= 500:
            return errors.NETWORK_FAILURE
        return errors.unexpected_failure(str(e))
    except Exception as e:
        logger.exception("get_free_slots query failed")
        return errors.unexpected_failure(str(e))

    # Build busy ranges
    busy_ranges = []
    for b in busy_list:
        busy_ranges.append(
            (_parse_iso8601(b["start"]), _parse_iso8601(b["end"]))
        )
    busy_ranges.sort(key=lambda x: x[0])

    # Compute free slots as gaps, then clip to working hours per day
    def clip_to_working_hours(gap_start: datetime, gap_end: datetime):
        """Yield (start, end) segments of gap that fall within working hours."""
        current = gap_start
        while current < gap_end:
            work_start = current.replace(
                hour=working_hours_start, minute=0, second=0, microsecond=0
            )
            work_end = current.replace(
                hour=working_hours_end, minute=0, second=0, microsecond=0
            )
            slot_start = max(current, work_start)
            slot_end = min(gap_end, work_end)
            if slot_start < slot_end and (slot_end - slot_start).total_seconds() >= min_duration_minutes * 60:
                yield (slot_start, slot_end)
            # Advance to start of next day's working hours
            next_day = current.date() + timedelta(days=1)
            current = datetime(
                next_day.year, next_day.month, next_day.day,
                working_hours_start, 0, 0, tzinfo=gap_start.tzinfo
            )

    free_slots = []
    current = start_dt
    for bs, be in busy_ranges:
        if be <= current:
            continue
        if bs > current:
            for slot in clip_to_working_hours(current, min(bs, end_dt)):
                free_slots.append(slot)
        current = max(current, be)
        if current >= end_dt:
            break
    if current < end_dt:
        for slot in clip_to_working_hours(current, end_dt):
            free_slots.append(slot)

    if not free_slots:
        return "No free slots found in the given range."
    lines = [f"Free slots ({min_duration_minutes}min min, {working_hours_start}:00-{working_hours_end}:00):"]
    for s, e in free_slots:
        lines.append(f"  {s.isoformat()} - {e.isoformat()}")
    return "\n".join(lines)


def get_events_at_time(datetime_str: str, calendar_id: str = "primary") -> str:
    """Return events occurring at the given datetime. Each event includes its ID for use in update."""
    try:
        service = _get_service()
        dt = _parse_iso8601(datetime_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        window_start = dt - timedelta(days=1)
        window_end = dt + timedelta(days=1)
    except FileNotFoundError:
        return errors.AUTH_EXPIRED
    except Exception as e:
        logger.exception("get_events_at_time parse failed")
        return errors.unexpected_failure(str(e))

    try:
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=window_start.isoformat(),
                timeMax=window_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
    except HttpError as e:
        if e.resp.status == 403 and "quota" in str(e).lower():
            return errors.QUOTA_EXCEEDED
        if e.resp.status >= 500:
            return errors.NETWORK_FAILURE
        return errors.unexpected_failure(str(e))
    except Exception as e:
        logger.exception("get_events_at_time list failed")
        return errors.unexpected_failure(str(e))

    # Filter for events that overlap dt
    overlapping = []
    for ev in events:
        start_raw = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
        end_raw = ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")
        if not start_raw or not end_raw:
            continue
        ev_start = _parse_iso8601(start_raw)
        ev_end = _parse_iso8601(end_raw)
        if ev_start.tzinfo is None:
            ev_start = ev_start.replace(tzinfo=dt.tzinfo)
        if ev_end.tzinfo is None:
            ev_end = ev_end.replace(tzinfo=dt.tzinfo)
        if ev_start <= dt <= ev_end:
            overlapping.append(ev)

    if not overlapping:
        return f"No events at {datetime_str}."
    lines = [f"Events at {datetime_str}:"]
    for ev in overlapping:
        lines.append(f"  {_format_event_summary(ev)}")
    return "\n".join(lines)


def list_events(max_results: int = 10, calendar_id: str = "primary") -> str:
    """List the next N upcoming events. Each event includes its ID for use in update."""
    try:
        service = _get_service()
        now = _get_tz_aware_now()
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
    except FileNotFoundError:
        return errors.AUTH_EXPIRED
    except HttpError as e:
        if e.resp.status == 403 and "quota" in str(e).lower():
            return errors.QUOTA_EXCEEDED
        if e.resp.status >= 500:
            return errors.NETWORK_FAILURE
        return errors.unexpected_failure(str(e))
    except Exception as e:
        logger.exception("list_events failed")
        return errors.unexpected_failure(str(e))

    if not events:
        return "No upcoming events."
    lines = [f"Next {max_results} upcoming events:"]
    for ev in events:
        lines.append(f"  {_format_event_summary(ev)}")
    return "\n".join(lines)
