"""
Option C profile context: shared Gemini cache (full DNA+Style) + per-worker section focus.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from core.dna_sections import build_worker_section_text

try:
    from google.genai import types
except ImportError:
    types = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHARED_CACHE_INDEX_PATH = PROJECT_ROOT / "data" / "gemini_shared_cache_index.json"
GEMINI_CACHE_TTL_SECONDS = int(os.getenv("GEMINI_CACHE_TTL_SECONDS", "3600"))


def build_shared_cache_context(profile: dict) -> str:
    dna = (profile.get("dna_content") or "").strip()
    style = (profile.get("style_content") or "").strip()
    blocks: list[str] = []

    if dna:
        blocks.append(
            "--- CHANNEL DNA (FULL REFERENCE) ---\n"
            f"{dna}\n\n"
            "Use this as the complete strategic and visual identity for the channel."
        )
    if style:
        blocks.append(
            "--- CHANNEL STYLE GUIDE (FULL REFERENCE) ---\n"
            f"{style}\n\n"
            "Apply tone, voice, wording, and formatting rules from this guide."
        )

    if not blocks:
        return ""
    return "SHARED CHANNEL PROFILE CONTEXT\n\n" + "\n\n".join(blocks)


def build_worker_focus_block(worker_type: str, profile: dict) -> str:
    sections = build_worker_section_text(
        worker_type,
        profile.get("dna_content", ""),
        profile.get("style_content", ""),
    )
    focus = sections.get("focus_block", "").strip()
    if not focus:
        return ""
    return (
        f"WORKER FOCUS — {worker_type.upper()}\n"
        "Prioritize these rules for the current task. "
        "The full DNA and style guide are available in cached context.\n\n"
        f"{focus}"
    )


def channel_context_user_note() -> str:
    return (
        "\n\nCHANNEL CONTEXT NOTE:\n"
        "Full channel DNA and style guide are attached via cached content. "
        "Follow the WORKER FOCUS section above first; use cached context for anything else."
    )


def worker_channel_fields(worker_type: str, profile: dict) -> dict[str, str]:
    """Section-based dna/style fields for prompts when cache is unavailable."""
    sections = build_worker_section_text(
        worker_type,
        profile.get("dna_content", ""),
        profile.get("style_content", ""),
    )
    return {
        "dna_content": sections.get("dna_text", ""),
        "style_content": sections.get("style_text", ""),
        "worker_focus": build_worker_focus_block(worker_type, profile),
    }


def _cache_key(model_name: str, context: str) -> str:
    payload = f"{model_name}\n{context}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_cache_index() -> dict:
    if not SHARED_CACHE_INDEX_PATH.exists():
        return {}
    try:
        with open(SHARED_CACHE_INDEX_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache_index(index: dict) -> None:
    SHARED_CACHE_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SHARED_CACHE_INDEX_PATH, "w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=2)


def _is_cache_metadata_usable(cache) -> bool:
    expire_time = getattr(cache, "expire_time", None) or getattr(cache, "expireTime", None)
    if not expire_time:
        return True
    if isinstance(expire_time, str):
        try:
            expire_time = datetime.fromisoformat(expire_time.replace("Z", "+00:00"))
        except ValueError:
            return True
    if expire_time.tzinfo is None:
        expire_time = expire_time.replace(tzinfo=timezone.utc)
    return expire_time > datetime.now(timezone.utc)


def get_or_create_shared_cache(client, model_name: str, profile: dict, log_prefix: str = "SHARED_CACHE"):
    context = build_shared_cache_context(profile)
    if not context.strip() or types is None:
        return None

    key = _cache_key(model_name, context)
    index = _load_cache_index()
    cached = index.get(key)

    if cached and cached.get("name"):
        try:
            cache = client.caches.get(name=cached["name"])
            if _is_cache_metadata_usable(cache):
                client.caches.update(
                    name=cached["name"],
                    config=types.UpdateCachedContentConfig(ttl=f"{GEMINI_CACHE_TTL_SECONDS}s"),
                )
                print(f"✅ [{log_prefix}] Gemini shared cache HIT: {cached['name']}")
                return cached["name"]
        except Exception as error:
            print(f"⚠️ [{log_prefix}] Shared cache invalid, recreating: {error}")

    cache = client.caches.create(
        model=model_name,
        config=types.CreateCachedContentConfig(
            displayName=f"yt-creater-shared-{key[:12]}",
            contents=context,
            ttl=f"{GEMINI_CACHE_TTL_SECONDS}s",
        ),
    )
    cache_name = cache.name
    index[key] = {
        "name": cache_name,
        "model": model_name,
        "display_name": f"yt-creater-shared-{key[:12]}",
        "context_hash": key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_cache_index(index)
    print(f"✅ [{log_prefix}] Gemini shared cache CREATED: {cache_name}")
    return cache_name


def apply_cache_to_gen_config(gen_config_kwargs: dict, cached_content_name: str | None) -> dict:
    if cached_content_name:
        gen_config_kwargs["cached_content"] = cached_content_name
    return gen_config_kwargs
