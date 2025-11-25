"""Enhanced Salesforce routing with AI-driven object classification."""
from __future__ import annotations

import logging
from email.utils import parseaddr
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ..auth import resolve_user_id
from ..config import settings
from ..services.oauth_state import sign_state, verify_state
from ..services.salesforce_client import salesforce_client
from ..services.salesforce_oauth import exchange_code, get_authorization_url, get_salesforce_token
from ..services.token_service import delete_tokens
from ..storage.supabase_token_store import salesforce_token_store
from ..services.supabase_client import get_supabase_client
from ..services.ai_router import ai_router
from ..services.gmail_ingest import GmailIngestor

router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])
logger = logging.getLogger(__name__)
gmail_ingestor = GmailIngestor()


class DisconnectRequest(BaseModel):
  user_id: Optional[str] = None


class RouteEmailRequest(BaseModel):
  user_id: Optional[str] = None
  message_id: str


@router.get("/connect")
def connect_salesforce(request: Request, user_id: str | None = None):
  resolved_user_id = resolve_user_id(request, user_id)
  state = sign_state(resolved_user_id)
  url = get_authorization_url(state)
  return RedirectResponse(url=url)


@router.get("/callback")
def salesforce_callback(code: str, state: str):
  user_id = verify_state(state)
  exchange_code(user_id, code)
  return RedirectResponse(url=f"{str(settings.frontend_url).rstrip('/')}/home?connected=salesforce")


@router.get("/status")
def salesforce_status(request: Request, user_id: str | None = None):
  resolved_user_id = user_id or getattr(request.state, "user_id", None)
  if not resolved_user_id:
    return {"connected": False}
  try:
    record = get_salesforce_token(resolved_user_id)
  except HTTPException:
    return {"connected": False}
  return {
    "connected": True,
    "email": record.get("email"),
    "instance_url": record.get("instance_url"),
  }


@router.post("/disconnect")
def disconnect_salesforce(payload: DisconnectRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)
  delete_tokens(user_id, "salesforce")
  try:
    salesforce_token_store.delete(user_id)
    salesforce_token_store.clear_cache(user_id)
  except Exception as exc:
    logger.warning("Salesforce token delete failed for %s: %s", user_id, exc)
  return {"disconnected": True}


