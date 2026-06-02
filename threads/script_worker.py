import os
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

load_dotenv()

class ScriptWorker(QThread):
    progress_signal = pyqtSignal(str)     
    result_signal = pyqtSignal(str)  
    finished_signal = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        if genai is None:
            self.result_signal.emit("❌ LỖI: Thư viện 'google-genai' chưa được cài đặt.")
            self.finished_signal.emit()
            return
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.result_signal.emit("❌ LỖI NGHIÊM TRỌNG: Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client = genai.Client(api_key=api_key)
        model_name = 'gemini-1.5-flash'

        try:
            self.progress_signal.emit("✍️ Gemini đang cày kịch bản chi tiết...")
            
            # Nhóm 1: Dữ liệu nền móng
            dna = self.config.get("dna_content", "")
            style = self.config.get("style_content", "")

            # Nhóm 2: Thông số tùy biến
            tieu_de = self.config.get("topic", "")
            ngon_ngu = self.config.get("lang", "Tiếng Việt")
            ngoi_ke = self.config.get("pov", "Ngôi thứ 2 (Bạn)")
            cau_truc = self.config.get("structure", "Auto")
            so_phan = self.config.get("parts", "Auto")
            so_tu_muc_tieu = self.config.get("target_words", 1550)
            so_phut = self.config.get("target_mins", 10)
            
            # Nhóm 3: Dữ liệu mở rộng (Research)
            du_lieu_research = ""
            if self.config.get("research", False):
                self.progress_signal.emit("🔍 Đang thu thập dữ liệu Research...")
                # Mock dữ liệu research (sau này có thể ghép API search)
                du_lieu_research = "Research Data: This script requires deep factual accuracy. Incorporate highly relevant real-world examples and data points related to the topic."

            # --- BIẾN 1: SYSTEM PROMPT ---
            system_prompt = f"""You are an A-list YouTube scriptwriter and content strategist. Your task is to write a highly engaging video script that ABSOLUTELY complies with the brand style and formatting rules provided below.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY RULES (DO NOT VIOLATE):
1. Tone and writing rules: You must 100% adhere to the <style_guide> (sentence length, forbidden words, pronouns, use of numbers).
2. Do not use empty exclamations or cliché phrases (e.g., "amazing", "surprisingly", "sadly").
3. Write the full detailed dialogue. Do NOT write summaries, do NOT just outline.
4. The script output MUST BE entirely in the requested TARGET LANGUAGE, but keep the structural tags and syntax intact."""

            # --- BIẾN 2: USER PROMPT ---
            user_prompt = f"""Please write a detailed video script based on the following parameters:

- Video Title / Topic: {tieu_de}
- TARGET LANGUAGE: {ngon_ngu}
- Point of View (POV): {ngoi_ke}
- Script Structure: {cau_truc}
- Number of Parts: {so_phan}
- Target Word Count: Approximately {so_tu_muc_tieu} words.

<real_world_research_data>
{du_lieu_research}
</real_world_research_data>

OUTPUT SYNTAX FORMATTING (STRICTLY REQUIRED):
You are FREE TO BE CREATIVE with the content and how you name the sections (e.g., Level, Chapter, Act...) to best fit the requested Structure. 
However, the returned text SYNTAX MUST strictly follow the rules below so our software can parse it via Regex:

1. Metadata Block at the very top:
=== VIDEO TITLE ===
{tieu_de}

=== METADATA ===
- Target Duration: {so_phut} minutes
- Total Words: ~{so_tu_muc_tieu} words
- Number of Sections/Parts: {so_phan}
- Applied Formula/Structure: {cau_truc}

---

2. Section Headers Syntax:
ALL section headers MUST be placed between 3 equals signs and UPPERCASED. 
Example: === HOOK (0:00 - 0:35) === or === CHAPTER 1: THE TRUTH ABOUT INFLATION === or === ACT 2: THE CLIMAX ===

3. Dialogue Format (MOST IMPORTANT):
- WRITE PURE DIALOGUE ONLY. Do NOT insert production tags like [Setting...], [Sound...] or [Visual...] into the middle of the script dialogue.
- Every single dialogue sentence or minor thought MUST be separated by a blank line (Double line break). This is a prerequisite for cutting frames.

4. Transitions & Emphasis Syntax (Use flexibly when needed):
- Use `---` on a separate line to divide major Chapters/Acts.
- If there is a definitive statement or harsh truth, wrap it in asterisks: *This is the first illusion.*
- If you want to insert a call-to-action for the viewer (optional), use this syntax: >>> ACTION LAYER: [Action content]

NO introductory greetings, NO concluding remarks. Just print out the exact script matching the format."""

            # Cấu hình AI Generation
            gen_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )

            response = client.models.generate_content(
                model=model_name, 
                contents=user_prompt,
                config=gen_config
            )
            self.result_signal.emit(response.text)

        except Exception as e:
            self.result_signal.emit(f"❌ Lỗi AI: {str(e)}")
        finally:
            self.finished_signal.emit()