from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .gmail_ingest import GmailMessage
from .llm import gemini_client

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
  primary_object: str
  secondary_objects: List[str] = field(default_factory=list)
  confidence: float = 0.0
  reasoning: str = ""
  intent: str = "other"
  urgency: str = "medium"
  suggested_properties: Dict[str, Any] = field(default_factory=dict)
  create_note: bool = True
  target_crm: List[str] = field(default_factory=lambda: ["hubspot"])


class AIRouter:
  def __init__(self, *, confidence_threshold: float = 0.7):
    self.confidence_threshold = confidence_threshold

  def classify(self, email: GmailMessage) -> RoutingDecision:
    try:
      raw = gemini_client.classify_email_route(email)
      parsed = json.loads(raw)
      primary = str(parsed.get("primary_object") or "none").lower()
      secondary = [str(o).lower() for o in parsed.get("secondary_objects") or [] if o]
      target_crm = [str(c).lower() for c in parsed.get("target_crm") or ["hubspot"] if c]
      confidence = float(parsed.get("confidence") or 0.0)
      reasoning = parsed.get("reasoning") or ""
      intent = (parsed.get("intent") or "other").lower()
      urgency = (parsed.get("urgency") or "medium").lower()
      suggested_props = parsed.get("suggested_properties") or {}
      return RoutingDecision(
        primary_object=primary,
        secondary_objects=secondary,
        confidence=confidence,
        reasoning=reasoning,
        intent=intent,
        urgency=urgency,
        suggested_properties=suggested_props,
        create_note=True,
        target_crm=target_crm,
      )
    except Exception as exc:
      logger.warning("AI routing failed; defaulting to contact note", extra={"error": str(exc), "message_id": email.message_id})
      return RoutingDecision(primary_object="contacts", confidence=0.0, reasoning="fallback")


ai_router = AIRouter()
