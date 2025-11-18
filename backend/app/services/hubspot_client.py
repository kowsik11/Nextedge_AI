from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from ..config import settings
from .planner import CrmUpsertPlan
from .hubspot_oauth import get_hubspot_token, build_auth_url

logger = logging.getLogger(__name__)


class HubSpotClient:
  def __init__(self):
    pass

  def execute_plan(self, user_id: str, plan: CrmUpsertPlan) -> Dict[str, Any]:
    access_token = get_hubspot_token(user_id)["access_token"]
    contact_id = None
    company_id = None

    if plan.contact:
      contact_id = self._upsert_contact(access_token, plan.contact)
    if plan.company:
      company_id = self._upsert_company(access_token, plan.company)
    if contact_id and company_id:
      self._associate_contact_company(access_token, contact_id, company_id)

    note_id = None
    if contact_id:
      note_id = self._create_note(access_token, contact_id, plan.note)

    return {"contact_id": contact_id, "company_id": company_id, "note_id": note_id}

  def _headers(self, token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

  def _upsert_contact(self, token: str, contact_plan) -> str:
    existing = None
    if contact_plan.email:
      existing = self._search_contact(token, contact_plan.email)

    payload = {
      "properties": {
        "firstname": contact_plan.full_name.split(" ")[0],
        "lastname": contact_plan.full_name.split(" ")[-1],
      }
    }
    if contact_plan.email:
      payload["properties"]["email"] = contact_plan.email

    if existing:
      contact_id = existing["id"]
      self._request(
        "patch",
        f"/crm/v3/objects/contacts/{contact_id}",
        token,
        json=payload,
      )
      return contact_id

    response = self._request("post", "/crm/v3/objects/contacts", token, json=payload)
    return response["id"]

  def _search_contact(self, token: str, email: str) -> Optional[Dict[str, Any]]:
    body = {
      "filterGroups": [{"filters": [{"value": email, "propertyName": "email", "operator": "EQ"}]}],
      "limit": 1,
    }
    response = self._request("post", "/crm/v3/objects/contacts/search", token, json=body, allow_404=True)
    results = (response or {}).get("results") if response else None
    return results[0] if results else None

  def _upsert_company(self, token: str, company_plan) -> str:
    existing = None
    if company_plan.domain:
      existing = self._search_company(token, "domain", company_plan.domain)
    if not existing:
      existing = self._search_company(token, "name", company_plan.name)

    payload = {"properties": {"name": company_plan.name}}
    if company_plan.domain:
      payload["properties"]["domain"] = company_plan.domain

    if existing:
      company_id = existing["id"]
      self._request("patch", f"/crm/v3/objects/companies/{company_id}", token, json=payload)
      return company_id

    response = self._request("post", "/crm/v3/objects/companies", token, json=payload)
    return response["id"]

  def _search_company(self, token: str, property_name: str, value: str) -> Optional[Dict[str, Any]]:
    body = {
      "filterGroups": [{"filters": [{"value": value, "propertyName": property_name, "operator": "EQ"}]}],
      "limit": 1,
    }
    response = self._request("post", "/crm/v3/objects/companies/search", token, json=body, allow_404=True)
    results = (response or {}).get("results") if response else None
    return results[0] if results else None

  def _associate_contact_company(self, token: str, contact_id: str, company_id: str) -> None:
    path = f"/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company"
    self._request("put", path, token)

  def _create_note(self, token: str, contact_id: str, note_plan) -> str:
    payload = {
      "properties": {
        "hs_note_title": note_plan.title,
        "hs_note_body": note_plan.body,
        "hs_timestamp": datetime.now(timezone.utc).isoformat(),
      }
    }
    response = self._request("post", "/crm/v3/objects/notes", token, json=payload)
    note_id = response["id"]
    assoc_path = f"/crm/v3/objects/notes/{note_id}/associations/contacts/{contact_id}/note_to_contact"
    self._request("put", assoc_path, token)
    return note_id

  def create_blog_post(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/cms/v3/blogs/posts", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_blogs(self, user_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/content/api/v2/blogs", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    objects = response.get("objects") if isinstance(response, dict) else None
    blogs = []
    if isinstance(objects, list):
      for blog in objects:
        if not isinstance(blog, dict):
          continue
        blogs.append(
          {
            "id": str(blog.get("id")),
            "name": blog.get("name"),
            "slug": blog.get("slug"),
          }
        )
    return {"results": blogs, "total": len(blogs)}

  def list_blog_authors(self, user_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/cms/v3/blogs/authors", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  # Contacts test helpers
  def create_contact(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/contacts", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def update_contact(self, user_id: str, contact_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("patch", f"/crm/v3/objects/contacts/{contact_id}", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def get_contact(self, user_id: str, contact_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", f"/crm/v3/objects/contacts/{contact_id}", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def search_contacts(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/contacts/search", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_contacts(self, user_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/crm/v3/objects/contacts", token, params=params or {"limit": 5})
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_read_contacts(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/contacts/batch/read", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_create_contacts(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/contacts/batch/create", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_update_contacts(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/contacts/batch/update", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_upsert_contacts(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/contacts/batch/upsert", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def associate_contact(self, user_id: str, path: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("put", path, token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def _request(
    self,
    method: str,
    path: str,
    token: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    allow_404: bool = False,
  ) -> Optional[Dict[str, Any]]:
    base_url = str(settings.hubspot_api_base).rstrip("/")
    url = path if path.startswith("http") else f"{base_url}{path}"
    try:
      req_headers = self._headers(token)
      with httpx.Client(timeout=20) as client:
        response = client.request(method.upper(), url, headers=req_headers, params=params, json=json)
    except httpx.HTTPError as exc:
      raise HTTPException(status_code=500, detail=f"HubSpot request failed: {exc}") from exc

    if allow_404 and response.status_code == 404:
      return None
    if response.status_code >= 400:
      missing_scopes = None
      try:
        payload = response.json()
        category = payload.get("category")
        if response.status_code == 403 and category == "MISSING_SCOPES":
          missing_scopes = payload
      except Exception:
        payload = response.text
      if missing_scopes:
        authorize_url = build_auth_url("reauthorize")
        detail = {
          "message": "HubSpot is missing required scopes. Reconnect with updated scopes to continue.",
          "authorize_url": authorize_url,
          "hubspot_error": missing_scopes,
        }
        raise HTTPException(status_code=403, detail=detail)
      raise HTTPException(status_code=response.status_code, detail=payload)
    if response.content:
      return response.json()
    return None


hubspot_client = HubSpotClient()
