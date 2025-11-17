from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from postgrest import APIError

from ..services.supabase_client import get_supabase_client


class SupabaseTokenStore:
  def __init__(self, provider: str, table: str = "oauth_connections"):
    self.provider = provider
    self.table = table
    self.client = get_supabase_client()

  @staticmethod
  def compute_expiry(expires_in: int) -> str:
    """Buffer token expiry slightly so we refresh before a hard expiration."""
    return (datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)).isoformat()

  def save(self, user_id: str, record: Dict[str, Any]) -> None:
    payload = {
      "user_id": user_id,
      "provider": self.provider,
      "access_token": record.get("access_token"),
      "refresh_token": record.get("refresh_token"),
      "expires_at": record.get("expires_at"),
      "scope": record.get("scope"),
      "email": record.get("email") or record.get("user_email"),
      "external_user_id": record.get("google_user_id") or record.get("portal_id"),
      "metadata": record,
    }
    try:
      self.client.table(self.table).upsert(payload, returning="minimal").execute()
    except APIError as exc:
      raise RuntimeError(f"Failed to persist OAuth tokens for {self.provider}: {exc}") from exc

  def load(self, user_id: str) -> Optional[Dict[str, Any]]:
    try:
      response = self.client.table(self.table).select("*").eq("user_id", user_id).eq("provider", self.provider).maybe_single().execute()
    except APIError as exc:
      raise RuntimeError(f"Failed to load OAuth tokens for {self.provider}: {exc}") from exc
    data = response.data if hasattr(response, "data") else None
    if not data:
      return None
    metadata = data.get("metadata") or {}
    # Merge core fields to preserve expected keys for existing callers.
    return {
      **metadata,
      "access_token": data.get("access_token") or metadata.get("access_token"),
      "refresh_token": data.get("refresh_token") or metadata.get("refresh_token"),
      "expires_at": data.get("expires_at") or metadata.get("expires_at"),
      "scope": data.get("scope") or metadata.get("scope"),
      "email": data.get("email") or metadata.get("email"),
      "user_email": data.get("email") or metadata.get("user_email"),
      "google_user_id": data.get("external_user_id") or metadata.get("google_user_id"),
      "portal_id": data.get("external_user_id") or metadata.get("portal_id"),
    }

  def delete(self, user_id: str) -> None:
    try:
      self.client.table(self.table).delete().eq("user_id", user_id).eq("provider", self.provider).execute()
    except APIError as exc:
      raise RuntimeError(f"Failed to delete OAuth tokens for {self.provider}: {exc}") from exc


gmail_token_store = SupabaseTokenStore("gmail")
hubspot_token_store = SupabaseTokenStore("hubspot")
