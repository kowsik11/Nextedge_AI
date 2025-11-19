from __future__ import annotations

import logging
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from httpx import QueryParams
from pydantic import BaseModel

from ..auth import resolve_user_id
from ..config import settings
from ..services.hubspot_client import hubspot_client
from ..services.hubspot_oauth import (
  exchange_code as hubspot_exchange_code,
  get_hubspot_token,
)
from ..services.oauth_state import sign_state, verify_state
from ..services.token_service import delete_tokens
from ..storage.supabase_token_store import hubspot_token_store

router = APIRouter(prefix="/api/hubspot", tags=["hubspot"])
logger = logging.getLogger(__name__)

CMS_BLOG_POST_SAMPLE: Dict[str, Any] = {
  "name": "Codex Sample Blog Post",
  "contentGroupId": "258518788828",
  "slug": "codex-sample-post",
  "blogAuthorId": "258546201299",
  "metaDescription": "Synthetic payload used to exercise the CMS blog POST endpoints.",
  "useFeaturedImage": False,
  "postBody": "<p>This is a sample payload triggered from the Safe Point control panel.</p>",
}

# Contacts sample payloads
CONTACT_CREATE_SAMPLE: Dict[str, Any] = {
  "properties": {
    "email": "test+dummy@example.com",
    "firstname": "Test",
    "lastname": "Contact",
    "phone": "+18885551234",
    "company": "Safe Point",
    "website": "example.com",
  }
}

CONTACT_UPDATE_ID = "1234567890"
CONTACT_UPDATE_SAMPLE: Dict[str, Any] = {"properties": {"firstname": "Updated"}}

CONTACT_SEARCH_SAMPLE: Dict[str, Any] = {
  "filterGroups": [
    {"filters": [{"propertyName": "email", "operator": "EQ", "value": "test+dummy@example.com"}]}
  ]
}

CONTACT_BATCH_READ_SAMPLE: Dict[str, Any] = {
  "properties": ["email", "firstname", "lastname"],
  "inputs": [{"id": "1234567890"}, {"id": "9876543210"}],
}

CONTACT_BATCH_CREATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"properties": {"email": "batch1@example.com", "firstname": "Batch", "lastname": "One"}},
    {"properties": {"email": "batch2@example.com", "firstname": "Batch", "lastname": "Two"}},
  ]
}

CONTACT_BATCH_UPDATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"id": "1234567890", "properties": {"favorite_food": "burger"}},
    {"id": "9876543210", "properties": {"favorite_food": "donut"}},
  ]
}

CONTACT_BATCH_UPSERT_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"id": "upsert1@example.com", "idProperty": "email", "properties": {"phone": "+12345670000"}},
    {"id": "upsert2@example.com", "idProperty": "email", "properties": {"phone": "+12345671111"}},
  ]
}

CONTACT_ASSOCIATE_PATH = "/crm/v3/objects/contacts/1234567890/associations/companies/1111111111/279"

# Companies sample payloads
COMPANY_CREATE_SAMPLE: Dict[str, Any] = {
  "properties": {
    "name": "Codex Sample Company",
    "domain": "codex-sample.com",
    "city": "Cambridge",
    "industry": "INFORMATION_TECHNOLOGY_AND_SERVICES",
    "phone": "+16175550123",
    "state": "Massachusetts",
  }
}

COMPANY_UPDATE_ID = "1122334455"
COMPANY_UPDATE_SAMPLE: Dict[str, Any] = {"properties": {"name": "Codex Updated Company"}}

COMPANY_SEARCH_SAMPLE: Dict[str, Any] = {
  "filterGroups": [
    {"filters": [{"propertyName": "domain", "operator": "EQ", "value": "codex-sample.com"}]}
  ]
}

COMPANY_BATCH_READ_SAMPLE: Dict[str, Any] = {
  "properties": ["name", "domain"],
  "inputs": [{"id": "1122334455"}, {"id": "5566778899"}],
}

COMPANY_BATCH_CREATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"properties": {"name": "Batch Company One", "domain": "batch-one.example.com"}},
    {"properties": {"name": "Batch Company Two", "domain": "batch-two.example.com"}},
  ]
}

COMPANY_BATCH_UPDATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"id": "1122334455", "properties": {"industry": "COMPUTER_SOFTWARE"}},
    {"id": "5566778899", "properties": {"industry": "MANAGEMENT_CONSULTING"}},
  ]
}

