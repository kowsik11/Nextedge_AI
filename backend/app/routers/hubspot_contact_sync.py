from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..services.hubspot_client import hubspot_client

router = APIRouter(prefix="/api/hubspot", tags=["hubspot"])


@router.post("/contact-sync")
def contact_sync(request: Request, email: str):
  user_id = getattr(request.state, "user_id", None)
  if not user_id:
    raise HTTPException(status_code=401, detail="Unauthorized")

  contact = hubspot_client.find_contact_by_email(user_id, email)
  if not contact:
    contact = hubspot_client.create_contact(user_id, email)
  return {"contact": contact}
