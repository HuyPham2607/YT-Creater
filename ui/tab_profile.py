import json
import os
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGridLayout, QFrame, QScrollArea, 
                             QSizePolicy, QDialog, QLineEdit, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QCursor
from ui.components import DropZoneWidget
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

load_dotenv()

# Đường dẫn file lưu trữ database
DB_FILE = "profiles.json"
ACTIVE_PROFILE_FILE = "active_profile.json" # File lưu cấu hình khi bấm "Apply to All Tools"

class ProfileExtractWorker(QThread):
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, style_content, dna_content, topic_content):
        super().__init__()
        self.style_content = style_content
        self.dna_content = dna_content
        self.topic_content = topic_content

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
            prompt = f"""You are an AI assistant helping to set up a YouTube channel profile.
Analyze the following provided context documents (Style Guide, DNA, Topic) and extract key information into a JSON object.
Output ONLY a valid JSON object matching the requested schema. No markdown, no conversational filler.

Schema:
{{
  "name": "Channel name (if found, otherwise invent a suitable short one based on context)",
  "niche": "Main topic/niche of the channel",
  "visual": "Visual style (e.g. 2D Cartoon, Anime, Cinematic, Dark Academia)",
  "lang": "Primary language of the content",
  "pov": "Point of View (e.g. Ngôi 2 (Bạn), Ngôi 1 (Tôi), Ngôi 3)",
  "char_style": "Brief description of the main character/mascot style",
  "bg_style": "Brief description of the background/environment style"
}}

--- STYLE GUIDE ---
{self.style_content}

--- DNA ---
{self.dna_content}

--- TOPIC ---
{self.topic_content}
"""

            gen_config = types.GenerateContentConfig(
                temperature=0.2
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=gen_config
            )

            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                self.result_signal.emit(match.group(0))
            else:
                self.error_signal.emit("AI không trả về JSON hợp lệ.")
                
        except Exception as e:
            self.error_signal.emit(f"Lỗi AI: {str(e)}")
        finally:
            self.finished_signal.emit()

