from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urljoin
import httpx

from ..config import settings
from ..services.oauth_state import sign_state, verify_state
from ..services.gmail_oauth import build_auth_url, exchange_code
from ..storage.supabase_token_store import gmail_token_store
from ..storage.message_store import message_store
from ..storage.state_store import state_store
from pydantic import BaseModel
from ..auth import resolve_user_id
from ..services.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/google", tags=["google"])


@router.get("/connect")
async def connect_google(request: Request, user_id: str | None = None):
  resolved_user_id = resolve_user_id(request, user_id)
  return RedirectResponse(build_auth_url(sign_state(resolved_user_id)))


@router.get("/callback")
async def google_callback(request: Request):
  code = request.query_params.get("code")
  state = request.query_params.get("state")
  if not code or not state:
    raise HTTPException(status_code=400, detail="Missing authorization code or state")

  user_id = verify_state(state)

  await exchange_code(user_id, code)
  baseline_at = datetime.now(timezone.utc).isoformat()
  state_store.set_baseline(user_id, baseline_at)
  message_store.reset_user(user_id)

  # Clear previous mailbox data and initialize gmail_connections for this user
  supabase = get_supabase_client()
  try:
    supabase.table("gmail_messages").delete().eq("user_id", user_id).execute()
    supabase.table("gmail_connections").upsert(
      {
        "user_id": user_id,
        "gmail_user": profile.get("emailAddress"),
        "email": profile.get("emailAddress"),
        "baseline_at": baseline_at,
        "baseline_ready": True,
        "last_poll_at": None,
        "created_at": baseline_at,
        "updated_at": baseline_at,
      }
    ).execute()
  except Exception:
    # best-effort cleanup
    pass

  frontend_base = str(settings.frontend_url).rstrip("/")
  redirect_path = "home?connected=google"
  redirect_url = urljoin(f"{frontend_base}/", redirect_path)

  return RedirectResponse(url=redirect_url)


class DisconnectRequest(BaseModel):
  user_id: str | None = None


@router.post("/disconnect")
async def disconnect_google(payload: DisconnectRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)

  gmail_token_store.delete(user_id)
  state_store.reset_user(user_id)
  message_store.reset_user(user_id)

  return {"disconnected": True}


async def _fetch_gmail_profile(access_token: str) -> Dict[str, Optional[str]]:
  profile_url = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
  headers = {"Authorization": f"Bearer {access_token}"}
  async with httpx.AsyncClient(timeout=30) as client:
    response = await client.get(profile_url, headers=headers)
  if response.status_code >= 400:
    raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail profile: {response.text}")
  return response.json()
