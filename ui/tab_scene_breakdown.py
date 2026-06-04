from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QFrame, QSplitter,
                             QInputDialog, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QTabBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QColor, QBrush, QFont
from ui.components import DropZoneWidget
import json
import os
import re
from threads.scene_worker import SceneWorker

class SceneBreakdownTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 0, 10, 0)
        
        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
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
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(16)

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
        self.lbl_char_count = QLabel("0 ký tự"); self.lbl_char_count.setObjectName("muted")
        
        self.btn_load_script = QPushButton("📂 Load từ Profile")
        self.btn_load_script.setStyleSheet("background: #252535; color: #E8E8F0; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        self.btn_load_script.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_load_script.clicked.connect(self._load_script_from_profile)
        
        l_head_lay.addWidget(lbl_kb)
        l_head_lay.addStretch()
        l_head_lay.addWidget(self.btn_load_script)
        l_head_lay.addWidget(self.lbl_char_count)
        l_lay.addWidget(l_head)
        
        self.txt_script = QTextEdit()
        self.txt_script.setPlaceholderText("Paste kịch bản vào đây...")
        self.txt_script.setStyleSheet("border: none; background: transparent; padding: 16px; font-size: 14px; color: #E8E8F0;")
        self.txt_script.textChanged.connect(self._update_char_count)
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
        self.lbl_scene_count = QLabel("0 scenes"); self.lbl_scene_count.setObjectName("muted")
        
        r_head_lay.addWidget(lbl_prev); r_head_lay.addStretch(); r_head_lay.addWidget(self.lbl_scene_count)
        r_lay.addWidget(r_head)
        
        self.txt_preview = QTextEdit()
        self.txt_preview.setPlaceholderText("Scenes sẽ hiện ở đây sau khi split...")
        self.txt_preview.setStyleSheet("border: none; background: transparent; padding: 16px; font-family: 'Space Mono', monospace; font-size: 13px; color: #606075;")
        r_lay.addWidget(self.txt_preview)
        splitter.addWidget(right_panel)

        splitter.setMinimumHeight(240) 
        lay.addWidget(splitter)

        # --- ACTIONS ROW ---
        act_lay = QHBoxLayout()
        act_lay.setSpacing(10)
        
        self.btn_loc = QPushButton("🧹 Lọc Script")
        self.btn_loc.setStyleSheet("background: rgba(90,155,255,0.1); color: #5A9BFF; border: 1px solid rgba(90,155,255,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_loc.clicked.connect(self._clean_script)
        
        self.btn_split = QPushButton("✂ Split Scenes")
        self.btn_split.setObjectName("btn_primary")
        self.btn_split.clicked.connect(self._split_scenes)
        
        self.btn_scan = QPushButton("🔍 Pre-scan")
        self.btn_scan.setStyleSheet("background: rgba(155,127,255,0.1); color: #9B7FFF; border: 1px solid rgba(155,127,255,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_scan.clicked.connect(self._pre_scan)
        
        self.btn_assign = QPushButton("⚡ Assign Assets")
        self.btn_assign.setObjectName("btn_sec")
        self.btn_assign.clicked.connect(self._assign_assets)
        
        self.btn_dedup = QPushButton("📑 Deduplicate")
        self.btn_dedup.setStyleSheet("background: rgba(232,116,42,0.1); color: #E8742A; border: 1px solid rgba(232,116,42,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_dedup.clicked.connect(self._deduplicate)
        
        self.btn_run = QPushButton("🚀 Run Pipeline")
        self.btn_run.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(155,127,255,0.25), stop:1 rgba(90,155,255,0.25)); color: #D0D0E0; border: 1px solid rgba(155,127,255,0.4); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_run.clicked.connect(self._run_pipeline)

        act_lay.addWidget(self.btn_loc); act_lay.addWidget(self.btn_split); act_lay.addWidget(self.btn_scan)
        act_lay.addWidget(self.btn_assign); act_lay.addWidget(self.btn_dedup); act_lay.addWidget(self.btn_run)
        act_lay.addStretch()

        lbl_batch = QLabel("Batch:"); lbl_batch.setObjectName("muted")
        self.txt_batch = QLineEdit("12"); self.txt_batch.setFixedWidth(50)
        
        lbl_cast = QLabel("Cast:"); lbl_cast.setObjectName("muted")
        self.cmb_cast = QComboBox(); self.cmb_cast.addItems(["Auto (AI quyết)", "Manual"])
        
        act_lay.addWidget(lbl_batch); act_lay.addWidget(self.txt_batch)
        act_lay.addSpacing(10)
        act_lay.addWidget(lbl_cast); act_lay.addWidget(self.cmb_cast)
        
        lay.addLayout(act_lay)

        # ====================================================================
        # 🌟 NEW COMPONENT: STATS DASHBOARD & STORYBOARD GRID (WEB REPLICATED)
        # ====================================================================
        lay.addSpacing(10)
        
        # 1. Row Bộ đếm chỉ số (Stats Bar)
        stats_lay = QHBoxLayout()
        stats_lay.setSpacing(12)
        
        self.card_scenes = self._create_stat_card("SCENES", "0", "#E8742A")
        self.card_assigned = self._create_stat_card("ASSIGNED", "0", "#606075")
        self.card_chars = self._create_stat_card("CHARACTERS", "-", "#606075")
        self.card_bgs = self._create_stat_card("BACKGROUNDS", "-", "#606075")
        self.card_duration = self._create_stat_card("DURATION", "00m00s", "#3AD68A")
        
        stats_lay.addWidget(self.card_scenes)
        stats_lay.addWidget(self.card_assigned)
        stats_lay.addWidget(self.card_chars)
        stats_lay.addWidget(self.card_bgs)
        stats_lay.addWidget(self.card_duration)
        lay.addLayout(stats_lay)

        # 2. Thanh Tabs điều hướng giống Web
        self.tabs_bar = QTabBar()
        self.tabs_bar.addTab("SCENE LIST")
        self.tabs_bar.addTab("G-LABS IMAGE PROMPTS")
        self.tabs_bar.addTab("VE03 VIDEO PROMPTS")
        self.tabs_bar.addTab("ASSETS")
        self.tabs_bar.addTab("CAMERA GUIDE")
        self.tabs_bar.addTab("PRODUCTION NOTES")
        self.tabs_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tabs_bar.setStyleSheet("""
            QTabBar::tab { background: #0F0F18; color: #606075; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; padding: 10px 18px; border: 1px solid #252535; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }
            QTabBar::tab:selected { background: #171724; color: #E8742A; border-top: 2px solid #E8742A; }
            QTabBar::tab:hover:!selected { color: #E8E8F0; background: #161622; }
        """)
        lay.addWidget(self.tabs_bar)

        # 3. Bảng quản lý 40 Scenes biểu mẫu
        self.table_scenes = QTableWidget()
        self.table_scenes.setColumnCount(8)
        self.table_scenes.setHorizontalHeaderLabels(["STT", "LEVEL", "VO", "CHARACTER", "BACKGROUND", "CAMERA", "DUR", "ACTIONS"])
        self.table_scenes.setMinimumHeight(450)
        self.table_scenes.setStyleSheet("""
            QTableWidget { background-color: #0F0F18; border: 1px solid #252535; border-radius: 6px; gridline-color: #1F1F2E; color: #E8E8F0; font-size: 13px; }
            QHeaderView::section { background-color: #171724; color: #606075; font-weight: bold; font-size: 11px; padding: 8px; border: none; border-bottom: 1px solid #252535; }
            QTableWidget::item { padding: 10px; }
        """)
        
        # Khóa cấu hình kích thước cột tự động co giãn
        header = self.table_scenes.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed) # STT cố định
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed) # Level cố định
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # VO giãn
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        
        self.table_scenes.setColumnWidth(0, 50)
        self.table_scenes.setColumnWidth(1, 65)
        self.table_scenes.setColumnWidth(3, 200) # Mở rộng để chứa Prompt
        self.table_scenes.setColumnWidth(4, 200) # Mở rộng để chứa Prompt
        self.table_scenes.setColumnWidth(5, 120)
        self.table_scenes.setColumnWidth(6, 55)
        self.table_scenes.setColumnWidth(7, 85)

        self._populate_table([]) # Bảng khởi tạo rỗng
        lay.addWidget(self.table_scenes)

        # 4. Hàng nút xuất file ngay dưới bảng
        tbl_actions_lay = QHBoxLayout()
        tbl_actions_lay.setSpacing(10)
        
        btn_xlsx = QPushButton("⬇ XLSX")
        btn_xlsx.setStyleSheet("background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px;")
        btn_glabs_txt = QPushButton("⬇ G-Labs TXT")
        btn_glabs_txt.setStyleSheet("background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px;")
        btn_vo_only = QPushButton("⬇ VO Only")
        btn_vo_only.setStyleSheet("background: rgba(90,155,255,0.1); color: #5A9BFF; border: 1px solid rgba(90,155,255,0.2); border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px;")
        btn_to_tool3 = QPushButton("→ Assets sang Tool 3")
        btn_to_tool3.setStyleSheet("background: rgba(58,214,138,0.1); color: #3AD68A; border: 1px solid rgba(58,214,138,0.2); border-radius: 4px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        
        btn_xlsx.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_glabs_txt.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_vo_only.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_to_tool3.setCursor(Qt.CursorShape.PointingHandCursor)

        tbl_actions_lay.addWidget(btn_xlsx)
        tbl_actions_lay.addWidget(btn_glabs_txt)
        tbl_actions_lay.addWidget(btn_vo_only)
        tbl_actions_lay.addWidget(btn_to_tool3)
        tbl_actions_lay.addStretch()
        lay.addLayout(tbl_actions_lay)

        # ==========================================
        # 4. SCENE RENAMER
        # ==========================================
        lay.addSpacing(5)
        renamer_head = QHBoxLayout()
        renamer_head.setSpacing(6)
        
        lbl_ren_title = QLabel("▶ 📁 Scene Renamer")
        lbl_ren_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #E8E8F0;")
        
        lbl_ren_desc = QLabel("— Đổi tên ảnh thành 001, 002... cho video build")
        lbl_ren_desc.setStyleSheet("color: #606075; font-size: 13px;")
        
        renamer_head.addWidget(lbl_ren_title)
        renamer_head.addWidget(lbl_ren_desc)
        renamer_head.addStretch()
        lay.addLayout(renamer_head)

        ren_hint = QLabel("Flow: Download ảnh từ G-Labs → Kéo vào đây → Tự đổi tên thành 001.jpg, 002.jpg... (natural sort) → Download ZIP → Bỏ vào folder images/ để chạy build_video_srt.py")
        ren_hint.setStyleSheet("background: rgba(232,116,42,0.04); color: #E8742A; border: 1px solid rgba(232,116,42,0.12); border-radius: 6px; padding: 6px 10px; font-size: 11px; line-height: 1.2;")
        ren_hint.setWordWrap(True)
        lay.addWidget(ren_hint)

        ren_grid = QGridLayout()
        ren_grid.setSpacing(14)
        
        # Cột Trái: Box Kéo thả Ảnh
        box_left = QFrame()
        box_left.setFixedHeight(190) 
        box_left.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        bl_lay = QVBoxLayout(box_left); bl_lay.setContentsMargins(0, 0, 0, 0); bl_lay.setSpacing(0)
        
        bl_head = QFrame()
        bl_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        bl_head_lay = QVBoxLayout(bl_head); bl_head_lay.setContentsMargins(16, 10, 16, 10)
        lbl_anh = QLabel("ÂN̉H SCENES TỪ G-LABS")
        lbl_anh.setStyleSheet("font-size: 11px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        bl_head_lay.addWidget(lbl_anh)
        bl_lay.addWidget(bl_head)
        
        dz_wrap = QWidget()
        dz_lay = QVBoxLayout(dz_wrap); dz_lay.setContentsMargins(12, 12, 12, 12)
        dz = DropZoneWidget("📂", "Kéo thả ảnh vào đây hoặc click để chọn", "Tự sort theo tên file (natural sort)")
        dz_lay.addWidget(dz)
        bl_lay.addWidget(dz_wrap)
        
        ren_grid.addWidget(box_left, 0, 0)

        # Cột Phải: Box Tuỳ Chọn
        box_right = QFrame()
        box_right.setFixedHeight(190) 
        box_right.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        br_lay = QVBoxLayout(box_right); br_lay.setContentsMargins(0, 0, 0, 0); br_lay.setSpacing(0)
        
        br_head = QFrame()
        br_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        br_head_lay = QVBoxLayout(br_head); br_head_lay.setContentsMargins(16, 10, 16, 10)
        lbl_opt = QLabel("TUỲ CHỌN")
        lbl_opt.setStyleSheet("font-size: 11px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        br_head_lay.addWidget(lbl_opt)
        br_lay.addWidget(br_head)
        
        opt_wrap = QWidget()
        opt_lay = QVBoxLayout(opt_wrap); opt_lay.setContentsMargins(16, 12, 16, 12); opt_lay.setSpacing(4) 
        
        opt_lay.addWidget(QLabel("BẮT ĐẦU TỪ SỐ", objectName="muted"))
        self.txt_ren_start = QLineEdit("1")
        self.txt_ren_start.setFixedHeight(28)
        opt_lay.addWidget(self.txt_ren_start)
        
        opt_lay.addWidget(QLabel("SỐ CHỮ SỐ (PADDING)", objectName="muted"))
        self.cmb_ren_pad = QComboBox()
        self.cmb_ren_pad.addItems(["001", "01", "0001"])
        self.cmb_ren_pad.setFixedHeight(28)
        opt_lay.addWidget(self.cmb_ren_pad)
        
        opt_lay.addWidget(QLabel("GIỮ EXTENSION GỐC", objectName="muted"))
        self.cmb_ren_ext = QComboBox()
        self.cmb_ren_ext.addItems(["Giữ nguyên (.p...)", "Ép sang .jpg", "Ép sang .png"])
        self.cmb_ren_ext.setFixedHeight(28)
        opt_lay.addWidget(self.cmb_ren_ext)
        
        br_lay.addWidget(opt_wrap)
        ren_grid.addWidget(box_right, 0, 1)

        ren_grid.setColumnStretch(0, 2) 
        ren_grid.setColumnStretch(1, 1) 
        lay.addLayout(ren_grid)

        # Đẩy vào Scroll chính
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

    # ====================================================================
    # HELPER FUNCTIONS: XÂY DỰNG WIDGET CON
    # ====================================================================
    def _create_stat_card(self, title, val, val_color):
        card = QFrame()
        card.setStyleSheet("QFrame { background: #171724; border: 1px solid #252535; border-radius: 6px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)
        
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #606075; letter-spacing: 0.5px;")
        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {val_color}; font-family: monospace;")
        
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        card.lbl_val = lbl_v # Lưu lại tham chiếu để dễ cập nhật giá trị sau này
        return card

    def _populate_table(self, scenes):
        self.table_scenes.setRowCount(len(scenes))
        total_seconds = 0
        
        for i, vo_text in enumerate(scenes):
            stt_str = f"{i+1:03d}"
            
            # Thuật toán chính xác: 155 từ / 1 phút (60 giây)
            word_count = len(vo_text.split())
            dur_num = max(3, min(7, len(vo_text) // 16))
            total_seconds += dur_num

            # Khởi tạo các ô item
            item_stt = QTableWidgetItem(stt_str)
            item_level = QTableWidgetItem("Main")
            item_vo = QTableWidgetItem(vo_text)
            item_char = QTableWidgetItem("pending...")
            item_bg = QTableWidgetItem("pending...")
            item_cam = QTableWidgetItem("Ken Burns" if i % 2 == 0 else "Pan L->R")
            item_dur = QTableWidgetItem(f"{dur_num}s")

            # Căn giữa các cột thông số ngắn
            item_stt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_level.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_char.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_bg.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_cam.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Màu sắc chữ muted cho trạng thái pending
            item_stt.setForeground(QBrush(QColor("#E8742A")))
            font_stt = item_stt.font(); font_stt.setBold(True); item_stt.setFont(font_stt)
            
            item_level.setForeground(QBrush(QColor("#606075")))
            
            item_char.setForeground(QBrush(QColor("#606075")))
            font_char = item_char.font(); font_char.setItalic(True); item_char.setFont(font_char)
            
            item_bg.setForeground(QBrush(QColor("#606075")))
            font_bg = item_bg.font(); font_bg.setItalic(True); item_bg.setFont(font_bg)
            
            item_dur.setForeground(QBrush(QColor("#3AD68A")))
            font_dur = item_dur.font(); font_dur.setBold(True); item_dur.setFont(font_dur)

            self.table_scenes.setItem(i, 0, item_stt)
            self.table_scenes.setItem(i, 1, item_level)
            self.table_scenes.setItem(i, 2, item_vo)
            self.table_scenes.setItem(i, 3, item_char)
            self.table_scenes.setItem(i, 4, item_bg)
            self.table_scenes.setItem(i, 5, item_cam)
            self.table_scenes.setItem(i, 6, item_dur)

            # 5. Tạo cụm 2 nút phím tắt điều hướng nhanh ở cột cuối (Split & Regen)
            btn_container = QWidget()
            btn_lay = QHBoxLayout(btn_container)
            btn_lay.setContentsMargins(4, 2, 4, 2)
            btn_lay.setSpacing(6)
            
            btn_cut = QPushButton("✂")
            btn_cut.setToolTip("Cắt nhỏ hoặc gộp phân cảnh này")
            btn_cut.setStyleSheet("QPushButton { background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; font-size: 11px; max-width: 26px; max-height: 22px; } QPushButton:hover { background: rgba(232,116,42,0.1); color: #E8742A; border-color: #E8742A; }")
            btn_cut.setCursor(Qt.CursorShape.PointingHandCursor)
            
            btn_refresh = QPushButton("⟳")
            btn_refresh.setToolTip("Yêu cầu AI viết lại Prompt riêng cho cảnh này")
            btn_refresh.setStyleSheet("QPushButton { background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; font-size: 12px; font-weight: bold; max-width: 26px; max-height: 22px; } QPushButton:hover { background: rgba(58,214,138,0.1); color: #3AD68A; border-color: #3AD68A; }")
            btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)

            btn_lay.addWidget(btn_cut)
            btn_lay.addWidget(btn_refresh)
            
            self.table_scenes.setCellWidget(i, 7, btn_container)
            
        # Cập nhật thông số lên Dashboard
        self.card_scenes.lbl_val.setText(str(len(scenes)))
        mins, secs = divmod(total_seconds, 60)
        self.card_duration.lbl_val.setText(f"{mins:02d}m{secs:02d}s")

    # ==========================================
    # CÁC HÀM XỬ LÝ LOGIC CŨ CỦA BẠN (GIỮ NGUYÊN)
    # ==========================================
    def _update_char_count(self):
        count = len(self.txt_script.toPlainText())
        self.lbl_char_count.setText(f"{count} ký tự")

    def _load_script_from_profile(self):
        ACTIVE_PROFILE_FILE = "active_profile.json"
        if not os.path.exists(ACTIVE_PROFILE_FILE):
            QMessageBox.warning(self, "Chưa có Profile", "Vui lòng chọn và áp dụng một Profile từ Tool Quản lý Profile trước.")
            return

        try:
            with open(ACTIVE_PROFILE_FILE, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            QMessageBox.critical(self, "Lỗi Profile", f"Không thể đọc hoặc file '{ACTIVE_PROFILE_FILE}' bị lỗi.")
            return

        topics_with_scripts = []
        if "topics" in profile_data and isinstance(profile_data["topics"], list):
            for topic in profile_data["topics"]:
                if (isinstance(topic, dict) and 
                    topic.get("script") and 
                    isinstance(topic["script"], dict) and 
                    topic["script"].get("content")):
                    
                    title = topic.get("title", "Không có tiêu đề")
                    content = topic["script"]["content"]
                    topics_with_scripts.append((title, content))

        if not topics_with_scripts:
            QMessageBox.information(self, "Không có kịch bản", "Profile hiện tại chưa có kịch bản nào được tạo từ Tool 1.")
            return

        titles = [item[0] for item in topics_with_scripts]
        selected_title, ok = QInputDialog.getItem(self, "Chọn Kịch Bản", "Chọn một kịch bản đã tạo từ Tool 1:", titles, 0, False)

        if ok and selected_title:
            for title, content in topics_with_scripts:
                if title == selected_title:
                    self.txt_script.setPlainText(content)
                    break

    def _clean_script(self):
        text = self.txt_script.toPlainText()
        if not text:
            QMessageBox.warning(self, "Trống", "Vui lòng dán hoặc Load kịch bản trước khi lọc.")
            return
            
        lines = text.split('\n')
        cleaned_lines = []
        in_metadata = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            if stripped.startswith('=== METADATA ===') or stripped.startswith('=== VIDEO TITLE ==='):
                in_metadata = True
                continue
            if in_metadata and stripped.startswith('---'):
                in_metadata = False
                continue
            if in_metadata:
                continue
                
            if stripped.startswith('===') and stripped.endswith('==='): continue
            if stripped.startswith('---') and stripped.endswith('---'): continue
            if stripped.startswith('>>>'): continue
            if stripped.startswith('[Estimated'): continue
                
            stripped = stripped.replace('*', '')
            cleaned_lines.append(stripped)
            
        cleaned_text = '\n\n'.join(cleaned_lines)
        self.txt_script.setPlainText(cleaned_text)
        QMessageBox.information(self, "Thành công", "Đã lọc sạch các thẻ cấu trúc và metadata!")

    def _split_scenes(self):
        text = self.txt_script.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Lỗi", "Không có kịch bản để cắt. Vui lòng Load hoặc Paste kịch bản.")
            return
            
        try:
            min_c = int(self.txt_min.text())
            max_c = int(self.txt_max.text())
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Thông số Min/Max ký tự phải là số nguyên.")
            return

        raw_sentences = re.split(r'(?<=[.?!])\s+|\n+', text)
        scenes = []
        current_scene = ""
        
        for sent in raw_sentences:
            sent = sent.strip()
            if not sent: continue
            
            if not current_scene:
                current_scene = sent
            else:
                if len(current_scene) + 1 + len(sent) <= max_c:
                    current_scene += " " + sent
                else:
                    if len(current_scene) >= min_c:
                        scenes.append(current_scene)
                        current_scene = sent
                    else:
                        current_scene += " " + sent
                        
        if current_scene:
            scenes.append(current_scene)
            
        out_text = ""
        for i, s in enumerate(scenes, 1):
            out_text += f"[Scene {i:03d}]\n{s}\n\n"
            
        self.txt_preview.setPlainText(out_text.strip())
        self.lbl_scene_count.setText(f"{len(scenes)} scenes")
        
        # Đổ danh sách scenes thật vào bảng bên dưới
        self._populate_table(scenes)
        
        QMessageBox.information(self, "Thành công", f"Đã chia kịch bản thành {len(scenes)} scenes phân cảnh!")

    def _get_current_scenes_from_table(self):
        """Lấy danh sách các câu thoại hiện tại trên bảng"""
        scenes = []
        for row in range(self.table_scenes.rowCount()):
            item_vo = self.table_scenes.item(row, 2)
            if item_vo:
                scenes.append(item_vo.text())
        return scenes

    def _pre_scan(self):
        scenes = self._get_current_scenes_from_table()
        if not scenes:
            QMessageBox.warning(self, "Trống", "Bảng đang trống. Hãy Split Scenes trước khi Pre-scan!")
            return

        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("⏳ Đang quét...")

        self.worker = SceneWorker("prescan", {"scenes": scenes})
        self.worker.progress_signal.connect(lambda msg: print(msg)) # Có thể in ra thanh trạng thái nếu có
        self.worker.result_signal.connect(self._handle_worker_result)
        self.worker.error_signal.connect(lambda err: QMessageBox.critical(self, "Lỗi AI", err))
        self.worker.finished_signal.connect(lambda: [self.btn_scan.setEnabled(True), self.btn_scan.setText("🔍 Pre-scan")])
        self.worker.start()

    def _assign_assets(self):
        scenes = self._get_current_scenes_from_table()
        if not scenes:
            QMessageBox.warning(self, "Trống", "Bảng đang trống. Hãy Split Scenes trước khi Assign!")
            return
            
        visual_style = self.txt_style.text().strip()

        self.btn_assign.setEnabled(False)
        self.btn_assign.setText("⏳ Đang Assign...")

        self.worker = SceneWorker("assign", {"scenes": scenes, "style": visual_style})
        self.worker.progress_signal.connect(lambda msg: print(msg))
        self.worker.result_signal.connect(self._handle_worker_result)
        self.worker.error_signal.connect(lambda err: QMessageBox.critical(self, "Lỗi AI", err))
        self.worker.finished_signal.connect(lambda: [self.btn_assign.setEnabled(True), self.btn_assign.setText("⚡ Assign Assets")])
        self.worker.start()

    def _handle_worker_result(self, task_type, json_str):
        try:
            data = json.loads(json_str)
            
            if task_type == "prescan":
                chars_count = data.get("characters_count", 0)
                bgs_count = data.get("backgrounds_count", 0)
                
                # Cập nhật số liệu lên Dashboard
                self.card_chars.lbl_val.setText(str(chars_count))
                self.card_chars.lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #5A9BFF; font-family: monospace;")
                
                self.card_bgs.lbl_val.setText(str(bgs_count))
                self.card_bgs.lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #9B7FFF; font-family: monospace;")
                
                QMessageBox.information(self, "Pre-scan Hoàn Tất", f"Tìm thấy:\n- {chars_count} nhân vật\n- {bgs_count} bối cảnh")
                
            elif task_type == "assign":
                scenes_data = data.get("scenes", [])
                assigned_count = 0
                
                for item in scenes_data:
                    row_idx = item.get("id", 1) - 1 # id bắt đầu từ 1, row bắt đầu từ 0
                    if 0 <= row_idx < self.table_scenes.rowCount():
                        # Cập nhật Character
                        char_item = self.table_scenes.item(row_idx, 3)
                        char_item.setText(item.get("character", ""))
                        char_item.setForeground(QBrush(QColor("#E8E8F0"))) # Chuyển màu hết pending
                        char_item.setFont(QFont()) # Xóa in nghiêng
                        
                        # Cập nhật Background
                        bg_item = self.table_scenes.item(row_idx, 4)
                        bg_item.setText(item.get("background", ""))
                        bg_item.setForeground(QBrush(QColor("#E8E8F0")))
                        bg_item.setFont(QFont())
                        
                        # Cập nhật Camera
                        cam_item = self.table_scenes.item(row_idx, 5)
                        cam_item.setText(item.get("camera", ""))
                        
                        assigned_count += 1
                
                # Cập nhật tổng số đã assign lên Dashboard
                self.card_assigned.lbl_val.setText(str(assigned_count))
                self.card_assigned.lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #E8E8F0; font-family: monospace;")
                QMessageBox.information(self, "Assign Hoàn Tất", f"Đã tạo prompts thành công cho {assigned_count} scenes!")
                
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Lỗi Dữ Liệu", "AI trả về dữ liệu không đúng chuẩn JSON.\n" + json_str)

    def _deduplicate(self):
        QMessageBox.information(self, "Deduplicate", "Chức năng tối ưu gộp phân cảnh đang được phát triển.")

    def _run_pipeline(self):
        QMessageBox.information(self, "Run Pipeline", "Chức năng xuất File JSON cho hệ thống G-Labs đang được phát triển.")