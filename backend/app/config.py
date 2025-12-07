from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
  frontend_url: HttpUrl = Field(..., alias="FRONTEND_URL")

  google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
  google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
  google_redirect_uri: HttpUrl = Field(..., alias="GOOGLE_REDIRECT_URI")
  google_scopes_raw: str = Field("https://www.googleapis.com/auth/gmail.readonly", alias="GOOGLE_SCOPES")

  gemini_endpoint: HttpUrl = Field("https://generativelanguage.googleapis.com/v1beta/models", alias="GEMINI_ENDPOINT")
  gemini_model: str = Field("gemini-2.0-flash", alias="GEMINI_MODEL")
  gemini_api_keys_raw: str = Field(..., alias="GEMINI_API_KEYS")

  hubspot_client_id: str = Field(..., alias="HUBSPOT_CLIENT_ID")
  hubspot_client_secret: str = Field(..., alias="HUBSPOT_CLIENT_SECRET")
  hubspot_redirect_uri: HttpUrl = Field(..., alias="HUBSPOT_REDIRECT_URI")
  hubspot_scope: str = Field(..., alias="HUBSPOT_SCOPE")
  hubspot_optional_scope: str = Field("", alias="HUBSPOT_OPTIONAL_SCOPE")
  hubspot_auth_base: AnyHttpUrl = Field("https://app.hubspot.com/oauth", alias="HUBSPOT_AUTH_BASE")
  hubspot_api_base: AnyHttpUrl = Field("https://api.hubapi.com", alias="HUBSPOT_API_BASE")

  # Salesforce OAuth
  salesforce_client_id: str = Field("", alias="SALESFORCE_CLIENT_ID")
  salesforce_client_secret: str = Field("", alias="SALESFORCE_CLIENT_SECRET")
  salesforce_redirect_uri: AnyHttpUrl = Field(
    "http://localhost:8000/api/salesforce/callback", alias="SALESFORCE_REDIRECT_URI"
  )
  salesforce_auth_url: AnyHttpUrl = Field(
    "https://login.salesforce.com/services/oauth2/authorize", alias="SALESFORCE_AUTH_URL"
  )
  salesforce_token_url: AnyHttpUrl = Field(
    "https://login.salesforce.com/services/oauth2/token", alias="SALESFORCE_TOKEN_URL"
  )
  salesforce_api_version: str = Field("v61.0", alias="SALESFORCE_API_VERSION")
  salesforce_scopes: str = Field("api refresh_token web openid", alias="SALESFORCE_SCOPES")

  supabase_url: AnyHttpUrl = Field(..., alias="SUPABASE_URL")
  supabase_anon_key: str = Field(..., alias="SUPABASE_ANON_KEY")
  supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")
  supabase_jwks_url: AnyHttpUrl | None = Field(None, alias="SUPABASE_JWKS_URL")

  # Google Sheets
  google_sheets_client_id: str = Field(..., alias="GOOGLE_SHEETS_CLIENT_ID")
  google_sheets_client_secret: str = Field(..., alias="GOOGLE_SHEETS_CLIENT_SECRET")
  google_sheets_redirect_uri: AnyHttpUrl = Field(..., alias="GOOGLE_SHEETS_REDIRECT_URI")
  google_sheets_scopes: List[str] = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive.file",
      "https://www.googleapis.com/auth/gmail.readonly",
  ]

  model_config = SettingsConfigDict(env_file=ENV_PATH, env_file_encoding="utf-8", extra="ignore")

  @property
  def google_scopes(self) -> List[str]:
    return [scope.strip() for scope in self.google_scopes_raw.replace(",", " ").split() if scope.strip()]

  @property
  def gemini_api_keys(self) -> List[str]:
    return [key.strip() for key in self.gemini_api_keys_raw.replace(",", " ").split() if key.strip()]

  @property
  def salesforce_scope_list(self) -> List[str]:
    return [scope.strip() for scope in self.salesforce_scopes.replace(",", " ").split() if scope.strip()]

  @property
  def supabase_keys_endpoint(self) -> AnyHttpUrl:
    if self.supabase_jwks_url:
      return self.supabase_jwks_url
    return AnyHttpUrl(f"{str(self.supabase_url).rstrip('/')}/auth/v1/keys")  # type: ignore[arg-type]


settings = Settings()  # type: ignore[arg-type]
