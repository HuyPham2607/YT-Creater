from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QFrame, QSplitter)
from PyQt6.QtCore import Qt
from ui.components import DropZoneWidget

class SceneBreakdownTab(QWidget):
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
        
        lbl_title = QLabel("Scene Breakdown")
        lbl_title.setObjectName("page_title")
        vbox_h.addWidget(lbl_title)
        
        lbl_desc = QLabel("Split script theo dấu câu → Assign character + background bằng Claude API")
        lbl_desc.setObjectName("page_desc")
        vbox_h.addWidget(lbl_desc)
        
        header.addLayout(vbox_h)
        header.addStretch()
        
        lbl_badge = QLabel("Tool 2")
        lbl_badge.setObjectName("page_badge")
        header.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignTop)
        
        main_lay.addLayout(header)

        # ==========================================
        # 2. SCROLL AREA
        # ==========================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(20)

        # --- WORKFLOW HINT ---
        hint_text = ("💡 <b>Workflow:</b> Tool 2 = dùng mỗi video. Split scenes + tạo G-Labs prompts cho từng scene. "
                     "Tab 'G-Labs Prompts' chứa prompts sẵn sàng paste vào G-Labs.<br>"
                     "Tool 3 = dùng 1 lần khi setup kênh. Tạo reference sheets cho character/background.")
        hint = QLabel(hint_text)
        hint.setStyleSheet("background: rgba(232,116,42,0.06); border: 1px solid rgba(232,116,42,0.15); "
                           "border-radius: 8px; padding: 12px 16px; color: #E8742A; line-height: 1.5; font-size: 13px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # --- SETTINGS GRID ---
        grid = QGridLayout()
        grid.setSpacing(14)
        
        lbl_vs = QLabel("VISUAL STYLE"); lbl_vs.setObjectName("muted")
        lbl_lang = QLabel("NGÔN NGỮ VO"); lbl_lang.setObjectName("muted")
        lbl_min = QLabel("MIN KÝ TỰ / SCENE"); lbl_min.setObjectName("muted")
        lbl_max = QLabel("MAX KÝ TỰ / SCENE"); lbl_max.setObjectName("muted")
        
        grid.addWidget(lbl_vs, 0, 0); grid.addWidget(lbl_lang, 0, 1)
        grid.addWidget(lbl_min, 0, 2); grid.addWidget(lbl_max, 0, 3)

        self.txt_style = QLineEdit("Crayon Capital - Dark (cinematic)")
        self.txt_lang = QLineEdit("Tiếng Việt")
        self.txt_min = QLineEdit("30")
        self.txt_max = QLineEdit("100")

        grid.addWidget(self.txt_style, 1, 0); grid.addWidget(self.txt_lang, 1, 1)
        grid.addWidget(self.txt_min, 1, 2); grid.addWidget(self.txt_max, 1, 3)
        lay.addLayout(grid)

        # --- SPLITTER: KỊCH BẢN & PREVIEW ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(12)

        # Panel Trái: Kịch bản
        left_panel = QFrame()
        left_panel.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        l_lay = QVBoxLayout(left_panel); l_lay.setContentsMargins(0, 0, 0, 0); l_lay.setSpacing(0)
        
        l_head = QFrame()
        l_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        l_head_lay = QHBoxLayout(l_head); l_head_lay.setContentsMargins(16, 12, 16, 12)
        
        lbl_kb = QLabel("🔴 KỊCH BẢN")
        lbl_kb.setStyleSheet("font-size: 12px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        lbl_char_count = QLabel("0 ký tự"); lbl_char_count.setObjectName("muted")
        
        l_head_lay.addWidget(lbl_kb); l_head_lay.addStretch(); l_head_lay.addWidget(lbl_char_count)
        l_lay.addWidget(l_head)
        
        self.txt_script = QTextEdit()
        self.txt_script.setPlaceholderText("Paste kịch bản vào đây...")
        self.txt_script.setStyleSheet("border: none; background: transparent; padding: 16px; font-size: 14px; color: #E8E8F0;")
        l_lay.addWidget(self.txt_script)
        splitter.addWidget(left_panel)

        # Panel Phải: Preview
        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        r_lay = QVBoxLayout(right_panel); r_lay.setContentsMargins(0, 0, 0, 0); r_lay.setSpacing(0)
        
        r_head = QFrame()
        r_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        r_head_lay = QHBoxLayout(r_head); r_head_lay.setContentsMargins(16, 12, 16, 12)
        
        lbl_prev = QLabel("🔵 PREVIEW SCENES")
        lbl_prev.setStyleSheet("font-size: 12px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        lbl_scene_count = QLabel("0 scenes"); lbl_scene_count.setObjectName("muted")
        
        r_head_lay.addWidget(lbl_prev); r_head_lay.addStretch(); r_head_lay.addWidget(lbl_scene_count)
        r_lay.addWidget(r_head)
        
        self.txt_preview = QTextEdit()
        self.txt_preview.setPlaceholderText("Scenes sẽ hiện ở đây sau khi split...")
        self.txt_preview.setStyleSheet("border: none; background: transparent; padding: 16px; font-family: 'Space Mono', monospace; font-size: 13px; color: #606075;")
        r_lay.addWidget(self.txt_preview)
        splitter.addWidget(right_panel)

        splitter.setMinimumHeight(350)
        lay.addWidget(splitter)

        # --- ACTIONS ROW ---
        act_lay = QHBoxLayout()
        act_lay.setSpacing(10)
        
        btn_loc = QPushButton("🧹 Lọc Script")
        btn_loc.setStyleSheet("background: rgba(90,155,255,0.1); color: #5A9BFF; border: 1px solid rgba(90,155,255,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        
        btn_split = QPushButton("✂ Split Scenes")
        btn_split.setObjectName("btn_primary")
        
        btn_scan = QPushButton("🔍 Pre-scan")
        btn_scan.setStyleSheet("background: rgba(155,127,255,0.1); color: #9B7FFF; border: 1px solid rgba(155,127,255,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        
        btn_assign = QPushButton("⚡ Assign Assets")
        btn_assign.setObjectName("btn_sec")
        
        btn_dedup = QPushButton("📑 Deduplicate")
        btn_dedup.setStyleSheet("background: rgba(232,116,42,0.1); color: #E8742A; border: 1px solid rgba(232,116,42,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        
        btn_run = QPushButton("🚀 Run Pipeline")
        btn_run.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(155,127,255,0.25), stop:1 rgba(90,155,255,0.25)); color: #D0D0E0; border: 1px solid rgba(155,127,255,0.4); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")

        act_lay.addWidget(btn_loc); act_lay.addWidget(btn_split); act_lay.addWidget(btn_scan)
        act_lay.addWidget(btn_assign); act_lay.addWidget(btn_dedup); act_lay.addWidget(btn_run)
        act_lay.addStretch()

        lbl_batch = QLabel("Batch:"); lbl_batch.setObjectName("muted")
        self.txt_batch = QLineEdit("12"); self.txt_batch.setFixedWidth(50)
        
        lbl_cast = QLabel("Cast:"); lbl_cast.setObjectName("muted")
        self.cmb_cast = QComboBox(); self.cmb_cast.addItems(["Auto (AI quyết)", "Manual"])
        
        act_lay.addWidget(lbl_batch); act_lay.addWidget(self.txt_batch)
        act_lay.addSpacing(10)
        act_lay.addWidget(lbl_cast); act_lay.addWidget(self.cmb_cast)
        
        lay.addLayout(act_lay)

        # ==========================================
        # 3. SCENE RENAMER
        # ==========================================
        lay.addSpacing(10)
        renamer_head = QHBoxLayout()
        
        lbl_ren_title = QLabel("Scene Renamer")
        lbl_ren_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #E8E8F0;")
        
        lbl_ren_desc = QLabel("— Đổi tên ảnh thành 001, 002... cho video build")
        lbl_ren_desc.setObjectName("muted")
        
        renamer_head.addWidget(lbl_ren_title)
        renamer_head.addWidget(lbl_ren_desc)
        renamer_head.addStretch()
        lay.addLayout(renamer_head)

        ren_hint = QLabel("Flow: Download ảnh từ G-Labs → Kéo vào đây → Tự đổi tên thành 001.jpg, 002.jpg... (natural sort) → Download ZIP → Bỏ vào folder images/ để chạy build_video_srt.py")
        ren_hint.setStyleSheet("background: rgba(232,116,42,0.05); color: #E8742A; border: 1px solid rgba(232,116,42,0.2); border-radius: 6px; padding: 10px 14px; font-size: 12px;")
        ren_hint.setWordWrap(True)
        lay.addWidget(ren_hint)

        ren_grid = QGridLayout()
        ren_grid.setSpacing(14)
        
        # Cột Trái: Box Ảnh
        box_left = QFrame()
        box_left.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        bl_lay = QVBoxLayout(box_left); bl_lay.setContentsMargins(0, 0, 0, 0); bl_lay.setSpacing(0)
        
        bl_head = QFrame()
        bl_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        bl_head_lay = QVBoxLayout(bl_head); bl_head_lay.setContentsMargins(16, 12, 16, 12)
        lbl_anh = QLabel("ẢNH SCENES TỪ G-LABS")
        lbl_anh.setStyleSheet("font-size: 12px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        bl_head_lay.addWidget(lbl_anh)
        bl_lay.addWidget(bl_head)
        
        dz_wrap = QWidget()
        dz_lay = QVBoxLayout(dz_wrap); dz_lay.setContentsMargins(16, 16, 16, 16)
        dz = DropZoneWidget("📂", "Kéo thả ảnh vào đây hoặc click để chọn", "Tự sort theo tên file (natural sort)")
        dz_lay.addWidget(dz)
        bl_lay.addWidget(dz_wrap)
        
        ren_grid.addWidget(box_left, 0, 0)

        # Cột Phải: Box Tuỳ Chọn
        box_right = QFrame()
        box_right.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        br_lay = QVBoxLayout(box_right); br_lay.setContentsMargins(0, 0, 0, 0); br_lay.setSpacing(0)
        
        br_head = QFrame()
        br_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        br_head_lay = QVBoxLayout(br_head); br_head_lay.setContentsMargins(16, 12, 16, 12)
        lbl_opt = QLabel("TUỲ CHỌN")
        lbl_opt.setStyleSheet("font-size: 12px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        br_head_lay.addWidget(lbl_opt)
        br_lay.addWidget(br_head)
        
        opt_wrap = QWidget()
        opt_lay = QVBoxLayout(opt_wrap); opt_lay.setContentsMargins(16, 16, 16, 16); opt_lay.setSpacing(12)
        
        opt_lay.addWidget(QLabel("BẮT ĐẦU TỪ SỐ", objectName="muted"))
        self.txt_ren_start = QLineEdit("1")
        opt_lay.addWidget(self.txt_ren_start)
        
        opt_lay.addWidget(QLabel("SỐ CHỮ SỐ (PADDING)", objectName="muted"))
        self.cmb_ren_pad = QComboBox()
        self.cmb_ren_pad.addItems(["001", "01", "0001"])
        opt_lay.addWidget(self.cmb_ren_pad)
        
        opt_lay.addWidget(QLabel("GIỮ EXTENSION GỐC", objectName="muted"))
        self.cmb_ren_ext = QComboBox()
        self.cmb_ren_ext.addItems(["Giữ nguyên (.p...)", "Ép sang .jpg", "Ép sang .png"])
        opt_lay.addWidget(self.cmb_ren_ext)
        opt_lay.addStretch()
        
        br_lay.addWidget(opt_wrap)
        ren_grid.addWidget(box_right, 0, 1)

        ren_grid.setColumnStretch(0, 2) # Cột ảnh to hơn
        ren_grid.setColumnStretch(1, 1) # Cột tuỳ chọn nhỏ hơn
        lay.addLayout(ren_grid)

        # Đẩy vào Scroll
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)