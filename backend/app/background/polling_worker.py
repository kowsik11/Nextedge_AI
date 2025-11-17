from __future__ import annotations

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from ..services.token_service import get_or_refresh_tokens, log_token_event
from ..services.gmail_oauth import refresh_token as gmail_refresh
from ..services.supabase_client import get_supabase_client
from ..services.hubspot_client import hubspot_client

logger = logging.getLogger(__name__)


async def fetch_unread_messages(access_token: str, q: str | None = None) -> List[Dict[str, Any]]:
  headers = {"Authorization": f"Bearer {access_token}"}
  url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
  params = {"q": "is:unread", "maxResults": 50}
  if q:
    params["q"] = f"{params['q']} {q}"
  async with httpx.AsyncClient(timeout=20) as client:
    res = await client.get(url, headers=headers, params=params)
  res.raise_for_status()
  data = res.json()
  return data.get("messages") or []


async def fetch_message_detail(token: str, msg_id: str) -> Dict[str, Any]:
  headers = {"Authorization": f"Bearer {token}"}
  url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=metadata"
  async with httpx.AsyncClient(timeout=20) as client:
    res = await client.get(url, headers=headers)
  res.raise_for_status()
  return res.json()


def derive_flags(payload: Dict[str, Any]) -> Dict[str, bool]:
  snippet = payload.get("snippet", "") or ""
  parts = (payload.get("payload", {}) or {}).get("parts") or []
  has_attachments = any(part.get("filename") for part in parts if part.get("filename"))
  return {
    "has_attachments": has_attachments,
    "has_images": "img" in snippet.lower(),
    "has_links": "http" in snippet.lower(),
  }


