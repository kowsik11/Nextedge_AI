from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..auth import resolve_user_id
from ..storage.message_store import message_store
from ..services.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("/summary")
def inbox_summary(request: Request, user_id: str | None = None):
  resolved_user_id = user_id or getattr(request.state, "user_id", None)
  if not resolved_user_id:
    raise HTTPException(status_code=401, detail="Missing authenticated user")
  supabase = get_supabase_client()

  # Pull last_poll_at from gmail_connections
  conn_resp = supabase.table("gmail_connections").select("last_poll_at").eq("user_id", resolved_user_id).maybe_single().execute()
  conn = conn_resp.data if hasattr(conn_resp, "data") else None
  last_poll_at = conn.get("last_poll_at") if conn else None

  resp = supabase.table("gmail_messages").select("status, received_at").eq("user_id", resolved_user_id).execute()
  rows = resp.data if hasattr(resp, "data") else []
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
    else:  # treat unknown as new
      counts["new"] += 1
    ra = row.get("received_at")
    if ra and (last_received is None or ra > last_received):
      last_received = ra

  return {
    "connected": True,
    "last_checked_at": last_poll_at,
    "counts": counts,
    "total": total,
  }


@router.get("/messages")
def inbox_messages(
  request: Request,
  user_id: str | None = None,
  status: str = Query("new", description="new | processed | error | all"),
  query: str | None = None,
  limit: int = Query(50, ge=1, le=200),
):
  resolved_user_id = user_id or getattr(request.state, "user_id", None)
  if not resolved_user_id:
    raise HTTPException(status_code=401, detail="Missing authenticated user")

  status = status.lower()
  valid = {
    "new",
    "processed",
    "error",
    "pending_ai_analysis",
    "ai_analyzed",
    "routed",
    "accepted",
    "rejected",
    "needs_review",
    "all",
  }
  if status not in valid:
    raise HTTPException(status_code=400, detail="Invalid status filter")

  supabase = get_supabase_client()
  query_builder = supabase.table("gmail_messages").select("*").eq("user_id", resolved_user_id).order("received_at", desc=True).limit(limit)

  if status != "all":
    if status == "new":
      query_builder = query_builder.in_("status", ["new", "baseline", "pending_ai_analysis"])
    elif status == "pending_ai_analysis":
      query_builder = query_builder.in_("status", ["pending_ai_analysis", "new", "baseline"])
    else:
      query_builder = query_builder.eq("status", status)

  resp = query_builder.execute()
  rows = resp.data if hasattr(resp, "data") else []

  # Optional simple search
  if query:
    q_lower = query.lower()
    rows = [
      r
      for r in rows
      if q_lower in (r.get("subject") or "").lower()
      or q_lower in (r.get("sender") or "").lower()
      or q_lower in (r.get("snippet") or "").lower()
    ]

  return {"status": status, "count": len(rows), "messages": rows}


@router.get("/messages/{message_id}")
def inbox_message_detail(request: Request, message_id: str, user_id: str | None = None):
  resolved_user_id = resolve_user_id(request, user_id)
  record = message_store.get(resolved_user_id, message_id)
  if not record:
    raise HTTPException(status_code=404, detail="Message not found")
  return record
