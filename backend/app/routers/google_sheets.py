from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from email.utils import parseaddr
import json
from datetime import datetime, timezone

from ..config import settings
from ..services.supabase_client import get_supabase
from ..services.google_sheets_service import GoogleSheetsService
from ..services.llm import gemini_client
from ..models.email import EmailMessage, AIExtraction

router = APIRouter(prefix="/api/google-sheets", tags=["Google Sheets"])

class SpreadsheetSelection(BaseModel):
    user_id: str
    spreadsheet_id: str

class SyncEmailRequest(BaseModel):
  user_id: str
  email_id: str
  reasoning: Optional[str] = None
  classification: Optional[str] = None


def _get_or_create_default_spreadsheet(supabase, connection: dict, service: GoogleSheetsService, workspace_id: str) -> dict:
  """Ensure a spreadsheet exists; create one if missing."""
  if connection.get("spreadsheet_id"):
    return connection
  created = service.create_spreadsheet(f"NextEdge Emails - {workspace_id}")
  spreadsheet_id = created.get("id") or ""
  spreadsheet_name = created.get("name")
  spreadsheet_url = created.get("url")
  if spreadsheet_id:
    try:
      service.initialize_sheet_headers(spreadsheet_id)
    except Exception as exc:
      print(f"Failed to init headers on auto-created sheet: {exc}")
  payload = {
    "spreadsheet_id": spreadsheet_id,
    "spreadsheet_name": spreadsheet_name,
    "spreadsheet_url": spreadsheet_url,
  }
  supabase.table("google_sheets_connections").update(payload).eq("id", connection.get("id")).execute()
  return {**connection, **payload}


def _safe(value: str | None, default: str = "N/A") -> str:
  if value is None:
    return default
  if isinstance(value, str) and value.strip() == "":
    return default
  return str(value)


def _parse_sender(sender_raw: str | None) -> tuple[str, str]:
  name, email = parseaddr(sender_raw or "")
  email_val = email or "N/A"
  if name:
    from_name = name.strip()
  else:
    # derive from domain
    domain_part = email.split("@")[1] if "@" in email else ""
    from_name = domain_part.split(".")[0].capitalize() if domain_part else "Unknown"
  return email_val, from_name or "Unknown"


def _truncate(text: str, limit: int) -> str:
  if text is None:
    return ""
  return text[:limit] + ("..." if len(text) > limit else "")


def _run_ai_enrichment(email_row: dict) -> dict:
  """
  Run an AI pass to fill classification/intent/sender_label/entities/etc.
  Uses subject + body only; falls back to safe defaults.
  """
  defaults = {
    "classification": "None",
    "confidence": 0.0,
    "intent": "N/A",
    "urgency": "Medium",
    "sentiment": "Neutral",
    "sender_label": "Unknown",
    "entities": [],
    "reasoning": "N/A",
  }

  subject = (email_row.get("subject") or "").strip()
  body = (email_row.get("body_text") or email_row.get("snippet") or "").strip()
  prompt = f"""
You are an email analyst. Use ONLY the provided subject and body. Do not invent facts.
Return a single JSON object with ALL fields present:
{{
  "classification": "Lead|Case|Contact|Opportunity|None",
  "confidence": 0.0-1.0,
  "intent": "short phrase like sales|support|job opportunity|N/A",
  "urgency": "Low|Medium|High|Critical",
  "sentiment": "Positive|Neutral|Negative",
  "sender_label": "human label for sender (e.g., Upwork, Salesforce, Customer, Internal, Unknown)",
  "entities": [{{"type": "company|person|product|job_role|date|other", "value": "..." }}],
  "reasoning": "one short sentence explaining the classification"
}}
Rules:
- If uncertain, use defaults: classification "None", confidence 0.0, intent "N/A", urgency "Medium", sentiment "Neutral", sender_label "Unknown", entities [].
- Entities must come from the text only; if none, return an empty array.
- Output JSON only, no extra text.
Subject: {subject or "N/A"}
Body: {body or "N/A"}
""".strip()

  try:
    raw = gemini_client._invoke(prompt, email_row.get("message_id", "") or email_row.get("id", ""), "sheets_enrichment")
    parsed = json.loads(raw)
  except Exception:
    return defaults

  try:
    classification = parsed.get("classification") or defaults["classification"]
    conf = parsed.get("confidence", defaults["confidence"])
    try:
      conf = float(conf)
    except Exception:
      conf = defaults["confidence"]
    conf = max(0.0, min(1.0, conf))
    intent = parsed.get("intent") or defaults["intent"]
    urg = parsed.get("urgency") or defaults["urgency"]
    if urg not in ["Low", "Medium", "High", "Critical"]:
      urg = defaults["urgency"]
    sent = parsed.get("sentiment") or defaults["sentiment"]
    if sent not in ["Positive", "Neutral", "Negative"]:
      sent = defaults["sentiment"]
    sender_label = parsed.get("sender_label") or defaults["sender_label"]
    ents = parsed.get("entities") or []
    if not isinstance(ents, list):
      ents = []
    reasoning = parsed.get("reasoning") or defaults["reasoning"]
    return {
      "classification": classification,
      "confidence": conf,
      "intent": intent,
      "urgency": urg,
      "sentiment": sent,
      "sender_label": sender_label,
      "entities": ents,
      "reasoning": reasoning,
    }
  except Exception:
    return defaults


