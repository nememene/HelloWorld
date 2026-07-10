from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def _expand_env(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        key = value[2:-1]
        return os.getenv(key, "")
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    load_dotenv()
    config_path = Path(path)
    if not config_path.exists():
        config_path = Path("config.example.yaml")
    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _expand_env(data)