COMPANY_BATCH_UPSERT_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"id": "codex-upsert-1.com", "idProperty": "domain", "properties": {"name": "Codex Upsert One"}},
    {"id": "codex-upsert-2.com", "idProperty": "domain", "properties": {"name": "Codex Upsert Two"}},
  ]
}

COMPANY_ASSOCIATE_PATH = "/crm/v3/objects/companies/1122334455/associations/contacts/9998887777/company_to_contact"

# Deals sample payloads
DEAL_CREATE_SAMPLE: Dict[str, Any] = {
  "properties": {
    "dealname": "Codex Sample Deal",
    "amount": "7500",
    "pipeline": "default",
    "dealstage": "appointmentscheduled",
    "closedate": "2024-12-25T12:00:00Z",
  }
}

DEAL_UPDATE_ID = "44556677"
DEAL_UPDATE_SAMPLE: Dict[str, Any] = {"properties": {"amount": "12500", "dealstage": "contractsent"}}

DEAL_SEARCH_SAMPLE: Dict[str, Any] = {
  "filterGroups": [
    {
      "filters": [
        {"propertyName": "dealname", "operator": "EQ", "value": "Codex Sample Deal"},
      ]
    }
  ]
}

DEAL_BATCH_READ_SAMPLE: Dict[str, Any] = {
  "properties": ["dealname", "amount", "dealstage"],
  "inputs": [{"id": "44556677"}, {"id": "99887766"}],
}

DEAL_BATCH_CREATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {
      "properties": {
        "dealname": "Batch Deal Alpha",
        "amount": "3200",
        "pipeline": "default",
        "dealstage": "appointmentscheduled",
      }
    },
    {
      "properties": {
        "dealname": "Batch Deal Beta",
        "amount": "5400",
        "pipeline": "default",
        "dealstage": "qualifiedtobuy",
      }
    },
  ]
}

DEAL_BATCH_UPDATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"id": "44556677", "properties": {"amount": "9000"}},
    {"id": "99887766", "properties": {"dealstage": "presentationscheduled"}},
  ]
}

DEAL_ASSOCIATE_PATH = "/crm/v3/objects/deals/44556677/associations/contacts/12345678/4"

DEAL_BATCH_ARCHIVE_SAMPLE: Dict[str, Any] = {
  "inputs": [{"id": "44556677"}, {"id": "99887766"}, {"id": "11221122"}],
}

DEAL_PIN_UPDATE_ID = "44556677"
DEAL_PIN_SAMPLE: Dict[str, Any] = {"properties": {"hs_pinned_engagement_id": 123456789}}

# Tickets sample payloads
TICKET_CREATE_SAMPLE: Dict[str, Any] = {
  "properties": {
    "subject": "Codex Sample Ticket",
    "content": "Customer cannot access the Safe Point portal.",
    "hs_pipeline": "0",
    "hs_pipeline_stage": "1",
    "hs_ticket_priority": "HIGH",
  }
}

TICKET_UPDATE_ID = "4444888856"
TICKET_UPDATE_SAMPLE: Dict[str, Any] = {"properties": {"subject": "Updated ticket subject"}}

TICKET_SEARCH_SAMPLE: Dict[str, Any] = {
  "filterGroups": [
    {
      "filters": [
        {"propertyName": "subject", "operator": "EQ", "value": "troubleshoot report"},
      ]
    }
  ]
}

TICKET_BATCH_READ_SAMPLE: Dict[str, Any] = {
  "properties": ["subject", "hs_pipeline_stage", "hs_pipeline"],
  "inputs": [{"id": "4444888856"}, {"id": "666699988"}],
}

TICKET_BATCH_UPDATE_SAMPLE: Dict[str, Any] = {
  "inputs": [
    {"id": "4444888856", "properties": {"hs_pipeline_stage": "2"}},
    {"id": "666699988", "properties": {"subject": "Escalated troubleshoot report"}},
  ]
}

TICKET_ASSOCIATE_PATH = "/crm/v3/objects/tickets/4444888856/associations/contacts/123456789/16"

TICKET_PIN_UPDATE_ID = "4444888856"
TICKET_PIN_SAMPLE: Dict[str, Any] = {"properties": {"hs_pinned_engagement_id": 123456789}}

TICKET_DELETE_ID = "4444888856"
TICKET_BATCH_ARCHIVE_SAMPLE: Dict[str, Any] = {
  "inputs": [{"id": "4444888856"}, {"id": "666699988"}],
}

