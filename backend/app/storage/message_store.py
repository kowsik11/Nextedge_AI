from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

if TYPE_CHECKING:
  from ..services.gmail_ingest import GmailMessage

from ..services.supabase_client import get_supabase_client

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "inbox_messages.json"
DEFAULT_BUCKET = {"last_checked_at": None, "messages": {}}
MAX_STORED_MESSAGES = 10


def _utcnow() -> str:
  return datetime.now(timezone.utc).isoformat()


class MessageStore:
  def __init__(self, path: Path = DEFAULT_PATH):
    self.path = path
    self.path.parent.mkdir(parents=True, exist_ok=True)

  def _read(self) -> Dict[str, Any]:
    if not self.path.exists():
      return {"users": {}}
    with self.path.open("r", encoding="utf-8") as handle:
      return json.load(handle)

  def _write(self, payload: Dict[str, Any]) -> None:
    with self.path.open("w", encoding="utf-8") as handle:
      json.dump(payload, handle, indent=2)

  def record_poll(self, user_id: str, messages: Iterable["GmailMessage"]) -> None:
    data = self._read()
    bucket = self._bucket_for_user(data, user_id, prune=True)
    existing: Dict[str, Any] = bucket.get("messages", {})
    supabase_rows: List[Dict[str, Any]] = []
    now_iso = _utcnow()
    for message in messages:
      if message.message_id in existing:
        continue
      existing[message.message_id] = self._serialize_message(message)
      supabase_rows.append(self._serialize_supabase_row(user_id, message, now_iso))
    bucket["messages"] = self._prune_messages(existing)
    bucket["last_checked_at"] = _utcnow()
    data["users"][user_id] = bucket
    self._write(data)
    if supabase_rows:
      try:
        supabase = get_supabase_client()
        supabase.table("gmail_messages").upsert(supabase_rows, on_conflict="user_id,message_id").execute()
      except Exception:
        # Best-effort; we still keep the local store.
        pass

  def _serialize_message(self, message: "GmailMessage") -> Dict[str, Any]:
    has_attachments = any(message.attachments)
    has_images = any(att.mime_type.startswith("image/") for att in message.attachments)
    body_sample = (message.body_text or "").strip()
    has_links = "http://" in body_sample or "https://" in body_sample
    return {
      "id": message.message_id,
      "thread_id": message.thread_id,
      "subject": message.subject or "(no subject)",
      "sender": message.sender,
      "snippet": message.snippet,
      "preview": body_sample[:800],
      "received_at": message.sent_at.isoformat() if message.sent_at else None,
      "status": "pending_ai_analysis",
      "has_attachments": has_attachments,
      "has_images": has_images,
      "has_links": has_links,
      "gmail_url": self._gmail_url(message),
      "crm_record_url": None,
      "crm_note_id": None,
      "hubspot_note_id": None,
      "hubspot_object_type": None,
      "ai_routing_decision": None,
      "ai_confidence": None,
      "ai_summary": None,
      "error": None,
      "created_at": _utcnow(),
      "updated_at": _utcnow(),
    }

  def _serialize_supabase_row(self, user_id: str, message: "GmailMessage", created_at: str) -> Dict[str, Any]:
    has_attachments = any(message.attachments)
    has_images = any(att.mime_type.startswith("image/") for att in message.attachments)
    body_sample = (message.body_text or "").strip()
    has_links = "http://" in body_sample or "https://" in body_sample
    return {
      "user_id": user_id,
      "message_id": message.message_id,
      "thread_id": message.thread_id,
      "subject": message.subject or "(no subject)",
      "sender": message.sender,
      "snippet": message.snippet,
      "preview": body_sample[:800],
      "status": "pending_ai_analysis",
      "has_attachments": has_attachments,
      "has_images": has_images,
      "has_links": has_links,
      "gmail_url": self._gmail_url(message),
      "crm_record_url": None,
      "ai_routing_decision": None,
      "ai_confidence": None,
      "ai_summary": None,
      "hubspot_object_type": None,
      "hubspot_contact_id": None,
      "hubspot_company_id": None,
      "hubspot_deal_id": None,
      "hubspot_ticket_id": None,
      "hubspot_order_id": None,
      "hubspot_note_id": None,
      "error": None,
      "received_at": message.sent_at.isoformat() if message.sent_at else None,
      "created_at": created_at,
      "updated_at": created_at,
    }

  @staticmethod
  def _gmail_url(message: "GmailMessage") -> str:
    thread_or_id = message.thread_id or message.message_id
    return f"https://mail.google.com/mail/u/0/#inbox/{thread_or_id}"

  def update_status(
    self,
    user_id: str,
    message_id: str,
    *,
    status: str,
    crm_contact_id: Optional[str] = None,
    crm_note_id: Optional[str] = None,
    hubspot_portal_id: Optional[int] = None,
    hubspot_object_type: Optional[str] = None,
    ai_routing_decision: Optional[Dict[str, Any]] = None,
    ai_confidence: Optional[float] = None,
    hubspot_company_id: Optional[str] = None,
    hubspot_deal_id: Optional[str] = None,
    hubspot_ticket_id: Optional[str] = None,
    hubspot_order_id: Optional[str] = None,
    error: Optional[str] = None,
  ) -> None:
    data = self._read()
    bucket = self._bucket_for_user(data, user_id, prune=True)
    entry = bucket.get("messages", {}).get(message_id)
    if not entry:
      return
    entry["status"] = status
    entry["updated_at"] = _utcnow()
    entry["error"] = error
    if crm_contact_id and hubspot_portal_id:
      entry["crm_record_url"] = f"https://app.hubspot.com/contacts/{hubspot_portal_id}/record/0-1/{crm_contact_id}"
    if crm_note_id:
      entry["hubspot_note_id"] = crm_note_id
    if hubspot_object_type is not None:
      entry["hubspot_object_type"] = hubspot_object_type
    if ai_routing_decision is not None:
      entry["ai_routing_decision"] = ai_routing_decision
    if ai_confidence is not None:
      entry["ai_confidence"] = ai_confidence
    if hubspot_company_id is not None:
      entry["hubspot_company_id"] = hubspot_company_id
    if hubspot_deal_id is not None:
      entry["hubspot_deal_id"] = hubspot_deal_id
    if hubspot_ticket_id is not None:
      entry["hubspot_ticket_id"] = hubspot_ticket_id
    if hubspot_order_id is not None:
      entry["hubspot_order_id"] = hubspot_order_id
    bucket["messages"][message_id] = entry
    data["users"][user_id] = bucket
    self._write(data)

  def list_messages(self, user_id: str, *, status: Optional[str] = None, query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    data = self._read()
    bucket = self._bucket_for_user(data, user_id, prune=True)
    records = list(bucket.get("messages", {}).values())
    if status:
      records = [row for row in records if row.get("status") == status]
    if query:
      lowered = query.lower()
      records = [
        row
        for row in records
        if lowered in (row.get("subject") or "").lower()
        or lowered in (row.get("sender") or "").lower()
        or lowered in (row.get("preview") or "").lower()
      ]
    records.sort(key=lambda row: row.get("received_at") or row.get("created_at"), reverse=True)
    return records[:limit]

  def summary(self, user_id: str) -> Dict[str, Any]:
    data = self._read()
    bucket = self._bucket_for_user(data, user_id, prune=True)
    records = list(bucket.get("messages", {}).values())
    statuses = [
      "new",
      "pending_ai_analysis",
      "ai_analyzed",
      "needs_review",
      "routed",
      "accepted",
      "rejected",
      "error",
    ]
    counts = {key: 0 for key in statuses}
    for row in records:
      status = row.get("status", "new")
      normalized = status if status in counts else "new"
      counts[normalized] += 1
    return {
      "last_checked_at": bucket.get("last_checked_at"),
      "counts": counts,
      "total": len(records),
    }

  def mark_error(self, user_id: str, message_id: str, detail: str) -> None:
    self.update_status(user_id, message_id, status="error", error=detail)

  def get(self, user_id: str, message_id: str) -> Optional[Dict[str, Any]]:
    bucket = self._bucket_for_user(self._read(), user_id, prune=True)
    return bucket.get("messages", {}).get(message_id)

  def reset_user(self, user_id: str) -> None:
    data = self._read()
    users = data.setdefault("users", {})
    users[user_id] = dict(DEFAULT_BUCKET)
    self._write(data)

  def _bucket_for_user(self, data: Dict[str, Any], user_id: str, prune: bool = False) -> Dict[str, Any]:
    users = data.setdefault("users", {})
    if user_id not in users:
      users[user_id] = dict(DEFAULT_BUCKET)
    if prune:
      users[user_id]["messages"] = self._prune_messages(users[user_id].get("messages", {}))
    return users[user_id]

  def _prune_messages(self, messages: Dict[str, Any]) -> Dict[str, Any]:
    if not messages:
      return {}
    records = list(messages.values())
    records.sort(key=self._sort_key, reverse=True)
    trimmed = records[:MAX_STORED_MESSAGES]
    return {row["id"]: row for row in trimmed}

  @staticmethod
  def _sort_key(record: Dict[str, Any]) -> str:
    return record.get("received_at") or record.get("created_at") or ""


message_store = MessageStore()
