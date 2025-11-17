from __future__ import annotations

import json
import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from httpx import QueryParams
from pydantic import BaseModel

from ..config import settings
from ..services.hubspot_client import hubspot_client
from ..services.hubspot_oauth import get_hubspot_token, exchange_code as hubspot_exchange_code
from ..services.oauth_state import sign_state, verify_state
from ..services.token_service import delete_tokens
from ..tests_catalog import HUBSPOT_TESTS, HUBSPOT_TEST_MAP
from ..tests_samples import HUBSPOT_TEST_SAMPLES
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


class CmsBlogPostTestRequest(BaseModel):
  user_id: str | None = None

class DisconnectRequest(BaseModel):
  user_id: str | None = None


class BlogAuthorsRequest(BaseModel):
  user_id: str | None = None


class BlogPostScheduleRequest(BaseModel):
  user_id: str | None = None
  post_id: str
  publish_date: str


class HubSpotTestRunRequest(BaseModel):
  user_id: str | None = None
  key: str
  path_override: Optional[str] = None
  payload: Optional[str] = None
  payload_type: Optional[Literal["json", "form"]] = None
  query: Optional[Dict[str, Any]] = None
  headers: Optional[Dict[str, str]] = None


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


@router.post("/blogs/posts/schedule")
def schedule_blog_post(body: BlogPostScheduleRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  logger.info("Scheduling blog post %s for %s by %s", body.post_id, body.publish_date, resolved_user_id)
  return hubspot_client.schedule_blog_post(resolved_user_id, body.post_id, body.publish_date)


@router.get("/tests/catalog")
def tests_catalog():
  return {"results": HUBSPOT_TESTS}


@router.post("/tests/run")
def tests_run(body: HubSpotTestRunRequest, request: Request):
  resolved_user_id = resolve_user_id(request, body.user_id)
  entry = HUBSPOT_TEST_MAP.get(body.key)
  if not entry:
    raise HTTPException(status_code=404, detail="Test key not found.")

  sample = HUBSPOT_TEST_SAMPLES.get(body.key, {})
  path = body.path_override or sample.get("path") or entry["path"]

  payload_type = body.payload_type or sample.get("payload_type")
  json_payload: Optional[Dict[str, Any]] = None
  form_payload: Optional[str] = None
  if body.payload:
    payload_type = body.payload_type or payload_type or "json"
    if payload_type == "json":
      try:
        json_payload = json.loads(body.payload)
      except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc
    else:
      form_payload = body.payload
  elif sample.get("payload") is not None:
    payload_type = payload_type or ("json" if isinstance(sample["payload"], dict) else "form")
    if payload_type == "form":
      form_payload = sample["payload"]
    else:
      json_payload = sample["payload"]

  query: Dict[str, Any] = {}
  if isinstance(sample.get("query"), dict):
    query.update(sample["query"])
  if body.query:
    query.update(body.query)

  headers: Dict[str, str] = {}
  if isinstance(sample.get("headers"), dict):
    headers.update(sample["headers"])
  if body.headers:
    headers.update(body.headers)
  if payload_type == "form":
    headers = {"Content-Type": "application/x-www-form-urlencoded", **headers}

  result = hubspot_client.execute_raw(
    resolved_user_id,
    entry["method"],
    path,
    params=query or None,
    json=json_payload,
    data=form_payload,
    headers=headers,
  )

  return {"test": entry, "result": result}