# Orders constants
ORDER_UPDATE_ID = "9001001"
ORDER_BATCH_ARCHIVE_SAMPLE: Dict[str, Any] = {"inputs": [{"id": "9001001"}, {"id": "9001002"}]}
ORDER_TEST_STRING_PROPERTY = "codex_order_reference"
ORDER_TEST_NUMBER_PROPERTY = "codex_order_total"
ORDER_TEST_GROUP_NAME = "codex_orders_info"

# Commerce payments sample payloads
PAYMENT_CREATE_SAMPLE: Dict[str, Any] = {
  "properties": {
    "hs_initial_amount": "109.99",
    "hs_initiated_date": "2024-03-27T18:04:11.823Z",
    "hs_customer_email": "orders@example.com",
  }
}

PAYMENT_UPDATE_ID = "383552769679"
PAYMENT_UPDATE_SAMPLE: Dict[str, Any] = {"properties": {"hs_latest_status": "succeeded"}}

PAYMENT_SEARCH_SAMPLE: Dict[str, Any] = {
  "filterGroups": [
    {
      "filters": [
        {"propertyName": "hs_latest_status", "operator": "EQ", "value": "refunded"},
      ]
    }
  ],
  "properties": ["hs_latest_status", "hs_customer_email"],
}

PAYMENT_DELETE_ID = "383552769679"


def _is_property_writable(prop: Dict[str, Any]) -> bool:
  if prop.get("archived") or prop.get("hidden"):
    return False
  if prop.get("calculated") or prop.get("displayMode") == "calculation":
    return False
  direct_read_only = prop.get("readOnlyValue") or prop.get("readOnlyDefinition")
  if direct_read_only:
    return False
  metadata = prop.get("modificationMetadata") or {}
  if metadata.get("readOnlyValue") or metadata.get("readOnlyDefinition"):
    return False
  if metadata.get("archivable") is False:
    # still writable but check readOnlyProperties
    pass
  return True


def _pick_order_property(properties: list[Dict[str, Any]], preferred_names: list[str], allowed_types: set[str]):
  property_index = {prop["name"]: prop for prop in properties}
  for name in preferred_names:
    prop = property_index.get(name)
    if prop and _is_property_writable(prop) and prop.get("type") in allowed_types:
      if prop.get("type") == "enumeration" and not prop.get("options"):
        continue
      return prop
  for prop in properties:
    if not _is_property_writable(prop):
      continue
    if allowed_types and prop.get("type") not in allowed_types:
      continue
    if prop.get("type") == "enumeration" and not prop.get("options"):
      continue
    return prop
  return None


def _resolve_order_property_selection(user_id: str) -> Dict[str, Dict[str, Any] | None]:
  response = hubspot_client.list_object_properties(user_id, "orders")
  properties = response.get("results", [])
  string_prop = _pick_order_property(
    properties,
    ["order_number", "order_id", "ordername", "name", "hs_name"],
    {"string"},
  )
  number_prop = _pick_order_property(properties, ["total_amount", "amount", "hs_total_amount"], {"number"})
  status_prop = _pick_order_property(properties, ["status", "hs_status", "hs_latest_status"], {"enumeration"})
  if not status_prop:
    status_prop = _pick_order_property(properties, ["status", "hs_status"], {"string"})

  if not any([string_prop, number_prop, status_prop]):
    fallback = _pick_order_property(properties, [], {"string", "enumeration", "number"})
    if fallback:
      if fallback.get("type") == "string":
        string_prop = fallback
      elif fallback.get("type") == "number":
        number_prop = fallback
      else:
        status_prop = fallback

  if not any([string_prop, number_prop, status_prop]):
    _ensure_order_test_properties(user_id)
    refreshed = hubspot_client.list_object_properties(user_id, "orders")
    properties = refreshed.get("results", [])
    string_prop = _pick_order_property(
      properties,
      [ORDER_TEST_STRING_PROPERTY, "order_number", "order_id", "ordername", "name", "hs_name"],
      {"string"},
    )
    number_prop = _pick_order_property(
      properties,
      [ORDER_TEST_NUMBER_PROPERTY, "total_amount", "amount", "hs_total_amount"],
      {"number"},
    )

  if not any([string_prop, number_prop, status_prop]):
    raise HTTPException(
      status_code=400,
      detail="Unable to locate or create writable Orders properties. Ensure your HubSpot app has crm.schemas.orders.write scope and try again.",
    )

  return {
    "string_prop": string_prop,
    "number_prop": number_prop,
    "status_prop": status_prop,
  }


