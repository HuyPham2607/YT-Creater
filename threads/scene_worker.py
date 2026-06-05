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
    result_signal = pyqtSignal(str, str) # task_type, json_result
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, task_type: str, config: dict):
        super().__init__()
        self.task_type = task_type # 'prescan' hoặc 'assign'
        self.config = config       # chứa scenes, style...

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
        model_name = "gemini-3.5-flash" # Dùng flash cho nhanh và đủ tốt

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

    def _run_prescan(self, client, model_name, scenes):
        self.progress_signal.emit("🔍 AI đang đọc kịch bản để trích xuất tài nguyên...")
        
        # Ghép các scene lại thành text để AI đọc
        script_text = ""
        for idx, text in enumerate(scenes):
            script_text += f"Scene {idx + 1}: {text}\n"

        system_prompt = """You are an AI Script Analyzer for anime production. Your task is to read a list of chronological video scenes and extract a unique list of characters and background locations. You must normalize synonyms (e.g., 'the young boy' and 'Tanjiro' should be merged into 'Tanjiro'). Output ONLY a valid JSON object matching the requested schema. No markdown, no conversational filler.
        
        Expected JSON format:
        {
          "characters_count": number,
          "backgrounds_count": number,
          "characters_list": ["char 1", "char 2"],
          "backgrounds_list": ["bg 1", "bg 2"]
        }"""

        user_prompt = f"Analyze the following scenes and output the JSON:\n\n{script_text}"

        gen_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1 # Nhiệt độ thấp để đảm bảo tính nhất quán
        )

        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=gen_config
        )
        
        json_str = self._extract_json(response.text)
        self.result_signal.emit("prescan", json_str)

    def _run_assign(self, client, model_name, scenes, characters, backgrounds):
        self.progress_signal.emit("⚡ AI đang đóng vai Art Director để gán Nhân vật và Bối cảnh...")
        
        # Prepare input data
        input_data = []
        for idx, text in enumerate(scenes):
            input_data.append({"id": idx + 1, "VO": text})
            
        system_prompt = f"""You are an elite Art Director for an AI anime production pipeline. Your task is to assign exactly ONE 'character' and ONE 'background' to each scene based on the VO text.

        CRITICAL RULES:
        1. CHARACTER: You must select the character's name EXACTLY from this list:
        {characters}
        If multiple characters are in the scene, pick the main one. If no character is visible, use "none".
        
        2. BACKGROUND: You must select the background's name EXACTLY from this list:
        {backgrounds}
        
        3. CAMERA ANGLE: Assign a filmmaking camera tag (e.g., Close-up, Wide shot, Extreme Close-up, Establishing shot) based on the dramatic weight of the VO.
        
        Output format MUST be a single raw JSON matching the provided schema:
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

        user_prompt = f"Scenes to process:\n{json.dumps(input_data, ensure_ascii=False, indent=2)}\n\nGenerate the JSON output."

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

    def _extract_json(self, text: str) -> str:
        """Hàm regex để lấy đúng cục JSON từ response của Gemini (nếu có bọc markdown)"""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text # Trả về nguyên gốc nếu không tìm thấy pattern