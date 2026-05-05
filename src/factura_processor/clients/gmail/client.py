"""Gmail client: searches for invoice emails and downloads PDF attachments."""

import base64
import logging

from googleapiclient.discovery import build

from ...config import Settings
from ...utils import get_google_credentials
from .messages import Attachment, Email

logger = logging.getLogger(__name__)


class GmailClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        creds = get_google_credentials(settings)
        self._service = build("gmail", "v1", credentials=creds)
        self._label_id: str | None = None

    # ── Email search ───────────────────────────────────────────────────────────

    def get_invoice_emails(self) -> list[Email]:
        """Return every message that matches the configured Gmail query."""
        result = (
            self._service.users()
            .messages()
            .list(userId="me", q=self.settings.gmail_query)
            .execute()
        )
        message_refs = result.get("messages", [])
        logger.info("Emails found in Gmail: %d", len(message_refs))

        emails: list[Email] = []
        for ref in message_refs:
            try:
                email = self._fetch_email(ref["id"])
                if email.attachments:
                    emails.append(email)
            except Exception:
                logger.exception("Failed to fetch email %s", ref["id"])

        return emails

    def _fetch_email(self, message_id: str) -> Email:
        msg = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        subject = self._get_header(msg, "Subject")
        attachments = self._extract_pdf_attachments(msg)
        return Email(id=message_id, subject=subject, attachments=attachments)

    def _get_header(self, msg: dict, name: str) -> str:
        for h in msg.get("payload", {}).get("headers", []):
            if h["name"].lower() == name.lower():
                return h["value"]
        return ""

    # ── PDF attachment extraction ──────────────────────────────────────────────

    def _extract_pdf_attachments(self, msg: dict) -> list[Attachment]:
        attachments: list[Attachment] = []
        self._walk_parts(msg["id"], msg.get("payload", {}), attachments)
        return attachments

    def _walk_parts(self, message_id: str, part: dict, acc: list[Attachment]) -> None:
        """Walk the MIME tree recursively and pick up PDF parts."""
        if part.get("parts"):
            for subpart in part["parts"]:
                self._walk_parts(message_id, subpart, acc)
            return

        filename: str = part.get("filename", "")
        if not filename.lower().endswith(".pdf"):
            return

        body = part.get("body", {})
        attachment_id = body.get("attachmentId")

        if attachment_id:
            att = (
                self._service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            data = base64.urlsafe_b64decode(att["data"])
        elif body.get("data"):
            data = base64.urlsafe_b64decode(body["data"])
        else:
            return

        acc.append(Attachment(filename=filename, data=data))
        logger.debug("Found PDF attachment: %s (%d bytes)", filename, len(data))

    # ── Marking processed messages ─────────────────────────────────────────────

    def mark_as_processed(self, message_id: str) -> None:
        """Apply the processed label and clear UNREAD."""
        label_id = self._get_or_create_label()
        self._service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id], "removeLabelIds": ["UNREAD"]},
        ).execute()
        logger.info("Email %s marked as processed", message_id)

    def _get_or_create_label(self) -> str:
        if self._label_id:
            return self._label_id

        labels = self._service.users().labels().list(userId="me").execute()
        for label in labels.get("labels", []):
            if label["name"] == self.settings.processed_label:
                self._label_id = label["id"]
                return self._label_id

        # Label doesn't exist yet, create it on the fly.
        new_label = (
            self._service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": self.settings.processed_label,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        self._label_id = new_label["id"]
        logger.info("Created Gmail label '%s'", self.settings.processed_label)
        return self._label_id
