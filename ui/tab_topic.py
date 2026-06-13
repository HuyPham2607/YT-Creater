import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QGridLayout,
                             QComboBox, QScrollArea, QApplication, QFileDialog, QFrame,
                             QSizePolicy, QMessageBox, QDialog, QListWidget, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from ui.components import DropZoneWidget
from threads.topic_worker import TopicWorker
from core.profile_store import (
    build_done_content,
    load_active_profile,
    save_topic_to_active_profile,
)

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
    def __init__(self, index, topic_name, titles, angle, hook, tags, ctr_level, diff_level, details=None):
        super().__init__()
        details = details or {}
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
        lbl_overall = QLabel(f"SCORE: {details.get('overall_score', '-')}")
        lbl_overall.setStyleSheet("background: rgba(232,116,42,0.12); color: #E8742A; border: 1px solid rgba(232,116,42,0.3); padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        h_lay.addWidget(lbl_ctr)
        h_lay.addWidget(lbl_diff)
        h_lay.addWidget(lbl_overall)
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

        strategic_lay = QGridLayout()
        strategic_lay.setContentsMargins(16, 0, 16, 12)
        strategic_lay.setSpacing(12)
        strategic_items = [
            ("AUDIENCE", details.get("target_audience", "")),
            ("PROMISE", details.get("one_line_promise", "")),
            ("TREND / LOCAL", " | ".join(filter(None, [details.get("trend_connection", ""), details.get("local_vietnam_angle", "")]))),
            ("BETTER ANGLE", " ? ".join(filter(None, [details.get("competitor_common_angle", ""), details.get("our_better_angle", "")]))),
            ("RETENTION", " ? ".join(details.get("retention_hooks", []) if isinstance(details.get("retention_hooks"), list) else [])),
            ("RESEARCH", ", ".join(details.get("research_keywords", []) if isinstance(details.get("research_keywords"), list) else [])),
            ("VISUAL", details.get("visual_potential", "")),
            ("RISK", details.get("risk_or_watchout", "")),
        ]
        for idx, (label, value) in enumerate(strategic_items):
            if not value:
                continue
            row, col = divmod(idx, 2)
            box = QLabel(f"<b>{label}</b><br>{value}")
            box.setObjectName("desc_lbl")
            box.setWordWrap(True)
            box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            strategic_lay.addWidget(box, row, col)
        main_lay.addLayout(strategic_lay)

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
        self.btn_save = btn_s
        self.btn_tool1 = btn_t
        self.btn_copy = btn_c
        self._details = details or {}
        f_lay.addWidget(self.btn_save)
        main_lay.addWidget(foot_frm)


# =======================================================
# TAB CHÍNH
# =======================================================
class TopicIdeatorTab(QWidget):
    send_to_script = pyqtSignal(dict)

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
        self.current_topics = []
        self.current_model_used = "AI"

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

        # --- 1b. TOPICS ĐÃ LƯU TRONG PROFILE ---
        lay.addWidget(QLabel("TOPICS ĐÃ LƯU TRONG PROFILE", objectName="section_label"))
        saved_row = QHBoxLayout()
        self.lbl_saved_topics = QLabel("0 topic trong Profile")
        self.lbl_saved_topics.setObjectName("muted")
        self.btn_view_saved_topics = QPushButton("📋 Xem danh sách đã lưu", objectName="btn_sec")
        self.btn_view_saved_topics.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_saved_topics.clicked.connect(self._view_saved_topics_from_profile)
        saved_row.addWidget(self.lbl_saved_topics)
        saved_row.addStretch()
        saved_row.addWidget(self.btn_view_saved_topics)
        lay.addLayout(saved_row)

        saved_hint = QLabel(
            "Sau khi Generate: bấm «→ Tool 1» trên card để chọn title phụ và chuyển sang viết kịch bản "
            "(tự lưu vào Profile). Hoặc bấm ★ Save rồi dùng «Chọn từ Profile» ở Tool 1."
        )
        saved_hint.setWordWrap(True)
        saved_hint.setStyleSheet("color: #606075; font-size: 11px; margin-bottom: 4px;")
        lay.addWidget(saved_hint)

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

        self.cmb_focus = QComboBox(); self.cmb_focus.addItems(["CTR cao nhất", "Evergreen nhất", "Góc độ độc đáo", "Dễ làm nhất", "Cân bằng"]); grid.addWidget(self.cmb_focus, 1, 3)

        grid.setColumnStretch(0, 1); grid.setColumnStretch(1, 1); grid.setColumnStretch(2, 2); grid.setColumnStretch(3, 1)
        lay.addLayout(grid)
        lay.addWidget(QLabel("YÊU CẦU BỔ SUNG (OPTIONAL)", objectName="muted"))
        self.txt_extra_request = QTextEdit()
        self.txt_extra_request.setFixedHeight(72)
        self.txt_extra_request.setPlaceholderText("VD: Ưu tiên topics có yếu tố tranh luận, tránh drama rẻ tiền, phù hợp video 12 phút...")
        lay.addWidget(self.txt_extra_request)


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

        self.btn_sort_overall = QPushButton("Sort: Overall", objectName="btn_sec")
        self.btn_sort_production = QPushButton("Sort: Production", objectName="btn_sec")
        self.btn_sort_evergreen = QPushButton("Sort: Evergreen", objectName="btn_sec")
        self.btn_sort_overall.clicked.connect(lambda: self._sort_topics("overall_score", "Overall"))
        self.btn_sort_production.clicked.connect(lambda: self._sort_topics("production_score", "Production"))
        self.btn_sort_evergreen.clicked.connect(lambda: self._sort_topics("evergreen_score", "Evergreen"))
        act_lay.addWidget(self.btn_sort_overall)
        act_lay.addWidget(self.btn_sort_production)
        act_lay.addWidget(self.btn_sort_evergreen)
        
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
        self.done_content = build_done_content(profile_data)
        self._profile_data = profile_data
        self._update_saved_topics_label(profile_data)
        
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

        if self.done_content:
            self.dz_done.lbl_desc.setText("Đã nạp từ Profile")
            self.dz_done.lbl_desc.setStyleSheet("color: #3AD68A;")
        else:
            self.dz_done.lbl_desc.setText("Upload để tránh trùng lặp")
            self.dz_done.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
            
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
    def _update_saved_topics_label(self, profile_data=None):
        profile_data = profile_data or getattr(self, "_profile_data", {}) or {}
        topics = profile_data.get("topics") or []
        with_script = sum(
            1 for topic in topics
            if isinstance(topic.get("script"), dict) and (topic.get("script") or {}).get("content")
        )
        self.lbl_saved_topics.setText(f"{len(topics)} topic đã lưu · {with_script} có kịch bản")

    def _normalize_topic_data(self, topic):
        data = dict(topic or {})
        if not data.get("topic_name") and data.get("title"):
            data["topic_name"] = data["title"]
        return data

    def _build_topic_card(self, index, topic_data, *, saved=False):
        topic = self._normalize_topic_data(topic_data)
        titles = [
            (
                item.get("text", ""),
                "{} | score {}".format(item.get("formula", ""), item.get("score", "-")),
            )
            for item in topic.get("titles", [])
            if isinstance(item, dict)
        ]
        card = TopicCard(
            index,
            topic.get("topic_name", "Unknown Topic"),
            titles,
            topic.get("unique_angle", ""),
            topic.get("hook_sentence", ""),
            topic.get("tags", []),
            str(topic.get("ctr_level", "HIGH")),
            str(topic.get("difficulty_level", "MEDIUM")),
            details=topic,
        )
        if saved:
            card.btn_save.setText("✓ Đã lưu")
            card.btn_save.setEnabled(False)
            card.btn_save.setStyleSheet(
                "background: #282840; color: #8A8AA0; border: none; border-radius: 6px; "
                "padding: 6px 16px; font-weight: bold; font-size: 12px;"
            )
        self._wire_card_actions(card, topic)
        return card

    def _wire_card_actions(self, card, topic_data):
        card.btn_tool1.clicked.connect(
            lambda checked=False, topic=topic_data, card_widget=card: self._on_send_to_tool1(topic, card_widget)
        )
        card.btn_copy.clicked.connect(
            lambda checked=False, topic=topic_data: self._copy_topic_json(topic)
        )

    def _copy_topic_json(self, topic_data):
        topic = self._normalize_topic_data(topic_data)
        QApplication.clipboard().setText(json.dumps(topic, ensure_ascii=False, indent=2))
        QMessageBox.information(self, "Đã copy", "Đã copy toàn bộ JSON topic vào clipboard.")

    def _pick_subtitle_dialog(self, topic_data, parent=None):
        topic = self._normalize_topic_data(topic_data)
        topic_name = topic.get("topic_name", "Không tên")
        subtitles = [
            item for item in topic.get("titles", [])
            if isinstance(item, dict) and (item.get("text") or "").strip()
        ]
        if not subtitles:
            QMessageBox.warning(parent or self, "Thiếu title", "Topic này không có title phụ để chọn.")
            return None

        if len(subtitles) == 1:
            return subtitles[0].get("text", "").strip()

        dialog = QDialog(parent or self)
        dialog.setWindowTitle("Chọn title phụ → Tool 1")
        dialog.resize(640, 420)
        dialog.setStyleSheet("""
            QDialog { background-color: #0F0F18; border: 1px solid #252535; }
            QLabel { color: #E8E8F0; font-size: 13px; }
            QListWidget { background-color: #18182B; border: 1px solid #282840; border-radius: 8px; color: #E8E8F0; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #252535; }
            QListWidget::item:selected { background-color: rgba(232,116,42,0.2); border: 1px solid #E8742A; }
        """)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Topic: <b>{topic_name}</b><br>Chọn 1 title phụ để viết kịch bản:"))

        list_widget = QListWidget()
        list_widget.setWordWrap(True)
        for item in subtitles:
            formula = item.get("formula", "")
            score = item.get("score", "-")
            list_widget.addItem(f"{item.get('text', '')}\n   {formula} | score {score}")
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_ok = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText("→ Tool 1")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        row = list_widget.currentRow()
        if row < 0 or row >= len(subtitles):
            return None
        return subtitles[row].get("text", "").strip()

    def _mark_card_saved(self, card_widget):
        if not card_widget:
            return
        card_widget.btn_save.setText("✓ Đã lưu")
        card_widget.btn_save.setEnabled(False)
        card_widget.btn_save.setStyleSheet(
            "background: #282840; color: #8A8AA0; border: none; border-radius: 6px; "
            "padding: 6px 16px; font-weight: bold; font-size: 12px;"
        )

    def _on_send_to_tool1(self, topic_data, card_widget=None):
        if not load_active_profile():
            QMessageBox.warning(
                self,
                "Chưa có Profile",
                "Vui lòng chọn và áp dụng một Profile đang hoạt động trước.",
            )
            return

        selected_subtitle = self._pick_subtitle_dialog(topic_data)
        if not selected_subtitle:
            return

        if not self._save_topic_to_profile(topic_data, card_widget, silent=True):
            return

        topic = self._normalize_topic_data(topic_data)
        topic_name = topic.get("topic_name", "")
        selected_item = None
        for item in topic.get("titles", []):
            if isinstance(item, dict) and (item.get("text") or "").strip() == selected_subtitle:
                selected_item = item
                break

        topic_strategy = dict(topic)
        if selected_item:
            topic_strategy["selected_title"] = selected_item
        topic_strategy["selected_title_text"] = selected_subtitle

        self.send_to_script.emit({
            "topic_title": topic_name,
            "selected_subtitle": selected_subtitle,
            "topic_strategy": topic_strategy,
        })

    def _append_script_status_block(self, parent_layout, topic_data):
        script = topic_data.get("script") if isinstance(topic_data.get("script"), dict) else None
        if not script:
            return

        box = QFrame()
        box.setStyleSheet(
            "QFrame { background: rgba(58,214,138,0.06); border: 1px solid rgba(58,214,138,0.2); "
            "border-radius: 8px; margin: 0 0 12px 0; }"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.addWidget(QLabel(
            "<b>TRẠNG THÁI KỊCH BẢN</b>",
            styleSheet="color: #3AD68A; font-size: 10px; font-weight: bold; border: none; background: transparent;",
        ))
        script_title = (script.get("title") or "").strip()
        if script_title:
            lay.addWidget(QLabel(
                f"Title đã chọn: {script_title}",
                styleSheet="color: #E8E8F0; font-size: 12px; border: none; background: transparent;",
            ))
        content = (script.get("content") or "").strip()
        if content:
            preview = content if len(content) <= 500 else content[:500] + "..."
            preview_lbl = QLabel(preview)
            preview_lbl.setWordWrap(True)
            preview_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            preview_lbl.setStyleSheet(
                "color: #C4C4DC; font-size: 12px; border: none; background: transparent; line-height: 1.4;"
            )
            lay.addWidget(preview_lbl)
        research = (script.get("research") or "").strip()
        if research:
            research_preview = research if len(research) <= 300 else research[:300] + "..."
            lay.addWidget(QLabel(
                f"<b>Research:</b> {research_preview}",
                styleSheet="color: #8A8AA0; font-size: 11px; border: none; background: transparent;",
            ))
        parent_layout.addWidget(box)

    def _view_saved_topics_from_profile(self):
        profile_data = load_active_profile() or getattr(self, "_profile_data", {}) or {}
        topics = profile_data.get("topics") or []
        if not topics:
            QMessageBox.information(
                self,
                "Chưa có topic",
                "Profile chưa có topic nào được lưu.\n\n"
                "Cách dùng:\n"
                "1. Bấm Generate Topics\n"
                "2. Bấm lưu trên card topic bạn chọn\n"
                "3. Mở Tool 1 → «Chọn từ Profile» để viết kịch bản",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Topics đã lưu trong Profile")
        dialog.resize(min(1200, self.window().width() if self.window() else 1200), 820)
        dialog.setStyleSheet("""
            QDialog { background-color: #08080D; }
            QLabel { color: #E8E8F0; }
            QScrollArea { border: none; background: transparent; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 12)

        header = QLabel(
            f"<b>Profile: {profile_data.get('name', 'Active')}</b> — "
            f"{len(topics)} topic đã lưu · cuộn để xem chi tiết đầy đủ như khi Generate"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        cards_lay = QVBoxLayout(container)
        cards_lay.setContentsMargins(0, 0, 8, 0)
        cards_lay.setSpacing(16)

        for index, topic in enumerate(topics, 1):
            cards_lay.addWidget(self._build_topic_card(index, topic, saved=True))
            self._append_script_status_block(cards_lay, topic)

        cards_lay.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dialog.reject)
        btn_box.button(QDialogButtonBox.StandardButton.Close).setText("Đóng")
        layout.addWidget(btn_box)
        dialog.exec()

    def _generate_topics(self):
        self.btn_gen.setEnabled(False)
        self.btn_gen.setText("⏳ Đang xử lý AI...")
        
        # Xoá các kết quả cũ nếu có
        self.current_topics = []
        self.current_model_used = "AI"
        self._clear_results()

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
            "extra": self.txt_extra_request.toPlainText().strip(),
            "style_content": getattr(self, 'style_content', ""),
            "dna_content": getattr(self, 'dna_content', ""),
            "done_content": getattr(self, 'done_content', ""),
            "profile_data": getattr(self, '_profile_data', {}),
        }

        self.worker = TopicWorker(config)
        self.worker.result_signal.connect(self._on_worker_result)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    def _clear_results(self):
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def _score_value(self, topic, key):
        value = topic.get(key, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _sort_topics(self, score_key, label):
        if not self.current_topics:
            QMessageBox.information(self, "Chưa có topic", "Hãy Generate Topics trước khi sort.")
            return

        self.current_topics = sorted(
            self.current_topics,
            key=lambda topic: self._score_value(topic, score_key),
            reverse=True
        )
        self._render_topics(self.current_topics, self.current_model_used, sort_label=label)

    def _render_topics(self, topics, model_used="AI", sort_label=None):
        self._clear_results()
        suffix = f" • sorted by {sort_label}" if sort_label else ""
        self.lbl_result_count.setText(f"✓ {len(topics)} topics via {model_used}{suffix}")
        self.output_header.setText(f"| TOPICS ({len(topics)})")
        self.output_header.show()

        for i, t in enumerate(topics, 1):
            card = self._build_topic_card(i, t, saved=False)
            card.btn_save.clicked.connect(
                lambda checked=False, topic_data=t, card_widget=card: self._save_topic_to_profile(topic_data, card_widget)
            )
            self.results_layout.addWidget(card)

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
            self.current_topics = topics
            self.current_model_used = model_used
            self._render_topics(self.current_topics, self.current_model_used)

        except Exception as e:
            lbl_err = QLabel(f"❌ Lỗi parse JSON từ AI: {str(e)}\n\nData nhận được:\n{result_str}")
            lbl_err.setStyleSheet("color: #E84040; font-size: 14px;")
            self.results_layout.addWidget(lbl_err)

    def _save_topic_to_profile(self, topic_data, card_widget=None, *, silent=False):
        if not load_active_profile():
            if not silent:
                QMessageBox.warning(self, "Chưa có Profile", "Vui lòng chọn và áp dụng một Profile đang hoạt động trước khi lưu.")
            return False

        topic_to_save = topic_data.copy()
        if "topic_name" in topic_to_save:
            topic_to_save["title"] = topic_to_save.pop("topic_name")
        topic_to_save.setdefault("script", None)

        try:
            profile_data, created = save_topic_to_active_profile(topic_to_save)
            self._profile_data = profile_data
            self.done_content = build_done_content(profile_data)
            self._update_saved_topics_label(profile_data)
            self._mark_card_saved(card_widget)

            if not silent:
                if created:
                    QMessageBox.information(
                        self,
                        "Thành công",
                        f"Đã lưu topic '{topic_to_save.get('title')}' vào Profile (active + thư viện).",
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Đã cập nhật",
                        f"Topic '{topic_to_save.get('title')}' đã tồn tại — đã cập nhật dữ liệu.",
                    )
            return True
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Lỗi Lưu File", f"Không thể lưu topic vào Profile:\n{e}")
            return False

    def _on_worker_finished(self):
        self.btn_gen.setEnabled(True)
        self.btn_gen.setText("💡 Generate Topics")
