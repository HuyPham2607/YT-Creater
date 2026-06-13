"""
Central profile persistence: profiles.json + active_profile.json sync.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_FILE = PROJECT_ROOT / "profiles.json"
ACTIVE_PROFILE_FILE = PROJECT_ROOT / "active_profile.json"


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
        json.dump(data, handle, ensure_ascii=False, indent=4)


def normalize_profile(profile: dict | None) -> dict:
    data = deepcopy(profile or {})
    topics = data.get("topics")
    if not isinstance(topics, list):
        data["topics"] = []
    return data


def load_profiles() -> list[dict]:
    raw = _read_json(DB_FILE, [])
    if not isinstance(raw, list):
        raw = []
    profiles = [normalize_profile(item) for item in raw if isinstance(item, dict)]
    _migrate_active_topics_into_library(profiles)
    return profiles


def save_profiles(profiles: list[dict]) -> None:
    normalized = [normalize_profile(item) for item in profiles]
    _write_json(DB_FILE, normalized)


def load_active_profile() -> dict | None:
    data = _read_json(ACTIVE_PROFILE_FILE, None)
    if not isinstance(data, dict):
        return None
    return normalize_profile(data)


def save_active_profile(profile: dict) -> None:
    _write_json(ACTIVE_PROFILE_FILE, normalize_profile(profile))


def find_profile_index_by_name(profiles: list[dict], name: str) -> int:
    target = (name or "").strip().lower()
    if not target:
        return -1
    for index, profile in enumerate(profiles):
        if (profile.get("name") or "").strip().lower() == target:
            return index
    return -1


def _migrate_active_topics_into_library(profiles: list[dict]) -> None:
    """One-time merge: active_profile topics -> matching library profile."""
    active = _read_json(ACTIVE_PROFILE_FILE, None)
    if not isinstance(active, dict):
        return
    active = normalize_profile(active)
    active_topics = active.get("topics") or []
    if not active_topics:
        return

    index = find_profile_index_by_name(profiles, active.get("name", ""))
    if index < 0:
        return

    library_topics = profiles[index].get("topics") or []
    if library_topics:
        return

    profiles[index]["topics"] = deepcopy(active_topics)
    save_profiles(profiles)


def sync_active_to_library(active: dict | None = None) -> bool:
    active = normalize_profile(active or load_active_profile())
    if not active or not active.get("name"):
        return False

    profiles = load_profiles()
    index = find_profile_index_by_name(profiles, active["name"])
    if index < 0:
        return False

    merged = normalize_profile(profiles[index])
    merged["topics"] = deepcopy(active.get("topics", []))
    profiles[index] = merged
    save_profiles(profiles)
    return True


def apply_profile_from_library(profile_data: dict) -> dict:
    applied = normalize_profile(profile_data)
    save_active_profile(applied)
    return applied


def apply_profile_by_index(profiles: list[dict], index: int) -> dict | None:
    if index < 0 or index >= len(profiles):
        return None
    return apply_profile_from_library(profiles[index])


def _normalize_topic_for_save(topic_data: dict) -> dict:
    topic = deepcopy(topic_data)
    if "topic_name" in topic and "title" not in topic:
        topic["title"] = topic.pop("topic_name")
    if "script" not in topic:
        topic["script"] = None
    return topic


def upsert_topic(profile: dict, topic_data: dict) -> tuple[dict, bool]:
    """Returns (profile, created_new)."""
    profile = normalize_profile(profile)
    topic = _normalize_topic_for_save(topic_data)
    title = (topic.get("title") or "").strip()
    if not title:
        raise ValueError("Topic title is empty.")

    for existing in profile["topics"]:
        if (existing.get("title") or "").strip() == title:
            existing.update(topic)
            return profile, False

    profile["topics"].append(topic)
    return profile, True


def upsert_topic_script(
    profile: dict,
    topic_title: str,
    script_payload: dict,
) -> dict:
    profile = normalize_profile(profile)
    topic_title = (topic_title or "").strip()
    if not topic_title:
        raise ValueError("Topic title is empty.")

    for topic in profile["topics"]:
        if (topic.get("title") or "").strip() == topic_title:
            topic["script"] = script_payload
            return profile

    profile["topics"].append({
        "title": topic_title,
        "script": script_payload,
    })
    return profile


def save_topic_to_active_profile(topic_data: dict) -> tuple[dict, bool]:
    active = load_active_profile()
    if not active:
        raise FileNotFoundError("active_profile.json")
    active, created = upsert_topic(active, topic_data)
    save_active_profile(active)
    sync_active_to_library(active)
    return active, created


def save_script_to_active_profile(topic_title: str, script_payload: dict) -> dict:
    active = load_active_profile()
    if not active:
        active = {"name": "Active Profile", "topics": []}
    active = upsert_topic_script(active, topic_title, script_payload)
    save_active_profile(active)
    sync_active_to_library(active)
    return active


def build_done_content(profile: dict, include_master_topic_list: bool = True) -> str:
    """Topics already saved/produced + optional master topic markdown."""
    profile = normalize_profile(profile)
    blocks: list[str] = []

    produced_lines: list[str] = []
    for topic in profile.get("topics", []):
        title = (topic.get("title") or "").strip()
        if not title:
            continue
        produced_lines.append(f"- TOPIC: {title}")
        for item in topic.get("titles", []) or []:
            if isinstance(item, dict):
                text = (item.get("text") or "").strip()
                if text:
                    produced_lines.append(f"  - TITLE: {text}")
        script = topic.get("script") or {}
        if isinstance(script, dict):
            script_title = (script.get("title") or "").strip()
            if script_title:
                produced_lines.append(f"  - PRODUCED SCRIPT TITLE: {script_title}")

    if produced_lines:
        blocks.append(
            "--- SAVED / PRODUCED TOPICS (DO NOT DUPLICATE) ---\n"
            + "\n".join(produced_lines)
        )

    master = (profile.get("topic_content") or "").strip()
    if include_master_topic_list and master:
        blocks.append(
            "--- MASTER TOPIC LIST (REFERENCE — avoid near-duplicates) ---\n"
            + master
        )

    return "\n\n".join(blocks)
