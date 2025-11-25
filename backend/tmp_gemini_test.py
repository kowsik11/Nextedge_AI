"""
Quick one-off Gemini connectivity check.
Reads GEMINI_API_KEYS, GEMINI_ENDPOINT, GEMINI_MODEL from environment/.env,
sends a minimal prompt, prints the first candidate text.
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


def main() -> int:
    # Load .env from repo root
    repo_root = Path(__file__).resolve().parents[1]
    env_paths = [repo_root / ".env", repo_root / "backend" / ".env"]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)

    keys = os.getenv("GEMINI_API_KEYS", "")
    endpoint = os.getenv("GEMINI_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/models")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    api_key = keys.split(",")[0].strip() if keys else ""
    if not api_key:
        print("No GEMINI_API_KEYS found", file=sys.stderr)
        return 1

    url = f"{endpoint.rstrip('/')}/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Say hello in one short sentence."}
                ]
            }
        ]
    }

    try:
        resp = requests.post(url, params={"key": api_key}, json=payload, timeout=15)
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - manual probe
        print(f"Request failed: {exc}", file=sys.stderr)
        if hasattr(exc, "response") and getattr(exc, "response", None) is not None:
            try:
                print(exc.response.text, file=sys.stderr)
            except Exception:
                pass
        return 1

    data = resp.json()
    candidates = data.get("candidates") or []
    text = ""
    if candidates:
        parts = candidates[0].get("content", {}).get("parts") or []
        if parts:
            text = parts[0].get("text", "")
    print("Gemini response:", text or json.dumps(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
