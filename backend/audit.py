"""Privacy-conscious append-only agent activity log."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
_WRITE_LOCK = threading.Lock()
_SENSITIVE_KEY = re.compile(r"password|secret|token|api.?key|email|pin", re.IGNORECASE)
_EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_BEARER = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)


def _safe(value: Any, key: str = "") -> Any:
    """Keep previews short and redact common credential or personal-data fields."""
    if _SENSITIVE_KEY.search(key):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(k): _safe(v, str(k)) for k, v in list(value.items())[:12]}
    if isinstance(value, (list, tuple)):
        items = [_safe(item) for item in value[:6]]
        if len(value) > 6:
            items.append(f"… {len(value) - 6} more")
        return items
    if isinstance(value, str):
        value = _EMAIL.sub("[email]", value)
        value = _BEARER.sub("Bearer [redacted]", value)
        return value[:180] + ("…" if len(value) > 180 else "")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:180]


def append_event(
    *,
    run_id: str,
    event: str,
    tool_name: str | None,
    args: Any,
    result: Any,
    stop_reason: str | None,
) -> None:
    """Append one record while preserving all earlier records across runs.

    Writes a valid JSON array atomically. The array is loaded and extended, never
    reset; atomic replacement prevents readers from observing a partial file.
    """
    record = {
        "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "run_id": run_id,
        "event": event,
        "tool_name": tool_name,
        "args": _safe(args),
        "result": _safe(result),
        "stop_reason": stop_reason,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        records: list[dict[str, Any]] = []
        if AUDIT_PATH.exists():
            try:
                existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError("The agent audit trail could not be read safely.") from error
            if not isinstance(existing, list):
                raise RuntimeError("The agent audit trail must remain a JSON array.")
            records = existing
        records.append(record)

        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=AUDIT_PATH.parent,
                prefix="audit_trail.", suffix=".tmp", delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                json.dump(records, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, AUDIT_PATH)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