def _derive_ai_fields(email_row: dict) -> dict:
  # Defaults
  defaults = {
    "classification": "None",
    "confidence": 0.0,
    "intent": "N/A",
    "urgency": "Medium",
    "sentiment": "Neutral",
    "sender_label": "Unknown",
    "entities": [],
    "reasoning": "N/A",
  }
  routing = email_row.get("ai_routing_decision") or {}
  result = defaults.copy()
  try:
    result["classification"] = routing.get("primary_object") or defaults["classification"]
    conf = routing.get("confidence")
    if conf is None:
      conf = email_row.get("ai_confidence")
    if conf is None:
      conf = defaults["confidence"]
    result["confidence"] = max(0.0, min(1.0, float(conf)))
    result["intent"] = routing.get("intent") or defaults["intent"]
    urg = routing.get("urgency") or defaults["urgency"]
    if urg not in ["Low", "Medium", "High", "Critical"]:
      urg = "Medium"
    result["urgency"] = urg
    sent = routing.get("sentiment") or defaults["sentiment"]
    if sent not in ["Positive", "Neutral", "Negative"]:
      sent = "Neutral"
    result["sentiment"] = sent
    result["sender_label"] = routing.get("sender_label") or defaults["sender_label"]
    ents = routing.get("entities")
    if isinstance(ents, list):
      result["entities"] = ents
    result["reasoning"] = routing.get("reasoning") or email_row.get("ai_summary") or defaults["reasoning"]
  except Exception:
    return defaults
  return result

def get_or_create_workspace(user_id: str) -> str:
    """
    Ensure a workspace row exists for this user and return its id.
    Uses the user's Supabase auth id as owner_id.
    """
    supabase = get_supabase()
    try:
        # Upsert using the user's id as workspace id to avoid extra lookups
        supabase.table("workspaces").upsert(
            {
                "id": user_id,
                "name": "Default Workspace",
                "owner_id": user_id,
            },
            on_conflict="id",
        ).execute()
        return user_id
    except Exception as exc:
        print(f"Workspace upsert failed: {exc}")

    raise HTTPException(status_code=500, detail="Could not resolve workspace for user")

@router.get("/auth")
async def initiate_oauth(user_id: str):
    """Initiate Google Sheets OAuth flow"""
    # Verify user/workspace exists
    get_or_create_workspace(user_id)
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_sheets_client_id,
                "client_secret": settings.google_sheets_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=settings.google_sheets_scopes,
        redirect_uri=str(settings.google_sheets_redirect_uri)
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=user_id  # Pass user_id as state
    )
    
    return {"auth_url": authorization_url}

@router.get("/callback")
@router.get("/auth/google-sheets/callback")
async def oauth_callback(code: str, state: str):
    """Handle OAuth callback and store tokens"""
    user_id = state
    workspace_id = get_or_create_workspace(user_id)
    
    try:
        supabase = get_supabase()
        existing = supabase.table("google_sheets_connections").select("*").eq("workspace_id", workspace_id).execute()

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_sheets_client_id,
                    "client_secret": settings.google_sheets_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=settings.google_sheets_scopes,
            redirect_uri=str(settings.google_sheets_redirect_uri)
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        # Google may omit refresh_token on re-consent; reuse stored token if present
        if not credentials.refresh_token and existing.data:
            stored_refresh = existing.data[0].get("refresh_token")
            if stored_refresh:
                credentials.refresh_token = stored_refresh
        if not credentials.refresh_token:
            raise HTTPException(status_code=400, detail="Google did not return a refresh token. Remove the app from your Google Account permissions and reconnect with consent.")
        
        service = GoogleSheetsService(credentials.token, credentials.refresh_token)
        # Auto-create a spreadsheet if none exists
        created_sheet = service.create_spreadsheet("NextEdge Emails")
        spreadsheet_id = created_sheet.get("id") or ""
        spreadsheet_name = created_sheet.get("name")
        spreadsheet_url = created_sheet.get("url")
        # Initialize headers on the new sheet
        if spreadsheet_id:
            try:
                service.initialize_sheet_headers(spreadsheet_id)
            except Exception as exc:
                print(f"Failed to initialize headers on new sheet: {exc}")

        data = {
            "workspace_id": workspace_id,
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_expires_at": credentials.expiry.isoformat() if credentials.expiry else None,
            "scopes": credentials.scopes,
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_url": spreadsheet_url,
            "status": "active"
        }
        
        # Check if connection exists
        if existing.data:
            supabase.table("google_sheets_connections").update(data).eq("workspace_id", workspace_id).execute()
        else:
            supabase.table("google_sheets_connections").insert(data).execute()
            
        # Redirect to frontend
        frontend_base = str(settings.frontend_url).rstrip("/")
        return RedirectResponse(url=f"{frontend_base}/home?connected=sheets")
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
async def get_connection_status(user_id: str):
    """Get Google Sheets connection status"""
    workspace_id = get_or_create_workspace(user_id)
    supabase = get_supabase()
    
    response = supabase.table("google_sheets_connections").select("*").eq("workspace_id", workspace_id).execute()
    
    if not response.data:
        return {"status": "disconnected"}
        
    connection = response.data[0]
    return {
        "status": connection["status"],
        "spreadsheet_name": connection.get("spreadsheet_name"),
        "last_sync_at": connection.get("last_sync_at")
    }

