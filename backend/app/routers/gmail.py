from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.gmail_ingest import gmail_ingestor
from ..storage.supabase_token_store import gmail_token_store
from ..storage.message_store import message_store
from ..storage.state_store import state_store
from ..auth import resolve_user_id
from ..background.polling_worker import poll_gmail_for_user

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


class SyncRequest(BaseModel):
  user_id: str | None = None
  max_messages: int = Field(100, ge=1, le=500)
  query: Optional[str] = None
  label_ids: Optional[List[str]] = None


@router.get("/status")
def gmail_status(request: Request, user_id: str | None = None):
  # Do not 401; allow query param fallback
  resolved_user_id = user_id or getattr(request.state, "user_id", None)
  if not resolved_user_id:
    return {"connected": False}

  record = gmail_token_store.load(resolved_user_id)
  if not record:
    return {"connected": False}

  state = state_store.get_state(resolved_user_id)
  summary = message_store.summary(resolved_user_id)
  return {
    "connected": True,
    "email": record.get("email"),
    "google_user_id": record.get("google_user_id"),
    "history_id": record.get("history_id"),
    "scopes": record.get("scope"),
    "last_checked_at": summary.get("last_checked_at"),
    "counts": summary.get("counts"),
    "total_indexed": summary.get("total"),
    "baseline_at": state.get("baseline_at"),
    "baseline_ready": state.get("baseline_ready"),
  }


@router.post("/sync/start")
async def sync_gmail(payload: SyncRequest, request: Request):
  resolved_user_id = resolve_user_id(request, payload.user_id)
  try:
    result = await poll_gmail_for_user(resolved_user_id)
  except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc)) from exc
  return {"inserted": result.get("inserted"), "errors": result.get("errors"), "last_poll_at": result.get("last_poll_at")}
