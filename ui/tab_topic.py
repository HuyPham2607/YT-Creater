from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea)
from PyQt6.QtCore import Qt
from ui.components import DropZoneWidget

class TopicIdeatorTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(32, 32, 32, 32)
        
        # ==========================================
        # 1. HEADER (TIÊU ĐỀ & MÔ TẢ)
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 20)
        
        vbox_header = QVBoxLayout()
        vbox_header.addWidget(QLabel("Topic Ideator", objectName="page_title"))
        vbox_header.addWidget(QLabel("Generate validated topics với hook titles + unique angle + CTR score", objectName="page_desc"))
        
        header.addLayout(vbox_header)
        header.addStretch()
        
        lbl_badge = QLabel("Tool 0", objectName="page_badge")
        header.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        # ==========================================
        # SCROLL AREA CHO PHẦN NỘI DUNG CHÍNH
        # ==========================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(24)

        # --- 1. CONTEXT FILES ---
        lay.addWidget(QLabel("CONTEXT FILES (OPTIONAL)", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)
        ctx_lay.addWidget(DropZoneWidget("📋", "STYLE GUIDE", "Upload để suggest đúng tone"))
        ctx_lay.addWidget(DropZoneWidget("🧬", "DNA KÊNH", "Upload để suggest đúng format"))
        ctx_lay.addWidget(DropZoneWidget("📝", "TOPICS ĐÃ LÀM", "Upload để tránh trùng lặp"))
        lay.addLayout(ctx_lay)

        # --- 2. NGÁCH KÊNH ---
        lay.addWidget(QLabel("NGÁCH KÊNH", objectName="section_label"))
        
        tags_lay = QHBoxLayout()
        tags = ["Tài chính", "Tội phạm", "Lịch sử", "Khoa học", "Tâm lý học", "Địa chính trị", "Tiểu sử", "Triết học"]
        for tag in tags:
            b = QPushButton(tag, objectName="tag_btn")
            b.setCheckable(True)
            tags_lay.addWidget(b)
            
        b_c = QPushButton("+ Tuỳ chỉnh", objectName="tag_btn")
        b_c.setCheckable(True)
        tags_lay.addWidget(b_c)
        tags_lay.addStretch()
        lay.addLayout(tags_lay)

        self.txt_custom_niche = QLineEdit()
        self.txt_custom_niche.setPlaceholderText("Nhập ngách tuỳ chỉnh...")
        lay.addWidget(self.txt_custom_niche)

        # --- 3. SETTINGS 4 CỘT ---
        grid = QGridLayout()
        grid.setSpacing(16)

        # Hàng 0: Labels
        grid.addWidget(QLabel("SỐ TOPICS", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("NGÔN NGỮ OUTPUT", objectName="muted"), 0, 1)
        grid.addWidget(QLabel("KÊNH THAM CHIẾU (STYLE)", objectName="muted"), 0, 2)
        grid.addWidget(QLabel("FOCUS", objectName="muted"), 0, 3)

        # Hàng 1: Inputs
        self.txt_topics = QLineEdit("10 topics")
        grid.addWidget(self.txt_topics, 1, 0, alignment=Qt.AlignmentFlag.AlignTop)

        self.txt_lang = QLineEdit("Tiếng Việt")
        grid.addWidget(self.txt_lang, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Xử lý riêng cột "Kênh tham chiếu" để có dòng Hint text bên dưới
        vbox_ref = QVBoxLayout()
        vbox_ref.setSpacing(6)
        self.cmb_ref = QComboBox()
        self.cmb_ref.setEditable(True)
        self.cmb_ref.lineEdit().setPlaceholderText("VD: https://youtube.com/@channel hoặc tên kênh")
        vbox_ref.addWidget(self.cmb_ref)
        
        lbl_hint = QLabel("Paste link kênh hoặc gõ tên — Claude sẽ adapt style theo kênh đó", objectName="muted")
        lbl_hint.setStyleSheet("font-size: 11px;") # Cỡ chữ nhỏ giống y hệt bản Web
        vbox_ref.addWidget(lbl_hint)
        grid.addLayout(vbox_ref, 1, 2)

        self.cmb_focus = QComboBox()
        self.cmb_focus.addItems(["Dễ làm nhất", "Viral cao nhất", "CTR cao nhất"])
        grid.addWidget(self.cmb_focus, 1, 3, alignment=Qt.AlignmentFlag.AlignTop)

        # Set tỷ lệ rộng cho cột Kênh tham chiếu lớn hơn các cột khác
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 1)
        lay.addLayout(grid)

        # --- 4. YÊU CẦU BỔ SUNG ---
        lay.addWidget(QLabel("YÊU CẦU BỔ SUNG (OPTIONAL)", objectName="section_label"))
        self.txt_extra = QTextEdit()
        self.txt_extra.setPlaceholderText("VD: Tránh topics về chiến tranh, Ưu tiên nhân vật nữ, focus góc kinh tế...")
        self.txt_extra.setMinimumHeight(100)
        lay.addWidget(self.txt_extra)

        # --- 5. BOTTOM ACTIONS ---
        act_lay = QHBoxLayout()
        
        # Nút bên trái
        btn_gen = QPushButton("💡 Generate Topics", objectName="btn_primary")
        btn_reset = QPushButton("✕ Reset", objectName="btn_sec")
        act_lay.addWidget(btn_gen)
        act_lay.addWidget(btn_reset)

        act_lay.addStretch() # Đẩy các nút sau sang góc phải

        # Nút bên phải
        btn_sort_ctr = QPushButton("Sort: CTR", objectName="btn_sec")
        btn_sort_easy = QPushButton("Sort: Easy", objectName="btn_sec")
        act_lay.addWidget(btn_sort_ctr)
        act_lay.addWidget(btn_sort_easy)

        lay.addLayout(act_lay)
        lay.addStretch()

        # Đẩy layout vào scroll
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)