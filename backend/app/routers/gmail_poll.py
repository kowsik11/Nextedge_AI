from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..background.polling_worker import poll_user

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.post("/poll")
async def poll(request: Request):
  user_id = getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")
  await poll_user(user_id)
  return {"status": "ok"}
