"""Shared OAuth helper for the Google APIs (Gmail and Sheets)."""

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..config import Settings

logger = logging.getLogger(__name__)

# Gmail needs `modify` to label messages; Sheets needs full read/write.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_google_credentials(settings: Settings) -> Credentials:
    """Return valid OAuth credentials, refreshing them when expired.

    On the first run this opens a browser to authorise access. The resulting
    token is persisted to disk so subsequent runs are non-interactive.
    """
    token_path = Path(settings.google_token_file)
    creds_path = Path(settings.google_credentials_file)

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        logger.debug("Loaded token from %s", token_path)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, refreshing…")
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {creds_path}\n"
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            logger.info("Starting OAuth flow, the browser will open…")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        logger.info("Token saved to %s", token_path)

    return creds
