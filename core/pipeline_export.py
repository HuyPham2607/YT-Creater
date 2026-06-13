"""
Export Pipeline — gom output từ tất cả Tool vào một thư mục duy nhất.
"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.profile_store import PROJECT_ROOT, load_active_profile


@dataclass
class ExportResult:
    export_dir: Path
    files_written: list[str] = field(default_factory=list)
    dirs_copied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def total_items(self) -> int:
        return len(self.files_written) + len(self.dirs_copied)


def slugify(text: str, max_len: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text.strip())
    return (text[:max_len].strip("_") or "untitled").lower()


def _resolve_project_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


def _write_text(export_dir: Path, rel_path: str, content: str, result: ExportResult) -> bool:
    text = (content or "").strip()
    if not text:
        return False
    target = export_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    result.files_written.append(rel_path)
    return True


def _write_json(export_dir: Path, rel_path: str, data: Any, result: ExportResult) -> bool:
    if data is None:
        return False
    if isinstance(data, (list, dict, str)) and not data:
        return False
    target = export_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    result.files_written.append(rel_path)
    return True


def _copy_tree(export_dir: Path, rel_dest: str, src: Path, result: ExportResult) -> int:
    if not src.exists() or not src.is_dir():
        return 0
    files = [p for p in src.rglob("*") if p.is_file()]
    if not files:
        return 0
    dest = export_dir / rel_dest
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    result.dirs_copied.append(rel_dest)
    return len(files)


def _find_topic_in_profile(profile: dict | None, topic_title: str, subtitle: str) -> dict | None:
    if not profile:
        return None
    topic_title = (topic_title or "").strip().lower()
    subtitle = (subtitle or "").strip().lower()
    for topic in profile.get("topics") or []:
        if not isinstance(topic, dict):
            continue
        name = (topic.get("title") or topic.get("topic_name") or "").strip().lower()
        if topic_title and name == topic_title:
            return topic
        for item in topic.get("titles") or []:
            if isinstance(item, dict) and (item.get("text") or "").strip().lower() == subtitle:
                return topic
    return None


def collect_pipeline_snapshot(main_window) -> dict:
    profile = load_active_profile() or {}
    script = main_window.tab_script
    scene = main_window.tab_scene
    asset = main_window.tab_asset
    camera = main_window.tab_camera
    thumb = main_window.tab_thumb
    meta = main_window.tab_meta
    qc = main_window.tab_qc
    voice = main_window.tab_voice
    glabs = main_window.tab_glabs

    script_title = script.txt_topic.text().strip()
    topic_title = getattr(script, "current_topic_title", "") or script_title
    topic_strategy = getattr(script, "current_topic_strategy", {}) or {}
    matched_topic = _find_topic_in_profile(profile, topic_title, script_title)

    glabs_prompts = getattr(scene.tab_glabs, "_prompts", []) or []
    veo3_prompts = getattr(scene.tab_veo3, "_prompts", []) or []

    voice_out = (voice.txt_output.text().strip() or "outputs/voice")
    voice_project = voice.txt_project.text().strip() or "voice_project"
    glabs_images_dir = glabs.txt_out_dir.text().strip() or "outputs/glabs_images"
    glabs_video_path = ""
    if hasattr(glabs, "txt_video_out_dir"):
        glabs_video_path = glabs.txt_video_out_dir.text().strip()

    return {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "profile_name": profile.get("name", ""),
        "profile_niche": profile.get("niche", ""),
        "profile_lang": profile.get("lang", ""),
        "script_title": script_title,
        "topic_title": topic_title,
        "topic_strategy": topic_strategy,
        "matched_topic": matched_topic,
        "research": script.txt_research.toPlainText().strip() or getattr(script, "_research_notes", ""),
        "script": script.txt_output.toPlainText().strip(),
        "scene_script_input": scene.txt_script.toPlainText().strip(),
        "scene_preview": scene.txt_preview.toPlainText().strip(),
        "prescan_chars": scene.txt_prescan_chars.toPlainText().strip(),
        "prescan_bgs": scene.txt_prescan_bgs.toPlainText().strip(),
        "assigned_scenes": getattr(scene, "_assigned_data", []) or [],
        "prescan_data": getattr(scene, "_prescan_data", {}) or {},
        "glabs_prompts": glabs_prompts,
        "veo3_prompts": veo3_prompts,
        "asset_characters": asset.txt_characters.toPlainText().strip(),
        "asset_backgrounds": asset.txt_backgrounds.toPlainText().strip(),
        "asset_char_prompts": asset.txt_char_output.toPlainText().strip(),
        "asset_bg_prompts": asset.txt_bg_output.toPlainText().strip(),
        "asset_all_prompts": asset.txt_all_output.toPlainText().strip(),
        "asset_prescan": getattr(asset, "_prescan_data", {}) or {},
        "camera_outputs": getattr(camera, "_outputs", {}) or {},
        "thumbnail": {
            "concepts": thumb.txt_concepts.toPlainText().strip(),
            "prompts": thumb.txt_prompts.toPlainText().strip(),
            "canva": thumb.txt_canva.toPlainText().strip(),
            "json": thumb.txt_json.toPlainText().strip(),
            "result": getattr(thumb, "_result", {}) or {},
        },
        "metadata": {
            "analysis": meta.txt_analysis.toPlainText().strip(),
            "titles": meta.txt_titles.toPlainText().strip(),
            "description": meta.txt_desc.toPlainText().strip(),
            "tags": meta.txt_tags.toPlainText().strip(),
            "chapters": meta.txt_chapters.toPlainText().strip(),
            "all": meta.txt_all.toPlainText().strip(),
            "json": meta.txt_json.toPlainText().strip(),
            "result": getattr(meta, "_result", {}) or {},
            "input_title": meta.txt_title.text().strip(),
            "input_topic": meta.txt_topic.text().strip(),
        },
        "qc_report": qc._report_text() if hasattr(qc, "_report_text") else "",
        "voice_dir": str(_resolve_project_path(voice_out) / voice_project),
        "glabs_images_dir": str(_resolve_project_path(glabs_images_dir)),
        "glabs_video_dir": str(_resolve_project_path(glabs_video_path)) if glabs_video_path else "",
        "generated_topics": getattr(main_window.tab_topic, "current_topics", []) or [],
    }


def build_export_folder_name(snapshot: dict) -> str:
    profile = slugify(snapshot.get("profile_name") or "profile", 24)
    topic = slugify(snapshot.get("script_title") or snapshot.get("topic_title") or "video", 32)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{profile}_{topic}_{stamp}"


def build_default_export_parent(main_window) -> Path:
    snapshot = collect_pipeline_snapshot(main_window)
    folder = build_export_folder_name(snapshot)
    return PROJECT_ROOT / "outputs" / "pipeline" / folder


def export_pipeline(main_window, dest_parent: Path | None = None) -> ExportResult:
    snapshot = collect_pipeline_snapshot(main_window)
    folder_name = build_export_folder_name(snapshot)
    parent = Path(dest_parent) if dest_parent else (PROJECT_ROOT / "outputs" / "pipeline")
    export_dir = parent / folder_name
    if export_dir.exists():
        suffix = datetime.now().strftime("%S")
        export_dir = parent / f"{folder_name}_{suffix}"

    export_dir.mkdir(parents=True, exist_ok=True)
    result = ExportResult(export_dir=export_dir)

    profile_summary = {
        "name": snapshot.get("profile_name"),
        "niche": snapshot.get("profile_niche"),
        "lang": snapshot.get("profile_lang"),
        "script_title": snapshot.get("script_title"),
        "topic_title": snapshot.get("topic_title"),
    }
    _write_json(export_dir, "profile_summary.json", profile_summary, result)

    if snapshot.get("topic_strategy"):
        _write_json(export_dir, "topic/topic_strategy.json", snapshot["topic_strategy"], result)
    if snapshot.get("matched_topic"):
        _write_json(export_dir, "topic/saved_topic.json", snapshot["matched_topic"], result)
    if snapshot.get("generated_topics"):
        _write_json(export_dir, "topic/generated_topics.json", snapshot["generated_topics"], result)

    _write_text(export_dir, "script/title.txt", snapshot.get("script_title", ""), result)
    _write_text(export_dir, "script/research.txt", snapshot.get("research", ""), result)
    _write_text(export_dir, "script/script.txt", snapshot.get("script", ""), result)

    _write_text(export_dir, "scenes/script_input.txt", snapshot.get("scene_script_input", ""), result)
    _write_text(export_dir, "scenes/scene_preview.txt", snapshot.get("scene_preview", ""), result)
    _write_text(export_dir, "scenes/prescan_characters.txt", snapshot.get("prescan_chars", ""), result)
    _write_text(export_dir, "scenes/prescan_backgrounds.txt", snapshot.get("prescan_bgs", ""), result)
    _write_json(export_dir, "scenes/scenes.json", snapshot.get("assigned_scenes"), result)
    _write_json(export_dir, "scenes/prescan.json", snapshot.get("prescan_data"), result)

    if snapshot.get("glabs_prompts"):
        _write_text(export_dir, "scenes/glabs_image_prompts.txt", "\n".join(snapshot["glabs_prompts"]), result)
    if snapshot.get("veo3_prompts"):
        _write_text(export_dir, "scenes/veo3_video_prompts.txt", "\n".join(snapshot["veo3_prompts"]), result)

    _write_text(export_dir, "assets/characters.txt", snapshot.get("asset_characters", ""), result)
    _write_text(export_dir, "assets/backgrounds.txt", snapshot.get("asset_backgrounds", ""), result)
    _write_text(export_dir, "assets/character_prompts.txt", snapshot.get("asset_char_prompts", ""), result)
    _write_text(export_dir, "assets/background_prompts.txt", snapshot.get("asset_bg_prompts", ""), result)
    _write_text(export_dir, "assets/all_prompts.txt", snapshot.get("asset_all_prompts", ""), result)
    _write_json(export_dir, "assets/prescan.json", snapshot.get("asset_prescan"), result)

    camera = snapshot.get("camera_outputs") or {}
    _write_text(export_dir, "camera/capcut_sheet.txt", camera.get("capcut", ""), result)
    _write_text(export_dir, "camera/ai_motion_prompts.txt", camera.get("ai", ""), result)
    _write_text(export_dir, "camera/motion.csv", camera.get("csv", ""), result)

    thumb = snapshot.get("thumbnail") or {}
    _write_text(export_dir, "thumbnail/concepts.txt", thumb.get("concepts", ""), result)
    _write_text(export_dir, "thumbnail/glabs_prompts.txt", thumb.get("prompts", ""), result)
    _write_text(export_dir, "thumbnail/canva_guide.txt", thumb.get("canva", ""), result)
    if thumb.get("json"):
        _write_text(export_dir, "thumbnail/output.json", thumb["json"], result)
    elif thumb.get("result"):
        _write_json(export_dir, "thumbnail/output.json", thumb["result"], result)

    meta = snapshot.get("metadata") or {}
    _write_text(export_dir, "metadata/analysis.txt", meta.get("analysis", ""), result)
    _write_text(export_dir, "metadata/titles.txt", meta.get("titles", ""), result)
    _write_text(export_dir, "metadata/description.txt", meta.get("description", ""), result)
    _write_text(export_dir, "metadata/tags.txt", meta.get("tags", ""), result)
    _write_text(export_dir, "metadata/chapters.txt", meta.get("chapters", ""), result)
    _write_text(export_dir, "metadata/all.txt", meta.get("all", ""), result)
    if meta.get("json"):
        _write_text(export_dir, "metadata/output.json", meta["json"], result)
    elif meta.get("result"):
        _write_json(export_dir, "metadata/output.json", meta["result"], result)

    _write_text(export_dir, "qc/qc_report.txt", snapshot.get("qc_report", ""), result)

    voice_src = Path(snapshot.get("voice_dir", ""))
    if _copy_tree(export_dir, "voice", voice_src, result) == 0:
        result.skipped.append("voice (chưa có file TTS)")

    glabs_src = Path(snapshot.get("glabs_images_dir", ""))
    if _copy_tree(export_dir, "glabs_images", glabs_src, result) == 0:
        result.skipped.append("glabs_images (chưa có ảnh G-Labs)")

    video_src = Path(snapshot.get("glabs_video_dir", ""))
    if video_src and video_src.exists():
        if _copy_tree(export_dir, "glabs_videos", video_src, result) == 0:
            result.skipped.append("glabs_videos (thư mục trống)")
    else:
        result.skipped.append("glabs_videos (chưa cấu hình)")

    manifest = {
        "exported_at": snapshot.get("exported_at"),
        "export_dir": str(export_dir),
        "profile": snapshot.get("profile_name"),
        "script_title": snapshot.get("script_title"),
        "files_written": result.files_written,
        "dirs_copied": result.dirs_copied,
        "skipped": result.skipped,
    }
    _write_json(export_dir, "manifest.json", manifest, result)

    if not result.files_written and not result.dirs_copied:
        result.skipped.append("Không có dữ liệu nào để export — hãy chạy ít nhất Tool 1 (script).")

    return result
