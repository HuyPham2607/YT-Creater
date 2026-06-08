from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QFrame, QMessageBox,
                             QApplication, QFileDialog, QTabBar, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from threads.asset_prompt_worker import generate_all_prompts


class AssetPromptRunner(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            result = generate_all_prompts(
                prescan_data=self.config.get("prescan_data", {}),
                char_style=self.config.get("char_style", ""),
                bg_style=self.config.get("bg_style", ""),
                scene_style=self.config.get("scene_style", ""),
                channel_desc=self.config.get("channel_desc", ""),
                topic=self.config.get("topic", ""),
                channel_dna=self.config.get("channel_dna", ""),
                style_guide=self.config.get("style_guide", ""),
                on_progress=self.progress_signal.emit,
            )
            self.result_signal.emit(result or {"characters": {}, "backgrounds": {}})
        except Exception as error:
            self.error_signal.emit(str(error))

class AssetPromptsTab(QWidget):
    request_load_tool2 = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._prescan_data = {}
        self._generated_prompts = {"characters": {}, "backgrounds": {}}
        self.style_ref_text = ""
        self.style_content = ""
        self.dna_content = ""
        self.worker = None
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 2, 15, 10) # T膬ng margin bottom m峄檛 ch煤t 膽峄?n煤t th峄?
        
        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
        vbox_h = QVBoxLayout()
        
        lbl_title = QLabel("Asset Prompt Generator")
        lbl_title.setObjectName("page_title")
        vbox_h.addWidget(lbl_title)
        
        lbl_desc = QLabel("T岷 G-Labs prompts cho character reference sheets v脿 background reference sheets")
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
        # B峄?vi峄乶 c峄 ScrollArea 膽峄?nh矛n ph岷硁g v脿 m瓢峄 h啤n
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }") 
        
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(4)

        # --- WORKFLOW HINT ---
        hint_text = ("馃挕 <b>KHI N脌O D脵NG Tool 3?</b> Ch峄?d霉ng khi setup k锚nh m峄沬 - t岷 reference sheets cho nh芒n v岷璽 v脿 b峄慽 c岷h. "
                     "Sau 膽贸 d霉ng Tool 2 tab 'G-Labs Prompts' cho production h脿ng ng脿y.")
        hint = QLabel(hint_text)
        hint.setStyleSheet("background: rgba(232,116,42,0.06); border: 1px solid rgba(232,116,42,0.15); "
                           "border-radius: 8px; padding: 12px 16px; color: #E8742A; line-height: 1.5; font-size: 13px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # ==========================================
        # 3. MASCOT POSE LIBRARY
        # ==========================================
        lay.addWidget(QLabel("馃幁 MASCOT POSE LIBRARY - HYBRID: GEN 50 PROMPTS + PASTE G-LABS PRM + UPLOAD PNG LIB (PHASE 1A)", objectName="section_label"))
        
        mascot_grid = QGridLayout()
        mascot_grid.addWidget(QLabel("MASCOT NAME (KEBAB-CASE, D脵NG L脌M PREFIX FILE)", objectName="muted"), 0, 0)
        mascot_grid.addWidget(QLabel("REFERENCE IMAGE (1 岷H CANONICAL MASCOT, PNG/JPG)", objectName="muted"), 0, 1)

        self.txt_mascot_name = QLineEdit("long-mascot")
        mascot_grid.addWidget(self.txt_mascot_name, 1, 0)

        # N煤t Choose File
        box_file = QHBoxLayout()
        btn_choose = QPushButton("馃搧 Choose File"); btn_choose.setObjectName("btn_sec")
        lbl_file = QLabel("No file chosen"); lbl_file.setObjectName("muted")
        box_file.addWidget(btn_choose); box_file.addWidget(lbl_file); box_file.addStretch()
        mascot_grid.addLayout(box_file, 1, 1)
        lay.addLayout(mascot_grid)

        lay.addWidget(QLabel("STYLE DESCRIPTION (M脭 T岷?VISUAL MASCOT - M脌U, 膼岷禖 TR漂NG, ART STYLE)", objectName="muted"))
        self.txt_mascot_style = QTextEdit()
        self.txt_mascot_style.setPlaceholderText("Hand-drawn 2D cartoon goat character...")
        self.txt_mascot_style.setFixedHeight(40)
        lay.addWidget(self.txt_mascot_style)

        mascot_btns = QHBoxLayout()
        btn_gen_pose = QPushButton("鉁?Gen 50 Pose Prompts (Haicu)"); btn_gen_pose.setObjectName("btn_sec"); btn_gen_pose.setStyleSheet("color: #9B7FFF; border-color: rgba(155,127,255,0.4);")
        btn_copy_pose = QPushButton("馃搫 Copy All"); btn_copy_pose.setObjectName("btn_sec")
        btn_export_pose = QPushButton("馃捑 Export .txt"); btn_export_pose.setObjectName("btn_sec")
        
        mascot_btns.addWidget(btn_gen_pose); mascot_btns.addWidget(btn_copy_pose); mascot_btns.addWidget(btn_export_pose)
        mascot_btns.addStretch()
        lay.addLayout(mascot_btns)

        # Line ph芒n c谩ch
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

        self.txt_visual = create_info_col("VISUAL STYLE", "Crayon Capital 鈥?Dark")
        self.txt_channel_desc = create_info_col("CHANNEL DESCRIPTION", "Dark educational POV stories...")
        self.txt_topic = create_info_col("VIDEO TOPIC", "POV: Corrupt FBI Agent...")
        lay.addLayout(info_lay)

        # ==========================================
        # 5. STYLE PROMPTS (EDITABLE)
        # ==========================================
        style_head = QHBoxLayout()
        style_head.addWidget(QLabel("馃帹 STYLE PROMPTS (EDITABLE)", objectName="section_label"))
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
        self.txt_char_style.setStyleSheet("color: #3AD68A;") # Ch峄?m脿u xanh l谩
        self.txt_char_style.setFixedHeight(60)
        v_char.addWidget(self.txt_char_style)
        style_body.addLayout(v_char)

        v_bg = QVBoxLayout()
        v_bg.addWidget(QLabel("BACKGROUND STYLE", objectName="muted"), alignment=Qt.AlignmentFlag.AlignTop)
        self.txt_bg_style = QTextEdit()
        self.txt_bg_style.setText("2D cartoon background illustration, bold black outlines, detailed interior or exterior environment with depth and atmosphere, muted dark color palette browns grays...")
        self.txt_bg_style.setStyleSheet("color: #5A9BFF;") # Ch峄?m脿u xanh d瓢啤ng
        self.txt_bg_style.setFixedHeight(60)
        v_bg.addWidget(self.txt_bg_style)
        style_body.addLayout(v_bg)
        
        lay.addLayout(style_body)

        lay.addWidget(QLabel("SCENE STYLE (PROMPT NG岷甆 CHO TOOL 2 -> NANO BANANA PRO)", objectName="muted"))
        self.txt_scene_style = QTextEdit("2D cartoon style, bold thick black ink outlines, flat color fills, hand-drawn illustration\n\nPreset: Crayon Capital (Dark)")
        self.txt_scene_style.setFixedHeight(60)
        lay.addWidget(self.txt_scene_style)

        # ==========================================
        # 6. CHARACTERS & BACKGROUNDS LISTS
        # ==========================================
        lists_header = QHBoxLayout()
        lists_header.addWidget(QLabel("馃搵 DANH S脕CH T脌I NGUY脢N (ASSETS)", objectName="section_label"))
        lists_header.addStretch()
        self.btn_load_tool2 = QPushButton("馃搨 Load Data t峄?Tool 2")
        self.btn_load_tool2.setObjectName("btn_sec")
        self.btn_load_tool2.clicked.connect(lambda: self.request_load_tool2.emit())
        lists_header.addWidget(self.btn_load_tool2)
        lay.addLayout(lists_header)
        
        lists_lay = QHBoxLayout()
        
        # Characters Box
        box_char = QFrame()
        box_char.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        l_char = QVBoxLayout(box_char)
        l_char.addWidget(QLabel("馃敶 CHARACTERS", objectName="section_label"))
        self.txt_characters = QTextEdit("agent-young\nagent-corrupted\nharmon-boss")
        self.txt_characters.setStyleSheet("border: none; background: transparent; font-family: 'Space Mono', monospace; color: #E8E8F0;")
        self.txt_characters.setFixedHeight(70)
        l_char.addWidget(self.txt_characters)
        lists_lay.addWidget(box_char)

        # Backgrounds Box
        box_bg = QFrame()
        box_bg.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        l_bg = QVBoxLayout(box_bg)
        l_bg.addWidget(QLabel("馃數 BACKGROUNDS", objectName="section_label"))
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
        vision_head.addWidget(QLabel("馃摲 CHARACTER REFERENCE IMAGES (VISION API)", objectName="section_label"))
        vision_head.addStretch()
        
        vision_head.addWidget(QLabel("0 岷h", objectName="muted"))
        btn_clear = QPushButton("X贸a h岷縯"); btn_clear.setObjectName("btn_sec"); btn_clear.setFixedHeight(28)
        vision_head.addWidget(btn_clear)
        lay.addLayout(vision_head)

        box_vision = QFrame()
        box_vision.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        v_vision = QVBoxLayout(box_vision)
        
        lbl_v_desc = QLabel("Upload 岷h nh芒n v岷璽 鈫?Claude Vision s岷?<b>ph芒n t铆ch visual</b> 膽峄?gen prompt ch铆nh x谩c h啤n.<br>Ch峄峮 t锚n nh芒n v岷璽 t峄?list 鈫?upload 岷h t瓢啤ng 峄﹏g. <span style='color: #E8742A; font-weight: bold;'>H峄?tr峄? PNG, JPG, WEBP (max 5MB)</span>")
        lbl_v_desc.setStyleSheet("border: none; color: #606075; line-height: 1.5;")
        v_vision.addWidget(lbl_v_desc)
        
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setStyleSheet("background: #252535; border: none; margin: 8px 0;")
        v_vision.addWidget(line2)

        action_vision = QHBoxLayout()
        
        v_sel = QVBoxLayout()
        v_sel.addWidget(QLabel("CH峄孨 NH脗N V岷琓", objectName="muted"))
        self.cmb_characters = QComboBox()
        self.cmb_characters.addItem("-- Select from Characters --")
        self.cmb_characters.addItems(["agent-young", "agent-corrupted", "harmon-boss"])
        v_sel.addWidget(self.cmb_characters)
        action_vision.addLayout(v_sel, stretch=4)
        
        v_up = QVBoxLayout()
        v_up.addStretch()
        btn_upload_vision = QPushButton("馃搧 Upload 岷h"); btn_upload_vision.setObjectName("btn_sec")
        btn_upload_vision.setStyleSheet("color: #E8E8F0; background: #171724;")
        v_up.addWidget(btn_upload_vision)
        action_vision.addLayout(v_up, stretch=1)
        
        v_vision.addLayout(action_vision)
        lay.addWidget(box_vision)

        # 膼岷﹜ n峄檌 dung v脿o scroll
        lay.addStretch()
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        # ==========================================
        # 8. BOTTOM ACTIONS (膼脙 TH脢M STYLE GI峄怤G 岷H TH峄?2)
        # ==========================================
        # T岷 v霉ng container ri锚ng cho Bottom Actions 膽峄?ghim c峄﹏g 峄?膽谩y
        act_container = QWidget()
        act_container.setStyleSheet("background-color: transparent; margin-top: 5px;")
        act_lay = QHBoxLayout(act_container)
        act_lay.setContentsMargins(0, 5, 0, 0)
        
        # N煤t 1: Generate All Prompts (M脿u cam gi峄憂g 岷h)
        self.btn_gen_all = QPushButton("鈿?Generate All Prompts")
        self.btn_gen_all.setFixedWidth(220)
        self.btn_gen_all.setFixedHeight(38)
        self.btn_gen_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen_all.setStyleSheet("""
            QPushButton {
                background-color: #E8742A;
                color: #12121A;
                border: none;
                border-radius: 6px;
                font-weight: 800;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F08542;
            }
        """)
        self.btn_gen_all.clicked.connect(self._generate_all_prompts)
        act_lay.addWidget(self.btn_gen_all)

        # N煤t 2: Style Reference (N煤t ph峄?n峄乶 t峄慽 c贸 vi峄乶 s谩ng m峄?
        self.btn_style_ref = QPushButton("馃 Style Reference")
        self.btn_style_ref.setFixedWidth(160)
        self.btn_style_ref.setFixedHeight(38)
        self.btn_style_ref.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_style_ref.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #E8E8F0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.btn_style_ref.clicked.connect(self._toggle_style_ref)
        act_lay.addWidget(self.btn_style_ref)

        act_lay.addStretch() # 膼岷﹜ 2 n煤t sang l峄?tr谩i
        
        # Th锚m to脿n b峄?container v脿o layout ch铆nh (n岷眒 ngo脿i thanh scroll n锚n s岷?lu么n hi峄噉 峄?膽谩y)
        main_lay.addWidget(act_container)

        # Khung hi峄僴 th峄?Style Ref Prompt (岷╪ m岷穋 膽峄媙h)
        self.txt_style_ref_display = QTextEdit()
        self.txt_style_ref_display.setReadOnly(True)
        self.txt_style_ref_display.setFixedHeight(60)
        self.txt_style_ref_display.setStyleSheet("background: #171724; border: 1px solid rgba(232,116,42,0.5); border-radius: 6px; color: #E8742A; padding: 10px; font-family: 'Space Mono', monospace; font-size: 13px;")
        self.txt_style_ref_display.hide()
        main_lay.addWidget(self.txt_style_ref_display)

        self.output_panel = QFrame()
        self.output_panel.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        out_lay = QVBoxLayout(self.output_panel)
        out_lay.setContentsMargins(10, 8, 10, 10)

        out_head = QHBoxLayout()
        self.lbl_output = QLabel("Asset reference prompts ch瓢a 膽瓢峄 t岷.")
        self.lbl_output.setObjectName("muted")
        out_head.addWidget(self.lbl_output)
        out_head.addStretch()
        self.btn_copy_output = QPushButton("Copy Tab")
        self.btn_copy_output.setObjectName("btn_sec")
        self.btn_copy_output.clicked.connect(self._copy_current_output)
        self.btn_export_output = QPushButton("Export Tab")
        self.btn_export_output.setObjectName("btn_sec")
        self.btn_export_output.clicked.connect(self._export_current_output)
        out_head.addWidget(self.btn_copy_output)
        out_head.addWidget(self.btn_export_output)
        out_lay.addLayout(out_head)

        self.output_tabs = QTabBar()
        for name in ["Characters", "Backgrounds", "All Prompts"]:
            self.output_tabs.addTab(name)
        self.output_tabs.currentChanged.connect(self._on_output_tab_changed)
        self.output_tabs.setStyleSheet("""
            QTabBar::tab { background: #171724; color: #A1A1AA; padding: 7px 14px; border: 1px solid #252535; }
            QTabBar::tab:selected { color: #E8742A; border-bottom: 2px solid #E8742A; }
        """)
        out_lay.addWidget(self.output_tabs)

        self.output_stack = QStackedWidget()
        self.txt_char_output = QTextEdit(); self.txt_char_output.setReadOnly(True)
        self.txt_bg_output = QTextEdit(); self.txt_bg_output.setReadOnly(True)
        self.txt_all_output = QTextEdit(); self.txt_all_output.setReadOnly(True)
        for txt in [self.txt_char_output, self.txt_bg_output, self.txt_all_output]:
            txt.setMinimumHeight(180)
            txt.setStyleSheet("background: #08080D; border: 1px solid #252535; color: #E8E8F0; font-family: 'Space Mono', monospace; font-size: 12px;")
            self.output_stack.addWidget(txt)
        out_lay.addWidget(self.output_stack)
        self.output_panel.hide()
        main_lay.addWidget(self.output_panel)

    def apply_profile(self, profile_data):
        self.style_ref_text = profile_data.get("style_ref", "")
        self.style_content = profile_data.get("style_content", "")
        self.dna_content = profile_data.get("dna_content", "")
        if profile_data.get("char_style"):
            self.txt_char_style.setText(profile_data["char_style"])
        if profile_data.get("bg_style"):
            self.txt_bg_style.setText(profile_data["bg_style"])
        if profile_data.get("scene_style"):
            self.txt_scene_style.setText(profile_data["scene_style"])
        if profile_data.get("visual"):
            self.txt_visual.setText(profile_data["visual"])
        desc_parts = [profile_data.get("name", ""), profile_data.get("niche", ""), profile_data.get("visual", "")]
        desc = " | ".join(part for part in desc_parts if part)
        if desc:
            self.txt_channel_desc.setText(desc)

    def _toggle_style_ref(self):
        if self.txt_style_ref_display.isVisible():
            self.txt_style_ref_display.hide()
        else:
            text = getattr(self, "style_ref_text", "").strip()
            if not text:
                text = "No Style Reference Prompt in the active profile."
            self.txt_style_ref_display.setText(text)
            self.txt_style_ref_display.show()

    def load_assets_data(self, chars, bgs, prescan_data=None):
        if prescan_data:
            self._prescan_data = prescan_data
        if chars:
            self.txt_characters.setPlainText(chars)
            self.cmb_characters.clear()
            self.cmb_characters.addItem("-- Select from Characters --")
            self.cmb_characters.addItems([c for c in chars.split("\n") if c.strip()])
        if bgs:
            self.txt_backgrounds.setPlainText(bgs)

    def _asset_lines(self, txt):
        return [line.strip() for line in txt.splitlines() if line.strip()]

    def _build_minimal_prescan_data(self):
        return {
            "characters": {
                name: {
                    "display_name": name,
                    "description": "Asset name only. Use channel context and topic, but avoid inventing unsupported specifics.",
                    "continuity_traits": "Keep one stable visual identity across reference sheet and scenes.",
                    "scene_state_rules": "Adapt outfit, props, and era only when later scene prompts require it.",
                    "do_not_show": "No readable text, no logos, no copyrighted likeness, no celebrity likeness.",
                    "era_context": "inferred from current video topic",
                    "sample_scenes": [],
                }
                for name in self._asset_lines(self.txt_characters.toPlainText())
            },
            "backgrounds": {
                name: {
                    "display_name": name,
                    "description": "Asset name only. Use channel context and topic, but avoid inventing unsupported specifics.",
                    "continuity_traits": "Keep stable layout, atmosphere, palette, and recurring props.",
                    "scene_state_rules": "Adapt time, lighting, camera angle, and mood while preserving location identity.",
                    "do_not_show": "No characters, no people, no readable text, no logos, no copyrighted marks.",
                    "era_context": "inferred from current video topic",
                    "sample_scenes": [],
                }
                for name in self._asset_lines(self.txt_backgrounds.toPlainText())
            },
        }

    def _generate_all_prompts(self):
        prescan_data = self._prescan_data or self._build_minimal_prescan_data()
        if not prescan_data.get("characters") and not prescan_data.get("backgrounds"):
            QMessageBox.warning(self, "Missing data", "Load Characters/Backgrounds from Tool 2 first.")
            return

        self.btn_gen_all.setEnabled(False)
        self.btn_gen_all.setText("Generating...")
        self.lbl_output.setText("Calling AI to create asset reference prompts...")
        self.output_panel.show()

        self.worker = AssetPromptRunner({
            "prescan_data": prescan_data,
            "char_style": self.txt_char_style.toPlainText(),
            "bg_style": self.txt_bg_style.toPlainText(),
            "scene_style": self.txt_scene_style.toPlainText(),
            "channel_desc": self.txt_channel_desc.text().strip(),
            "topic": self.txt_topic.text().strip(),
            "channel_dna": self.dna_content,
            "style_guide": self.style_content,
        })
        self.worker.progress_signal.connect(self._on_generate_progress)
        self.worker.result_signal.connect(self._on_generate_success)
        self.worker.error_signal.connect(self._on_generate_error)
        self.worker.finished.connect(lambda: [self.btn_gen_all.setEnabled(True), self.btn_gen_all.setText("Generate All Prompts")])
        self.worker.start()

    def _on_generate_progress(self, message):
        self.lbl_output.setText(message)

    def _format_prompt_block(self, prompts):
        return "\n\n".join(f"### {name}\n{prompt}" for name, prompt in prompts.items())

    def _on_generate_success(self, result):
        self._generated_prompts = result
        char_prompts = result.get("characters", {})
        bg_prompts = result.get("backgrounds", {})
        self.txt_char_output.setPlainText(self._format_prompt_block(char_prompts))
        self.txt_bg_output.setPlainText(self._format_prompt_block(bg_prompts))
        all_text = "\n\n".join(
            block for block in [
                self._format_prompt_block(char_prompts),
                self._format_prompt_block(bg_prompts),
            ] if block
        )
        self.txt_all_output.setPlainText(all_text)
        self.lbl_output.setText(f"Done: {len(char_prompts)} character prompts + {len(bg_prompts)} background prompts.")
        self.output_panel.show()

    def _on_generate_error(self, message):
        self.lbl_output.setText("Generate failed.")
        QMessageBox.critical(self, "AI Error", message)

    def _on_output_tab_changed(self, index):
        self.output_stack.setCurrentIndex(index)

    def _current_output_text(self):
        return [self.txt_char_output, self.txt_bg_output, self.txt_all_output][self.output_tabs.currentIndex()].toPlainText().strip()

    def _copy_current_output(self):
        text = self._current_output_text()
        if not text:
            QMessageBox.warning(self, "Empty", "The current tab has no prompt yet.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Copied current tab prompts.")

    def _export_current_output(self):
        text = self._current_output_text()
        if not text:
            QMessageBox.warning(self, "Empty", "The current tab has no prompt yet.")
            return
        names = ["character-reference-prompts.txt", "background-reference-prompts.txt", "all-asset-reference-prompts.txt"]
        path, _ = QFileDialog.getSaveFileName(self, "Export prompts", names[self.output_tabs.currentIndex()], "Text Files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        QMessageBox.information(self, "Exported", path)