def _sample_value_for_property(prop: Dict[str, Any], suffix: str) -> Any | None:
  prop_type = prop.get("type")
  if prop_type == "number":
    return 149.0
  if prop_type == "enumeration":
    options = [opt for opt in prop.get("options", []) if not opt.get("hidden")]
    if options:
      return options[0]["value"]
    return None
  if prop_type == "datetime":
    return datetime.now(timezone.utc).isoformat()
  return f"CODX-ORDER-{suffix}"


def _build_order_properties(selection: Dict[str, Dict[str, Any] | None], suffix: str | None = None) -> Dict[str, Any]:
  suffix = suffix or uuid.uuid4().hex[:8].upper()
  payload: Dict[str, Any] = {}
  for key in ("string_prop", "number_prop", "status_prop"):
    prop = selection.get(key)
    if not prop:
      continue
    name = prop["name"]
    if name in payload:
      continue
    value = _sample_value_for_property(prop, suffix)
    if value is not None:
      payload[name] = value
  if not payload:
    raise HTTPException(
      status_code=400,
      detail="Unable to build an Orders payload because no writable properties were available.",
    )
  return payload


def _ensure_order_test_properties(user_id: str) -> None:
  _ensure_order_property_group(user_id)
  desired_definitions = [
    {
      "name": ORDER_TEST_STRING_PROPERTY,
      "label": "Codex Order Reference",
      "type": "string",
      "fieldType": "text",
      "groupName": ORDER_TEST_GROUP_NAME,
      "description": "Temporary property created by Codex to run Orders API tests.",
    },
    {
      "name": ORDER_TEST_NUMBER_PROPERTY,
      "label": "Codex Order Total",
      "type": "number",
      "fieldType": "number",
      "groupName": ORDER_TEST_GROUP_NAME,
      "description": "Temporary property created by Codex to run Orders API tests.",
    },
  ]

  for definition in desired_definitions:
    try:
      hubspot_client.create_object_property(user_id, "orders", definition)
    except HTTPException as exc:
      detail = exc.detail
      status = getattr(exc, "status_code", None)
      if status == 409 or (isinstance(detail, dict) and detail.get("category") == "CONFLICT"):
        continue
      raise


def _ensure_order_property_group(user_id: str) -> None:
  group_definition = {
    "name": ORDER_TEST_GROUP_NAME,
    "label": "Codex Orders Info",
    "displayName": "Codex Orders Info",
    "displayOrder": 10,
    "description": "Property group created by Codex to support Orders test buttons.",
  }
  try:
    hubspot_client.create_property_group(user_id, "orders", group_definition)
  except HTTPException as exc:
    detail = exc.detail
    status = getattr(exc, "status_code", None)
    if status == 409 or (isinstance(detail, dict) and detail.get("category") == "CONFLICT"):
      return
    if isinstance(detail, dict) and detail.get("subCategory") == "PropertyGroupError.GROUP_ALREADY_EXISTS":
      return
    raise


class CmsBlogPostTestRequest(BaseModel):
  user_id: str | None = None

class ContactTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None


class CompanyTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None


class DealTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None


class TicketTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None


class OrderTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None


class PaymentTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None

class DisconnectRequest(BaseModel):
  user_id: str | None = None


class BlogAuthorsRequest(BaseModel):
  user_id: str | None = None


class TokenInfoRequest(BaseModel):
  user_id: str | None = None


@router.get("/connect")
def connect_hubspot(request: Request, user_id: str | None = None):
  resolved_user_id = resolve_user_id(request, user_id)
  state = sign_state(resolved_user_id)
  params = QueryParams(
    {
      "client_id": settings.hubspot_client_id,
      "redirect_uri": str(settings.hubspot_redirect_uri),
      "scope": settings.hubspot_scope,
      "response_type": "code",
      "prompt": "consent",
      "access_type": "offline",
      "state": state,
    }
  )
  optional_scope = settings.hubspot_optional_scope.strip()
  if optional_scope:
    params = params.merge({"optional_scope": optional_scope})
  url = f"{str(settings.hubspot_auth_base).rstrip('/')}/authorize?{params}"
  return RedirectResponse(url=url)


@router.get("/callback")
def hubspot_callback(code: str, state: str):
  user_id = verify_state(state)
  hubspot_exchange_code(user_id, code)
  return RedirectResponse(url=f"{str(settings.frontend_url).rstrip('/')}/home?connected=hubspot")


