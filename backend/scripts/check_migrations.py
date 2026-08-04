"""CI sanity check for ordered, non-empty SQL migrations."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "migrations"
pattern = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")
files = sorted(ROOT.glob("*.sql"))
numbers: list[int] = []
for path in files:
    match = pattern.match(path.name)
    if not match:
        raise SystemExit(f"Migration filename is not ordered: {path.name}")
    numbers.append(int(match.group(1)))
    text = path.read_text(encoding="utf-8").strip()
    if not text or not re.search(r"\b(CREATE|ALTER|INSERT|UPDATE|DELETE|DROP)\b", text, re.IGNORECASE):
        raise SystemExit(f"Migration is empty or contains no SQL operation: {path.name}")

if len(numbers) != len(set(numbers)):
    raise SystemExit("Migration numbers must be unique")
if numbers and numbers != list(range(numbers[0], numbers[-1] + 1)):
    raise SystemExit(f"Migration numbers must be contiguous: {numbers}")

required_phase7_tables = {"itinerary_versions", "trip_edits", "share_links", "collaborators", "analytics_events", "audit_logs"}
phase7 = (ROOT / "005_phase7_collaboration_analytics.sql").read_text(encoding="utf-8")
missing = [table for table in required_phase7_tables if not re.search(rf"CREATE TABLE IF NOT EXISTS {table}\b", phase7)]
if missing:
    raise SystemExit(f"Phase 7 migration is missing tables: {', '.join(sorted(missing))}")

print(f"Validated {len(files)} ordered migrations")
