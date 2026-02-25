# Calendar MCP Assistant for Cursor

MCP server that exposes Google Calendar tools so you can use Cursor (with its built-in voice input) as a calendar assistant. Create events, check availability, see what's scheduled at a given time, and list upcoming events.

## Features

- **create_calendar_event** — Create events with title, start time, duration, location, description
- **update_calendar_event** — Update existing events by ID
- **get_free_slots** — Find available time slots within a date range (respects working hours)
- **get_events_at_time** — What should I do at 2pm? Returns events at a specific datetime
- **list_upcoming_events** — List the next N upcoming events

All datetime parameters use **ISO8601** (e.g., `2026-02-25T14:00:00+08:00`). Cursor's LLM handles natural language → ISO8601 conversion.

## Setup

### 1. Google Cloud credentials

1. Create a [Google Cloud project](https://console.cloud.google.com/)
2. Enable the [Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
3. Configure the [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) (Internal or External)
4. Create [OAuth 2.0 Desktop credentials](https://console.cloud.google.com/apis/credentials)
5. Download the JSON and save it as `credentials/client_secret.json`

### 2. Conda environment

```bash
conda env create -f environment.yml
conda activate calendar-mcp
```

### 3. OAuth flow (first run)

```bash
python -m calendar_mcp.auth
```

A browser opens for you to sign in to Google and authorize the app. The token is stored in `token.json` (gitignored). Token refresh is automatic.

### 4. Cursor MCP configuration

Add the project to Cursor and ensure the MCP server is configured. The project includes `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "calendar-assistant": {
      "command": "conda",
      "args": ["run", "-n", "calendar-mcp", "python", "-m", "calendar_mcp.server"],
      "cwd": "/path/to/assistant-agent",
      "env": { "PYTHONPATH": "src" }
    }
  }
}
```

Update `cwd` in `.cursor/mcp.json` to the full path of this project (e.g. `/home/you/assistant-agent`). Restart Cursor after adding the server.

### 5. Use voice or text in Cursor

Ask "What do I have at 2pm?" or "Create a meeting with John tomorrow at 3pm" or "List my upcoming events". Cursor will call the MCP tools automatically.

## Revoking access

Delete `token.json` and revoke the app in [Google Account permissions](https://myaccount.google.com/permissions).

## Switching accounts

Delete `token.json` and re-run `python -m calendar_mcp.auth` — the browser flow will prompt for account selection.

## Running tests

```bash
conda activate calendar-mcp
pytest tests/ -v
```

## Project structure

```
assistant-agent/
├── environment.yml
├── requirements.txt
├── src/calendar_mcp/
│   ├── auth.py      # OAuth2 + token refresh
│   ├── calendar.py  # Google Calendar API wrapper
│   ├── errors.py   # Error strings
│   └── server.py   # FastMCP server
├── credentials/     # client_secret.json (gitignored)
├── tests/
└── .cursor/mcp.json
```
