from __future__ import annotations

from typing import List, Optional
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.gmail_ingest import gmail_ingestor
from ..storage.supabase_token_store import gmail_token_store
from ..storage.message_store import message_store
from ..storage.state_store import state_store
from ..auth import resolve_user_id
from ..background.polling_worker import poll_gmail_for_user
from ..services.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
logger = logging.getLogger(__name__)


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
  supabase = get_supabase_client()
  try:
    conn = (
      supabase.table("gmail_connections")
      .select("baseline_at, baseline_ready, last_poll_at")
      .eq("user_id", resolved_user_id)
      .maybe_single()
      .execute()
    )
    conn_data = conn.data if hasattr(conn, "data") else None
  except Exception:
    conn_data = None
  try:
    resp = supabase.table("gmail_messages").select("status, received_at").eq("user_id", resolved_user_id).execute()
    rows = resp.data if hasattr(resp, "data") else []
  except Exception:
    rows = []

  counts = {
    "new": 0,
    "processed": 0,
    "error": 0,
    "pending_ai_analysis": 0,
    "ai_analyzed": 0,
    "routed": 0,
    "accepted": 0,
    "rejected": 0,
    "needs_review": 0,
  }
  total = 0
  last_received = None
  for row in rows:
    total += 1
    status = (row.get("status") or "new").lower()
    if status in counts:
      counts[status] += 1
    else:
      counts["new"] += 1
    ra = row.get("received_at")
    if ra and (last_received is None or ra > last_received):
      last_received = ra

  return {
    "connected": True,
    "email": record.get("email"),
    "google_user_id": record.get("google_user_id"),
    "history_id": record.get("history_id"),
    "scopes": record.get("scope"),
    "last_checked_at": (conn_data or {}).get("last_poll_at") or state.get("last_poll_at") or (conn_data or {}).get("baseline_at") or state.get("baseline_at"),
    "counts": counts,
    "total_indexed": total,
    "baseline_at": (conn_data or {}).get("baseline_at") or state.get("baseline_at"),
    "baseline_ready": (conn_data or {}).get("baseline_ready") if conn_data else state.get("baseline_ready"),
  }


@router.post("/sync/start")
async def sync_gmail(payload: SyncRequest, request: Request):
  resolved_user_id = resolve_user_id(request, payload.user_id)
  logger.info("gmail_sync_start user_id=%s max=%s", resolved_user_id, payload.max_messages)
  try:
    result = await poll_gmail_for_user(resolved_user_id)
    logger.info("gmail_sync_done user_id=%s inserted=%s errors=%s last_poll_at=%s", resolved_user_id, result.get("inserted"), result.get("errors"), result.get("last_poll_at"))
    return {"inserted": result.get("inserted"), "errors": result.get("errors"), "last_poll_at": result.get("last_poll_at")}
  except Exception as exc:
    logger.exception("gmail_sync_failed user_id=%s", resolved_user_id)
    raise HTTPException(status_code=500, detail=str(exc)) from exc
