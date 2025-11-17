from __future__ import annotations

import asyncio
from datetime import datetime

from ..services.supabase_client import get_supabase_client
from .polling_worker import poll_user


async def poll_all_users() -> None:
  supabase = get_supabase_client()
  resp = supabase.table("gmail_connections").select("user_id").execute()
  rows = resp.data if hasattr(resp, "data") else []
  user_ids = [row["user_id"] for row in rows if row.get("user_id")]
  for user_id in user_ids:
    await poll_user(user_id)


if __name__ == "__main__":
  asyncio.run(poll_all_users())
