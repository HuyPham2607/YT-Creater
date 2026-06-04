import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QApplication, QFileDialog, QFrame, QSizePolicy, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from ui.components import DropZoneWidget
from threads.topic_worker import TopicWorker

# =======================================================
# COMPONENT: KHUNG TITLE CLICK ĐƯỢC
# =======================================================
class ClickableTitleFrame(QFrame):
    def __init__(self, t_main, t_sub):
        super().__init__()
        self.setObjectName("title_btn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.t_main = t_main
        
        btn_lay = QVBoxLayout(self)
        btn_lay.setContentsMargins(12, 12, 12, 12)
        btn_lay.setSpacing(4)
        
        lbl_main = QLabel(f"<b>{t_main}</b>")
        lbl_main.setWordWrap(True)
        lbl_main.setStyleSheet("background: transparent; border: none; color: #C4C4DC; font-size: 13px;")
        lbl_main.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        lbl_sub = QLabel(t_sub)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("background: transparent; border: none; color: #5A5A7A; font-size: 11px;")
        lbl_sub.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        btn_lay.addWidget(lbl_main)
        btn_lay.addWidget(lbl_sub)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            QApplication.clipboard().setText(self.t_main)
        super().mousePressEvent(event)

# =======================================================
# COMPONENT: THẺ KẾT QUẢ TOPIC (CARD UI)
# =======================================================
class TopicCard(QFrame):
    def __init__(self, index, topic_name, titles, angle, hook, tags, ctr_level, diff_level):
        super().__init__()
        self.setObjectName("topic_card")
        self.setStyleSheet("""
            QFrame#topic_card { background: #131320; border: 1px solid #2A2A48; border-radius: 8px; }
            QLabel { color: #D0D0E0; }
            QLabel#card_header { font-size: 16px; font-weight: bold; color: #E8E8F0; }
            QLabel#section_lbl { font-size: 10px; font-weight: bold; color: #5A5A7A; letter-spacing: 1px; margin-bottom: 4px; margin-top: 8px; }
            QFrame#title_btn { background: #18182B; border: 1px solid #282840; border-radius: 6px; }
            QFrame#title_btn:hover { border-color: #5A4FCC; background: #1E1E35; }
            QTextEdit#desc_box { background: #18182B; border: 1px solid #282840; border-radius: 6px; padding: 10px; color: #C4C4DC; font-size: 13px; line-height: 1.5; }
            QLabel#desc_lbl { background: #18182B; border: 1px solid #282840; border-radius: 6px; padding: 10px; color: #C4C4DC; font-size: 13px; }
            QPushButton#tag_mini { background: #18182B; border: 1px solid #282840; border-radius: 4px; padding: 4px 8px; color: #8A8AA0; font-size: 11px; }
            QPushButton#action_btn { background: transparent; border: 1px solid #282840; border-radius: 4px; padding: 6px 12px; color: #A0A0C0; font-size: 12px; font-weight: bold; }
            QPushButton#action_btn:hover { color: #FFF; border-color: #5A4FCC; }
            QPushButton#save_btn { background: #E8742A; border: none; border-radius: 6px; padding: 6px 16px; color: #000; font-weight: bold; font-size: 12px; }
            QPushButton#save_btn:hover { background: #FF9A50; }
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # 1. HEADER DÒNG TỐI
        header_frm = QFrame()
        header_frm.setStyleSheet("background: #1A1A2E; border-bottom: 1px solid #282840; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        h_lay = QHBoxLayout(header_frm)
        h_lay.setContentsMargins(16, 12, 16, 12)
        
        lbl_idx = QLabel(f"#{index:02d}")
        lbl_idx.setStyleSheet("color: #5A5A7A; font-weight: bold; font-size: 14px; margin-right: 8px;")
        h_lay.addWidget(lbl_idx)
        
        h_lay.addWidget(QLabel(topic_name, objectName="card_header"))
        h_lay.addStretch()
        
        # Badges
        lbl_ctr = QLabel(f"CTR: {ctr_level}")
        lbl_ctr.setStyleSheet("background: rgba(0, 230, 118, 0.1); color: #00E676; border: 1px solid rgba(0, 230, 118, 0.3); padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        lbl_diff = QLabel(diff_level)
        lbl_diff.setStyleSheet("background: rgba(77, 166, 255, 0.1); color: #4DA6FF; border: 1px solid rgba(77, 166, 255, 0.3); padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        h_lay.addWidget(lbl_ctr)
        h_lay.addWidget(lbl_diff)
        main_lay.addWidget(header_frm)

        # 2. BODY CHIA 2 CỘT
        body_lay = QHBoxLayout()
        body_lay.setContentsMargins(16, 12, 16, 12)
        body_lay.setSpacing(20)

        # Cột trái: Titles
        left_vbox = QVBoxLayout()
        left_vbox.addWidget(QLabel("TITLES (CLICK ĐỂ COPY)", objectName="section_lbl"))
        for t_main, t_sub in titles:
            btn_t = ClickableTitleFrame(t_main, t_sub)
            left_vbox.addWidget(btn_t)
        left_vbox.addStretch()
        body_lay.addLayout(left_vbox, 1) # Stretch = 1

        # Cột phải: Angle & Hook
        right_vbox = QVBoxLayout()
        right_vbox.addWidget(QLabel("ANGLE ĐỘC ĐÁO", objectName="section_lbl"))
        txt_angle = QLabel(angle)
        txt_angle.setObjectName("desc_lbl")
        txt_angle.setWordWrap(True)
        txt_angle.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        txt_angle.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right_vbox.addWidget(txt_angle)
        
        right_vbox.addWidget(QLabel("HOOK SENTENCE", objectName="section_lbl"))
        txt_hook = QLabel(hook)
        txt_hook.setObjectName("desc_lbl")
        txt_hook.setWordWrap(True)
        txt_hook.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        txt_hook.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right_vbox.addWidget(txt_hook)
        right_vbox.addStretch()
        body_lay.addLayout(right_vbox, 1) # Stretch = 1

        main_lay.addLayout(body_lay)

        # 3. FOOTER
        foot_frm = QFrame()
        foot_frm.setStyleSheet("border-top: 1px solid #282840; background: transparent;")
        f_lay = QHBoxLayout(foot_frm)
        f_lay.setContentsMargins(16, 12, 16, 12)
        
        for tag in tags:
            f_lay.addWidget(QPushButton(tag, objectName="tag_mini"))
            
        f_lay.addSpacing(16)
        btn_c = QPushButton("📄 Copy", objectName="action_btn"); btn_c.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_t = QPushButton("→ Tool 1", objectName="action_btn"); btn_t.setCursor(Qt.CursorShape.PointingHandCursor)
        f_lay.addWidget(btn_c)
        f_lay.addWidget(btn_t)
        f_lay.addStretch()
        
        btn_s = QPushButton("★ Save", objectName="save_btn"); btn_s.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save = btn_s # Expose the button
        f_lay.addWidget(self.btn_save)
        main_lay.addWidget(foot_frm)


# =======================================================
# TAB CHÍNH
# =======================================================
class TopicIdeatorTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 5, 15, 5) # Nén lề dọc
        
        # --- CSS TỔNG THỂ ---
        self.setStyleSheet("""
            TopicIdeatorTab { background-color: #08080D; }
            QLabel#page_title { font-size: 20px; font-weight: bold; color: #E8E8F0; }
            QLabel#page_desc { font-size: 12px; color: #606075; margin-bottom: 5px;}
            QLabel#section_label { font-size: 11px; font-weight: bold; color: #5A5A7A; letter-spacing: 1px; text-transform: uppercase; margin-top: 10px; margin-bottom: 5px; }
            QLabel#muted { color: #8A8AA0; font-size: 12px; font-weight: bold; margin-bottom: 2px; }
            QPushButton#tag_btn { background: #18182B; border: 1px solid #282840; border-radius: 16px; padding: 6px 14px; color: #A0A0C0; }
            QPushButton#tag_btn:checked { background: rgba(90, 79, 204, 0.2); border-color: #5A4FCC; color: #FFF; font-weight: bold; }
            QComboBox, QLineEdit { background: #18182B; border: 1px solid #282840; border-radius: 6px; padding: 8px 12px; color: #E8E8F0; }
            QTextEdit { background: #18182B; border: 1px solid #282840; border-radius: 8px; padding: 10px; color: #E8E8F0; }
            QPushButton#btn_primary { background: #E8742A; color: #000; border-radius: 6px; padding: 10px 20px; font-weight: bold; font-size: 14px; }
            QPushButton#btn_primary:hover { background: #FF9A50; }
            QPushButton#btn_sec { background: transparent; border: 1px solid #282840; color: #D0D0E0; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
            QPushButton#btn_sec:hover { border-color: #5A4FCC; color: #FFF; }
        """)

        # 1. HEADER
        header = QHBoxLayout()
        vbox_header = QVBoxLayout()
        vbox_header.addWidget(QLabel("Topic Ideator", objectName="page_title"))
        vbox_header.addWidget(QLabel("Generate validated topics với hook titles + unique angle + CTR score", objectName="page_desc"))
        header.addLayout(vbox_header)
        header.addStretch()
        main_lay.addLayout(header)

        # SCROLL AREA
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(8) # Giảm spacing

        # DATA
        self.style_content = ""
        self.dna_content = ""
        self.done_content = ""

        # --- 1. CONTEXT FILES ---
        lay.addWidget(QLabel("CONTEXT FILES (OPTIONAL)", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)
        self.dz_style = DropZoneWidget("📋", "STYLE GUIDE", "Upload để suggest đúng tone")
        self.dz_dna = DropZoneWidget("🧬", "DNA KÊNH", "Upload để suggest đúng format")
        self.dz_done = DropZoneWidget("📝", "TOPICS ĐÃ LÀM", "Upload để tránh trùng lặp")
        
        self.dz_style.file_loaded.connect(lambda p, c: setattr(self, 'style_content', c))
        self.dz_dna.file_loaded.connect(lambda p, c: setattr(self, 'dna_content', c))
        self.dz_done.file_loaded.connect(lambda p, c: setattr(self, 'done_content', c))

        ctx_lay.addWidget(self.dz_style); ctx_lay.addWidget(self.dz_dna); ctx_lay.addWidget(self.dz_done)
        lay.addLayout(ctx_lay)

        # --- 2. NGÁCH KÊNH ---
        lay.addWidget(QLabel("NGÁCH KÊNH", objectName="section_label"))
        tags_lay = QHBoxLayout()
        tags = ["Tài chính", "Tội phạm", "Lịch sử", "Khoa học", "Tâm lý học", "Địa chính trị", "Tiểu sử", "Triết học"]
        for tag in tags:
            b = QPushButton(tag, objectName="tag_btn")
            b.setCheckable(True)
            tags_lay.addWidget(b)
            
        b_c = QPushButton("+ Tuỳ chỉnh", objectName="tag_btn"); b_c.setCheckable(True)
        tags_lay.addWidget(b_c)
        tags_lay.addStretch()
        lay.addLayout(tags_lay)

        self.txt_custom_niche = QLineEdit()
        self.txt_custom_niche.setPlaceholderText("Nhập ngách tuỳ chỉnh...")
        lay.addWidget(self.txt_custom_niche)

        # --- 3. SETTINGS ---
        grid = QGridLayout(); grid.setSpacing(16)
        grid.addWidget(QLabel("SỐ TOPICS", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("NGÔN NGỮ OUTPUT", objectName="muted"), 0, 1)
        grid.addWidget(QLabel("KÊNH THAM CHIẾU (STYLE)", objectName="muted"), 0, 2)
        grid.addWidget(QLabel("FOCUS", objectName="muted"), 0, 3)

        self.cmb_topics = QComboBox(); self.cmb_topics.addItems(["5", "10", "15", "20"]); grid.addWidget(self.cmb_topics, 1, 0)
        self.cmb_lang = QComboBox(); self.cmb_lang.addItems(["Tiếng Việt", "English"]); grid.addWidget(self.cmb_lang, 1, 1)

        self.cmb_ref = QComboBox(); self.cmb_ref.setEditable(True)
        self.cmb_ref.lineEdit().setPlaceholderText("VD: https://youtube.com/@channel")
        grid.addWidget(self.cmb_ref, 1, 2)

        self.cmb_focus = QComboBox(); self.cmb_focus.addItems(["CTR cao nhất", "Evergreen", "Góc độ độc đáo"]); grid.addWidget(self.cmb_focus, 1, 3)

        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1); grid.setColumnStretch(2, 2); grid.setColumnStretch(3, 1)
        lay.addLayout(grid)

        # --- 4. BOTTOM ACTIONS (Đẩy lên trên kết quả như trong ảnh) ---
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("background: #282840; border: none; margin: 10px 0;")
        lay.addWidget(line)

        act_lay = QHBoxLayout()
        self.btn_gen = QPushButton("💡 Generate Topics", objectName="btn_primary")
        self.btn_gen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gen.clicked.connect(self._generate_topics)
        
        btn_reset = QPushButton("✕ Reset", objectName="btn_sec")
        act_lay.addWidget(self.btn_gen)
        act_lay.addWidget(btn_reset)

        act_lay.addStretch()

        act_lay.addWidget(QPushButton("Sort: CTR", objectName="btn_sec"))
        act_lay.addWidget(QPushButton("Sort: Easy", objectName="btn_sec"))
        
        self.lbl_result_count = QLabel("✓ 0 topics generated")
        self.lbl_result_count.setStyleSheet("color: #00E676; font-weight: bold; margin-left: 10px;")
        act_lay.addWidget(self.lbl_result_count)

        lay.addLayout(act_lay)

        # --- 5. OUTPUT CONTAINER (Chứa danh sách Card) ---
        self.output_header = QLabel("| TOPICS (0)")
        self.output_header.setStyleSheet("color: #8A8AA0; font-weight: bold; font-size: 13px; letter-spacing: 1px; margin-top: 15px;")
        lay.addWidget(self.output_header)
        self.output_header.hide() # Ẩn đi khi chưa có kết quả

        # Đây là Layout dọc sẽ chứa các Thẻ TopicCard
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(16)
        lay.addLayout(self.results_layout)

        lay.addStretch()
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

    def apply_profile(self, profile_data):
        self.style_content = profile_data.get("style_content", "")
        self.dna_content = profile_data.get("dna_content", "")
        
        if self.style_content:
            self.dz_style.lbl_desc.setText("Đã nạp từ Profile")
            self.dz_style.lbl_desc.setStyleSheet("color: #3AD68A;")
        else:
            self.dz_style.lbl_desc.setText("Upload để suggest đúng tone")
            self.dz_style.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
            
        if self.dna_content:
            self.dz_dna.lbl_desc.setText("Đã nạp từ Profile")
            self.dz_dna.lbl_desc.setStyleSheet("color: #3AD68A;")
        else:
            self.dz_dna.lbl_desc.setText("Upload để suggest đúng format")
            self.dz_dna.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
            
        self.txt_custom_niche.setText(profile_data.get("niche", ""))
        
        # Cập nhật ngôn ngữ
        lang = profile_data.get("lang", "Tiếng Việt")
        for i in range(self.cmb_lang.count()):
            if lang.lower() in self.cmb_lang.itemText(i).lower() or self.cmb_lang.itemText(i).lower() in lang.lower():
                self.cmb_lang.setCurrentIndex(i)
                break

    # =======================================================
    # LOGIC: KẾT NỐI AI WORKER VÀ RENDER KẾT QUẢ
    # =======================================================
    def _generate_topics(self):
        self.btn_gen.setEnabled(False)
        self.btn_gen.setText("⏳ Đang xử lý AI...")
        
        # Xoá các kết quả cũ nếu có
        for i in reversed(range(self.results_layout.count())): 
            self.results_layout.itemAt(i).widget().setParent(None)

        # Quét các nút Tag Ngách Kênh đang được check
        niches = []
        for btn in self.findChildren(QPushButton, "tag_btn"):
            if btn.isChecked():
                if btn.text() == "+ Tuỳ chỉnh":
                    if self.txt_custom_niche.text().strip():
                        niches.append(self.txt_custom_niche.text().strip())
                else:
                    niches.append(btn.text())
        niche_str = ", ".join(niches) if niches else "Chưa xác định"

        # Gom cấu hình
        config = {
            "niche": niche_str,
            "num_topics": self.cmb_topics.currentText(),
            "lang": self.cmb_lang.currentText(),
            "ref_channel": self.cmb_ref.currentText(),
            "focus": self.cmb_focus.currentText(),
            "extra": "", # Bạn có thể thêm ô nhập Yêu cầu bổ sung trên UI sau
            "style_content": getattr(self, 'style_content', ""),
            "dna_content": getattr(self, 'dna_content', ""),
            "done_content": getattr(self, 'done_content', "")
        }

        self.worker = TopicWorker(config)
        self.worker.result_signal.connect(self._on_worker_result)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_result(self, result_str):
        if result_str.startswith("❌"):
            lbl_err = QLabel(result_str)
            lbl_err.setStyleSheet("color: #E84040; font-weight: bold; font-size: 14px;")
            self.results_layout.addWidget(lbl_err)
            return

        try:
            data = json.loads(result_str)
            topics = data.get("topics", [])
            model_used = data.get("model_used", "AI")
            
            self.lbl_result_count.setText(f"✓ {len(topics)} topics via {model_used}")
            self.output_header.setText(f"| TOPICS ({len(topics)})")
            self.output_header.show()

            for i, t in enumerate(topics, 1):
                t_name = t.get("topic_name", "Unknown Topic")
                t_titles = [(item.get("text", ""), item.get("formula", "")) for item in t.get("titles", [])]
                t_angle = t.get("unique_angle", "")
                t_hook = t.get("hook_sentence", "")
                t_tags = t.get("tags", [])
                t_ctr = str(t.get("ctr_level", "HIGH"))
                t_diff = str(t.get("difficulty_level", "MEDIUM"))

                card = TopicCard(i, t_name, t_titles, t_angle, t_hook, t_tags, t_ctr, t_diff)
                # Kết nối nút Save của card với hàm lưu vào profile
                card.btn_save.clicked.connect(lambda checked=False, topic_data=t, card_widget=card: self._save_topic_to_profile(topic_data, card_widget))
                self.results_layout.addWidget(card)

        except Exception as e:
            lbl_err = QLabel(f"❌ Lỗi parse JSON từ AI: {str(e)}\n\nData nhận được:\n{result_str}")
            lbl_err.setStyleSheet("color: #E84040; font-size: 14px;")
            self.results_layout.addWidget(lbl_err)

    def _save_topic_to_profile(self, topic_data, card_widget):
        ACTIVE_PROFILE_FILE = "active_profile.json"
        if not os.path.exists(ACTIVE_PROFILE_FILE):
            QMessageBox.warning(self, "Chưa có Profile", "Vui lòng chọn và áp dụng một Profile đang hoạt động trước khi lưu.")
            return

        try:
            with open(ACTIVE_PROFILE_FILE, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            QMessageBox.critical(self, "Lỗi Profile", f"Không thể đọc hoặc file '{ACTIVE_PROFILE_FILE}' bị lỗi.")
            return

        # Chuẩn bị dữ liệu topic để lưu, đổi 'topic_name' thành 'title' để khớp với Tool 2
        topic_to_save = topic_data.copy()
        if 'topic_name' in topic_to_save:
            topic_to_save['title'] = topic_to_save.pop('topic_name')
        
        # Thêm trường script rỗng để Tool 1 có thể điền vào sau
        topic_to_save['script'] = None 

        if "topics" not in profile_data or not isinstance(profile_data.get("topics"), list):
            profile_data["topics"] = []

        # Kiểm tra trùng lặp dựa trên title
        existing_titles = [t.get("title") for t in profile_data["topics"] if t.get("title")]
        if topic_to_save.get("title") in existing_titles:
            QMessageBox.information(self, "Đã tồn tại", f"Topic '{topic_to_save.get('title')}' đã được lưu vào profile rồi.")
            card_widget.btn_save.setText("✓ Đã lưu")
            card_widget.btn_save.setEnabled(False)
            card_widget.btn_save.setStyleSheet("background: #282840; color: #8A8AA0; border: none; border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
            return

        profile_data["topics"].append(topic_to_save)

        try:
            with open(ACTIVE_PROFILE_FILE, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=4)
            
            card_widget.btn_save.setText("✓ Đã lưu")
            card_widget.btn_save.setEnabled(False)
            card_widget.btn_save.setStyleSheet("background: #282840; color: #8A8AA0; border: none; border-radius: 6px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
            QMessageBox.information(self, "Thành công", f"Đã lưu topic '{topic_to_save.get('title')}' vào Profile đang hoạt động.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Lưu File", f"Không thể ghi vào file '{ACTIVE_PROFILE_FILE}':\n{e}")

    def _on_worker_finished(self):
        self.btn_gen.setEnabled(True)
        self.btn_gen.setText("💡 Generate Topics")