@router.get("/spreadsheets")
async def list_spreadsheets(user_id: str):
    """List user's Google Sheets"""
    workspace_id = get_or_create_workspace(user_id)
    supabase = get_supabase()
    
    response = supabase.table("google_sheets_connections").select("*").eq("workspace_id", workspace_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    connection = response.data[0]
    service = GoogleSheetsService(connection["access_token"], connection["refresh_token"])
    
    return service.list_spreadsheets()

@router.post("/select-spreadsheet")
async def select_spreadsheet(selection: SpreadsheetSelection):
    """Set target spreadsheet for syncing"""
    workspace_id = get_or_create_workspace(selection.user_id)
    supabase = get_supabase()
    
    # Get connection
    response = supabase.table("google_sheets_connections").select("*").eq("workspace_id", workspace_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Connection not found")
        
    connection = response.data[0]
    service = GoogleSheetsService(connection["access_token"], connection["refresh_token"])
    
    # Get sheet info
    info = service.get_spreadsheet_info(selection.spreadsheet_id)
    
    # Initialize headers
    service.initialize_sheet_headers(selection.spreadsheet_id)
    
    # Update connection
    supabase.table("google_sheets_connections").update({
        "spreadsheet_id": selection.spreadsheet_id,
        "spreadsheet_name": info["name"],
        "spreadsheet_url": info["url"]
    }).eq("id", connection["id"]).execute()
    
    return {"success": True, "spreadsheet": info}

@router.post("/sync-email")
async def sync_email_to_sheets(request: SyncEmailRequest):
    """Send a specific email to Google Sheets, optionally updating DB first"""
    workspace_id = get_or_create_workspace(request.user_id)
    supabase = get_supabase()

    # 1. Get connection
    conn_response = supabase.table("google_sheets_connections").select("*").eq("workspace_id", workspace_id).execute()
    if not conn_response.data:
        raise HTTPException(status_code=404, detail="Google Sheets not connected")
    connection = conn_response.data[0]
    service = GoogleSheetsService(connection["access_token"], connection["refresh_token"])
    connection = _get_or_create_default_spreadsheet(supabase, connection, service, workspace_id)
    if not connection.get("spreadsheet_id"):
        raise HTTPException(status_code=400, detail="No spreadsheet selected")

    # Ensure headers exist on the default sheet tab
    try:
        service.initialize_sheet_headers(connection["spreadsheet_id"])
    except Exception as exc:
        print(f"Sheets header init failed: {exc}")

    # 2. Update Supabase with any overrides
    updates: dict[str, Any] = {}
    if request.reasoning is not None:
        updates["reasoning"] = request.reasoning
    if request.classification is not None:
        updates["classification"] = request.classification
    if updates:
        check = supabase.table("ai_analysis").select("id").eq("email_id", request.email_id).execute()
        if check.data:
            supabase.table("ai_analysis").update(updates).eq("email_id", request.email_id).execute()
        else:
            updates["email_id"] = request.email_id
            supabase.table("ai_analysis").insert(updates).execute()

    # 3. Get email from Gmail messages (frontend sends gmail_messages.id)
    email_response = (
        supabase.table("gmail_messages")
        .select("*")
        .eq("id", request.email_id)
        .eq("user_id", request.user_id)
        .execute()
    )
    if not email_response.data:
        raise HTTPException(status_code=404, detail="Gmail message not found")
    email = email_response.data[0]

    enriched_ai = _run_ai_enrichment(email)
    routing_ai = _derive_ai_fields(email)
    ai_fields = {**routing_ai, **enriched_ai}

    from_email, from_name_guess = _parse_sender(email.get("sender"))
    from_name = (
        ai_fields.get("sender_label")
        if ai_fields.get("sender_label") not in [None, "", "Unknown"]
        else from_name_guess
    )
    # Prefer routing classification if present; else enriched/default
    classification_value = routing_ai.get("classification") or enriched_ai.get("classification") or "None"
    confidence_value = ai_fields.get("confidence", 0)
    confidence_pct = f"{confidence_value * 100:.2f}%"
    entities_value = ai_fields.get("entities") or []
    entities_str = (
        "; ".join([f"{ent.get('type')}: {ent.get('value')}" for ent in entities_value if isinstance(ent, dict)])
        if entities_value
        else "N/A"
    )

    # Body preview vs full body
    full_body = email.get("body_text") or email.get("snippet") or ""
    if full_body and len(full_body) > 10000:
        full_body = full_body[:10000]
    preview_source = email.get("snippet") or full_body
    body_preview = _truncate(preview_source, 300)

    # Persist AI snapshot to Supabase (gmail_messages_ai helper table)
    try:
        supabase.table("gmail_messages_ai").upsert(
            {
                "gmail_message_id": email.get("id"),
                "user_id": email.get("user_id"),
                "message_id": email.get("message_id"),
                "ai_routing_decision": {
                    "classification": classification_value,
                    "confidence": confidence_value,
                    "intent": ai_fields.get("intent"),
                    "urgency": ai_fields.get("urgency"),
                    "sentiment": ai_fields.get("sentiment"),
                    "sender_label": ai_fields.get("sender_label"),
                    "entities": ai_fields.get("entities"),
                    "reasoning": ai_fields.get("reasoning"),
                },
                "ai_summary": ai_fields.get("reasoning"),
                "ai_confidence": confidence_value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="gmail_message_id",
        ).execute()
    except Exception as exc:
        # Best-effort; do not fail the sync if this upsert fails
        print(f"Failed to upsert gmail_messages_ai: {exc}")

    # 4. Format data with safe defaults
    formatted_data = {
        "received_at": _safe(email.get("received_at"), datetime.now(timezone.utc).isoformat()),
        "email_id": _safe(email.get("id")),
        "from_email": _safe(from_email),
        "from_name": _safe(from_name),
        "subject": _safe(email.get("subject"), "(no subject)"),
        "classification": _safe(classification_value, "None"),
        "body_preview": _safe(body_preview, "N/A"),
        "body_full": _safe(full_body or email.get("snippet"), "N/A"),
        "confidence_score": confidence_pct,
        "urgency": _safe(ai_fields.get("urgency"), "Medium"),
        "sentiment": _safe(ai_fields.get("sentiment"), "Neutral"),
        "intent": _safe(ai_fields.get("intent"), "N/A"),
        "entities": entities_str,
        "reasoning": _safe(ai_fields.get("reasoning"), "N/A"),
        "has_attachments": "Yes" if email.get("has_attachments") else "No",
        "labels": ", ".join(email.get("labels", []) or []) if email.get("labels") else "N/A",
        "thread_id": _safe(email.get("thread_id"), "N/A"),
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "status": "synced",
    }

    # 5. Append to sheet and log sync
    try:
        row_number = service.append_email_row(connection["spreadsheet_id"], formatted_data)
    except Exception:
        # Only fail the request if the Sheets append failed
        raise HTTPException(status_code=500, detail="Sheets sync failed")

    supabase_log_status = "success"
    try:
        supabase.table("google_sheets_sync_log").insert({
            "connection_id": connection["id"],
            "email_id": email.get("id"),
            "sheet_row_number": row_number,
            "sync_status": "success",
            "classification_type": classification_value,
            "synced_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as exc:
        supabase_log_status = "failed"
        try:
            supabase.table("google_sheets_sync_log").insert({
                "connection_id": connection["id"],
                "email_id": email.get("id"),
                "sheet_row_number": row_number,
                "sync_status": "failed",
                "error_message": str(exc),
                "classification_type": classification_value,
                "synced_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception:
            pass

    supabase.table("google_sheets_connections").update({
        "last_sync_at": datetime.utcnow().isoformat()
    }).eq("id", connection["id"]).execute()

    return {
        "success": True,
        "row_number": row_number,
        "spreadsheet_url": connection.get("spreadsheet_url"),
        "supabase_log_status": supabase_log_status,
    }

@router.post("/disconnect")
async def disconnect_sheets(user_id: str):
    """Disconnect Google Sheets integration"""
    try:
        workspace_id = get_or_create_workspace(user_id)
        supabase = get_supabase()
        supabase.table("google_sheets_connections").delete().eq("workspace_id", workspace_id).execute()
        return {"success": True}
    except Exception:
        # If workspace resolution fails, maybe just return success as it's already disconnected effectively
        return {"success": True}