@router.get("/status")
def hubspot_status(request: Request, user_id: str | None = None):
  # Do not 401; allow query param fallback
  resolved_user_id = user_id or getattr(request.state, "user_id", None)
  if not resolved_user_id:
    return {"connected": False}
  try:
    record = get_hubspot_token(resolved_user_id)
  except HTTPException:
    return {"connected": False}
  if not record:
    return {"connected": False}
  return {"connected": True, "email": record.get("email") or record.get("user_email")}

@router.post("/disconnect")
def disconnect_hubspot(payload: DisconnectRequest, request: Request):
  user_id = resolve_user_id(request, payload.user_id)
  delete_tokens(user_id, "hubspot")
  try:
    hubspot_token_store.delete(user_id)
    hubspot_token_store.clear_cache(user_id)
  except Exception as exc:
    logger.warning("HubSpot token delete failed for %s: %s", user_id, exc)
  print("HubSpot tokens deleted for user:", user_id)
  return {"disconnected": True}


@router.post("/debug/token-info")
def hubspot_token_info(body: TokenInfoRequest):
  if os.getenv("DEV_DEBUG", "").lower() != "true":
    raise HTTPException(status_code=403, detail="forbidden")
  user_id = body.user_id
  if not user_id:
    raise HTTPException(status_code=400, detail="user_id required")
  row = hubspot_token_store.load_raw(user_id)
  if not row:
    raise HTTPException(status_code=404, detail="no token")
  metadata = row.get("metadata") or {}
  access_token = row.get("access_token") or metadata.get("access_token")
  token_preview = f"{access_token[:8]}..." if access_token else None
  return {
    "exists": True,
    "token_id": row.get("id"),
    "created_at": row.get("created_at"),
    "scopes": row.get("scope") or metadata.get("scope"),
    "token_preview": token_preview,
  }


