from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.gmail_ingest import gmail_ingestor
from ..services.llm import gemini_client
from ..services.ai_router import ai_router
from ..services.validator import validator_service
from ..services.planner import build_enhanced_crm_plan
from ..services.hubspot_client import hubspot_client
from ..services.hubspot_oauth import get_hubspot_token
from ..storage.message_store import message_store
from ..services.supabase_client import get_supabase_client

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)


class PipelineRequest(BaseModel):
  user_id: str | None = Field(None, description="Supabase user id")
  max_messages: int = Field(3, ge=1, le=500)
  execute_hubspot: bool = False

class AnalyzeRequest(BaseModel):
  user_id: str | None = None
  message_id: str
  note_override: str | None = None

class RejectRequest(BaseModel):
  user_id: str | None = None
  message_id: str


class AcceptRequest(BaseModel):
  user_id: str | None = None
  message_id: str
  note_override: str | None = None

from ..auth import resolve_user_id


@router.post("/run")
def run_pipeline(payload: PipelineRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)
  start = time.perf_counter()
  try:
    messages = gmail_ingestor.poll(user_id, max_messages=payload.max_messages)
  except RuntimeError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc

  supabase = get_supabase_client()
  results = []
  portal_id = None
  try:
    connection = get_hubspot_token(user_id)
    portal_id = connection.get("external_user_id") or connection.get("portal_id")
  except Exception:
    portal_id = None

  for message in messages:
    message_start = time.perf_counter()
    try:
      routing = ai_router.classify(message)
      raw_json = gemini_client.analyze_email(message)
      extraction = validator_service.validate(message, raw_json)
      extraction.routing_decision = routing.__dict__
      enhanced_plan = build_enhanced_crm_plan(message, extraction, routing)

      status = "ai_analyzed"
      hubspot_result = None
      if payload.execute_hubspot:
        hubspot_result = hubspot_client.execute_enhanced_plan(user_id, enhanced_plan)
        status = "accepted"

      now_iso = datetime.now(timezone.utc).isoformat()
      upsert_payload = _build_supabase_row(
        user_id=user_id,
        message=message,
        status=status,
        routing=routing.__dict__,
        hubspot_result=hubspot_result or {},
        updated_at=now_iso,
      )
      supabase.table("gmail_messages").upsert(upsert_payload, on_conflict="user_id,message_id").execute()

      results.append(
        {
          "message_id": message.message_id,
          "extraction": extraction.model_dump(),
          "plan": enhanced_plan.model_dump(),
          "hubspot": hubspot_result,
          "latency_ms": round((time.perf_counter() - message_start) * 1000, 2),
        }
      )
    except Exception as exc:
      logger.exception("Pipeline failed", extra={"message_id": message.message_id})
      try:
        now_iso = datetime.now(timezone.utc).isoformat()
        error_payload = _build_supabase_row(
          user_id=user_id,
          message=message,
          status="error",
          routing=None,
          hubspot_result={},
          updated_at=now_iso,
          error=str(exc),
        )
        supabase.table("gmail_messages").upsert(error_payload, on_conflict="user_id,message_id").execute()
      except Exception:
        message_store.update_status(user_id, message.message_id, status="error", error=str(exc))

  return {"processed": len(results), "latency_ms": round((time.perf_counter() - start) * 1000, 2), "results": results}


def _build_supabase_row(
  *,
  user_id: str,
  message,
  status: str,
  routing: dict | None,
  hubspot_result: dict,
  updated_at: str,
  error: str | None = None,
) -> dict:
  """
  Build a row for gmail_messages upsert. Minimal required fields are included so that
  the row is created if missing, and updated if present.
  """
  routing_target_crm = []
  routing_primary = None
  if routing:
    routing_target_crm = routing.get("target_crm") or []
    routing_primary = routing.get("primary_object")
  return {
    "user_id": user_id,
    "message_id": message.message_id,
    "thread_id": getattr(message, "thread_id", None),
    "subject": getattr(message, "subject", None),
    "sender": getattr(message, "sender", None),
    "snippet": getattr(message, "snippet", None),
    "preview": getattr(message, "snippet", None),
    "status": status,
    "has_attachments": bool(getattr(message, "attachments", [])),
    "has_images": any(getattr(att, "mime_type", "").startswith("image/") for att in getattr(message, "attachments", [])),
    "has_links": "http" in (getattr(message, "body_text", "") or ""),
    "gmail_url": f"https://mail.google.com/mail/u/0/#inbox/{message.thread_id or message.message_id}",
    "crm_record_url": None,
    "ai_routing_decision": routing,
    "ai_confidence": routing.get("confidence") if routing else None,
    "hubspot_object_type": routing_primary if routing and ("hubspot" in routing_target_crm or not routing_target_crm) else None,
    "salesforce_object_type": routing_primary if routing and "salesforce" in routing_target_crm else None,
    "hubspot_contact_id": hubspot_result.get("contact_id"),
    "hubspot_company_id": hubspot_result.get("company_id"),
    "hubspot_deal_id": hubspot_result.get("deal_id"),
    "hubspot_ticket_id": hubspot_result.get("ticket_id"),
    "hubspot_order_id": hubspot_result.get("order_id"),
    "hubspot_note_id": hubspot_result.get("note_id"),
    "error": error,
    "received_at": getattr(message, "sent_at", None).isoformat() if getattr(message, "sent_at", None) else None,
    "updated_at": updated_at,
    "created_at": updated_at,
  }


