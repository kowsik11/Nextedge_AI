from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException

from ..config import settings
from .salesforce_oauth import get_salesforce_token, refresh_access_token

logger = logging.getLogger(__name__)


class SalesforceClient:
  """Minimal Salesforce REST client covering core CRM objects."""

  def _get_headers(self, access_token: str) -> Dict[str, str]:
    return {
      "Authorization": f"Bearer {access_token}",
      "Content-Type": "application/json",
      "Accept": "application/json",
    }

  def _build_url(self, instance_url: str, path: str) -> str:
    api_base = f"{instance_url.rstrip('/')}/services/data/{settings.salesforce_api_version}"
    return f"{api_base}{path}"

  def _request_with_refresh(
    self,
    user_id: str,
    method: str,
    url: str,
    *,
    token_data: Dict[str, Any],
    json: Optional[Dict[str, Any]] = None,
  ) -> Dict[str, Any]:
    """
    Perform a Salesforce request and refresh the token once on INVALID_SESSION_ID / 401.
    """
    def do_call(access_token: str) -> requests.Response:
      return requests.request(method, url, json=json, headers=self._get_headers(access_token), timeout=30)

    resp = do_call(token_data["access_token"])
    if resp.status_code == 401:
      # Attempt refresh once if we have a refresh_token
      try:
        err_json = resp.json()
      except Exception:
        err_json = {}
      messages = err_json if isinstance(err_json, list) else err_json.get("errors") or err_json
      text_repr = str(messages)
      if "INVALID_SESSION_ID" in text_repr and token_data.get("refresh_token"):
        try:
          refreshed = refresh_access_token(user_id, token_data["refresh_token"])
          token_data = {**token_data, **refreshed}
          resp = do_call(token_data["access_token"])
        except Exception as exc:  # pragma: no cover - refresh path
          logger.error("Salesforce token refresh failed: %s", exc)

    if resp.status_code >= 400:
      try:
        detail = resp.json()
      except Exception:
        detail = resp.text
      logger.error("Salesforce API error %s %s: %s", method, url, detail)
      raise HTTPException(status_code=resp.status_code, detail=detail)

    try:
      return resp.json()
    except Exception:
      return {}

  # ---- Contacts ----
  def create_contact(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Contact")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  def search_contact_by_email(self, user_id: str, email: str) -> Optional[Dict[str, Any]]:
    token_data = get_salesforce_token(user_id)
    soql = f"SELECT Id, FirstName, LastName, Email FROM Contact WHERE Email = '{email}' LIMIT 1"
    url = self._build_url(token_data["instance_url"], f"/query?q={soql}")
    data = self._request_with_refresh(user_id, "GET", url, token_data=token_data)
    if data.get("totalSize", 0) > 0:
      return data["records"][0]
    return None

  def update_contact(self, user_id: str, contact_id: str, properties: Dict[str, Any]) -> None:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], f"/sobjects/Contact/{contact_id}")
    self._request_with_refresh(user_id, "PATCH", url, token_data=token_data, json=properties)

  def upsert_contact(self, user_id: str, email: str, properties: Dict[str, Any]) -> str:
    existing = self.search_contact_by_email(user_id, email)
    if existing:
      self.update_contact(user_id, existing["Id"], properties)
      return existing["Id"]
    created = self.create_contact(user_id, properties)
    return created.get("id") or created.get("Id") or ""

  # ---- Accounts ----
  def create_account(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Account")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  def search_account_by_name(self, user_id: str, name: str) -> Optional[Dict[str, Any]]:
    token_data = get_salesforce_token(user_id)
    soql = f"SELECT Id, Name FROM Account WHERE Name = '{name}' LIMIT 1"
    url = self._build_url(token_data["instance_url"], f"/query?q={soql}")
    data = self._request_with_refresh(user_id, "GET", url, token_data=token_data)
    if data.get("totalSize", 0) > 0:
      return data["records"][0]
    return None

  def upsert_account(self, user_id: str, name: str, properties: Dict[str, Any]) -> str:
    existing = self.search_account_by_name(user_id, name)
    if existing:
      token_data = get_salesforce_token(user_id)
      url = self._build_url(token_data["instance_url"], f"/sobjects/Account/{existing['Id']}")
      self._request("PATCH", url, token=token_data["access_token"], json=properties)
      return existing["Id"]
    created = self.create_account(user_id, properties)
    return created.get("id") or created.get("Id") or ""

  # ---- Leads ----
  def create_lead(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Lead")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  # ---- Opportunity ----
  def create_opportunity(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Opportunity")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  # ---- Case ----
  def create_case(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Case")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  # ---- Campaign ----
  def create_campaign(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Campaign")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  # ---- Order ----
  def create_order(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Order")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)

  # ---- Task ----
  def create_task(self, user_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    token_data = get_salesforce_token(user_id)
    url = self._build_url(token_data["instance_url"], "/sobjects/Task")
    return self._request_with_refresh(user_id, "POST", url, token_data=token_data, json=properties)


salesforce_client = SalesforceClient()
