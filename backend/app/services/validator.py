from __future__ import annotations

import json
import logging
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError

from .gmail_ingest import GmailMessage
from .llm import gemini_client

logger = logging.getLogger(__name__)


class Person(BaseModel):
  name: str
  email: Optional[str] = None


class Company(BaseModel):
  name: str
  domain: Optional[str] = None


class ValidatedExtraction(BaseModel):
  message_id: str
  people: List[Person] = Field(default_factory=list)
  company: Optional[Company] = None
  intent: Optional[str] = None
  amount: Optional[str] = None
  dates: List[str] = Field(default_factory=list)
  next_steps: List[str] = Field(default_factory=list)
  summary: str
  evidence: str
  routing_decision: Optional[dict] = None


class ValidationService:
  def __init__(self, max_retries: int = 3):
    self.max_retries = max_retries

  def validate(self, email: GmailMessage, raw_json: str) -> ValidatedExtraction:
    attempt = 0
    error_message = None

    while attempt < self.max_retries:
      attempt += 1
      try:
        payload = json.loads(raw_json)
        extraction = ValidatedExtraction.model_validate({**payload, "message_id": email.message_id})
        logger.info("Validated extraction", extra={"message_id": email.message_id, "attempt": attempt})
        return extraction
      except (json.JSONDecodeError, ValidationError) as exc:
        error_message = str(exc)
        logger.warning(
          "Extraction validation failed",
          extra={"message_id": email.message_id, "attempt": attempt, "error": error_message},
        )
        raw_json = gemini_client.repair(email, error_message)

    raise RuntimeError(f"Unable to validate extraction after {self.max_retries} attempts: {error_message}")


validator_service = ValidationService()
