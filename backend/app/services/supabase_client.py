from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from ..config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
  return create_client(str(settings.supabase_url), settings.supabase_service_role_key)


# Backwards compatibility for previous imports
def get_supabase() -> Client:
  return get_supabase_client()
