from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from .config import settings


class JwksCache:
  """Minimal in-memory JWKS cache with TTL."""

  def __init__(self, ttl_seconds: int = 600):
    self.ttl_seconds = ttl_seconds
    self._cached: Optional[Dict[str, Any]] = None
    self._expires_at: float = 0
    self._lock = asyncio.Lock()

  async def get(self) -> Dict[str, Any]:
    async with self._lock:
      if self._cached and time.time() < self._expires_at:
        return self._cached
      async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(str(settings.supabase_keys_endpoint))
      response.raise_for_status()
      self._cached = response.json()
      self._expires_at = time.time() + self.ttl_seconds
      return self._cached


jwks_cache = JwksCache()


async def decode_supabase_jwt(token: str) -> Dict[str, Any]:
  try:
    header = jwt.get_unverified_header(token)
  except JWTError as exc:
    raise HTTPException(status_code=401, detail="Invalid token header") from exc

  jwks = await jwks_cache.get()
  keys = jwks.get("keys") or []
  signing_key = next((key for key in keys if key.get("kid") == header.get("kid")), None)
  if not signing_key:
    raise HTTPException(status_code=401, detail="Signing key not found for token")

  try:
    # Supabase access tokens use HS256 by default; we disable audience verification to avoid client mismatch.
    return jwt.decode(token, signing_key, algorithms=[header.get("alg", "HS256")], options={"verify_aud": False})
  except JWTError as exc:
    raise HTTPException(status_code=401, detail="Token validation failed") from exc


async def attach_user_to_request(request: Request) -> None:
  auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
  if not auth_header or not auth_header.lower().startswith("bearer "):
    return
  token = auth_header.split()[1]
  claims = await decode_supabase_jwt(token)
  user_id = claims.get("sub") or claims.get("user_id") or claims.get("id")
  if not user_id:
    raise HTTPException(status_code=401, detail="Token missing subject")
  request.state.user_id = user_id
  request.state.user_claims = claims


def resolve_user_id(request: Request, explicit_user_id: Optional[str] = None) -> str:
  user_id = explicit_user_id or getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Missing authenticated user")
  return user_id
