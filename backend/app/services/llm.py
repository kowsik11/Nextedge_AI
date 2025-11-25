from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from ..config import settings
from .gmail_ingest import GmailMessage

logger = logging.getLogger(__name__)


class GeminiClient:
  def __init__(self):
    self.api_keys = settings.gemini_api_keys
    if not self.api_keys:
      raise RuntimeError("GEMINI_API_KEYS is not configured.")
    self.endpoint = str(settings.gemini_endpoint).rstrip("/")
    self.model = settings.gemini_model

  def _compose_url(self) -> str:
    if self.endpoint.endswith(self.model):
      return self.endpoint
    return f"{self.endpoint}/{self.model}:generateContent"

  def analyze_email(self, email: GmailMessage) -> str:
    prompt = self._build_prompt(email)
    return self._invoke(prompt, email.message_id, "analysis")

  def classify_email_route(self, email: GmailMessage) -> str:
    prompt = self._build_routing_prompt(email)
    return self._invoke(prompt, email.message_id, "routing")

  def repair(self, email: GmailMessage, error_message: str) -> str:
    prompt = (
      "Your previous JSON response was invalid.\n"
      f"Reason: {error_message}\n"
      "Return only corrected JSON matching the required schema.\n"
      f"Email context:\n{email.consolidated_text}"
    )
    return self._invoke(prompt, email.message_id, "repair")

  def _invoke(self, prompt: str, message_id: str, purpose: str) -> str:
    url = self._compose_url()
    payload = {
      "contents": [{"role": "user", "parts": [{"text": prompt}]}],
      "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }

    for idx, api_key in enumerate(self.api_keys, start=1):
      start = time.perf_counter()
      try:
        with httpx.Client(timeout=30) as client:
          response = client.post(url, params={"key": api_key}, json=payload)
      except httpx.HTTPError as exc:
        logger.warning(
          "Gemini request failed",
          extra={"message_id": message_id, "purpose": purpose, "attempt": idx, "error": str(exc)},
        )
        continue

      latency = round((time.perf_counter() - start) * 1000, 2)
      if response.status_code == 200:
        data = response.json()
        try:
          return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
          logger.warning(
            "Gemini returned unexpected payload",
            extra={"message_id": message_id, "purpose": purpose, "error": str(exc)},
          )
          continue

      if response.status_code in {401, 403, 429, 500, 502, 503, 504}:
        logger.warning(
          "Gemini call failed, rotating key",
          extra={"message_id": message_id, "purpose": purpose, "status": response.status_code, "attempt": idx},
        )
        continue

      raise RuntimeError(f"Gemini error ({response.status_code}): {response.text}")

    raise RuntimeError("All Gemini API keys exhausted.")

  def _build_prompt(self, email: GmailMessage) -> str:
    metadata = [
      f"Subject: {email.subject or 'N/A'}",
      f"From: {email.sender or 'N/A'}",
      f"To: {', '.join(email.recipients) or 'N/A'}",
      f"Sent at: {email.sent_at.isoformat() if email.sent_at else 'N/A'}",
    ]
    instructions = """
Extract structured CRM data from the email body and attachments.
Return JSON with keys:
- people: array of { "name": string, "email": string }
- company: { "name": string, "domain": string }
- intent: string
- amount: string
- dates: array of strings
- next_steps: array of strings
- summary: string
- evidence: string (quote or reference)
If a field is unknown, use an empty string or empty array.
"""
    return "\n".join(filter(None, [*metadata, "", instructions, "", email.consolidated_text]))

  def _build_routing_prompt(self, email: GmailMessage) -> str:
    metadata = [
      f"Subject: {email.subject or 'N/A'}",
      f"From: {email.sender or 'N/A'}",
      f"To: {', '.join(email.recipients) or 'N/A'}",
      f"Sent at: {email.sent_at.isoformat() if email.sent_at else 'N/A'}",
    ]
    instructions = """
Classify this email for CRM routing. Support both HubSpot and Salesforce terminology. Return JSON only:
{
  "target_crm": ["hubspot", "salesforce"],  // one or both - which CRM(s) should receive this
  "primary_object": "contacts|leads|accounts|opportunities|cases|companies|deals|tickets|campaigns|orders|notes|none",
  "secondary_objects": ["contacts", "leads", "accounts", ...],
  "confidence": float (0-1),
  "reasoning": "one-sentence explanation of why this classification",
  "intent": "sales|support|billing|spam|personal|other",
  "urgency": "high|medium|low",
  "suggested_properties": {
    "deal": {"dealname": "...", "amount": "5000"},
    "opportunity": {"name": "...", "amount": "10000"},
    "ticket": {"subject": "...", "content": "..."},
    "case": {"subject": "...", "priority": "High"},
    "lead": {"company": "...", "status": "Open"},
    "campaign": {"name": "...", "type": "Email"}
  }
}

CRITICAL OBJECT SELECTION RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HubSpot Terminology:
  - contacts: Individual people (networking, general communication)
  - companies: Organizations/businesses
  - deals: Active sales opportunities with monetary value
  - tickets: Customer support issues, technical problems
  - orders: Purchase orders, transactions

Salesforce Terminology:
  - contacts: Individual people already in the system
  - leads: NEW prospects not yet qualified (use when email mentions "lead" or is from unknown sender inquiring about products)
  - accounts: Organizations/businesses (same as companies)
  - opportunities: Sales deals with specific value (same as deals)
  - cases: Support tickets, customer issues (same as tickets)
  - campaigns: Marketing initiatives, email blasts, events

CLASSIFICATION LOGIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Email mentions "Lead object", "Salesforce Lead", "Lead API" → primary_object: "leads"
2. New prospect asking about products/services → primary_object: "leads"
3. Quote request with specific amount → primary_object: "opportunities" or "deals"
4. Support request, bug report, technical issue → primary_object: "cases" or "tickets"
5. Marketing announcement, newsletter → primary_object: "campaigns"
6. Known contact follow-up → primary_object: "contacts"
7. Company-level discussion → primary_object: "accounts" or "companies"
8. Purchase order → primary_object: "orders"
9. Spam or irrelevant → primary_object: "none"

TARGET_CRM SELECTION:
  - If email mentions "Salesforce", "SFDC", or Salesforce-specific terms → include "salesforce" in target_crm
  - If email mentions "HubSpot" → include "hubspot" in target_crm
  - For general business emails → both ["hubspot", "salesforce"]
  - For spam/personal → []

EXAMPLES:
  ✓ "Lead Object Access Needed for Integration" → primary_object: "leads", target_crm: ["salesforce"]
  ✓ "Interested in purchasing your software" → primary_object: "leads", target_crm: ["hubspot", "salesforce"]
  ✓ "Quote for 100 licenses - $50,000" → primary_object: "opportunities", target_crm: ["hubspot", "salesforce"]
  ✓ "Cannot log into my account" → primary_object: "cases", target_crm: ["hubspot", "salesforce"]
  ✓ "Monthly newsletter - Product updates" → primary_object: "campaigns", target_crm: ["salesforce"]
  
NEVER return "none" unless the email is spam or completely irrelevant to business.
"""
    return "\n".join(filter(None, [*metadata, "", instructions, "", email.consolidated_text]))


gemini_client = GeminiClient()
