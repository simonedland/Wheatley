"""Configuration loader helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

# Default config path relative to this file
# wheatley_V2/helper/config.py -> wheatley_V2/config/config.yaml
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"


def _require(cfg: Dict[str, Any], path: list[str]) -> Any:
    """Return nested config value or raise a clear error if missing."""
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            joined = "/".join(path)
            raise KeyError(f"Missing required config key: {joined}")
        cur = cur[key]
    return cur


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load config/config.yaml and require all referenced values."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a YAML mapping")

    # Validate essential keys
    _require(loaded, ["secrets", "openai_api_key"])
    _require(loaded, ["llm", "model"])

    return loaded
