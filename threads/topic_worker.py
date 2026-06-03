import os
import time
import json
import re
from pathlib import Path
try:
    from google import genai
except ImportError:
    genai = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class TopicWorker(QThread):
    result_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        if genai is None:
            self.result_signal.emit("❌ LỖI: Thư viện 'google-genai' chưa được cài đặt. Vui lòng chạy lệnh 'pip install google-genai' trong terminal.")
            self.finished_signal.emit()
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.result_signal.emit("❌ LỖI: Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client = genai.Client(api_key=api_key)

        try:
            # === SYSTEM PROMPT & RULES (IN ENGLISH) ===
            prompt = "You are a world-class YouTube content strategist and algorithm expert.\n"
            prompt += f"Your task is to generate {self.config.get('num_topics', '10')} highly engaging video topics.\n\n"
            
            prompt += "CRITICAL RULE: You must output ONLY a valid JSON object. No markdown, no explanations, no greetings.\n"
            prompt += "The JSON keys must be in ENGLISH, but the content values MUST be written in the target language.\n\n"
            
            # === USER CONFIGURATION ===
            prompt += f"TARGET LANGUAGE FOR CONTENT: {self.config.get('lang', 'Tiếng Việt')}\n"
            prompt += f"CHANNEL NICHE: {self.config.get('niche', 'Unspecified')}\n"
            prompt += f"OPTIMIZATION FOCUS: {self.config.get('focus', 'Highest CTR')}\n"
            prompt += f"REFERENCE CHANNEL INSPIRATION: {self.config.get('ref_channel', 'None')}\n"
            prompt += f"EXTRA REQUESTS: {self.config.get('extra', 'None')}\n\n"
            
            # === OPTIONAL CONTEXT BLOCKS ===
            if self.config.get('style_content'):
                prompt += f"--- CHANNEL STYLE GUIDE ---\n{self.config['style_content']}\n"
                prompt += "-> Adopt this tone and style for the titles and hooks.\n\n"
                
            if self.config.get('dna_content'):
                prompt += f"--- CHANNEL DNA ---\n{self.config['dna_content']}\n"
                prompt += "-> Ensure the unique angles match this channel format.\n\n"
                
            if self.config.get('done_content'):
                prompt += f"--- PREVIOUS TOPICS (DO NOT DUPLICATE) ---\n{self.config['done_content']}\n\n"

            # === REQUIRED JSON STRUCTURE ===
            prompt += """
REQUIRED JSON FORMAT:
{
  "topics": [
    {
      "topic_name": "Broad conceptual name of the video",
      "titles": [
        {"text": "First clickbait title option", "formula": "Name of the psychological formula used (e.g. Curiosity Gap)"},
        {"text": "Second title option", "formula": "Fear of Missing Out"},
        {"text": "Third title option", "formula": "Contrarian View"}
      ],
      "unique_angle": "Detailed explanation of the unique perspective/layer this video takes compared to competitors.",
      "hook_sentence": "The exact first sentence spoken in the video to hook the viewer.",
      "ctr_level": "HIGH", 
      "difficulty_level": "EASY, MEDIUM, or HARD",
      "tags": ["tag1", "tag2", "tag3"]
    }
  ]
}
"""
            print("\n" + "="*50)
            print("📤 [TOPIC_WORKER] FULL PROMPT SENT TO AI:")
            print(prompt)
            print("="*50 + "\n")

            # Danh sách các model theo thứ tự ưu tiên (Fallback Chain)
            model_priority = [
                "gemini-3.5-flash"
            ]

            last_error = ""
            for model_name in model_priority:
                retries = 2  # Tăng lên 2 lần thử lại cho bản Pro
                while retries >= 0:
                    try:
                        print(f"🚀 [TOPIC_WORKER] ACTIVE MODEL: {model_name}")
                        print(f"📡 [TOPIC_WORKER] Sending request to {model_name}... (Please wait)")
                        
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt
                        )

                        
                        # Kiểm tra xem có phản hồi hợp lệ không (tránh lỗi Safety filters)
                        if not response.candidates or not response.candidates[0].content.parts:
                            print(f"🛡️ [TOPIC_WORKER] {model_name} BLOCKED by Safety Filters.")
                            raise ValueError(f"Bị chặn bởi bộ lọc an toàn của {model_name}.")

                        raw_text = response.text
                        print("\n" + "-"*30)
                        print(f"📥 [TOPIC_WORKER] RAW RESPONSE FROM {model_name}:")
                        print(raw_text)
                        print("-"*30 + "\n")
                        
                        # Regex to extract JSON securely
                        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                        if json_match:
                            clean_json = json_match.group(0)
                            data = json.loads(clean_json)
                            # Nhét thêm tên model vào JSON để UI hiển thị
                            data["model_used"] = model_name.split("/")[-1]
                            
                            print(f"✅ [TOPIC_WORKER] SUCCESS: Valid JSON result from {model_name}")
                            self.result_signal.emit(json.dumps(data))
                            return # Thành công, thoát hàm run
                        else:
                            print(f"❌ [TOPIC_WORKER] JSON Pattern not found in {model_name} response.")
                            raise ValueError(f"Model {model_name} không trả về đúng cấu trúc JSON.")

                    except Exception as e:
                        err_msg = str(e)
                        print(f"⚠️ [TOPIC_WORKER] {model_name} FAILED: {err_msg}")
                        last_error = f"[{model_name.split('/')[-1]}] {str(e)}"
                        
                        # Nếu lỗi API Key bị lộ (403), dừng ngay lập tức vì thử model khác cũng vô ích
                        if "leaked" in err_msg.lower() or "403" in err_msg.lower():
                            self.result_signal.emit("❌ LỖI: API Key của bạn đã bị lộ hoặc không có quyền (403). Hãy kiểm tra file .env!")
                            self.finished_signal.emit()
                            return

                        # Nếu gặp lỗi hạn mức hoặc lỗi hệ thống, thử retry trước khi fallback
                        if any(x in err_msg.lower() for x in ["429", "quota", "limit", "503", "overloaded", "not found", "deadline"]):
                            if retries > 0:
                                wait_time = 5
                                print(f"⏳ [TOPIC_WORKER] {model_name} hit quota/limit. Retrying ({retries} left) in {wait_time}s...")
                                time.sleep(wait_time)
                                retries -= 1
                                continue
                            else:
                                print(f"🔄 [TOPIC_WORKER] {model_name} exhausted retries. Falling back...")
                                break # Dừng vòng lặp while để for loop chuyển sang model tiếp theo
                        else:
                            print(f"⚠️ [TOPIC_WORKER] Unexpected error with {model_name}. Attempting fallback...")
                            break 

            print(f"🛑 [TOPIC_WORKER] All models failed. Last error: {last_error}")
            raise Exception(f"Tất cả các model đều thất bại. Lỗi cuối cùng: {last_error}")

        except Exception as e:
            self.result_signal.emit(f"❌ Lỗi AI API: {str(e)}")
        finally:
            self.finished_signal.emit()