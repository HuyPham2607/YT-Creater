"""Convert SRT subtitle files to YouTube chapter lines."""
from __future__ import annotations

import re
from pathlib import Path


def _srt_time_to_seconds(timestamp: str) -> int:
    hh, mm, rest = timestamp.split(":")
    ss, _ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss)


def srt_to_chapter_lines(srt_path: str | Path, *, min_gap_seconds: int = 45) -> str:
    path = Path(srt_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    text = path.read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        time_line = lines[1] if "-->" in lines[1] else lines[0]
        if "-->" not in time_line:
            continue
        start = time_line.split("-->")[0].strip()
        body = " ".join(lines[2:] if "-->" in lines[1] else lines[1:])
        body = re.sub(r"<[^>]+>", "", body).strip()
        if body:
            cues.append((_srt_time_to_seconds(start), body))

    if not cues:
        return ""

    chapters = []
    last_second = -min_gap_seconds
    for second, body in cues:
        if second - last_second < min_gap_seconds and chapters:
            continue
        mm, ss = divmod(second, 60)
        hh, mm = divmod(mm, 60)
        stamp = f"{hh:d}:{mm:02d}:{ss:02d}" if hh else f"{mm:d}:{ss:02d}"
        title = body[:60] + ("..." if len(body) > 60 else "")
        chapters.append(f"{stamp} {title}")
        last_second = second
    return "\n".join(chapters)
