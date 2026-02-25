"""OAuth2 token handling and automatic refresh."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Paths relative to project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CREDENTIALS_FILE = _PROJECT_ROOT / "credentials" / "client_secret.json"
_TOKEN_FILE = _PROJECT_ROOT / "token.json"


def get_credentials() -> Credentials:
    """
    Return valid credentials for Google Calendar API.
    Loads from token.json, refreshes if expired, or runs OAuth flow if no token.
    Raises if credentials file is missing or OAuth flow cannot run (e.g. in MCP context).
    """
    creds = None
    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Credentials file not found at {_CREDENTIALS_FILE}. "
                    "Download client_secret.json from Google Cloud Console and place it in credentials/."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(_CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Persist credentials
        _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def run_oauth_flow() -> None:
    """
    Run the OAuth flow and save token.json.
    Call this via: python -m calendar_mcp.auth
    """
    if not _CREDENTIALS_FILE.exists():
        print(f"Error: Credentials file not found at {_CREDENTIALS_FILE}")
        print("Download client_secret.json from Google Cloud Console and place it in credentials/.")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(_CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {_TOKEN_FILE}")


if __name__ == "__main__":
    run_oauth_flow()
