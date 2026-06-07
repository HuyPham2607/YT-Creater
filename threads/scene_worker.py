import os
import json
import re
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

load_dotenv()

class SceneWorker(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, str)  # task_type, json_result
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, task_type: str, config: dict):
        super().__init__()
        self.task_type = task_type  # 'prescan' | 'assign'
        self.config = config

    def run(self):
        if genai is None:
            self.error_signal.emit("❌ Thư viện 'google-genai' chưa được cài đặt.")
            self.finished_signal.emit()
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.error_signal.emit("❌ Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client = genai.Client(api_key=api_key)
        model_name = "gemini-3.5-flash"

        try:
            scenes = self.config.get("scenes", [])
            if not scenes:
                raise ValueError("Không có danh sách scenes để xử lý.")

            if self.task_type == "prescan":
                self._run_prescan(client, model_name, scenes)
            elif self.task_type == "assign":
                self._run_assign(
                    client,
                    model_name,
                    scenes,
                    self.config.get("characters", ""),
                    self.config.get("backgrounds", "")
                )

        except Exception as e:
            self.error_signal.emit(f"❌ Lỗi: {str(e)}")
        finally:
            self.finished_signal.emit()

    # ──────────────────────────────────────────────────────────────────────
    # PRESCAN — Quét nhân vật + bối cảnh + MÔ TẢ chi tiết từng asset
    # ──────────────────────────────────────────────────────────────────────
    def _run_prescan(self, client, model_name, scenes):
        self.progress_signal.emit("🔍 AI đang đọc toàn bộ kịch bản để trích xuất và mô tả tài nguyên...")

        # Gửi toàn bộ scenes — cần đọc hết để hiểu từng nhân vật xuất hiện ở đâu
        script_text = "\n".join(
            f"Scene {i+1}: {text}" for i, text in enumerate(scenes)
        )

        system_prompt = """You are an AI Script Analyzer and Visual Art Director for video production.

Your task: read ALL scenes of a script, then for EACH unique character and background location:
1. Extract a unique kebab-case identifier
2. Write a concise but specific visual description (2-4 sentences) based ONLY on context clues in the script
3. List up to 3 representative scene snippets where this asset appears

IMPORTANT RULES:
- Base descriptions STRICTLY on what the script implies (era, setting, role, clothing hints)
- If the script says "xuyên không sang Ai Cập" → the character wears ancient Egyptian clothing
- If the script says "bác sĩ tại bệnh viện" → white coat, hospital setting
- Do NOT invent details not supported by the script
- Normalize synonyms: "người chủ", "ông chủ", "boss" → pick one kebab name
- For characters with no visual clues → description = "role only, appearance undefined in script"
- kebab-case: lowercase, no accents, spaces → hyphens

Output ONLY valid raw JSON, no markdown fences, no explanation.

Schema:
{
  "characters_count": number,
  "backgrounds_count": number,
  "characters": {
    "kebab-name": {
      "display_name": "Tên hiển thị",
      "description": "Visual description inferred from script context...",
      "era_context": "modern / ancient-egypt / feudal-china / futuristic / etc.",
      "sample_scenes": ["Scene text 1", "Scene text 2"]
    }
  },
  "backgrounds": {
    "kebab-name": {
      "display_name": "Tên hiển thị",
      "description": "Visual description of the location inferred from script...",
      "era_context": "modern / ancient-egypt / feudal-china / futuristic / etc.",
      "sample_scenes": ["Scene text 1", "Scene text 2"]
    }
  }
}"""

        user_prompt = (
            f"Analyze ALL scenes below and output the enriched JSON:\n\n{script_text}"
        )

        gen_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1
        )

        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=gen_config
        )

        json_str = self._extract_json(response.text)
        self.result_signal.emit("prescan", json_str)

    # ──────────────────────────────────────────────────────────────────────
    # ASSIGN — Gán character + background + camera cho từng scene
    # (Không thay đổi so với version cũ)
    # ──────────────────────────────────────────────────────────────────────
    def _run_assign(self, client, model_name, scenes, characters, backgrounds):
        self.progress_signal.emit("⚡ AI đang đóng vai Art Director để gán Nhân vật và Bối cảnh...")

        input_data = [{"id": i + 1, "VO": text} for i, text in enumerate(scenes)]

        system_prompt = f"""You are an elite Art Director for an AI video production pipeline.
Assign exactly ONE character and ONE background to each scene based on the VO text.

CRITICAL RULES:
1. CHARACTER — pick EXACTLY from this list (use kebab-case key):
{characters}
If no character is visible, use "none".

2. BACKGROUND — pick EXACTLY from this list (use kebab-case key):
{backgrounds}

3. CAMERA ANGLE — assign a filmmaking tag based on dramatic weight:
   Close-up | Wide shot | Extreme Close-up | Establishing shot | Over-the-shoulder | POV

Output ONLY raw JSON:
{{
  "scenes": [
    {{
      "id": 1,
      "character": "...",
      "background": "...",
      "camera": "..."
    }}
  ]
}}"""

        user_prompt = (
            f"Scenes to process:\n"
            f"{json.dumps(input_data, ensure_ascii=False, indent=2)}\n\n"
            f"Generate the JSON output."
        )

        gen_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1
        )

        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=gen_config
        )

        json_str = self._extract_json(response.text)
        self.result_signal.emit("assign", json_str)

    # ──────────────────────────────────────────────────────────────────────
    # HELPER
    # ──────────────────────────────────────────────────────────────────────
    def _extract_json(self, text: str) -> str:
        """Strip markdown fences nếu AI không tuân thủ, trả về JSON thuần."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text