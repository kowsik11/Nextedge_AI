from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from postgrest import APIError
from datetime import datetime, timezone

from .supabase_client import get_supabase_client

TOKENS_TABLE = "oauth_connections"
EVENTS_TABLE = "oauth_token_events"


def compute_expiry(expires_in: int) -> str:
  return (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)).isoformat()


def save_tokens(user_id: str, provider: str, record: Dict[str, Any]) -> None:
  payload = {
    "user_id": user_id,
    "provider": provider,
    "access_token": record.get("access_token"),
    "refresh_token": record.get("refresh_token"),
    "expires_at": record.get("expires_at"),
    "scope": record.get("scope"),
    "email": record.get("email"),
    "external_user_id": record.get("external_user_id"),
    "metadata": record,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "created_at": record.get("created_at"),
  }
  supabase = get_supabase_client()
  try:
    supabase.table(TOKENS_TABLE).upsert(payload, returning="minimal").execute()
  except APIError as exc:
    raise RuntimeError(f"Failed to persist tokens for {provider}: {exc}") from exc


def load_tokens(user_id: str, provider: str) -> Optional[Dict[str, Any]]:
  supabase = get_supabase_client()
  try:
    resp = (
      supabase.table(TOKENS_TABLE)
      .select("*")
      .eq("user_id", user_id)
      .eq("provider", provider)
      .maybe_single()
      .execute()
    )
  except APIError as exc:
    raise RuntimeError(f"Failed to load tokens for {provider}: {exc}") from exc
  data = resp.data if hasattr(resp, "data") else None
  return data


def delete_tokens(user_id: str, provider: str) -> None:
  supabase = get_supabase_client()
  supabase.table(TOKENS_TABLE).delete().eq("user_id", user_id).eq("provider", provider).execute()


def tokens_expired(record: Dict[str, Any]) -> bool:
  expires_at = record.get("expires_at")
  if not expires_at:
    return True
  return datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc)


def log_token_event(user_id: str, provider: str, event: str, payload: Dict[str, Any]) -> None:
  supabase = get_supabase_client()
  try:
    supabase.table(EVENTS_TABLE).insert(
      {"user_id": user_id, "provider": provider, "event": event, "payload": payload, "created_at": datetime.now(timezone.utc).isoformat()}
    ).execute()
  except APIError:
    # Optional table; ignore if missing
    return


def get_or_refresh_tokens(user_id: str, provider: str, *, refresh_fn=None) -> Dict[str, Any]:
  record = load_tokens(user_id, provider)
  if not record:
    raise RuntimeError(f"{provider} not connected")

  def _log(event: str, payload: Dict[str, Any]):
    try:
      log_token_event(user_id, provider, event, payload)
    except Exception:
      return

  expires_at = record.get("expires_at")
  if expires_at:
    try:
      expiry_dt = datetime.fromisoformat(expires_at)
    except Exception:
      expiry_dt = datetime.now(timezone.utc)
  else:
    expiry_dt = datetime.now(timezone.utc) - timedelta(seconds=1)

  if expiry_dt > datetime.now(timezone.utc):
    return record

  if not refresh_fn:
    raise RuntimeError(f"{provider} token expired and no refresh function provided")

  try:
    updated = refresh_fn(user_id, record)
    _log("refresh", {"status": "success"})
    return updated
  except Exception as exc:
    _log("refresh_failed", {"error": str(exc)})
    raise
