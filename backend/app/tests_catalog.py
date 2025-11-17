from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

DOC_PATH = Path(__file__).resolve().parents[2] / "hubspot_olddocs_api.md"

_ENDPOINT_PATTERN = re.compile(r"`([^`]+)`")


def _slugify(*parts: str) -> str:
  base = "-".join(part for part in parts if part)
  slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
  return slug or "endpoint"


def _extract_method_path(segment: str) -> Tuple[str, str]:
  match = _ENDPOINT_PATTERN.search(segment)
  if not match:
    return "GET", segment.strip()

  content = match.group(1).strip()
  if not content:
    return "GET", segment.strip()

  pieces = content.split(None, 1)
  if len(pieces) == 2 and pieces[0].isalpha() and pieces[0].upper() == pieces[0]:
    return pieces[0].upper(), pieces[1].strip()
  return "GET", content


def _parse_doc() -> List[Dict[str, str]]:
  if not DOC_PATH.exists():
    return []

  entries: List[Dict[str, str]] = []
  used_keys: Dict[str, int] = {}
  current_section: str | None = None
  current_subsection: str | None = None
  collecting_multi = False

  with DOC_PATH.open("r", encoding="utf-8") as handle:
    lines = handle.readlines()

  for raw_line in lines:
    line = raw_line.rstrip("\n")
    stripped = line.strip()

    if stripped.startswith("## "):
      current_section = stripped[3:].strip()
      collecting_multi = False
      continue

    if stripped.startswith("### "):
      current_subsection = stripped[4:].strip()
      collecting_multi = False
      continue

    if stripped.startswith("- **Endpoints**"):
      collecting_multi = True
      continue

    if collecting_multi:
      if stripped.startswith("- `") or stripped.startswith("`") or stripped.startswith("- **Endpoint**"):
        method, path = _extract_method_path(stripped)
        title = current_subsection or current_section or path
        key_base = _slugify(title, method, path)
        count = used_keys.get(key_base, 0)
        used_keys[key_base] = count + 1
        key = key_base if count == 0 else f"{key_base}-{count+1}"
        entries.append(
          {
            "key": key,
            "method": method,
            "path": path,
            "section": current_section or "General",
            "title": current_subsection or current_section or path,
          }
        )
        continue

      if stripped.startswith("- "):
        # bullet without endpoint; skip
        continue

      if stripped == "":
        continue

      collecting_multi = False

    if stripped.startswith("- **Endpoint**"):
      method, path = _extract_method_path(stripped)
      title = current_subsection or current_section or path
      key_base = _slugify(title, method, path)
      count = used_keys.get(key_base, 0)
      used_keys[key_base] = count + 1
      key = key_base if count == 0 else f"{key_base}-{count+1}"
      entries.append(
        {
          "key": key,
          "method": method,
          "path": path,
          "section": current_section or "General",
          "title": current_subsection or current_section or path,
        }
      )

  return entries


HUBSPOT_TESTS: List[Dict[str, str]] = _parse_doc()
HUBSPOT_TEST_MAP: Dict[str, Dict[str, str]] = {entry["key"]: entry for entry in HUBSPOT_TESTS}