# =======================================================
# 1. CỬA SỔ POP-UP: TẠO MỚI & CHỈNH SỬA (Giữ nguyên logic của bạn)
# =======================================================
class ProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tạo Profile mới")
        self.resize(750, 480) 
        self.style_content = ""
        self.dna_content = ""
        self.topic_content = ""
        
        self.setStyleSheet("""
            QDialog { background-color: #0F0F18; border: 1px solid #252535; }
            QLabel { color: #E8E8F0; }
            QLineEdit, QTextEdit { background-color: #08080D; border: 1px solid #252535; border-radius: 8px; padding: 10px; color: #E8E8F0; font-size: 14px; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #E8742A; }
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(32, 32, 32, 20)

        head_lay = QHBoxLayout()
        self.lbl_title = QLabel("Tạo Profile mới")
        self.lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #E8E8F0;")
        head_lay.addWidget(self.lbl_title)
        head_lay.addStretch()
        main_lay.addLayout(head_lay)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #252535; border: none; margin: 10px 0;")
        main_lay.addWidget(line)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        widget = QWidget()
        form_lay = QVBoxLayout(widget)
        form_lay.setContentsMargins(0, 10, 16, 10)
        form_lay.setSpacing(20)

        self.txt_name = QLineEdit()
        self.txt_niche = QLineEdit("Roleplay & Makeover")
        self.txt_visual = QLineEdit("2D Cartoon")
        self.txt_lang = QLineEdit("Tiếng Việt, English")
        self.txt_pov = QLineEdit("Ngôi 2 (Bạn)")
        self.txt_char = QTextEdit()
        self.txt_bg = QTextEdit()
        
        self.txt_char.setMaximumHeight(80)
        self.txt_bg.setMaximumHeight(80)

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        
        v_name = QVBoxLayout()
        v_name.addWidget(QLabel("TÊN KÊNH *", objectName="muted"))
        v_name.addWidget(self.txt_name)
        row1.addLayout(v_name)

        v_niche = QVBoxLayout()
        v_niche.addWidget(QLabel("NGÁCH", objectName="muted"))
        v_niche.addWidget(self.txt_niche)
        row1.addLayout(v_niche)
        form_lay.addLayout(row1)

        form_lay.addWidget(QLabel("DEFAULT SETTINGS", objectName="section_label"))
        grid_def = QGridLayout()
        grid_def.setSpacing(16)
        grid_def.addWidget(QLabel("VISUAL STYLE", objectName="muted"), 0, 0)
        grid_def.addWidget(QLabel("NGÔN NGỮ", objectName="muted"), 0, 1)
        grid_def.addWidget(QLabel("POV STYLE", objectName="muted"), 0, 2)
        grid_def.addWidget(self.txt_visual, 1, 0)
        grid_def.addWidget(self.txt_lang, 1, 1)
        grid_def.addWidget(self.txt_pov, 1, 2)
        form_lay.addLayout(grid_def)

        form_lay.addWidget(QLabel("STYLE PROMPTS G-LABS", objectName="section_label"))
        form_lay.addWidget(QLabel("CHARACTER STYLE", objectName="muted"))
        form_lay.addWidget(self.txt_char)
        form_lay.addWidget(QLabel("BACKGROUND STYLE", objectName="muted"))
        form_lay.addWidget(self.txt_bg)

        form_lay.addWidget(QLabel("CONTEXT FILES", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)
        
        self.dz_style = DropZoneWidget("📋", "STYLE GUIDE", "Upload .md")
        self.dz_dna = DropZoneWidget("🧬", "DNA KÊNH", "Upload .md")
        self.dz_topic = DropZoneWidget("📝", "CHỦ ĐỀ", "Upload .md")
        
        self.dz_style.file_loaded.connect(lambda p, c: setattr(self, 'style_content', c))
        self.dz_dna.file_loaded.connect(lambda p, c: setattr(self, 'dna_content', c))
        self.dz_topic.file_loaded.connect(lambda p, c: setattr(self, 'topic_content', c))
        
        ctx_lay.addWidget(self.dz_style)
        ctx_lay.addWidget(self.dz_dna)
        ctx_lay.addWidget(self.dz_topic)
        form_lay.addLayout(ctx_lay)

        self.btn_extract = QPushButton("⚡ Auto Extract", objectName="btn_sec")
        self.btn_extract.setFixedWidth(150)
        self.btn_extract.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_extract.clicked.connect(self.auto_extract_data)
        form_lay.addWidget(self.btn_extract)

        form_lay.addStretch()
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        act_lay = QHBoxLayout()
        act_lay.setContentsMargins(0, 10, 0, 0)
        act_lay.addStretch()
        
        btn_cancel = QPushButton("Hủy", objectName="btn_sec")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Lưu Profile", objectName="btn_primary")
        btn_save.clicked.connect(self.validate_and_save)
        
        act_lay.addWidget(btn_cancel)
        act_lay.addWidget(btn_save)
        main_lay.addLayout(act_lay)

    def auto_extract_data(self):
        if not (self.style_content or self.dna_content or self.topic_content):
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng upload ít nhất 1 file (Style, DNA hoặc Topic) trước khi trích xuất!")
            return

        self.btn_extract.setText("⏳ Đang trích xuất...")
        self.btn_extract.setEnabled(False)
        
        self.extract_worker = ProfileExtractWorker(self.style_content, self.dna_content, self.topic_content)
        self.extract_worker.result_signal.connect(self._on_extract_result)
        self.extract_worker.error_signal.connect(self._on_extract_error)
        self.extract_worker.finished_signal.connect(self._on_extract_finished)
        self.extract_worker.start()

    def _on_extract_result(self, json_str):
        try:
            data = json.loads(json_str)
            if data.get("name"): self.txt_name.setText(data.get("name"))
            if data.get("niche"): self.txt_niche.setText(data.get("niche"))
            if data.get("visual"): self.txt_visual.setText(data.get("visual"))
            if data.get("lang"): self.txt_lang.setText(data.get("lang"))
            if data.get("pov"): self.txt_pov.setText(data.get("pov"))
            if data.get("char_style"): self.txt_char.setText(data.get("char_style"))
            if data.get("bg_style"): self.txt_bg.setText(data.get("bg_style"))
            QMessageBox.information(self, "Thành công", "Đã trích xuất dữ liệu thành công từ file Context!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi parse JSON: {e}\n{json_str}")

    def _on_extract_error(self, err_msg):
        QMessageBox.critical(self, "Lỗi trích xuất", err_msg)

    def _on_extract_finished(self):
        self.btn_extract.setText("⚡ Auto Extract")
        self.btn_extract.setEnabled(True)

    def validate_and_save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Tên Kênh!")
            self.txt_name.setFocus()
            return
        self.accept()

    def get_profile_data(self):
        return {
            "name": self.txt_name.text().strip(),
            "niche": self.txt_niche.text().strip(),
            "visual": self.txt_visual.text().strip(),
            "lang": self.txt_lang.text().strip(),
            "pov": self.txt_pov.text().strip(),
            "char_style": self.txt_char.toPlainText().strip(),
            "bg_style": self.txt_bg.toPlainText().strip(),
            "style_content": self.style_content,
            "dna_content": self.dna_content,
            "topic_content": self.topic_content
        }

    def load_data(self, data):
        self.lbl_title.setText("Chỉnh sửa Profile")
        self.setWindowTitle("Chỉnh sửa Profile")
        self.txt_name.setText(data.get("name", ""))
        self.txt_niche.setText(data.get("niche", ""))
        self.txt_visual.setText(data.get("visual", ""))
        self.txt_lang.setText(data.get("lang", ""))
        self.txt_pov.setText(data.get("pov", ""))
        self.txt_char.setText(data.get("char_style", ""))
        self.txt_bg.setText(data.get("bg_style", ""))
        
        self.style_content = data.get("style_content", "")
        self.dna_content = data.get("dna_content", "")
        self.topic_content = data.get("topic_content", "")
        
        if self.style_content:
            self.dz_style.lbl_desc.setText("Đã lưu (có sẵn)")
            self.dz_style.lbl_desc.setStyleSheet("color: #3AD68A; font-size: 11px;")
        if self.dna_content:
            self.dz_dna.lbl_desc.setText("Đã lưu (có sẵn)")
            self.dz_dna.lbl_desc.setStyleSheet("color: #3AD68A; font-size: 11px;")
        if self.topic_content:
            self.dz_topic.lbl_desc.setText("Đã lưu (có sẵn)")
            self.dz_topic.lbl_desc.setStyleSheet("color: #3AD68A; font-size: 11px;")


# =======================================================
# 2. COMPONENT BÊN TRÁI: ITEM DANH SÁCH PROFILE
# =======================================================
class ProfileListItem(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, data, index, is_active=False):
        super().__init__()
        self.index = index
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Style active / inactive giống web
        if is_active:
            self.setStyleSheet("""
                QFrame { background: rgba(232,116,42,0.1); border: 1px solid #E8742A; border-radius: 8px; }
                QLabel { background: transparent; border: none; }
            """)
        else:
            self.setStyleSheet("""
                QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }
                QFrame:hover { background: #161622; border: 1px solid #353545; }
                QLabel { background: transparent; border: none; }
            """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        lbl_name = QLabel(data.get("name", "Unknown Profile"))
        lbl_name.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {'#E8742A' if is_active else '#E8E8F0'};")
        
        # Mô tả ngắn gọn giống thẻ bên trái web
        desc = f"{data.get('niche', 'Niche')} • {data.get('lang', 'vi')} • {data.get('visual', 'custom')}"
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("font-size: 12px; color: #8A8A9E;")
        lbl_desc.setWordWrap(True)

        lay.addWidget(lbl_name)
        lay.addWidget(lbl_desc)

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)


# =======================================================
# 3. TAB CHÍNH: PROFILE MANAGER (Master-Detail Layout)
# =======================================================
class ProfileManagerTab(QWidget):
    profile_applied = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.profiles = []
        self.selected_index = -1
        
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15)
        main_lay.setSpacing(20)

        # ---------------------------------------------------
        # PANE BÊN TRÁI: DANH SÁCH PROFILES
        # ---------------------------------------------------
        left_pane = QWidget()
        left_pane.setFixedWidth(280)
        left_lay = QVBoxLayout(left_pane)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(10)

        # Đưa nút Tạo mới lên Header cùng hàng với chữ Profiles
        list_header_lay = QHBoxLayout()
        self.lbl_profile_count = QLabel("Profiles (0)")
        self.lbl_profile_count.setStyleSheet("font-size: 16px; font-weight: bold; color: #E8E8F0;")
        list_header_lay.addWidget(self.lbl_profile_count)
        list_header_lay.addStretch()
        self.btn_new_profile = QPushButton("+ Tạo mới", objectName="btn_primary")
        self.btn_new_profile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_new_profile.clicked.connect(self.open_new_profile_dialog)
        list_header_lay.addWidget(self.btn_new_profile)
        left_lay.addLayout(list_header_lay)

        # Khu vực scroll danh sách
        scroll_list = QScrollArea()
        scroll_list.setWidgetResizable(True)
        scroll_list.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.list_widget = QWidget()
        self.list_lay = QVBoxLayout(self.list_widget)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(8)
        self.list_lay.addStretch()
        
        scroll_list.setWidget(self.list_widget)
        left_lay.addWidget(scroll_list)


        # ---------------------------------------------------
        # PANE BÊN PHẢI: CHI TIẾT PROFILE (Khớp giao diện Web)
        # ---------------------------------------------------
        self.right_pane = QFrame()
        self.right_pane.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 12px; }")
        right_lay = QVBoxLayout(self.right_pane)
        right_lay.setContentsMargins(24, 24, 24, 24)
        right_lay.setSpacing(20)

        # Tiêu đề "Chi tiet Profile"
        lbl_detail_title = QLabel("Chi tiết Profile")
        lbl_detail_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E8E8F0; border: none;")
        right_lay.addWidget(lbl_detail_title)

        # Hàng chứa Tên Kênh và Cụm Nút chức năng
        header_lay = QHBoxLayout()
        self.lbl_active_name = QLabel("• CHƯA CHỌN PROFILE")
        self.lbl_active_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #E8742A; text-transform: uppercase; border: none;")
        
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setStyleSheet("QPushButton { background: #1A1A24; color: #E8E8F0; border: 1px solid #353545; border-radius: 6px; padding: 6px 12px; font-size: 13px; } QPushButton:hover { background: #252535; }")
        
        self.btn_apply = QPushButton("Apply to All Tools")
        self.btn_apply.setStyleSheet("QPushButton { background: rgba(58,214,138,0.1); color: #3AD68A; border: 1px solid #3AD68A; border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 13px; } QPushButton:hover { background: rgba(58,214,138,0.2); }")
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setStyleSheet("QPushButton { background: transparent; color: #E84040; border: 1px solid rgba(232,64,64,0.5); border-radius: 6px; padding: 6px 12px; font-size: 13px; } QPushButton:hover { background: rgba(232,64,64,0.1); }")
        
        self.btn_edit.clicked.connect(self.edit_profile)
        self.btn_apply.clicked.connect(self.apply_to_all_tools)
        self.btn_delete.clicked.connect(self.delete_profile)

        header_lay.addWidget(self.lbl_active_name)
        header_lay.addStretch()
        header_lay.addWidget(self.btn_edit)
        header_lay.addWidget(self.btn_apply)
        header_lay.addWidget(self.btn_delete)
        right_lay.addLayout(header_lay)

        # Lưới thông tin chi tiết
        grid_info = QGridLayout()
        grid_info.setVerticalSpacing(16)
        grid_info.setHorizontalSpacing(24)
        
        # Row 1
        grid_info.addWidget(QLabel("NGÁCH", objectName="muted"), 0, 0)
        self.lbl_val_niche = QLabel("-")
        self.lbl_val_niche.setStyleSheet("color: #E8E8F0; font-size: 14px; font-weight: bold; border: none;")
        grid_info.addWidget(self.lbl_val_niche, 1, 0)

        grid_info.addWidget(QLabel("NGÔN NGỮ", objectName="muted"), 0, 1)
        self.lbl_val_lang = QLabel("-")
        self.lbl_val_lang.setStyleSheet("color: #E8E8F0; font-size: 14px; border: none;")
        grid_info.addWidget(self.lbl_val_lang, 1, 1)

        grid_info.addWidget(QLabel("STYLE / VISUAL", objectName="muted"), 0, 2)
        self.lbl_val_visual = QLabel("-")
        self.lbl_val_visual.setStyleSheet("color: #E8E8F0; font-size: 14px; border: none;")
        grid_info.addWidget(self.lbl_val_visual, 1, 2)

        # Row 2
        grid_info.addWidget(QLabel("CẤU TRÚC (Mặc định)", objectName="muted"), 2, 0)
        lbl_val_struct = QLabel("Tuỳ chọn ở Tool 1")
        lbl_val_struct.setStyleSheet("color: #8A8A9E; font-size: 14px; border: none;")
        grid_info.addWidget(lbl_val_struct, 3, 0)

        grid_info.addWidget(QLabel("TARGET", objectName="muted"), 2, 1)
        lbl_val_target = QLabel("Tuỳ chọn ở Tool 1")
        lbl_val_target.setStyleSheet("color: #8A8A9E; font-size: 14px; border: none;")
        grid_info.addWidget(lbl_val_target, 3, 1)

        grid_info.addWidget(QLabel("POV", objectName="muted"), 2, 2)
        self.lbl_val_pov = QLabel("-")
        self.lbl_val_pov.setStyleSheet("color: #E8E8F0; font-size: 14px; border: none;")
        grid_info.addWidget(self.lbl_val_pov, 3, 2)
        
        grid_info.setColumnStretch(0, 2)
        grid_info.setColumnStretch(1, 1)
        grid_info.setColumnStretch(2, 1)
        right_lay.addLayout(grid_info)

        # Khối hiển thị File Context (Giả lập giống web với dấu tick xanh)
        right_lay.addSpacing(10)
        self.box_style = self.create_status_box("✓ Style Guide loaded (Sẵn sàng)")
        self.box_dna = self.create_status_box("✓ DNA loaded (Sẵn sàng)")
        self.box_topic = self.create_status_box("✓ Chu De loaded (Sẵn sàng)")
        right_lay.addWidget(self.box_style)
        right_lay.addWidget(self.box_dna)
        right_lay.addWidget(self.box_topic)

        # Notes
        self.lbl_notes = QLabel("Notes: ...")
        self.lbl_notes.setStyleSheet("color: #8A8A9E; font-size: 13px; border: none;")
        self.lbl_notes.setWordWrap(True)
        right_lay.addWidget(self.lbl_notes)

        right_lay.addStretch()

        # ---------------------------------------------------
        # Thêm vào Layout chính
        # ---------------------------------------------------
        main_lay.addWidget(left_pane)
        main_lay.addWidget(self.right_pane)

        self.load_database()
        self.update_detail_view() # Ẩn đi nếu chưa có profile

    def create_status_box(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("background: rgba(58,214,138,0.05); color: #3AD68A; border: 1px solid rgba(58,214,138,0.2); border-radius: 6px; padding: 10px 15px; font-family: monospace;")
        return lbl

    def load_database(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.profiles = json.load(f)
            except Exception:
                self.profiles = []
        
        # Chọn mặc định cái đầu tiên nếu có
        if self.profiles:
            self.selected_index = 0
        else:
            self.selected_index = -1
            
        self.render_list()

    def save_database(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.profiles, f, ensure_ascii=False, indent=4)

    def render_list(self):
        # Xóa list cũ
        while self.list_lay.count() > 1: # Chừa lại addStretch ở cuối
            item = self.list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_profile_count.setText(f"Profiles ({len(self.profiles)})")

        for index, profile_data in enumerate(self.profiles):
            is_active = (index == self.selected_index)
            item = ProfileListItem(profile_data, index, is_active)
            item.clicked.connect(self.select_profile)
            self.list_lay.insertWidget(self.list_lay.count() - 1, item)
            
        self.update_detail_view()

    def select_profile(self, index):
        self.selected_index = index
        self.render_list() # Render lại để cập nhật màu viền active

    def update_detail_view(self):
        if self.selected_index >= 0 and self.selected_index < len(self.profiles):
            self.right_pane.show()
            data = self.profiles[self.selected_index]
            
            self.lbl_active_name.setText(f"• {data.get('name', 'UNKNOWN').upper()}")
            self.lbl_val_niche.setText(data.get("niche", "-"))
            self.lbl_val_lang.setText(data.get("lang", "-"))
            self.lbl_val_visual.setText(data.get("visual", "-"))
            self.lbl_val_pov.setText(data.get("pov", "-"))
            
            # Gộp character và background style vào Notes
            notes = f"Notes:\n- Character: {data.get('char_style', 'N/A')}\n- Background: {data.get('bg_style', 'N/A')}"
            self.lbl_notes.setText(notes)
            
            # Hiển thị hoặc ẩn các hộp báo trạng thái File
            self.box_style.setVisible(bool(data.get("style_content")))
            self.box_dna.setVisible(bool(data.get("dna_content")))
            self.box_topic.setVisible(bool(data.get("topic_content")))
        else:
            self.right_pane.hide()

    def apply_to_all_tools(self):
        """Lưu profile đang chọn thành Active Profile để các Tool khác dùng"""
        if self.selected_index >= 0:
            active_data = self.profiles[self.selected_index]
            try:
                with open(ACTIVE_PROFILE_FILE, "w", encoding="utf-8") as f:
                    json.dump(active_data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Thành công", f"Đã áp dụng cấu hình của kênh '{active_data['name']}' cho toàn bộ Tools!")
                self.profile_applied.emit(active_data)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu Active Profile:\n{e}")

    def open_new_profile_dialog(self):
        dialog = ProfileDialog(self)
        if dialog.exec(): 
            new_data = dialog.get_profile_data()
            self.profiles.append(new_data) 
            self.selected_index = len(self.profiles) - 1 # Tự động chọn profile vừa tạo
            self.save_database()           
            self.render_list()             

    def edit_profile(self):
        if self.selected_index >= 0:
            dialog = ProfileDialog(self)
            dialog.load_data(self.profiles[self.selected_index])
            if dialog.exec():
                updated_data = dialog.get_profile_data()
                self.profiles[self.selected_index] = updated_data
                self.save_database()
                self.render_list()

    def delete_profile(self):
        if self.selected_index >= 0:
            profile_name = self.profiles[self.selected_index].get("name", "kênh này")
            reply = QMessageBox.question(self, 'Xác nhận xóa', 
                                         f'Bạn có chắc chắn muốn xóa profile "{profile_name}"?\n(Thao tác này không thể hoàn tác)',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.profiles.pop(self.selected_index)
                self.selected_index = 0 if self.profiles else -1
                self.save_database()     
                self.render_list()