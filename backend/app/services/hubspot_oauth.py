from __future__ import annotations

import urllib.parse

import httpx
from fastapi import HTTPException
from typing import Any, Dict

from ..config import settings
from ..storage.supabase_token_store import hubspot_token_store


def build_auth_url(state: str) -> str:
  scope = urllib.parse.quote(settings.hubspot_scope)
  optional_scope = urllib.parse.quote(settings.hubspot_optional_scope) if settings.hubspot_optional_scope else ""
  base = str(settings.hubspot_auth_base).rstrip("/")
  redirect_uri = urllib.parse.quote(str(settings.hubspot_redirect_uri))
  url = (
    f"{base}/authorize?client_id={settings.hubspot_client_id}"
    f"&redirect_uri={redirect_uri}"
    f"&scope={scope}"
    f"&response_type=code"
    f"&state={state}"
  )
  if optional_scope:
    url = f"{url}&optional_scope={optional_scope}"
  return url


def exchange_code(user_id: str, code: str) -> Dict[str, Any]:
  url = f"{str(settings.hubspot_api_base).rstrip('/')}/oauth/v1/token"
  data = {
    "grant_type": "authorization_code",
    "client_id": settings.hubspot_client_id,
    "client_secret": settings.hubspot_client_secret,
    "redirect_uri": str(settings.hubspot_redirect_uri),
    "code": code,
  }
  with httpx.Client(timeout=20) as client:
    resp = client.post(url, data=data)
  if resp.status_code != 200:
    raise HTTPException(status_code=400, detail=resp.text)
  payload = resp.json()
  expires_at = hubspot_token_store.compute_expiry(int(payload.get("expires_in", 3600)))
  record = {
    "access_token": payload["access_token"],
    "refresh_token": payload.get("refresh_token"),
    "expires_at": expires_at,
    "scope": payload.get("scope", "").split(),
    "email": (payload.get("user") or {}).get("email"),
    "external_user_id": payload.get("hub_id"),
    "portal_id": payload.get("hub_id"),
  }
  hubspot_token_store.save(user_id, record)
  return record


def refresh_token(user_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
  url = f"{str(settings.hubspot_api_base).rstrip('/')}/oauth/v1/token"
  data = {
    "grant_type": "refresh_token",
    "client_id": settings.hubspot_client_id,
    "client_secret": settings.hubspot_client_secret,
    "refresh_token": record["refresh_token"],
  }
  with httpx.Client(timeout=20) as client:
    resp = client.post(url, data=data)
  if resp.status_code != 200:
    raise HTTPException(status_code=400, detail=resp.text)
  payload = resp.json()
  expires_at = hubspot_token_store.compute_expiry(int(payload.get("expires_in", 3600)))
  updated = {
    "access_token": payload["access_token"],
    "refresh_token": record["refresh_token"],
    "expires_at": expires_at,
    "scope": payload.get("scope", "").split(),
    "email": record.get("email"),
    "external_user_id": record.get("external_user_id"),
    "portal_id": record.get("portal_id"),
  }
  hubspot_token_store.save(user_id, updated)
  return updated


def get_hubspot_token(user_id: str) -> Dict[str, Any]:
  record = hubspot_token_store.load(user_id)
  if not record:
    raise HTTPException(status_code=400, detail="HubSpot not connected")
  if not record.get("refresh_token") and not record.get("access_token"):
    raise HTTPException(status_code=400, detail="HubSpot tokens missing")
  expires_at = record.get("expires_at")
  if expires_at:
    from datetime import datetime, timezone

    if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
      return refresh_token(user_id, record)
  return record
