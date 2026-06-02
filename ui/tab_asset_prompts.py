from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt

class AssetPromptsTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 2, 15, 2)
        
        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
        vbox_h = QVBoxLayout()
        
        lbl_title = QLabel("Asset Prompt Generator")
        lbl_title.setObjectName("page_title")
        vbox_h.addWidget(lbl_title)
        
        lbl_desc = QLabel("Tạo G-Labs prompts cho character reference sheets và background reference sheets")
        lbl_desc.setObjectName("page_desc")
        vbox_h.addWidget(lbl_desc)
        
        header.addLayout(vbox_h)
        header.addStretch()
        
        lbl_badge = QLabel("Tool 3")
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
        lay.setSpacing(4)

        # --- WORKFLOW HINT ---
        hint_text = ("💡 <b>KHI NÀO DÙNG Tool 3?</b> Chỉ dùng khi setup kênh mới - tạo reference sheets cho nhân vật và bối cảnh. "
                     "Sau đó dùng Tool 2 tab 'G-Labs Prompts' cho production hàng ngày.")
        hint = QLabel(hint_text)
        hint.setStyleSheet("background: rgba(232,116,42,0.06); border: 1px solid rgba(232,116,42,0.15); "
                           "border-radius: 8px; padding: 12px 16px; color: #E8742A; line-height: 1.5; font-size: 13px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # ==========================================
        # 3. MASCOT POSE LIBRARY
        # ==========================================
        lay.addWidget(QLabel("🎭 MASCOT POSE LIBRARY - HYBRID: GEN 50 PROMPTS + PASTE G-LABS PRM + UPLOAD PNG LIB (PHASE 1A)", objectName="section_label"))
        
        mascot_grid = QGridLayout()
        mascot_grid.addWidget(QLabel("MASCOT NAME (KEBAB-CASE, DÙNG LÀM PREFIX FILE)", objectName="muted"), 0, 0)
        mascot_grid.addWidget(QLabel("REFERENCE IMAGE (1 ẢNH CANONICAL MASCOT, PNG/JPG)", objectName="muted"), 0, 1)

        self.txt_mascot_name = QLineEdit("long-mascot")
        mascot_grid.addWidget(self.txt_mascot_name, 1, 0)

        # Nút Choose File
        box_file = QHBoxLayout()
        btn_choose = QPushButton("📁 Choose File"); btn_choose.setObjectName("btn_sec")
        lbl_file = QLabel("No file chosen"); lbl_file.setObjectName("muted")
        box_file.addWidget(btn_choose); box_file.addWidget(lbl_file); box_file.addStretch()
        mascot_grid.addLayout(box_file, 1, 1)
        lay.addLayout(mascot_grid)

        lay.addWidget(QLabel("STYLE DESCRIPTION (MÔ TẢ VISUAL MASCOT - MÀU, ĐẶC TRƯNG, ART STYLE)", objectName="muted"))
        self.txt_mascot_style = QTextEdit()
        self.txt_mascot_style.setPlaceholderText("Hand-drawn 2D cartoon goat character...")
        self.txt_mascot_style.setFixedHeight(40)
        lay.addWidget(self.txt_mascot_style)

        mascot_btns = QHBoxLayout()
        btn_gen_pose = QPushButton("✨ Gen 50 Pose Prompts (Haicu)"); btn_gen_pose.setObjectName("btn_sec"); btn_gen_pose.setStyleSheet("color: #9B7FFF; border-color: rgba(155,127,255,0.4);")
        btn_copy_pose = QPushButton("📄 Copy All"); btn_copy_pose.setObjectName("btn_sec")
        btn_export_pose = QPushButton("💾 Export .txt"); btn_export_pose.setObjectName("btn_sec")
        
        mascot_btns.addWidget(btn_gen_pose); mascot_btns.addWidget(btn_copy_pose); mascot_btns.addWidget(btn_export_pose)
        mascot_btns.addStretch()
        lay.addLayout(mascot_btns)

        # Line phân cách
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setStyleSheet("background: #252535; margin: 10px 0px;")
        lay.addWidget(line1)

        # ==========================================
        # 4. GENERAL INFO
        # ==========================================
        info_lay = QHBoxLayout()
        
        def create_info_col(title, text):
            v = QVBoxLayout()
            v.addWidget(QLabel(title, objectName="muted"))
            txt = QLineEdit(text)
            v.addWidget(txt)
            info_lay.addLayout(v)
            return txt

        self.txt_visual = create_info_col("VISUAL STYLE", "Crayon Capital — Dark")
        self.txt_channel_desc = create_info_col("CHANNEL DESCRIPTION", "Dark educational POV stories...")
        self.txt_topic = create_info_col("VIDEO TOPIC", "POV: Corrupt FBI Agent...")
        lay.addLayout(info_lay)

        # ==========================================
        # 5. STYLE PROMPTS (EDITABLE)
        # ==========================================
        style_head = QHBoxLayout()
        style_head.addWidget(QLabel("🎨 STYLE PROMPTS (EDITABLE)", objectName="section_label"))
        style_head.addStretch()
        
        btn_reset = QPushButton("Reset"); btn_reset.setObjectName("btn_sec"); btn_reset.setFixedHeight(30)
        btn_save = QPushButton("Save Custom"); btn_save.setObjectName("btn_sec"); btn_save.setFixedHeight(30)
        style_head.addWidget(btn_reset); style_head.addWidget(btn_save)
        lay.addLayout(style_head)

        # Character & Background Styles
        style_body = QHBoxLayout()
        
        v_char = QVBoxLayout()
        v_char.addWidget(QLabel("CHARACTER STYLE", objectName="muted"), alignment=Qt.AlignmentFlag.AlignTop)
        self.txt_char_style = QTextEdit()
        self.txt_char_style.setText("2D cartoon character, bold thick black ink outlines, perfectly round WHITE circle head (pure white, NOT skin-colored), small simple black dot eyes, thin simple eyebrow lines...")
        self.txt_char_style.setStyleSheet("color: #3AD68A;") # Chữ màu xanh lá
        self.txt_char_style.setFixedHeight(60)
        v_char.addWidget(self.txt_char_style)
        style_body.addLayout(v_char)

        v_bg = QVBoxLayout()
        v_bg.addWidget(QLabel("BACKGROUND STYLE", objectName="muted"), alignment=Qt.AlignmentFlag.AlignTop)
        self.txt_bg_style = QTextEdit()
        self.txt_bg_style.setText("2D cartoon background illustration, bold black outlines, detailed interior or exterior environment with depth and atmosphere, muted dark color palette browns grays...")
        self.txt_bg_style.setStyleSheet("color: #5A9BFF;") # Chữ màu xanh dương
        self.txt_bg_style.setFixedHeight(60)
        v_bg.addWidget(self.txt_bg_style)
        style_body.addLayout(v_bg)
        
        lay.addLayout(style_body)

        lay.addWidget(QLabel("SCENE STYLE (PROMPT NGẮN CHO TOOL 2 -> NANO BANANA PRO)", objectName="muted"))
        self.txt_scene_style = QTextEdit("2D cartoon style, bold thick black ink outlines, flat color fills, hand-drawn illustration\n\nPreset: Crayon Capital (Dark)")
        self.txt_scene_style.setFixedHeight(60)
        lay.addWidget(self.txt_scene_style)

        # ==========================================
        # 6. CHARACTERS & BACKGROUNDS LISTS
        # ==========================================
        lists_lay = QHBoxLayout()
        
        # Characters Box
        box_char = QFrame()
        box_char.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        l_char = QVBoxLayout(box_char)
        l_char.addWidget(QLabel("🔴 CHARACTERS", objectName="section_label"))
        self.txt_characters = QTextEdit("agent-young\nagent-corrupted\nharmon-boss")
        self.txt_characters.setStyleSheet("border: none; background: transparent; font-family: 'Space Mono', monospace; color: #E8E8F0;")
        self.txt_characters.setFixedHeight(70)
        l_char.addWidget(self.txt_characters)
        lists_lay.addWidget(box_char)

        # Backgrounds Box
        box_bg = QFrame()
        box_bg.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        l_bg = QVBoxLayout(box_bg)
        l_bg.addWidget(QLabel("🔵 BACKGROUNDS", objectName="section_label"))
        self.txt_backgrounds = QTextEdit("fbi-office-clean\ndark-office-night\nhome-kitchen")
        self.txt_backgrounds.setStyleSheet("border: none; background: transparent; font-family: 'Space Mono', monospace; color: #E8E8F0;")
        self.txt_backgrounds.setFixedHeight(70)
        l_bg.addWidget(self.txt_backgrounds)
        lists_lay.addWidget(box_bg)

        lay.addLayout(lists_lay)

        # ==========================================
        # 7. CHARACTER REFERENCE IMAGES (VISION API)
        # ==========================================
        vision_head = QHBoxLayout()
        vision_head.addWidget(QLabel("📷 CHARACTER REFERENCE IMAGES (VISION API)", objectName="section_label"))
        vision_head.addStretch()
        
        vision_head.addWidget(QLabel("0 ảnh", objectName="muted"))
        btn_clear = QPushButton("Xóa hết"); btn_clear.setObjectName("btn_sec"); btn_clear.setFixedHeight(28)
        vision_head.addWidget(btn_clear)
        lay.addLayout(vision_head)

        box_vision = QFrame()
        box_vision.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        v_vision = QVBoxLayout(box_vision)
        
        lbl_v_desc = QLabel("Upload ảnh nhân vật → Claude Vision sẽ <b>phân tích visual</b> để gen prompt chính xác hơn.<br>Chọn tên nhân vật từ list → upload ảnh tương ứng. <span style='color: #E8742A; font-weight: bold;'>Hỗ trợ: PNG, JPG, WEBP (max 5MB)</span>")
        lbl_v_desc.setStyleSheet("border: none; color: #606075; line-height: 1.5;")
        v_vision.addWidget(lbl_v_desc)
        
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet("background: #252535; border: none; margin: 8px 0;")
        v_vision.addWidget(line2)

        action_vision = QHBoxLayout()
        
        v_sel = QVBoxLayout()
        v_sel.addWidget(QLabel("CHỌN NHÂN VẬT", objectName="muted"))
        self.cmb_characters = QComboBox()
        self.cmb_characters.addItem("— Chọn từ danh sách Characters —")
        self.cmb_characters.addItems(["agent-young", "agent-corrupted", "harmon-boss"])
        v_sel.addWidget(self.cmb_characters)
        action_vision.addLayout(v_sel, stretch=4)
        
        v_up = QVBoxLayout()
        v_up.addStretch()
        btn_upload_vision = QPushButton("📁 Upload ảnh"); btn_upload_vision.setObjectName("btn_sec")
        btn_upload_vision.setStyleSheet("color: #E8E8F0; background: #171724;")
        v_up.addWidget(btn_upload_vision)
        action_vision.addLayout(v_up, stretch=1)
        
        v_vision.addLayout(action_vision)
        lay.addWidget(box_vision)

        # Đẩy nội dung vào scroll
        lay.addStretch()
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        # ==========================================
        # 8. BOTTOM ACTIONS
        # ==========================================
        act_lay = QHBoxLayout()
        
        btn_gen_all = QPushButton("⚡ Generate All Prompts", objectName="btn_primary")
        btn_gen_all.setFixedWidth(220)
        act_lay.addWidget(btn_gen_all)

        btn_style_ref = QPushButton("🧠 Style Reference", objectName="btn_sec")
        btn_style_ref.setFixedWidth(160)
        act_lay.addWidget(btn_style_ref)

        act_lay.addStretch()
        main_lay.addLayout(act_lay)