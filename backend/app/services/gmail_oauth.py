from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from ..config import settings
from ..storage.supabase_token_store import gmail_token_store
from ..services.supabase_client import get_supabase_client
from ..services.token_service import log_token_event


def build_auth_url(state: str) -> str:
  scopes = " ".join(settings.google_scopes)
  base = "https://accounts.google.com/o/oauth2/v2/auth"
  return (
    f"{base}?client_id={settings.google_client_id}"
    f"&redirect_uri={settings.google_redirect_uri}"
    f"&response_type=code&scope={scopes}"
    f"&access_type=offline&prompt=consent&state={state}"
  )


async def exchange_code(user_id: str, code: str) -> Dict[str, Any]:
  token_url = "https://oauth2.googleapis.com/token"
  payload = {
    "code": code,
    "client_id": settings.google_client_id,
    "client_secret": settings.google_client_secret,
    "redirect_uri": str(settings.google_redirect_uri),
    "grant_type": "authorization_code",
  }
  async with httpx.AsyncClient(timeout=20) as client:
    resp = await client.post(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
  if resp.status_code >= 400:
    raise HTTPException(status_code=400, detail=resp.text)
  tokens = resp.json()
  expires_at = gmail_token_store.compute_expiry(int(tokens.get("expires_in", 3600)))
  record = {
    "access_token": tokens["access_token"],
    "refresh_token": tokens.get("refresh_token"),
    "expires_at": expires_at,
    "scope": tokens.get("scope", "").split(),
  }
  gmail_token_store.save(user_id, record)
  await ensure_gmail_connection_row(user_id, record)
  return record


async def ensure_gmail_connection_row(user_id: str, token_record: Dict[str, Any]) -> None:
  supabase = get_supabase_client()
  async with httpx.AsyncClient(timeout=15) as client:
    res = await client.get(
      "https://gmail.googleapis.com/gmail/v1/users/me/profile",
      headers={"Authorization": f"Bearer {token_record['access_token']}"},
    )
  res.raise_for_status()
  profile = res.json()
  gmail_user = profile.get("emailAddress")
  now_iso = datetime.now(timezone.utc).isoformat()
  payload = {
    "user_id": user_id,
    "gmail_user": gmail_user,
    "email": gmail_user,
    "baseline_at": now_iso,
    "baseline_ready": False,
    "last_poll_at": None,
    "created_at": now_iso,
    "updated_at": now_iso,
  }
  supabase.table("gmail_connections").upsert(payload, returning="minimal").execute()


def refresh_token(user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
  token_url = "https://oauth2.googleapis.com/token"
  payload = {
    "grant_type": "refresh_token",
    "client_id": settings.google_client_id,
    "client_secret": settings.google_client_secret,
    "refresh_token": record["refresh_token"],
  }
  with httpx.Client(timeout=20) as client:
    resp = client.post(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
  if resp.status_code >= 400:
    log_token_event(user_id, "gmail", "refresh_failed", {"status_code": resp.status_code, "detail": resp.text})
    raise HTTPException(status_code=400, detail=resp.text)
  tokens = resp.json()
  expires_at = gmail_token_store.compute_expiry(int(tokens.get("expires_in", 3600)))
  updated = {
    "access_token": tokens["access_token"],
    "refresh_token": record["refresh_token"],
    "expires_at": expires_at,
    "scope": record.get("scope"),
  }
  gmail_token_store.save(user_id, updated)
  log_token_event(user_id, "gmail", "refresh", {"status": "success"})
  return updated


def get_gmail_token(user_id: str) -> Dict[str, Any]:
  record = gmail_token_store.load(user_id)
  if not record:
    raise HTTPException(status_code=400, detail="Gmail not connected")
  expires_at = record.get("expires_at")
  if expires_at:
    if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
      return refresh_token(user_id, record)
  return record
