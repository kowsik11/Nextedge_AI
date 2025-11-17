from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..services.hubspot_oauth import build_auth_url as build_hubspot_auth_url, exchange_code as exchange_hubspot_code
from ..services.gmail_oauth import build_auth_url as build_gmail_auth_url, exchange_code as exchange_gmail_code
from ..services.token_service import delete_tokens
from ..services.oauth_state import sign_state, verify_state

router = APIRouter(prefix="/api/oauth", tags=["oauth"])


@router.get("/hubspot/start")
def hubspot_start(request: Request):
  user_id = getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")
  return RedirectResponse(build_hubspot_auth_url(sign_state(user_id)))


@router.get("/hubspot/callback")
def hubspot_callback(code: str, state: str):
  user_id = verify_state(state)
  exchange_hubspot_code(user_id, code)
  return RedirectResponse("/home?connected=hubspot")


@router.get("/gmail/start")
def gmail_start(request: Request):
  user_id = getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")
  return RedirectResponse(build_gmail_auth_url(sign_state(user_id)))


@router.get("/gmail/callback")
async def gmail_callback(code: str, state: str):
  user_id = verify_state(state)
  await exchange_gmail_code(user_id, code)
  return RedirectResponse("/home?connected=gmail")


@router.post("/disconnect/{provider}")
def disconnect(provider: str, request: Request):
  user_id = getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")
  delete_tokens(user_id, provider)
  return {"disconnected": True}
