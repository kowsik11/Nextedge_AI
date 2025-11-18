from __future__ import annotations

import logging
from typing import Any, Dict

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from httpx import QueryParams
from pydantic import BaseModel

from ..config import settings
from ..services.hubspot_client import hubspot_client
from ..services.hubspot_oauth import get_hubspot_token, exchange_code as hubspot_exchange_code
from ..services.oauth_state import sign_state, verify_state
from ..services.token_service import delete_tokens
from ..auth import resolve_user_id

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


class CmsBlogPostTestRequest(BaseModel):
  user_id: str | None = None

class ContactTestRequest(BaseModel):
  user_id: str | None = None
  id: str | None = None

class DisconnectRequest(BaseModel):
  user_id: str | None = None


class BlogAuthorsRequest(BaseModel):
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
  return {"disconnected": True}


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
  if not body.id or not body.id.strip():
    raise HTTPException(status_code=400, detail="missing id")
  token_record = get_hubspot_token(resolved_user_id)
  token = token_record["access_token"]
  hubspot_url = f"{str(settings.hubspot_api_base).rstrip('/')}/crm/v3/objects/contacts/{body.id}"
  print("GET HubSpot URL:", hubspot_url, "token_first8:", token[:8])
  response = requests.get(hubspot_url, headers={"Authorization": f"Bearer {token}"})
  if response.status_code == 200:
    return response.json()
  if response.status_code == 404:
    raise HTTPException(status_code=404, detail="Contact not found on HubSpot")
  try:
    payload = response.json()
  except Exception:
    payload = response.text
  if response.status_code == 403:
    raise HTTPException(status_code=403, detail=payload)
  raise HTTPException(status_code=response.status_code, detail=payload)


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
