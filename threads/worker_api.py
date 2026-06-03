import time
import os
try:
    from google import genai
except ImportError:
    genai = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

# Thư viện đọc file Word
try:
    import docx
except ImportError:
    docx = None

# Nạp biến môi trường từ file .env
load_dotenv()

class AIWorker(QThread):
    progress_signal = pyqtSignal(str)     
    result_signal = pyqtSignal(str, str)  
    finished_signal = pyqtSignal()        

    def __init__(self, task_type, topic="", dna="", style="", research_enabled=False, file_paths=None):
        super().__init__()
        self.task_type = task_type
        self.topic = topic
        self.dna = dna
        self.style = style
        self.research_enabled = research_enabled
        self.file_paths = file_paths or []
        
        # Cấu hình Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai:
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-1.5-flash'
        else:
            self.client = None

    # Hàm thực sự đọc nội dung từ danh sách các file được kéo thả
    def read_files_content(self):
        combined_text = ""
        for path in self.file_paths:
            try:
                if path.endswith('.txt'):
                    with open(path, 'r', encoding='utf-8') as f:
                        combined_text += f.read() + "\n\n"
                elif path.endswith('.docx') and docx:
                    doc = docx.Document(path)
                    for para in doc.paragraphs:
                        combined_text += para.text + "\n"
                    combined_text += "\n\n"
            except Exception as e:
                print(f"Lỗi đọc file {path}: {e}")
        return combined_text

    def run(self):
        if not self.client:
            self.result_signal.emit("output", "❌ LỖI NGHIÊM TRỌNG: Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        try:
            # ---------------------------------------------------------
            # TÁC VỤ 1: ĐỌC FILE VÀ ÉP GEMINI TRÍCH XUẤT DNA
            # ---------------------------------------------------------
            if self.task_type == "analyze":
                self.progress_signal.emit(f"📂 Đang bóc tách text từ {len(self.file_paths)} file kịch bản...")
                source_text = self.read_files_content()
                
                if not source_text.strip():
                    raise Exception("Các file tải lên bị trống hoặc không thể đọc được nội dung.")

                self.progress_signal.emit("🤖 Đang ép Gemini phân tích ngược (Reverse Engineering)...")
                
                # Ép Gemini trả về định dạng có dải phân cách để code dễ bóc tách
                prompt = f"""Tôi sẽ cung cấp kịch bản viral của đối thủ.
                Hãy phân tích và trả về đúng 2 phần, ngăn cách nhau bằng cụm từ "---SPLIT_HERE---".
                Phần 1: CHANNEL DNA (Cấu trúc kịch bản, các phần Hook, Body, diễn biến tâm lý).
                Phần 2: STYLE GUIDE (Giọng văn, nguyên tắc xưng hô, độ dài câu, từ ngữ hay dùng).
                
                Nội dung kịch bản tham chiếu:
                {source_text[:30000]}
                """
                
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                res_text = response.text
                
                # Tự động cắt đôi kết quả để điền vào 2 ô TextEdit trên giao diện
                if "---SPLIT_HERE---" in res_text:
                    dna, style = res_text.split("---SPLIT_HERE---")
                else:
                    dna = res_text
                    style = "Gemini không tách rõ, vui lòng xem ở phần DNA phía trên."

                self.result_signal.emit("analyze_dna", dna.strip())
                self.result_signal.emit("analyze_style", style.strip())

            # ---------------------------------------------------------
            # TÁC VỤ 2: GEMINI LÊN Ý TƯỞNG TỪ DNA
            # ---------------------------------------------------------
            elif self.task_type == "ideas":
                self.progress_signal.emit("🧠 Đang gọi Gemini sáng tạo ý tưởng...")
                prompt = f"Dựa vào DNA kênh:\n{self.dna}\n\nStyle Guide:\n{self.style}\n\nHãy sáng tạo 5 tiêu đề video chuẩn viral về chủ đề: '{self.topic}'."
                response = self.client.models.generate_content(model=self.model_name, contents=prompt)
                self.result_signal.emit("output", response.text)

        except Exception as e:
            # Gửi lỗi ra màn hình chính
            self.result_signal.emit("analyze_dna", f"❌ Lỗi: {str(e)}")
            self.result_signal.emit("output", f"❌ Lỗi AI: {str(e)}")
        finally:
            self.finished_signal.emit()