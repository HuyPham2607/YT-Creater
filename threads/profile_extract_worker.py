import json
import os
import re
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal
from threads.gemini_retry import generate_content_with_retries

load_dotenv(Path(__file__).parent.parent / ".env")

EXTRACT_SCHEMA = """
{
  "name": "Channel name",
  "niche": "Niche / category",
  "visual": "Visual style summary",
  "lang": "Primary languages",
  "pov": "Narration POV",
  "char_style": "Character style prompt for G-Labs",
  "bg_style": "Background style prompt",
  "scene_style": "Scene aesthetic prompt",
  "style_ref": "Style reference prompt",
  "summary": "One paragraph channel summary"
}
""".strip()


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("AI không trả về JSON hợp lệ.")
        return json.loads(match.group(0))


class ProfileExtractWorker(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, payload: dict):
        super().__init__()
        self.payload = payload

    def run(self):
        if genai is None:
            self.error_signal.emit("Thư viện google-genai chưa được cài đặt.")
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.error_signal.emit("Không tìm thấy GEMINI_API_KEY trong .env")
            return

        client = genai.Client(api_key=api_key)
        style = (self.payload.get("style_content") or "").strip()
        dna = (self.payload.get("dna_content") or "").strip()
        hint_name = (self.payload.get("hint_name") or "").strip()

        if not style and not dna:
            self.error_signal.emit("Upload Style Guide hoặc DNA Kênh trước khi Auto Extract.")
            return

        system_prompt = (
            "You are a YouTube channel analyst. Extract structured profile fields from channel DNA/style documents. "
            "Infer practical production defaults for a faceless video pipeline. "
            "Return ONLY valid JSON matching the schema."
        )
        user_prompt = f"""Analyze the channel documents and extract profile fields.

Channel name hint: {hint_name or "unknown"}

STYLE GUIDE:
{style or "(empty)"}

CHANNEL DNA:
{dna or "(empty)"}

JSON schema:
{EXTRACT_SCHEMA}
"""

        try:
            def build_request(model_name):
                return {
                    "contents": user_prompt,
                    "config": types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.35,
                        response_mime_type="application/json",
                    ),
                }

            response, model_used = generate_content_with_retries(
                client=client,
                build_request=build_request,
                progress_callback=self.progress_signal.emit,
                log_prefix="PROFILE_EXTRACT",
            )
            data = _extract_json(response.text)
            data["model_used"] = model_used
            self.result_signal.emit(data)
        except Exception as exc:
            self.error_signal.emit(str(exc))
