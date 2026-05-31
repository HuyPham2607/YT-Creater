from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from ui.components import DropZoneWidget

class ScriptWriterTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(32, 32, 32, 32)
        
        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 20)
        vbox_h = QVBoxLayout()
        vbox_h.setSpacing(4)
        vbox_h.addWidget(QLabel("Script Writer", objectName="page_title"))
        vbox_h.addWidget(QLabel("Upload Style Guide + DNA + Chủ Đề → Generate full script theo đúng DNA kênh", objectName="page_desc"))
        header.addLayout(vbox_h)
        header.addStretch()
        header.addWidget(QLabel("Tool 1", objectName="page_badge"), alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        # ==========================================
        # 2. SCROLL AREA (FULL MÀN HÌNH NHƯ WEB)
        # ==========================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(20)

        # --- CONTEXT FILES ---
        lay.addWidget(QLabel("CONTEXT FILES", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)
        ctx_lay.addWidget(DropZoneWidget("📋", "STYLE GUIDE", "Upload .md hoặc .txt"))
        ctx_lay.addWidget(DropZoneWidget("🧬", "DNA KÊNH", "Upload .md hoặc .txt"))
        ctx_lay.addWidget(DropZoneWidget("📝", "CHỦ ĐỀ (OPTIONAL)", "Upload .md hoặc .txt"))
        lay.addLayout(ctx_lay)

        # --- CHỦ ĐỀ VIDEO ---
        lay.addWidget(QLabel("CHỦ ĐỀ VIDEO", objectName="section_label"))
        self.txt_topic = QLineEdit()
        self.txt_topic.setPlaceholderText("VD: POV: Bạn là đặc vụ CIA bị phản bội...")
        lay.addWidget(self.txt_topic)

        # --- CÀI ĐẶT ---
        lay.addWidget(QLabel("CÀI ĐẶT", objectName="section_label"))
        grid = QGridLayout()
        grid.setSpacing(14)
        
        grid.addWidget(QLabel("NGÔN NGỮ", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("CẤU TRÚC", objectName="muted"), 0, 1)
        grid.addWidget(QLabel("SỐ PHẦN", objectName="muted"), 0, 2)
        grid.addWidget(QLabel("TARGET PHÚT", objectName="muted"), 0, 3)
        grid.addWidget(QLabel("POV STYLE", objectName="muted"), 0, 4)
        
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Tiếng Việt", "English", "Italian", "Portuguese"])
        grid.addWidget(self.cmb_lang, 1, 0)

        self.cmb_struct = QComboBox()
        self.cmb_struct.addItems(["Levels - Escalation (POV)", "Problem - Solution", "Storytelling"])
        grid.addWidget(self.cmb_struct, 1, 1)

        self.txt_parts = QLineEdit("8")
        grid.addWidget(self.txt_parts, 1, 2)

        self.txt_mins = QLineEdit("12")
        grid.addWidget(self.txt_mins, 1, 3)

        self.cmb_pov = QComboBox()
        self.cmb_pov.addItems(["Ngôi 2 (Bạn)", "Ngôi 1 (Tôi)", "Ngôi 3 (Quan sát)"])
        grid.addWidget(self.cmb_pov, 1, 4)
        
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(4, 2)
        lay.addLayout(grid)

        # --- AI MODEL ---
        lay.addWidget(QLabel("AI MODEL", objectName="section_label"))
        self.cmb_ai = QComboBox()
        self.cmb_ai.addItems(["Claude 3.5 Sonnet", "Gemini 1.5 Pro"])
        self.cmb_ai.setMinimumWidth(300) # Giữ cho combobox AI ngắn lại giống giao diện web
        
        ai_lay = QHBoxLayout()
        ai_lay.addWidget(self.cmb_ai)
        ai_lay.addStretch()
        lay.addLayout(ai_lay)

        # --- CONTEXT BỔ SUNG ---
        lay.addWidget(QLabel("CONTEXT BỔ SUNG (OPTIONAL)", objectName="section_label"))
        self.txt_extra = QTextEdit()
        self.txt_extra.setPlaceholderText("Nhân vật, bối cảnh, twist muốn có, tone cụ thể...\n\nTip: Nếu chọn Auto structure, Claude sẽ tự quyết định số phần và tên từng phần phù hợp nhất với topic.")
        self.txt_extra.setMinimumHeight(100)
        lay.addWidget(self.txt_extra)

        # --- TOKEN COUNTER ---
        lbl_token = QLabel("✓ Input ~14k tokens / 28K")
        lbl_token.setStyleSheet("background-color: rgba(58,214,138,0.1); color: #3AD68A; border: 1px solid rgba(58,214,138,0.3); border-radius: 6px; padding: 12px 16px; font-weight: bold; font-size: 13px;")
        
        token_lay = QHBoxLayout()
        token_lay.addWidget(lbl_token)
        token_lay.addStretch() # Chặn để ô token không bị kéo dài ra toàn màn hình
        lay.addLayout(token_lay)

        # --- ACTION BUTTONS ---
        act_lay = QHBoxLayout()
        act_lay.setSpacing(16)
        act_lay.setContentsMargins(0, 10, 0, 0)
        
        btn_research = QPushButton("🔍 Research -> Viết Script", objectName="btn_primary")
        btn_write = QPushButton("✍️ Viết Ngay (không research)", objectName="btn_sec")
        
        act_lay.addWidget(btn_research)
        act_lay.addWidget(btn_write)
        act_lay.addStretch()
        lay.addLayout(act_lay)

        # Ép tất cả các thẻ lên trên cùng để gọn gàng
        lay.addStretch() 
        
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)