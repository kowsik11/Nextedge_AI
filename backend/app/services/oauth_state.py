from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Tuple

from fastapi import HTTPException

from ..config import settings


STATE_TTL_SECONDS = 600
SECRET_KEY = settings.hubspot_client_secret  # reuse an existing secret; in production, use a dedicated secret


def sign_state(user_id: str) -> str:
  timestamp = str(int(time.time()))
  payload = f"{user_id}:{timestamp}"
  signature = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
  token = f"{payload}:{signature}"
  return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")


def verify_state(state: str) -> str:
  try:
    decoded = base64.urlsafe_b64decode(state.encode("utf-8")).decode("utf-8")
    user_id, timestamp, signature = decoded.split(":")
  except Exception as exc:
    raise HTTPException(status_code=400, detail="Invalid state") from exc

  payload = f"{user_id}:{timestamp}"
  expected = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
  if not hmac.compare_digest(signature, expected):
    raise HTTPException(status_code=400, detail="Invalid state signature")
  if time.time() - int(timestamp) > STATE_TTL_SECONDS:
    raise HTTPException(status_code=400, detail="State expired")
  return user_id