async def poll_gmail_for_user(user_id: str) -> Dict[str, Any]:
  supabase = get_supabase_client()
  inserted = 0
  skipped = 0
  errors = 0
  logger.info("poll:start user_id=%s", user_id)
  try:
    tokens = get_or_refresh_tokens(user_id, "gmail", refresh_fn=gmail_refresh)
  except Exception as exc:
    logger.error("token:refresh_failed user_id=%s error=%s", user_id, exc)
    log_token_event(user_id, "gmail", "refresh_failed", {"error": str(exc)})
    raise

  access_token = tokens.get("access_token")
  if not access_token:
    raise RuntimeError("Missing access_token after refresh")

  conn_resp = supabase.table("gmail_connections").select("*").eq("user_id", user_id).maybe_single().execute()
  connection = conn_resp.data if hasattr(conn_resp, "data") else None
  baseline_ready = bool(connection.get("baseline_ready")) if connection else False
  baseline_at = connection.get("baseline_at") if connection else None
  last_poll_at = connection.get("last_poll_at") if connection else None

  # Establish baseline if missing: set baseline_at=now, baseline_ready=true, no import on this run
  if not baseline_at:
    baseline_at_iso = datetime.now(timezone.utc).isoformat()
    logger.info("baseline:set user_id=%s baseline_at=%s", user_id, baseline_at_iso)
    try:
      supabase.table("gmail_connections").upsert(
        {"user_id": user_id, "baseline_at": baseline_at_iso, "baseline_ready": True, "updated_at": baseline_at_iso, "last_poll_at": baseline_at_iso}
      ).execute()
    except Exception as exc:
      logger.error("db:update gmail_connections failed user_id=%s error=%s", user_id, exc)
      errors += 1
      raise
    return {"inserted": 0, "skipped": 0, "errors": errors, "last_poll_at": baseline_at_iso}

  # Baseline exists; if marked not ready, skip imports but mark ready to avoid repeated skips
  if not baseline_ready:
    try:
      supabase.table("gmail_connections").update({"baseline_ready": True, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("user_id", user_id).execute()
    except Exception as exc:
      logger.error("db:update gmail_connections set ready failed user_id=%s error=%s", user_id, exc)
      errors += 1
      raise
    return {"inserted": 0, "skipped": 0, "errors": errors, "last_poll_at": baseline_at}

  # Build Gmail filter: after baseline_at
  gmail_query = None
  cutoff_dt = None
  try:
    baseline_dt = datetime.fromisoformat(baseline_at)
    cutoff_dt = baseline_dt
  except Exception:
    cutoff_dt = None
  try:
    if last_poll_at:
      lp_dt = datetime.fromisoformat(last_poll_at)
      if cutoff_dt is None or lp_dt > cutoff_dt:
        cutoff_dt = lp_dt
  except Exception:
    pass
  # Clamp cutoff to now if somehow in the future
  try:
    now_dt = datetime.now(timezone.utc)
    if cutoff_dt and cutoff_dt > now_dt:
      cutoff_dt = now_dt
  except Exception:
    pass
  cutoff_ms = None
  if cutoff_dt:
    try:
      cutoff_ms = int(cutoff_dt.timestamp() * 1000)
      gmail_query = f"after:{int(cutoff_ms/1000)}"
    except Exception:
      gmail_query = None

  try:
    msgs = await fetch_unread_messages(access_token, gmail_query)
    logger.info("gmail:fetch count=%s user_id=%s q=%s", len(msgs), user_id, gmail_query)
  except Exception as exc:
    logger.error("gmail:fetch failed user_id=%s error=%s", user_id, exc)
    errors += 1
    raise

  now_iso = datetime.now(timezone.utc).isoformat()
  rows = []
  # Filter by baseline_at using internalDate if available
  for msg in msgs:
    try:
      full = await fetch_message_detail(access_token, msg["id"])
      headers = full.get("payload", {}).get("headers", [])
      subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
      sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "")
      flags = derive_flags(full)
      status = "baseline" if not baseline_ready else "new"
      row = {
        "user_id": user_id,
        "message_id": full.get("id"),
        "thread_id": full.get("threadId"),
        "subject": subject,
        "sender": sender,
        "snippet": full.get("snippet"),
        "preview": full.get("snippet"),
        "status": status,
        "has_attachments": flags["has_attachments"],
        "has_images": flags["has_images"],
        "has_links": flags["has_links"],
        "gmail_url": f"https://mail.google.com/mail/u/0/#inbox/{full.get('id')}",
        "crm_record_url": None,
        "error": None,
        "received_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso,
      }
      # client-side filter: only after baseline
      internal_date_ms = None
      try:
        internal_date_ms = int(full.get("internalDate"))
      except Exception:
        internal_date_ms = None
      if cutoff_ms is not None and internal_date_ms is not None and internal_date_ms <= cutoff_ms:
        skipped += 1
        continue
      rows.append(row)
    except Exception as exc:
      logger.error("gmail:message_parse_failed user_id=%s msg_id=%s error=%s", user_id, msg.get("id"), exc)
      errors += 1

  if rows:
    to_insert = []
    for r in rows:
      try:
        existing_resp = (
          supabase.table("gmail_messages")
          .select("id")
          .eq("user_id", user_id)
          .eq("message_id", r["message_id"])
          .maybe_single()
          .execute()
        )
        existing = existing_resp.data if hasattr(existing_resp, "data") else None
        if existing:
          skipped += 1
          continue
        to_insert.append(r)
      except Exception as exc:
        logger.error("db:lookup failed user_id=%s msg_id=%s error=%s", user_id, r.get("message_id"), exc)
        errors += 1

    if to_insert:
      try:
        supabase.table("gmail_messages").insert(to_insert).execute()
        inserted += len(to_insert)
        logger.info("db:insert success rows=%s user_id=%s", len(to_insert), user_id)
      except Exception as exc:
        logger.error("db:insert failed user_id=%s error=%s", user_id, exc)
        errors += len(to_insert)
        raise

  try:
    supabase.table("gmail_connections").update(
      {
        "baseline_ready": True,
        "last_poll_at": now_iso,
        "updated_at": now_iso,
      }
    ).eq("user_id", user_id).execute()
  except Exception as exc:
    logger.error("db:update gmail_connections failed user_id=%s error=%s", user_id, exc)

  logger.info("poll:end user_id=%s last_poll_at=%s", user_id, now_iso)
  return {"inserted": inserted, "skipped": skipped, "errors": errors, "last_poll_at": now_iso}


async def poll_user(user_id: str) -> None:
  await poll_gmail_for_user(user_id)


async def run_polling_once(user_ids: List[str]) -> None:
  await asyncio.gather(*(poll_user(uid) for uid in user_ids))


if __name__ == "__main__":
  asyncio.run(run_polling_once([]))