@router.post("/cms/test-blog-post")
def cms_test_blog_post(body: CmsBlogPostTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  logger.info("CMS blog post test requested by %s", resolved_user_id)
  hubspot_response = hubspot_client.create_blog_post(resolved_user_id, CMS_BLOG_POST_SAMPLE)
  return {
    "status": "success",
    "hubspot_response": hubspot_response,
    "payload": CMS_BLOG_POST_SAMPLE,
  }


@router.post("/blog-authors")
def blog_authors(body: BlogAuthorsRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  logger.info("Blog authors requested by %s", resolved_user_id)
  return hubspot_client.list_blog_authors(resolved_user_id)


@router.post("/blogs")
def list_blogs(body: BlogAuthorsRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  logger.info("Blogs requested by %s", resolved_user_id)
  return hubspot_client.list_blogs(resolved_user_id)


# Contacts test endpoints
@router.post("/test/contacts/create")
def test_contacts_create(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.create_contact(resolved_user_id, CONTACT_CREATE_SAMPLE)


@router.post("/test/contacts/update")
def test_contacts_update(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_contact(resolved_user_id, CONTACT_UPDATE_ID, CONTACT_UPDATE_SAMPLE)


@router.post("/test/contacts/get")
def test_contacts_get(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  contact_id = (body.id or "").strip()
  if not contact_id:
    raise HTTPException(status_code=400, detail="id required")

  token_record = get_hubspot_token(resolved_user_id)
  token = token_record.get("access_token")
  if not token:
    raise HTTPException(status_code=401, detail="No HubSpot token")

  hubspot_url = f"{str(settings.hubspot_api_base).rstrip('/')}/crm/v3/objects/contacts/{contact_id}"
  print("GET HubSpot URL:", hubspot_url, "token_preview:", token[:8] if token else None, "user_id:", resolved_user_id)

  response = requests.get(hubspot_url, headers={"Authorization": f"Bearer {token}"})
  try:
    payload = response.json()
  except Exception:
    payload = response.text

  if response.status_code == 404:
    return JSONResponse(status_code=404, content={"detail": "Contact not found on HubSpot"})
  if response.status_code >= 400:
    return JSONResponse(status_code=response.status_code, content=payload)
  return payload


@router.post("/test/contacts/search")
def test_contacts_search(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.search_contacts(resolved_user_id, CONTACT_SEARCH_SAMPLE)


@router.post("/test/contacts/list")
def test_contacts_list(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.list_contacts(resolved_user_id, params={"limit": 5})


@router.post("/test/contacts/batch-read")
def test_contacts_batch_read(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_read_contacts(resolved_user_id, CONTACT_BATCH_READ_SAMPLE)


@router.post("/test/contacts/batch-create")
def test_contacts_batch_create(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_create_contacts(resolved_user_id, CONTACT_BATCH_CREATE_SAMPLE)


@router.post("/test/contacts/batch-update")
def test_contacts_batch_update(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_update_contacts(resolved_user_id, CONTACT_BATCH_UPDATE_SAMPLE)


@router.post("/test/contacts/batch-upsert")
def test_contacts_batch_upsert(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_upsert_contacts(resolved_user_id, CONTACT_BATCH_UPSERT_SAMPLE)


@router.post("/test/contacts/associate")
def test_contacts_associate(body: ContactTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.associate_contact(resolved_user_id, CONTACT_ASSOCIATE_PATH)


# Companies test endpoints
@router.post("/test/companies/create")
def test_companies_create(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.create_company(resolved_user_id, COMPANY_CREATE_SAMPLE)


@router.post("/test/companies/update")
def test_companies_update(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_company(resolved_user_id, COMPANY_UPDATE_ID, COMPANY_UPDATE_SAMPLE)


@router.post("/test/companies/get")
def test_companies_get(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  company_id = (body.id or "").strip()
  if not company_id:
    raise HTTPException(status_code=400, detail="id required")

  token_record = get_hubspot_token(resolved_user_id)
  token = token_record.get("access_token")
  if not token:
    raise HTTPException(status_code=401, detail="No HubSpot token")

  hubspot_url = f"{str(settings.hubspot_api_base).rstrip('/')}/crm/v3/objects/companies/{company_id}"
  print("GET HubSpot Company URL:", hubspot_url, "token_preview:", token[:8] if token else None, "user_id:", resolved_user_id)

  response = requests.get(hubspot_url, headers={"Authorization": f"Bearer {token}"})
  try:
    payload = response.json()
  except Exception:
    payload = response.text

  if response.status_code == 404:
    return JSONResponse(status_code=404, content={"detail": "Company not found on HubSpot"})
  if response.status_code >= 400:
    return JSONResponse(status_code=response.status_code, content=payload)
  return payload


@router.post("/test/companies/search")
def test_companies_search(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.search_companies(resolved_user_id, COMPANY_SEARCH_SAMPLE)


@router.post("/test/companies/list")
def test_companies_list(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.list_companies(resolved_user_id, params={"limit": 5})


@router.post("/test/companies/batch-read")
def test_companies_batch_read(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_read_companies(resolved_user_id, COMPANY_BATCH_READ_SAMPLE)


@router.post("/test/companies/batch-create")
def test_companies_batch_create(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_create_companies(resolved_user_id, COMPANY_BATCH_CREATE_SAMPLE)


@router.post("/test/companies/batch-update")
def test_companies_batch_update(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_update_companies(resolved_user_id, COMPANY_BATCH_UPDATE_SAMPLE)


@router.post("/test/companies/batch-upsert")
def test_companies_batch_upsert(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_upsert_companies(resolved_user_id, COMPANY_BATCH_UPSERT_SAMPLE)


@router.post("/test/companies/associate")
def test_companies_associate(body: CompanyTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.associate_company(resolved_user_id, COMPANY_ASSOCIATE_PATH)


# Deals test endpoints
@router.post("/test/deals/create")
def test_deals_create(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.create_deal(resolved_user_id, DEAL_CREATE_SAMPLE)


@router.post("/test/deals/update")
def test_deals_update(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_deal(resolved_user_id, DEAL_UPDATE_ID, DEAL_UPDATE_SAMPLE)


@router.post("/test/deals/get")
def test_deals_get(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  deal_id = (body.id or "").strip()
  if not deal_id:
    raise HTTPException(status_code=400, detail="id required")

  token_record = get_hubspot_token(resolved_user_id)
  token = token_record.get("access_token")
  if not token:
    raise HTTPException(status_code=401, detail="No HubSpot token")

  hubspot_url = f"{str(settings.hubspot_api_base).rstrip('/')}/crm/v3/objects/deals/{deal_id}"
  print("GET HubSpot Deal URL:", hubspot_url, "token_preview:", token[:8] if token else None, "user_id:", resolved_user_id)

  response = requests.get(hubspot_url, headers={"Authorization": f"Bearer {token}"})
  try:
    payload = response.json()
  except Exception:
    payload = response.text

  if response.status_code == 404:
    return JSONResponse(status_code=404, content={"detail": "Deal not found on HubSpot"})
  if response.status_code >= 400:
    return JSONResponse(status_code=response.status_code, content=payload)
  return payload


@router.post("/test/deals/search")
def test_deals_search(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.search_deals(resolved_user_id, DEAL_SEARCH_SAMPLE)


@router.post("/test/deals/list")
def test_deals_list(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.list_deals(resolved_user_id, params={"limit": 5})


@router.post("/test/deals/batch-read")
def test_deals_batch_read(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_read_deals(resolved_user_id, DEAL_BATCH_READ_SAMPLE)


@router.post("/test/deals/batch-create")
def test_deals_batch_create(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_create_deals(resolved_user_id, DEAL_BATCH_CREATE_SAMPLE)


@router.post("/test/deals/batch-update")
def test_deals_batch_update(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_update_deals(resolved_user_id, DEAL_BATCH_UPDATE_SAMPLE)


@router.post("/test/deals/associate")
def test_deals_associate(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.associate_deal(resolved_user_id, DEAL_ASSOCIATE_PATH)


@router.post("/test/deals/pin-activity")
def test_deals_pin_activity(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_deal(resolved_user_id, DEAL_PIN_UPDATE_ID, DEAL_PIN_SAMPLE)


@router.post("/test/deals/batch-archive")
def test_deals_batch_archive(body: DealTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_archive_deals(resolved_user_id, DEAL_BATCH_ARCHIVE_SAMPLE)


# Tickets test endpoints
@router.post("/test/tickets/create")
def test_tickets_create(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.create_ticket(resolved_user_id, TICKET_CREATE_SAMPLE)


@router.post("/test/tickets/update")
def test_tickets_update(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_ticket(resolved_user_id, TICKET_UPDATE_ID, TICKET_UPDATE_SAMPLE)


@router.post("/test/tickets/get")
def test_tickets_get(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  ticket_id = (body.id or "").strip()
  if not ticket_id:
    raise HTTPException(status_code=400, detail="id required")

  token_record = get_hubspot_token(resolved_user_id)
  token = token_record.get("access_token")
  if not token:
    raise HTTPException(status_code=401, detail="No HubSpot token")

  hubspot_url = f"{str(settings.hubspot_api_base).rstrip('/')}/crm/v3/objects/tickets/{ticket_id}"
  print("GET HubSpot Ticket URL:", hubspot_url, "token_preview:", token[:8] if token else None, "user_id:", resolved_user_id)

  response = requests.get(hubspot_url, headers={"Authorization": f"Bearer {token}"})
  try:
    payload = response.json()
  except Exception:
    payload = response.text

  if response.status_code == 404:
    return JSONResponse(status_code=404, content={"detail": "Ticket not found on HubSpot"})
  if response.status_code >= 400:
    return JSONResponse(status_code=response.status_code, content=payload)
  return payload


@router.post("/test/tickets/search")
def test_tickets_search(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.search_tickets(resolved_user_id, TICKET_SEARCH_SAMPLE)


@router.post("/test/tickets/list")
def test_tickets_list(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.list_tickets(resolved_user_id, params={"limit": 5})


@router.post("/test/tickets/batch-read")
def test_tickets_batch_read(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_read_tickets(resolved_user_id, TICKET_BATCH_READ_SAMPLE)


@router.post("/test/tickets/batch-update")
def test_tickets_batch_update(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_update_tickets(resolved_user_id, TICKET_BATCH_UPDATE_SAMPLE)


@router.post("/test/tickets/associate")
def test_tickets_associate(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.associate_ticket(resolved_user_id, TICKET_ASSOCIATE_PATH)


@router.post("/test/tickets/pin-activity")
def test_tickets_pin_activity(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_ticket(resolved_user_id, TICKET_PIN_UPDATE_ID, TICKET_PIN_SAMPLE)


@router.post("/test/tickets/delete")
def test_tickets_delete(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.delete_ticket(resolved_user_id, TICKET_DELETE_ID)


@router.post("/test/tickets/batch-archive")
def test_tickets_batch_archive(body: TicketTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_archive_tickets(resolved_user_id, TICKET_BATCH_ARCHIVE_SAMPLE)


# Orders test endpoints
@router.post("/test/orders/create")
def test_orders_create(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  selection = _resolve_order_property_selection(resolved_user_id)
  properties = _build_order_properties(selection)
  return hubspot_client.create_order(resolved_user_id, {"properties": properties})


@router.post("/test/orders/update")
def test_orders_update(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  selection = _resolve_order_property_selection(resolved_user_id)
  properties = _build_order_properties(selection, suffix="UPDATE")
  return hubspot_client.update_order(resolved_user_id, ORDER_UPDATE_ID, {"properties": properties})


@router.post("/test/orders/get")
def test_orders_get(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  order_id = (body.id or "").strip()
  if not order_id:
    raise HTTPException(status_code=400, detail="id required")
  return hubspot_client.get_order(resolved_user_id, order_id)


@router.post("/test/orders/search")
def test_orders_search(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  selection = _resolve_order_property_selection(resolved_user_id)
  filter_prop = selection.get("string_prop") or selection.get("status_prop") or selection.get("number_prop")
  if not filter_prop:
    raise HTTPException(status_code=400, detail="No searchable Orders properties are available.")
  filter_value = _sample_value_for_property(filter_prop, "SEARCH")
  if filter_value is None:
    filter_value = "CODX-ORDER-SEARCH"
  payload = {
    "filterGroups": [
      {
        "filters": [
          {
            "propertyName": filter_prop["name"],
            "operator": "EQ",
            "value": str(filter_value),
          }
        ]
      }
    ],
    "properties": list(
      {prop["name"] for prop in selection.values() if isinstance(prop, dict)},
    ),
  }
  return hubspot_client.search_orders(resolved_user_id, payload)


@router.post("/test/orders/list")
def test_orders_list(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.list_orders(resolved_user_id, params={"limit": 5})


@router.post("/test/orders/batch-read")
def test_orders_batch_read(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  selection = _resolve_order_property_selection(resolved_user_id)
  properties = [prop["name"] for prop in selection.values() if isinstance(prop, dict)]
  payload = {"properties": properties, "inputs": [{"id": "9001001"}, {"id": "9001002"}]}
  return hubspot_client.batch_read_orders(resolved_user_id, payload)


@router.post("/test/orders/batch-create")
def test_orders_batch_create(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  selection = _resolve_order_property_selection(resolved_user_id)
  inputs = []
  for index in range(2):
    suffix = f"BATCH-{index + 1}-{uuid.uuid4().hex[:6].upper()}"
    inputs.append({"properties": _build_order_properties(selection, suffix=suffix)})
  return hubspot_client.batch_create_orders(resolved_user_id, {"inputs": inputs})


@router.post("/test/orders/batch-update")
def test_orders_batch_update(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  selection = _resolve_order_property_selection(resolved_user_id)
  first_update = {"id": "9001001", "properties": _build_order_properties(selection, suffix="UP1")}
  second_update = {"id": "9001002", "properties": _build_order_properties(selection, suffix="UP2")}
  return hubspot_client.batch_update_orders(
    resolved_user_id,
    {"inputs": [first_update, second_update]},
  )


@router.post("/test/orders/batch-archive")
def test_orders_batch_archive(body: OrderTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.batch_archive_orders(resolved_user_id, ORDER_BATCH_ARCHIVE_SAMPLE)


# Commerce payments test endpoints
@router.post("/test/payments/create")
def test_payments_create(body: PaymentTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  payload = deepcopy(PAYMENT_CREATE_SAMPLE)
  payload["properties"]["hs_initiated_date"] = datetime.now(timezone.utc).isoformat()
  payload["properties"]["hs_customer_email"] = f"orders+{uuid.uuid4().hex[:6]}@example.com"
  return hubspot_client.create_payment(resolved_user_id, payload)


@router.post("/test/payments/update")
def test_payments_update(body: PaymentTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.update_payment(resolved_user_id, PAYMENT_UPDATE_ID, PAYMENT_UPDATE_SAMPLE)


@router.post("/test/payments/get")
def test_payments_get(body: PaymentTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  payment_id = (body.id or "").strip()
  if not payment_id:
    raise HTTPException(status_code=400, detail="id required")
  return hubspot_client.get_payment(resolved_user_id, payment_id)


@router.post("/test/payments/search")
def test_payments_search(body: PaymentTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.search_payments(resolved_user_id, PAYMENT_SEARCH_SAMPLE)


@router.post("/test/payments/list")
def test_payments_list(body: PaymentTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.list_payments(resolved_user_id, params={"limit": 5})


@router.post("/test/payments/delete")
def test_payments_delete(body: PaymentTestRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  return hubspot_client.delete_payment(resolved_user_id, PAYMENT_DELETE_ID)
