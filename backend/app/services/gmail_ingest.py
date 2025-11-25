from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings
from ..storage.supabase_token_store import gmail_token_store
from ..storage.message_store import message_store
from ..storage.state_store import state_store
from .extract_text import extract_attachment_text

logger = logging.getLogger(__name__)


@dataclass
class AttachmentText:
  filename: str
  mime_type: str
  text: Optional[str]


@dataclass
class GmailMessage:
  message_id: str
  thread_id: Optional[str]
  subject: Optional[str]
  sender: Optional[str]
  recipients: List[str]
  sent_at: Optional[datetime]
  snippet: Optional[str]
  body_text: str
  attachments: List[AttachmentText]

  @property
  def consolidated_text(self) -> str:
    blocks = [self.body_text or ""]
    for attachment in self.attachments:
      if attachment.text:
        blocks.append(f"\nAttachment: {attachment.filename}\n{attachment.text}")
    return "\n\n".join(block.strip() for block in blocks if block.strip())


class GmailIngestor:
  def __init__(self):
    self.credentials: Dict[str, Credentials] = {}

  def fetch_message(self, user_id: str, message_id: str) -> GmailMessage:
    service = self._service(user_id)
    full = self._fetch_message_detail(service, message_id)
    if not full:
      raise RuntimeError("Message not found")
    return full

  def poll(
    self,
    user_id: str,
    max_messages: int = 100,
    *,
    query: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
  ) -> List[GmailMessage]:
    if max_messages <= 0:
      return []

    state = state_store.get_state(user_id)
    baseline_at = state.get("baseline_at")
    if not baseline_at:
      raise RuntimeError("Baseline timestamp missing for Gmail. Please reconnect Gmail to reset the baseline.")
    if not state.get("baseline_ready"):
      state_store.mark_baseline_ready(user_id)
      logger.info("Baseline established; skipping initial poll", extra={"user_id": user_id, "baseline_at": baseline_at})
      return []

    baseline_dt = self._parse_iso8601(baseline_at)
    baseline_filter = f"after:{int(baseline_dt.timestamp())}"

    service = self._service(user_id)
    processed_ids = set(state.get("processed_ids", []))
    collected: List[GmailMessage] = []
    next_page_token: Optional[str] = None
    label_ids = label_ids or None
    requested_query = query or None
    gmail_query = " ".join(part for part in [baseline_filter, requested_query] if part)

    try:
      while len(collected) < max_messages:
        request = (
          service.users()
          .messages()
          .list(
            userId="me",
            labelIds=label_ids,
            q=gmail_query,
            maxResults=min(100, max_messages),
            pageToken=next_page_token,
          )
        )
        response = request.execute()
        for entry in response.get("messages", []) or []:
          message_id = entry["id"]
          if message_id in processed_ids:
            continue
          gmail_message = self._fetch_message_detail(service, message_id)
          if gmail_message:
            collected.append(gmail_message)
          if len(collected) >= max_messages:
            break
        next_page_token = response.get("nextPageToken")
        if not next_page_token or not response.get("messages"):
          break
    except HttpError as exc:  # pragma: no cover - network
      logger.error("Failed to list Gmail messages", extra={"error": str(exc), "user_id": user_id})
      raise RuntimeError(f"Failed to query Gmail: {exc}") from exc

    if collected:
      for message in collected:
        processed_ids.add(message.message_id)
      last_id = collected[-1].message_id
      state_store.update_state(user_id, last_uid=last_id, processed_ids=list(processed_ids))
      message_store.record_poll(user_id, collected)
      logger.info(
        "Gmail poll complete",
        extra={
          "user_id": user_id,
          "fetched": len(collected),
          "last_message_id": last_id,
        },
      )
    else:
      logger.info("Gmail poll returned no new messages", extra={"user_id": user_id})

    return collected

  def _service(self, user_id: str):
    if user_id not in self.credentials:
      self.credentials[user_id] = self._load_credentials(user_id)
    return build("gmail", "v1", credentials=self.credentials[user_id], cache_discovery=False)

  def _load_credentials(self, user_id: str) -> Credentials:
    stored = gmail_token_store.load(user_id)
    if not stored:
      raise RuntimeError("Gmail is not connected for this user.")

    scopes = stored.get("scope") or settings.google_scopes
    if isinstance(scopes, str):
      scopes = [scope.strip() for scope in scopes.split() if scope.strip()]

    creds = Credentials(
      token=stored.get("access_token"),
      refresh_token=stored.get("refresh_token"),
      token_uri="https://oauth2.googleapis.com/token",
      client_id=settings.google_client_id,
      client_secret=settings.google_client_secret,
      scopes=scopes,
    )
    if creds.expired and creds.refresh_token:
      creds.refresh(Request())
      self._persist_refreshed_tokens(user_id, stored, creds)
    return creds

  @staticmethod
  def _parse_iso8601(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
      return dt.replace(tzinfo=timezone.utc)
    return dt

  def _persist_refreshed_tokens(self, user_id: str, stored: Dict[str, Any], creds: Credentials) -> None:
    expires_at = creds.expiry.isoformat() if creds.expiry else gmail_token_store.compute_expiry(3600)
    updated = {
      **stored,
      "access_token": creds.token,
      "expires_at": expires_at,
      "retrieved_at": datetime.utcnow().isoformat(),
    }
    gmail_token_store.save(user_id, updated)

  def _fetch_message_detail(self, service, message_id: str) -> Optional[GmailMessage]:
    try:
      raw = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full", metadataHeaders=["From", "To", "Subject", "Date"])
        .execute()
      )
    except HttpError as exc:  # pragma: no cover - network
      logger.error("Failed to fetch Gmail message", extra={"message_id": message_id, "error": str(exc)})
      return None

    payload = raw.get("payload", {})
    headers = {item["name"]: item["value"] for item in payload.get("headers", [])}

    sent_at = headers.get("Date")
    sent_at_dt = None
    if sent_at:
      try:
        sent_at_dt = parsedate_to_datetime(sent_at).astimezone(timezone.utc)
      except (TypeError, ValueError):
        sent_at_dt = None

    attachments = list(self._extract_attachments(service, raw))
    body_text = self._extract_body(payload) or ""

    return GmailMessage(
      message_id=raw["id"],
      thread_id=raw.get("threadId"),
      subject=headers.get("Subject"),
      sender=headers.get("From"),
      recipients=self._split_addresses(headers.get("To", "")),
      sent_at=sent_at_dt,
      snippet=raw.get("snippet"),
      body_text=body_text,
      attachments=attachments,
    )

  def _extract_body(self, payload: dict) -> Optional[str]:
    body = payload.get("body", {})
    data = body.get("data")
    if data:
      return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
      mime_type = part.get("mimeType", "")
      if mime_type == "text/plain":
        part_data = part.get("body", {}).get("data")
        if part_data:
          return base64.urlsafe_b64decode(part_data).decode("utf-8", errors="replace")
      elif mime_type.startswith("multipart/"):
        nested = self._extract_body(part)
        if nested:
          return nested
    return None

  def _extract_attachments(self, service, message: dict) -> Iterable[AttachmentText]:
    payload = message.get("payload", {})
    parts = payload.get("parts", []) or []
    message_id = message["id"]

    for part in self._walk_parts(parts):
      body = part.get("body", {})
      if "attachmentId" not in body:
        continue
      attachment_id = body["attachmentId"]
      attachment = (
        service.users()
        .messages()
        .attachments()
        .get(userId="me", messageId=message_id, id=attachment_id)
        .execute()
      )
      data = attachment.get("data")
      decoded = base64.urlsafe_b64decode(data) if data else None
      text = extract_attachment_text(part.get("filename", ""), part.get("mimeType", ""), decoded)
      yield AttachmentText(
        filename=part.get("filename", ""),
        mime_type=part.get("mimeType", ""),
        text=text,
      )

  def _walk_parts(self, parts: List[dict]) -> Iterable[dict]:
    for part in parts:
      yield part
      if "parts" in part:
        for sub in self._walk_parts(part.get("parts", []) or []):
          yield sub

  @staticmethod
  def _split_addresses(value: str) -> List[str]:
    if not value:
      return []
    return [addr.strip() for addr in value.split(",") if addr.strip()]


gmail_ingestor = GmailIngestor()
