from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.supabase_client import get_supabase

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("/list")
def list_messages(request: Request, status: str = Query("all"), limit: int = Query(50, ge=1, le=200)):
  user_id = getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")

  supabase = get_supabase()
  query = (
    supabase.table("gmail_messages")
    .select("*")
    .eq("user_id", user_id)
    .order("received_at", desc=True)
    .limit(limit)
  )
  if status != "all":
    query = query.eq("status", status)
  resp = query.execute()
  return {"messages": resp.data if hasattr(resp, "data") else []}
