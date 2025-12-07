from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import (
    google_oauth, 
    gmail, 
    pipeline, 
    hubspot, 
    inbox, 
    oauth, 
    gmail_poll, 
    hubspot_contact_sync, 
    messages, 
    salesforce,
    google_sheets
)
from .auth import attach_user_to_request

app = FastAPI(title="NextEdge Backend", version="1.0.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=[str(settings.frontend_url), "http://localhost:5173", "http://localhost:3000"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(google_oauth.router)
app.include_router(gmail.router)
app.include_router(hubspot.router)
app.include_router(salesforce.router)
app.include_router(pipeline.router)
app.include_router(inbox.router)
app.include_router(oauth.router)
app.include_router(gmail_poll.router)
app.include_router(hubspot_contact_sync.router)
app.include_router(messages.router)
app.include_router(google_sheets.router)


@app.middleware("http")
async def supabase_auth_middleware(request: Request, call_next):  # type: ignore[override]
  try:
    await attach_user_to_request(request)
  except Exception as exc:  # do not block requests; allow explicit user_id to pass through
    request.state.auth_error = str(exc)
  return await call_next(request)


@app.get("/healthz")
def healthcheck():
  return {"status": "ok"}