def _resolve_message_identifiers(user_id: str, raw_identifier: str) -> Tuple[str, Optional[str]]:
  """
  Accept either the DB row id or the Gmail message_id. Returns (gmail_message_id, db_row_id).
  If the db row can be found by id, we return its message_id for Gmail fetch and the db id for precise updates.
  """
  supabase = get_supabase_client()
  try:
    resp = (
      supabase.table("gmail_messages")
      .select("id, message_id")
      .eq("user_id", user_id)
      .eq("id", raw_identifier)
      .maybe_single()
      .execute()
    )
    row = resp.data if hasattr(resp, "data") else None
    if row:
      return row.get("message_id") or raw_identifier, row.get("id")
  except Exception:
    pass
  return raw_identifier, None


@router.post("/analyze")
def analyze_message(payload: AnalyzeRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)
  resolved_message_id, _ = _resolve_message_identifiers(user_id, payload.message_id)
  try:
    message = gmail_ingestor.fetch_message(user_id, resolved_message_id)
  except Exception as exc:
    raise HTTPException(status_code=404, detail=f"Message not found: {exc}") from exc

  routing = ai_router.classify(message)
  raw_json = gemini_client.analyze_email(message)
  extraction = validator_service.validate(message, raw_json)
  extraction.routing_decision = routing.__dict__
  enhanced_plan = build_enhanced_crm_plan(message, extraction, routing)
  if payload.note_override and enhanced_plan.note:
    enhanced_plan.note.body = payload.note_override

  now_iso = datetime.now(timezone.utc).isoformat()
  supabase = get_supabase_client()
  upsert_payload = _build_supabase_row(
    user_id=user_id,
    message=message,
    status="pending_ai_analysis",
    routing=routing.__dict__,
    hubspot_result={},
    updated_at=now_iso,
  )
  upsert_payload["ai_summary"] = extraction.summary
  supabase.table("gmail_messages").upsert(upsert_payload, on_conflict="user_id,message_id").execute()

  return {
    "status": "pending_ai_analysis",
    "routing": routing.__dict__,
    "extraction": extraction.model_dump(),
    "plan": enhanced_plan.model_dump(),
    "ai_summary": extraction.summary,
  }


@router.post("/accept")
def accept_message(payload: AcceptRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)
  resolved_message_id, _ = _resolve_message_identifiers(user_id, payload.message_id)
  try:
    message = gmail_ingestor.fetch_message(user_id, resolved_message_id)
  except Exception as exc:
    raise HTTPException(status_code=404, detail=f"Message not found: {exc}") from exc

  routing = ai_router.classify(message)
  raw_json = gemini_client.analyze_email(message)
  extraction = validator_service.validate(message, raw_json)
  extraction.routing_decision = routing.__dict__
  enhanced_plan = build_enhanced_crm_plan(message, extraction, routing)
  if payload.note_override and enhanced_plan.note:
    enhanced_plan.note.body = payload.note_override

  hubspot_result = hubspot_client.execute_enhanced_plan(user_id, enhanced_plan)

  now_iso = datetime.now(timezone.utc).isoformat()
  supabase = get_supabase_client()
  upsert_payload = _build_supabase_row(
    user_id=user_id,
    message=message,
    status="ai_analyzed",
    routing=routing.__dict__,
    hubspot_result=hubspot_result or {},
    updated_at=now_iso,
  )
  upsert_payload["ai_summary"] = extraction.summary
  supabase.table("gmail_messages").upsert(upsert_payload, on_conflict="user_id,message_id").execute()

  return {
    "status": "ai_analyzed",
    "routing": routing.__dict__,
    "extraction": extraction.model_dump(),
    "plan": enhanced_plan.model_dump(),
    "hubspot": hubspot_result,
    "ai_summary": extraction.summary,
  }


@router.post("/reject")
def reject_message(payload: RejectRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)
  resolved_message_id, db_row_id = _resolve_message_identifiers(user_id, payload.message_id)
  now_iso = datetime.now(timezone.utc).isoformat()
  supabase = get_supabase_client()
  try:
    query = supabase.table("gmail_messages").update({"status": "rejected", "updated_at": now_iso}).eq("user_id", user_id)
    if db_row_id:
      query = query.eq("id", db_row_id)
    else:
      query = query.eq("message_id", resolved_message_id)
    query.execute()
  except Exception as exc:
    raise HTTPException(status_code=500, detail=f"Unable to reject message: {exc}") from exc
  return {"status": "rejected", "message_id": payload.message_id}
