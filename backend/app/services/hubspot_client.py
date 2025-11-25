from __future__ import annotations

import logging
import re
import time
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

  def _search_contact(self, token: str, email: str) -> Optional[Dict[str, Any]]:
    if not email:
      return None
    body = {
      "filterGroups": [{"filters": [{"value": email, "propertyName": "email", "operator": "EQ"}]}],
      "limit": 1,
    }
    response = self._request("post", "/crm/v3/objects/contacts/search", token, json=body, allow_404=True)
    results = (response or {}).get("results") if response else None
    return results[0] if results else None

  def _upsert_contact(self, token: str, contact_plan) -> str:
    existing = self._search_contact(token, contact_plan.email) if contact_plan.email else None

    payload = {
      "properties": {
        "firstname": (contact_plan.full_name or "Unknown").split(" ")[0],
        "lastname": (contact_plan.full_name or "Unknown").split(" ")[-1],
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

    try:
      response = self._request("post", "/crm/v3/objects/contacts", token, json=payload)
      return response["id"]
    except HTTPException as exc:
      # Handle 409 conflicts by extracting existing ID or re-searching
      if exc.status_code == 409 and contact_plan.email:
        existing_id = self._extract_existing_id_from_error(exc.detail)
        if existing_id:
          return existing_id
        # fallback: search again
        found = self._search_contact(token, contact_plan.email)
        if found:
          return found["id"]
      raise

  @staticmethod
  def _extract_existing_id_from_error(detail: Any) -> Optional[str]:
    """
    Parse HubSpot conflict error messages like:
    "Contact already exists. Existing ID: 328941372098"
    """
    if not detail:
      return None
    if isinstance(detail, dict):
      message = detail.get("message", "")
    else:
      message = str(detail)
    match = re.search(r"Existing ID:\\s*(\\d+)", message)
    if match:
      return match.group(1)
    return None

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
    props = {
      # HubSpot notes commonly accept hs_note_body + hs_timestamp; omit hs_note_title (not present in your portal)
      "hs_note_body": note_plan.body or "(auto-generated note)",
      "hs_timestamp": int(time.time() * 1000),
    }

    def _send_note(properties: Dict[str, Any]) -> Dict[str, Any]:
      return self._request("post", "/crm/v3/objects/notes", token, json={"properties": properties})

    try:
      response = _send_note(props)
    except HTTPException as exc:
      detail = exc.detail if isinstance(exc.detail, dict) else {}
      missing = detail.get("context", {}).get("properties", []) if isinstance(detail, dict) else []
      if exc.status_code in (400, 422) and missing:
        # Patch missing required fields and retry once
        if "hs_timestamp" in missing:
          props["hs_timestamp"] = int(time.time() * 1000)
        if "hs_note_body" in missing:
          props["hs_note_body"] = props.get("hs_note_body") or "(auto-generated note)"
        response = _send_note(props)
      else:
        raise

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

  # Companies test helpers
  def create_company(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/companies", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def update_company(self, user_id: str, company_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("patch", f"/crm/v3/objects/companies/{company_id}", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def get_company(self, user_id: str, company_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", f"/crm/v3/objects/companies/{company_id}", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def search_companies(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/companies/search", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_companies(self, user_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/crm/v3/objects/companies", token, params=params or {"limit": 5})
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_read_companies(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/companies/batch/read", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_create_companies(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/companies/batch/create", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_update_companies(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/companies/batch/update", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_upsert_companies(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/companies/batch/upsert", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def associate_company(self, user_id: str, path: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("put", path, token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  # Deals test helpers
  def create_deal(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/deals", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def update_deal(self, user_id: str, deal_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("patch", f"/crm/v3/objects/deals/{deal_id}", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def get_deal(self, user_id: str, deal_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", f"/crm/v3/objects/deals/{deal_id}", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def search_deals(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/deals/search", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_deals(self, user_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/crm/v3/objects/deals", token, params=params or {"limit": 5})
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_read_deals(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/deals/batch/read", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_create_deals(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/deals/batch/create", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_update_deals(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/deals/batch/update", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def associate_deal(self, user_id: str, path: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("put", path, token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_archive_deals(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/deals/batch/archive", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  # Orders test helpers
  def create_order(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/orders", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def update_order(self, user_id: str, order_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("patch", f"/crm/v3/objects/orders/{order_id}", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def get_order(self, user_id: str, order_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", f"/crm/v3/objects/orders/{order_id}", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def search_orders(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/orders/search", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_orders(self, user_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/crm/v3/objects/orders", token, params=params or {"limit": 5})
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_read_orders(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/orders/batch/read", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_create_orders(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/orders/batch/create", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_update_orders(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/orders/batch/update", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_archive_orders(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/orders/batch/archive", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  # Commerce payments test helpers
  def create_payment(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/commerce_payments", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def update_payment(self, user_id: str, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("patch", f"/crm/v3/objects/commerce_payments/{payment_id}", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def get_payment(self, user_id: str, payment_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", f"/crm/v3/objects/commerce_payments/{payment_id}", token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def search_payments(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/commerce_payments/search", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_payments(self, user_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request(
      "get",
      "/crm/v3/objects/commerce_payments",
      token,
      params=params or {"limit": 5},
    )
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def delete_payment(self, user_id: str, payment_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("delete", f"/crm/v3/objects/commerce_payments/{payment_id}", token)
    return response or {"status": "deleted"}

  def list_object_properties(self, user_id: str, object_type: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", f"/crm/v3/properties/{object_type}", token)
    if response is None:
      raise HTTPException(status_code=502, detail=f"Empty response from HubSpot when loading {object_type} properties")
    return response

  def create_object_property(self, user_id: str, object_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", f"/crm/v3/properties/{object_type}", token, json=payload)
    if response is None:
      raise HTTPException(
        status_code=502,
        detail=f"HubSpot returned an empty response when creating {object_type} property.",
      )
    return response

  def execute_enhanced_plan(self, user_id: str, plan) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    result: Dict[str, Any] = {}

    if plan.contact:
      result["contact_id"] = self._upsert_contact(token, plan.contact)

    if plan.company:
      company_payload = {"properties": {"name": plan.company.name}}
      if plan.company.domain:
        company_payload["properties"]["domain"] = plan.company.domain
      created = self._request("post", "/crm/v3/objects/companies", token, json=company_payload)
      result["company_id"] = created.get("id")

    if getattr(plan, "deal", None):
      deal_payload = {
        "properties": {
          "dealname": plan.deal.dealname,
          "pipeline": plan.deal.pipeline,
          "dealstage": plan.deal.dealstage,
        }
      }
      if plan.deal.amount:
        deal_payload["properties"]["amount"] = plan.deal.amount
      if plan.deal.closedate:
        deal_payload["properties"]["closedate"] = plan.deal.closedate
      created = self._request("post", "/crm/v3/objects/deals", token, json=deal_payload)
      result["deal_id"] = created.get("id")

    if getattr(plan, "ticket", None):
      ticket_payload = {
        "properties": {
          "subject": plan.ticket.subject,
          "content": plan.ticket.content,
          "hs_ticket_priority": plan.ticket.priority,
          "hs_pipeline": plan.ticket.pipeline,
          "hs_pipeline_stage": plan.ticket.pipeline_stage,
        }
      }
      created = self._request("post", "/crm/v3/objects/tickets", token, json=ticket_payload)
      result["ticket_id"] = created.get("id")

    if getattr(plan, "order", None):
      order_payload = {"properties": {}}
      if plan.order.reference:
        order_payload["properties"]["order_number"] = plan.order.reference
      if plan.order.amount:
        order_payload["properties"]["amount"] = plan.order.amount
      if plan.order.status:
        order_payload["properties"]["status"] = plan.order.status
      created = self._request("post", "/crm/v3/objects/orders", token, json=order_payload)
      result["order_id"] = created.get("id")

    if getattr(plan, "note", None):
      # Create note and associate to any created objects (contact first, then others)
      note_id = self._create_note(token, result.get("contact_id"), plan.note)
      result["note_id"] = note_id
      assoc_targets = [
        ("companies", result.get("company_id"), "note_to_company"),
        ("deals", result.get("deal_id"), "note_to_deal"),
        ("tickets", result.get("ticket_id"), "note_to_ticket"),
        ("orders", result.get("order_id"), "note_to_order"),
      ]
      for obj_type, obj_id, assoc_label in assoc_targets:
        if not obj_id or not note_id:
          continue
        path = f"/crm/v3/objects/notes/{note_id}/associations/{obj_type}/{obj_id}/{assoc_label}"
        try:
          self._request("put", path, token)
        except Exception:
          continue

    return result

  def create_property_group(self, user_id: str, object_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", f"/crm/v3/properties/{object_type}/groups", token, json=payload)
    if response is None:
      raise HTTPException(
        status_code=502,
        detail=f"HubSpot returned an empty response when creating {object_type} property group.",
      )
    return response

  # Tickets test helpers
  def create_ticket(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/tickets", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def update_ticket(self, user_id: str, ticket_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("patch", f"/crm/v3/objects/tickets/{ticket_id}", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def search_tickets(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/tickets/search", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def list_tickets(self, user_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("get", "/crm/v3/objects/tickets", token, params=params or {"limit": 5})
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_read_tickets(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/tickets/batch/read", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def batch_update_tickets(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/tickets/batch/update", token, json=payload)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def associate_ticket(self, user_id: str, path: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("put", path, token)
    if response is None:
      raise HTTPException(status_code=502, detail="Empty response from HubSpot")
    return response

  def delete_ticket(self, user_id: str, ticket_id: str) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("delete", f"/crm/v3/objects/tickets/{ticket_id}", token)
    return response or {"status": "deleted"}

  def batch_archive_tickets(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    token = get_hubspot_token(user_id)["access_token"]
    response = self._request("post", "/crm/v3/objects/tickets/batch/archive", token, json=payload)
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
