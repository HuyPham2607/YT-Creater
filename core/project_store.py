"""Lightweight project persistence across app sessions."""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from core.profile_store import PROJECT_ROOT, load_active_profile
from core.pipeline_export import slugify

PROJECTS_DIR = PROJECT_ROOT / "data" / "projects"
ACTIVE_PROJECT_FILE = PROJECT_ROOT / "data" / "active_project.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


def collect_project_state(main_window) -> dict:
    script = main_window.tab_script
    scene = main_window.tab_scene
    profile = load_active_profile() or {}

    return {
        "version": 1,
        "updated_at": _now(),
        "profile_name": profile.get("name", ""),
        "script_title": script.txt_topic.text().strip(),
        "topic_title": getattr(script, "current_topic_title", ""),
        "topic_strategy": getattr(script, "current_topic_strategy", {}) or {},
        "research": script.txt_research.toPlainText().strip(),
        "script": script.txt_output.toPlainText().strip(),
        "scene_script": scene.txt_script.toPlainText().strip(),
        "assigned_scenes": deepcopy(getattr(scene, "_assigned_data", []) or []),
        "prescan_data": deepcopy(getattr(scene, "_prescan_data", {}) or {}),
        "export_dir": "",
    }


def build_project_name(main_window) -> str:
    state = collect_project_state(main_window)
    title = state.get("script_title") or state.get("topic_title") or "video"
    profile = slugify(state.get("profile_name") or "profile", 20)
    topic = slugify(title, 32)
    return f"{profile}_{topic}"


def save_active_project(main_window, *, export_dir: str = "") -> dict:
    existing = load_active_project() or {}
    state = collect_project_state(main_window)
    if export_dir:
        state["export_dir"] = export_dir

    name = existing.get("name") or build_project_name(main_window)
    project = {
        "name": name,
        "created_at": existing.get("created_at") or _now(),
        "updated_at": _now(),
        "state": state,
    }
    _write_json(ACTIVE_PROJECT_FILE, project)
    _write_json(PROJECTS_DIR / f"{name}.json", project)
    return project


def load_active_project() -> dict | None:
    data = _read_json(ACTIVE_PROJECT_FILE, None)
    return data if isinstance(data, dict) else None


def list_saved_projects() -> list[dict]:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in sorted(PROJECTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        item = _read_json(path, None)
        if isinstance(item, dict):
            projects.append(item)
    return projects


def restore_project_to_main_window(main_window, project: dict) -> None:
    state = project.get("state") or {}
    script = main_window.tab_script
    scene = main_window.tab_scene

    title = state.get("script_title", "")
    if title:
        script.txt_topic.setText(title)
    script.current_topic_title = state.get("topic_title", "")
    script.current_topic_strategy = state.get("topic_strategy") or {}
    script._research_notes = state.get("research", "")
    script.txt_research.setPlainText(state.get("research", ""))
    script.txt_output.setPlainText(state.get("script", ""))

    scene.txt_script.setPlainText(state.get("scene_script", ""))
    scene._prescan_data = deepcopy(state.get("prescan_data") or {})
    prescan = scene._prescan_data
    if isinstance(prescan, dict):
        if isinstance(prescan.get("characters"), dict):
            scene.txt_prescan_chars.setPlainText("\n".join(prescan["characters"].keys()))
        if isinstance(prescan.get("backgrounds"), dict):
            scene.txt_prescan_bgs.setPlainText("\n".join(prescan["backgrounds"].keys()))
    if hasattr(scene, "restore_assigned_scenes"):
        scene.restore_assigned_scenes(deepcopy(state.get("assigned_scenes") or []))
    else:
        scene._assigned_data = deepcopy(state.get("assigned_scenes") or [])

    name = project.get("name", "Project")
    main_window.btn_proj.setText(name[:28] + ("..." if len(name) > 28 else ""))
    main_window.btn_proj.setToolTip(
        f"Project: {name}\nCập nhật: {project.get('updated_at', '')}"
    )
