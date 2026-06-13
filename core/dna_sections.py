"""
Extract structured sections from Channel DNA and Style Guide markdown.
"""
from __future__ import annotations

import re
from typing import Iterable

HeadingRule = tuple[str, list[str]]

DNA_HEADINGS: list[HeadingRule] = [
    ("channel_info", [r"##\s*THÔNG TIN KÊNH", r"##\s*CHANNEL INFO"]),
    ("title_patterns", [r"##\s*1\.\s*TITLE PATTERNS", r"##\s*TITLE PATTERNS"]),
    ("hook_patterns", [r"##\s*2\.\s*HOOK PATTERNS", r"##\s*HOOK PATTERNS"]),
    ("video_structure", [r"##\s*3\.\s*VIDEO STRUCTURE", r"##\s*VIDEO STRUCTURE"]),
    ("thumbnail_style", [r"##\s*4\.\s*THUMBNAIL STYLE", r"##\s*THUMBNAIL STYLE"]),
    ("human_touch", [r"##\s*5\.\s*HUMAN TOUCH", r"##\s*HUMAN TOUCH"]),
    ("differentiation", [r"##\s*6\.\s*DIFFERENTIATION", r"DIFFERENTIATION vs"]),
    ("protagonist", [r"##\s*7\.\s*PROTAGONIST", r"PROTAGONIST IDENTITY"]),
]

STYLE_HEADINGS: list[HeadingRule] = [
    ("persona", [r"##\s*1\.\s*PERSONA", r"PERSONA DEFINITION"]),
    ("voice_rules", [r"##\s*3\.\s*VOICE RULES", r"VOICE RULES BLOCK", r"=== VOICE RULES"]),
    ("benchmark_passages", [r"##\s*4\.\s*BENCHMARK PASSAGES", r"BENCHMARK PASSAGES"]),
    ("thumbnail_text_bank", [r"##\s*6\.\s*THUMBNAIL TEXT BANK", r"THUMBNAIL TEXT BANK"]),
    ("thumbnail_composition", [r"##\s*THUMBNAIL COMPOSITION", r"Thumbnail Composition Rules"]),
    ("channel_strategy", [r"##\s*7\.\s*CHANNEL STRATEGY", r"CHANNEL STRATEGY"]),
]

WORKER_DNA_KEYS: dict[str, list[str]] = {
    "topic": ["channel_info", "title_patterns", "differentiation"],
    "script": ["hook_patterns", "video_structure", "human_touch"],
    "research": ["channel_info", "title_patterns"],
    "scene": ["protagonist", "thumbnail_style"],
    "asset": ["protagonist", "thumbnail_style"],
    "thumbnail": ["thumbnail_style", "protagonist"],
    "metadata": ["channel_info", "title_patterns"],
}

WORKER_STYLE_KEYS: dict[str, list[str]] = {
    "topic": [],
    "script": ["voice_rules", "benchmark_passages"],
    "research": [],
    "scene": [],
    "asset": [],
    "thumbnail": ["thumbnail_text_bank", "thumbnail_composition"],
    "metadata": ["voice_rules"],
}


def _find_heading_start(markdown: str, patterns: Iterable[str]) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            return match.start()
    return None


def extract_section(markdown: str, heading_patterns: Iterable[str]) -> str:
    text = (markdown or "").strip()
    if not text:
        return ""

    start = _find_heading_start(text, heading_patterns)
    if start is None:
        return ""

    section = text[start:]
    next_heading = re.search(r"\n##\s+", section[1:])
    if next_heading:
        section = section[: next_heading.start() + 1]
    return section.strip()


def extract_all_sections(markdown: str, rules: list[HeadingRule]) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, patterns in rules:
        content = extract_section(markdown, patterns)
        if content:
            found[key] = content
    return found


def extract_dna_sections(dna_content: str) -> dict[str, str]:
    return extract_all_sections(dna_content or "", DNA_HEADINGS)


def extract_style_sections(style_content: str) -> dict[str, str]:
    return extract_all_sections(style_content or "", STYLE_HEADINGS)


def _join_sections(section_map: dict[str, str], keys: list[str]) -> str:
    blocks = [section_map[key] for key in keys if section_map.get(key)]
    return "\n\n".join(blocks).strip()


def build_worker_section_text(
    worker_type: str,
    dna_content: str = "",
    style_content: str = "",
) -> dict[str, str]:
    dna_sections = extract_dna_sections(dna_content)
    style_sections = extract_style_sections(style_content)

    dna_keys = WORKER_DNA_KEYS.get(worker_type, [])
    style_keys = WORKER_STYLE_KEYS.get(worker_type, [])

    dna_text = _join_sections(dna_sections, dna_keys)
    style_text = _join_sections(style_sections, style_keys)

    focus_parts: list[str] = []
    if dna_text:
        focus_parts.append(f"--- DNA FOCUS ({worker_type.upper()}) ---\n{dna_text}")
    if style_text:
        focus_parts.append(f"--- STYLE FOCUS ({worker_type.upper()}) ---\n{style_text}")

    # Fallback when headings are missing: use full files (no blind head truncation).
    if not focus_parts:
        if (dna_content or "").strip():
            focus_parts.append(f"--- CHANNEL DNA ---\n{(dna_content or '').strip()}")
        if (style_content or "").strip():
            focus_parts.append(f"--- STYLE GUIDE ---\n{(style_content or '').strip()}")

    return {
        "dna_text": dna_text or (dna_content or "").strip(),
        "style_text": style_text or (style_content or "").strip(),
        "focus_block": "\n\n".join(focus_parts).strip(),
    }
