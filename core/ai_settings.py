"""Read/write AI settings (.env + data/ai_settings.json)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import dotenv_values, set_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
SETTINGS_FILE = PROJECT_ROOT / "data" / "ai_settings.json"

DEFAULT_MODEL_CHAIN = "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-3-flash-preview,gemini-2.5-flash-lite"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def load_ai_settings() -> dict:
    env = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    extra = _read_json(SETTINGS_FILE, {})
    return {
        "api_key": (env.get("GEMINI_API_KEY") or "").strip(),
        "model_chain": (env.get("GEMINI_MODEL_CHAIN") or extra.get("model_chain") or DEFAULT_MODEL_CHAIN).strip(),
        "cache_ttl_seconds": int(env.get("GEMINI_CACHE_TTL_SECONDS") or extra.get("cache_ttl_seconds") or 3600),
        "topic_temperature": float(extra.get("topic_temperature", 0.75)),
        "script_temperature": float(extra.get("script_temperature", 0.7)),
        "research_temperature": float(extra.get("research_temperature", 0.3)),
        "scene_temperature": float(extra.get("scene_temperature", 0.1)),
    }


def save_ai_settings(settings: dict) -> None:
    ENV_FILE.touch(exist_ok=True)
    api_key = (settings.get("api_key") or "").strip()
    if api_key:
        set_key(str(ENV_FILE), "GEMINI_API_KEY", api_key)

    model_chain = (settings.get("model_chain") or DEFAULT_MODEL_CHAIN).strip()
    set_key(str(ENV_FILE), "GEMINI_MODEL_CHAIN", model_chain)

    cache_ttl = int(settings.get("cache_ttl_seconds") or 3600)
    set_key(str(ENV_FILE), "GEMINI_CACHE_TTL_SECONDS", str(cache_ttl))

    _write_json(SETTINGS_FILE, {
        "model_chain": model_chain,
        "cache_ttl_seconds": cache_ttl,
        "topic_temperature": float(settings.get("topic_temperature", 0.75)),
        "script_temperature": float(settings.get("script_temperature", 0.7)),
        "research_temperature": float(settings.get("research_temperature", 0.3)),
        "scene_temperature": float(settings.get("scene_temperature", 0.1)),
    })

    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GEMINI_MODEL_CHAIN"] = model_chain
    os.environ["GEMINI_CACHE_TTL_SECONDS"] = str(cache_ttl)


def mask_api_key(api_key: str) -> str:
    key = (api_key or "").strip()
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"
