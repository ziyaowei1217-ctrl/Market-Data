from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")


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
