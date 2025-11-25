from __future__ import annotations

import logging
from typing import Dict

import requests
from fastapi import HTTPException

from ..config import settings
from ..storage.supabase_token_store import salesforce_token_store

logger = logging.getLogger(__name__)


def get_authorization_url(state: str) -> str:
  """Generate Salesforce OAuth authorization URL."""
  from urllib.parse import urlencode

  params = {
    "response_type": "code",
    "client_id": settings.salesforce_client_id,
    "redirect_uri": str(settings.salesforce_redirect_uri),
    "scope": settings.salesforce_scopes,
    "state": state,
  }
  return f"{settings.salesforce_auth_url}?{urlencode(params)}"


def exchange_code(user_id: str, code: str) -> Dict[str, str]:
  """Exchange auth code for tokens and persist in Supabase."""
  payload = {
    "grant_type": "authorization_code",
    "code": code,
    "client_id": settings.salesforce_client_id,
    "client_secret": settings.salesforce_client_secret,
    "redirect_uri": str(settings.salesforce_redirect_uri),
  }

  resp = requests.post(settings.salesforce_token_url, data=payload, timeout=30)
  if resp.status_code >= 400:
    detail = resp.text
    logger.error("Salesforce token exchange failed: %s", detail)
    raise HTTPException(status_code=resp.status_code, detail="Salesforce OAuth exchange failed")

  data = resp.json()
  record = {
    "access_token": data.get("access_token"),
    "refresh_token": data.get("refresh_token"),
    "instance_url": data.get("instance_url"),
    "id": data.get("id"),
    "issued_at": data.get("issued_at"),
    "signature": data.get("signature"),
    "scope": settings.salesforce_scope_list,
  }
  salesforce_token_store.save(user_id, record)
  salesforce_token_store.clear_cache(user_id)
  return record


def refresh_access_token(user_id: str, refresh_token: str) -> Dict[str, str]:
  payload = {
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
    "client_id": settings.salesforce_client_id,
    "client_secret": settings.salesforce_client_secret,
  }
  resp = requests.post(settings.salesforce_token_url, data=payload, timeout=30)
  if resp.status_code >= 400:
    raise HTTPException(status_code=resp.status_code, detail="Salesforce token refresh failed")
  data = resp.json()
  record = {
    "access_token": data.get("access_token"),
    "refresh_token": refresh_token,
    "instance_url": data.get("instance_url"),
    "scope": settings.salesforce_scope_list,
  }
  salesforce_token_store.save(user_id, record)
  salesforce_token_store.clear_cache(user_id)
  return record


def get_salesforce_token(user_id: str) -> Dict[str, str]:
  record = salesforce_token_store.load(user_id)
  if not record:
    raise HTTPException(status_code=401, detail="No Salesforce token for user")
  # TODO: add expiry check; Salesforce access tokens expire (~2h).
  if not record.get("access_token"):
    raise HTTPException(status_code=401, detail="Salesforce access token missing")
  return record
