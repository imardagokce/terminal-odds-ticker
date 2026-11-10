"""Persistent user configuration for the Odds Ticker."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def config_path() -> Path:
    """Return the platform-appropriate user configuration file path."""
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "terminal-odds-ticker" / "config.json"


def load_config() -> dict[str, Any]:
    """Load user configuration, returning an empty mapping when unavailable."""
    path = config_path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def save_api_key(api_key: str) -> None:
    """Save the supplied API key while retaining other configuration values."""
    config = load_config()
    config["api_key"] = api_key.strip()
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
