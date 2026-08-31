from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote, quote_plus


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
_CREDENTIAL_QUERY = re.compile(
    r"(?i)([?&](?:api[_-]?key|apikey|access[_-]?token|token|password|secret)=)"
    r"([^&#\s|,;\])}]+)"
)
_CREDENTIAL_HEADER = re.compile(
    r"(?i)\b(api[_-]?key|x-api-key|authorization)\s*:\s*"
    r"(?:bearer\s+)?([^\s,;]+)"
)
_URL_USERINFO = re.compile(r"(?i)(https?://)[^/@\s]+@")


def sanitize_audit_text(value: Any, *, secrets: tuple[str, ...] = ()) -> str:
    """Redact credentials before exception or provenance text is serialized."""
    text = str(value)
    for secret in secrets:
        if not secret:
            continue
        for candidate in {secret, quote(secret, safe=""), quote_plus(secret)}:
            if candidate:
                text = text.replace(candidate, "[REDACTED]")
    text = _CREDENTIAL_QUERY.sub(r"\1[REDACTED]", text)
    text = _CREDENTIAL_HEADER.sub(r"\1: [REDACTED]", text)
    return _URL_USERINFO.sub(r"\1[REDACTED]@", text)


def sanitize_audit_bytes(value: bytes, *, secrets: tuple[str, ...] = ()) -> bytes:
    """Sanitize textual audit bytes while leaving unrelated byte sequences exact."""
    sanitized = value
    for secret in secrets:
        if not secret:
            continue
        for candidate in {secret, quote(secret, safe=""), quote_plus(secret)}:
            if candidate:
                sanitized = sanitized.replace(
                    candidate.encode("utf-8"), b"[REDACTED]"
                )
    sanitized = re.sub(
        rb"(?i)([?&](?:api[_-]?key|apikey|access[_-]?token|token|password|secret)=)"
        rb"([^&#\s|,;\])}]+)",
        rb"\1[REDACTED]",
        sanitized,
    )
    sanitized = re.sub(
        rb"(?i)\b(api[_-]?key|x-api-key|authorization)\s*:\s*"
        rb"(?:bearer\s+)?([^\s,;]+)",
        rb"\1: [REDACTED]",
        sanitized,
    )
    return re.sub(
        rb"(?i)(https?://)[^/@\s]+@",
        rb"\1[REDACTED]@",
        sanitized,
    )


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_config_rows(
    section: str,
    path: str | Path | None = None,
) -> list[dict[str, str]]:
    """Load a configured row list, retaining explicit CSV compatibility."""
    if path is not None:
        explicit_path = Path(path)
        if explicit_path.suffix.lower() == ".csv":
            return _csv_rows(explicit_path)
        config_path = explicit_path
    else:
        config_path = DEFAULT_CONFIG_PATH

    document: Any = json.loads(config_path.read_text(encoding="utf-8"))
    value: Any = document
    try:
        for part in section.split("."):
            value = value[part]
    except (KeyError, TypeError) as error:
        raise KeyError(f"unknown config section: {section}") from error
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"config section is not a row list: {section}")
    return copy.deepcopy(value)