@router.post("/route-email")
def route_email_to_salesforce(payload: RouteEmailRequest, request: Request):
  """
  AI-driven routing to Salesforce CRM objects.
  Routes email to appropriate endpoint: Leads, Contacts, Cases, Opportunities, Campaigns, etc.
  """
  user_id = resolve_user_id(request, payload.user_id)
  supabase = get_supabase_client()
  
  # Fetch the message row
  row: dict | None = None
  message_id = payload.message_id
  try:
    resp = (
      supabase.table("gmail_messages")
      .select("*")
      .eq("user_id", user_id)
      .eq("message_id", message_id)
      .maybe_single()
      .execute()
    )
    row = resp.data if hasattr(resp, "data") else None
  except Exception:
    row = None
  if not row:
    try:
      resp = (
        supabase.table("gmail_messages")
        .select("*")
        .eq("user_id", user_id)
        .eq("id", message_id)
        .maybe_single()
        .execute()
      )
      row = resp.data if hasattr(resp, "data") else None
    except Exception:
      row = None
  if not row:
    raise HTTPException(status_code=404, detail="Message not found")

  # Fetch full email message for AI classification
  try:
    message = gmail_ingestor.fetch_message(user_id, row.get("message_id"))
  except Exception as exc:
    logger.error(f"Failed to fetch message for AI routing: {exc}")
    message = None

  # AI Classification to determine which Salesforce object to use
  routing = None
  if message:
    routing = ai_router.classify(message)
    logger.info(f"AI Routing Decision: {routing.primary_object} (confidence: {routing.confidence})")

  # === Helper Function: Build Comprehensive Description ===
  def build_comprehensive_description(
    routing: RoutingDecision | None,
    email_subject: str,
    email_body: str,
    name_guess: str,
    email_address: str,
    row: dict,
  ) -> str:
    """Build comprehensive description with AI metadata for any Salesforce object."""
    # AI Analysis Section
    ai_metadata_section = ""
    if routing:
      ai_metadata_section = f"""
╔═══════════════════════════════════════════════════════════════╗
║                       🤖 AI ANALYSIS REPORT                   ║
╚═══════════════════════════════════════════════════════════════╝

📊 CLASSIFICATION:
   • Primary Object: {routing.primary_object.upper()}
   • Intent: {routing.intent.upper()}
   • Urgency: {routing.urgency.upper()}
   • Confidence: {routing.confidence:.0%}

💡 AI REASONING:
   {routing.reasoning}

🎯 TARGET CRM:
   {', '.join([crm.upper() for crm in routing.target_crm]) if routing.target_crm else 'NOT SPECIFIED'}

"""
    
    # Sender Information Section
    sender_info = f"""
╔═══════════════════════════════════════════════════════════════╗
║                      📧 EMAIL INFORMATION                     ║
╚═══════════════════════════════════════════════════════════════╝

👤 FROM:
   Name: {name_guess or 'Unknown'}
   Email: {email_address}

📝 SUBJECT:
   {email_subject}

📅 RECEIVED:
   {row.get('received_at') or 'Recently'}

"""
    
    # Complete Description
    return f"""{ai_metadata_section}{sender_info}
╔═══════════════════════════════════════════════════════════════╗
║                      📄 EMAIL CONTENT                         ║
╚═══════════════════════════════════════════════════════════════╝

{email_body}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Automatically routed via NextEdge AI Integration
🔗 View original email: {row.get('gmail_url', 'N/A')}
"""
  
  # === Extract sender information ===
  sender = row.get("sender") or ""
  _, sender_email = parseaddr(sender)
  email_address = sender_email or f"user_{row.get('id', '')}@example.com"
  name_guess = sender.replace(f"<{sender_email}>", "").strip() if sender_email else sender
  
  # Get email content
  email_subject = row.get("subject") or "Email from NextEdge"
  email_body = row.get("preview") or row.get("snippet") or ""
  
  # Determine which Salesforce object to create based on AI routing
  primary_object = routing.primary_object if routing else "contacts"
  record_id = None
  crm_url = None
  object_type = None
  
  # Map both HubSpot and Salesforce terminology to Salesforce objects
  # This allows AI to use either terminology and route correctly
  salesforce_object_map = {
    # ===== Salesforce Native Terminology =====
    "contacts": "Contact",      # Individual people
    "leads": "Lead",             # New prospects (Salesforce-specific)
    "accounts": "Account",       # Organizations/businesses
    "opportunities": "Opportunity",  # Sales deals (Salesforce term)
    "cases": "Case",             # Support tickets (Salesforce term)
    "campaigns": "Campaign",     # Marketing campaigns (Salesforce-specific)
    "orders": "Order",           # Purchase orders
    
    # ===== HubSpot Terminology → Salesforce Mapping =====
    "companies": "Account",      # HubSpot companies → Salesforce Accounts
    "deals": "Opportunity",      # HubSpot deals → Salesforce Opportunities
    "tickets": "Case",           # HubSpot tickets → Salesforce Cases
    
    # ===== Common/Fallback =====
    "notes": "Task",             # Create as Task in Salesforce
    "none": "Contact",           # Fallback to Contact if classification unclear
  }
  
  sf_object = salesforce_object_map.get(primary_object, "Contact")
  
  logger.info(f"AI Classification: {primary_object} → Salesforce Object: {sf_object} (confidence: {routing.confidence if routing else 0:.0%})")
  
  try:
    if sf_object == "Contact":
      # Create/Update Contact with comprehensive AI metadata
      last_name = name_guess or "Contact"
      comprehensive_desc = build_comprehensive_description(
        routing, email_subject, email_body, name_guess, email_address, row
      )
      properties = {
        "LastName": last_name,
        "Email": email_address,
        "Description": comprehensive_desc,  # Full AI metadata
      }
      record_id = salesforce_client.upsert_contact(user_id, email_address, properties)
      object_type = "contacts"
      
    elif sf_object == "Lead":
      # Create Lead (for prospects not yet converted) with comprehensive AI metadata
      comprehensive_desc = build_comprehensive_description(
        routing, email_subject, email_body, name_guess, email_address, row
      )
      properties = {
        "LastName": name_guess or "Lead",
        "Email": email_address,
        "Company": "Unknown",
        "Status": "Open - Not Contacted",
        "Description": comprehensive_desc,  # Full AI metadata
      }
      result = salesforce_client.create_lead(user_id, properties)
      record_id = result.get("id") or result.get("Id")
      object_type = "leads"
      
    elif sf_object == "Case":
      # Create Case (for support tickets) with comprehensive AI metadata
      # First, create/find Contact for the sender
      contact_id = None
      try:
        contact_properties = {
          "LastName": name_guess or "Support Contact",
          "Email": email_address,
        }
        contact_id = salesforce_client.upsert_contact(user_id, email_address, contact_properties)
      except Exception as e:
        logger.warning(f"Failed to create Contact for Case: {e}")
      
      # Build comprehensive Case description with ALL AI metadata
      ai_metadata_section = ""
      if routing:
        ai_metadata_section = f"""
╔═══════════════════════════════════════════════════════════════╗
║                       🤖 AI ANALYSIS REPORT                   ║
╚═══════════════════════════════════════════════════════════════╝

📊 CLASSIFICATION:
   • Primary Object: {routing.primary_object.upper()}
   • Intent: {routing.intent.upper()}
   • Urgency: {routing.urgency.upper()}
   • Confidence: {routing.confidence:.0%}

💡 AI REASONING:
   {routing.reasoning}

🎯 TARGET CRM:
   {', '.join([crm.upper() for crm in routing.target_crm]) if routing.target_crm else 'NOT SPECIFIED'}

"""
      
      # Build sender information section
      sender_info = f"""
╔═══════════════════════════════════════════════════════════════╗
║                      📧 EMAIL INFORMATION                     ║
╚═══════════════════════════════════════════════════════════════╝

👤 FROM:
   Name: {name_guess or 'Unknown'}
   Email: {email_address}

📝 SUBJECT:
   {email_subject}

📅 RECEIVED:
   {row.get('received_at') or 'Recently'}

"""
      
      # Combine all sections
      full_description = f"""{ai_metadata_section}{sender_info}
╔═══════════════════════════════════════════════════════════════╗
║                      📄 EMAIL CONTENT                         ║
╚═══════════════════════════════════════════════════════════════╝

{email_body}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Automatically routed via NextEdge AI Integration
🔗 View original email: {row.get('gmail_url', 'N/A')}
"""
      
      properties = {
        "Subject": f"{email_subject} - {name_guess or sender_email}",  # Include sender name in subject
        "Description": full_description,  # Full comprehensive description
        "Origin": "Email",
        "Status": "New",
        "Priority": routing.urgency.capitalize() if routing else "Medium",
      }
      
      # Link to Contact if we have one
      if contact_id:
        properties["ContactId"] = contact_id
      
      result = salesforce_client.create_case(user_id, properties)
      record_id = result.get("id") or result.get("Id")
      object_type = "cases"
      
    elif sf_object == "Opportunity":
      # Create Opportunity (for deals/sales) with comprehensive AI metadata
      comprehensive_desc = build_comprehensive_description(
        routing, email_subject, email_body, name_guess, email_address, row
      )
      properties = {
        "Name": f"{email_subject or 'Opportunity from NextEdge'} - {name_guess or sender_email}",
        "StageName": "Prospecting",
        "CloseDate": "2025-12-31",  # Default close date
        "Description": comprehensive_desc,  # Full AI metadata
      }
      # If amount is suggested, add it
      if routing and routing.suggested_properties.get("deal", {}).get("amount"):
        properties["Amount"] = routing.suggested_properties["deal"]["amount"]
      
      result = salesforce_client.create_opportunity(user_id, properties)
      record_id = result.get("id") or result.get("Id")
      object_type = "opportunities"
      
    elif sf_object == "Campaign":
      # Create Campaign (for marketing) with comprehensive AI metadata
      comprehensive_desc = build_comprehensive_description(
        routing, email_subject, email_body, name_guess, email_address, row
      )
      properties = {
        "Name": f"{email_subject or 'Campaign from NextEdge'} - {name_guess or sender_email}",
        "Status": "Planned",
        "Type": "Email",
        "Description": comprehensive_desc,  # Full AI metadata
      }
      result = salesforce_client.create_campaign(user_id, properties)
      record_id = result.get("id") or result.get("Id")
      object_type = "campaigns"
      
    elif sf_object == "Order":
      # Create Order (requires Account) with comprehensive AI metadata
      comprehensive_desc = build_comprehensive_description(
        routing, email_subject, email_body, name_guess, email_address, row
      )
      properties = {
        "Status": "Draft",
        "Description": comprehensive_desc,  # Full AI metadata
      }
      result = salesforce_client.create_order(user_id, properties)
      record_id = result.get("id") or result.get("Id")
      object_type = "orders"
      
    else:
      # Default fallback to Contact
      last_name = name_guess or "Contact"
      properties = {
        "LastName": last_name,
        "Email": email_address,
        "Description": f"{email_subject}\n\n{email_body[:1000]}",
      }
      record_id = salesforce_client.upsert_contact(user_id, email_address, properties)
      object_type = "contacts"

    # Create a Task linked to the record (with prominent AI summary)
    if record_id and sf_object in ["Contact", "Lead", "Case"]:
      try:
        # Build comprehensive AI summary for Task description
        ai_summary_section = ""
        if routing:
          ai_summary_section = f"""
╔══════════════ AI ANALYSIS ══════════════╗
│ Primary Object: {routing.primary_object.upper()}
│ Intent: {routing.intent.upper()}
│ Urgency: {routing.urgency.upper()}
│ Confidence: {routing.confidence:.0%}
│
│ AI Reasoning:
│ {routing.reasoning}
╚═════════════════════════════════════════╝

"""
        
        task_properties = {
          "Subject": f"📧 {email_subject}",
          "Description": f"""{ai_summary_section}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📨 EMAIL FROM: {name_guess or sender}
📝 SUBJECT: {email_subject}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{email_body}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Routed via NextEdge AI
""",
          "Status": "Not Started",
          "Priority": routing.urgency.capitalize() if routing and routing.urgency else "Normal",
        }
        # Link to the appropriate record
        if sf_object == "Contact":
          task_properties["WhoId"] = record_id
        elif sf_object == "Lead":
          task_properties["WhoId"] = record_id
        # For Case, use WhatId
        elif sf_object == "Case":
          task_properties["WhatId"] = record_id
          
        salesforce_client.create_task(user_id, task_properties)
        logger.info(f"Created Task for {sf_object}: {email_subject}")
      except Exception as e:
        logger.warning(f"Failed to create Task in Salesforce: {e}")

    # Build CRM URL
    try:
      token = get_salesforce_token(user_id)
      instance = token.get("instance_url", "").rstrip("/")
      if record_id:
        crm_url = f"{instance}/{record_id}"
    except Exception:
      crm_url = None

    # Update gmail_messages table with proper column mapping
    update_payload = {
      "salesforce_object_type": object_type,
      "crm_record_url": crm_url or row.get("crm_record_url"),
      "status": "routed",
    }
    
    # Map object_type to correct Salesforce ID column
    if object_type == "contacts":
      update_payload["salesforce_contact_id"] = record_id
    elif object_type == "leads":
      update_payload["salesforce_lead_id"] = record_id
    elif object_type == "cases":
      update_payload["salesforce_case_id"] = record_id
    elif object_type == "opportunities":
      update_payload["salesforce_opportunity_id"] = record_id
    elif object_type == "campaigns":
      update_payload["salesforce_campaign_id"] = record_id
    elif object_type == "orders":
      update_payload["salesforce_order_id"] = record_id
    elif object_type == "accounts":
      update_payload["salesforce_account_id"] = record_id
    
    # Add AI routing info if available
    if routing:
      update_payload["ai_routing_decision"] = {
        "primary_object": routing.primary_object,
        "secondary_objects": routing.secondary_objects,
        "confidence": routing.confidence,
        "reasoning": routing.reasoning,
        "intent": routing.intent,
        "urgency": routing.urgency,
        "target_crm": routing.target_crm,
      }
      update_payload["ai_summary"] = routing.reasoning
      update_payload["ai_confidence"] = routing.confidence
    
    try:
      supabase.table("gmail_messages").update(update_payload).eq("user_id", user_id).eq("id", row.get("id")).execute()
      logger.info(f"Updated gmail_messages: {object_type} record_id={record_id}")
    except Exception as e:
      logger.warning(f"Failed to persist Salesforce routing metadata: {e}", exc_info=True)

    return {
      "routed": True,
      "object_type": object_type,
      "record_id": record_id,
      "crm_url": crm_url,
      "ai_routing": {
        "primary_object": routing.primary_object if routing else "contacts",
        "confidence": routing.confidence if routing else 0.0,
        "reasoning": routing.reasoning if routing else "Manual routing",
      },
    }
    
  except Exception as exc:
    logger.error(f"Failed to route email to Salesforce: {exc}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"Salesforce routing failed: {str(exc)}")
