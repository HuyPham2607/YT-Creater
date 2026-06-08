import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QGridLayout,
                             QComboBox, QScrollArea, QSpinBox,
                             QProgressBar, QSplitter, QSizePolicy,
                             QMessageBox, QInputDialog, QDialog, QListWidget, QDialogButtonBox)
from PyQt6.QtCore import Qt
from ui.components import DropZoneWidget
from threads.script_worker import ScriptWorker
from threads.research_worker import ResearchWorker


class ScriptWriterTab(QWidget):
    def __init__(self):
        super().__init__()

        # ── Internal state ────────────────────────────────────────
        self.style_content   = ""
        self.dna_content     = ""
        self._research_notes = ""   # filled after research completes
        self._last_config    = {}   # saved config so Write uses same params
        self.current_topic_title = ""
        self.current_topic_strategy = {}

        # ── Root layout ───────────────────────────────────────────
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 0, 10, 0)

        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        vbox_h = QVBoxLayout()
        vbox_h.setSpacing(0)
        vbox_h.addWidget(QLabel("Script Writer", objectName="page_title"))
        vbox_h.addWidget(QLabel(
            "Upload Style Guide + DNA + Chủ Đề → Research → Generate full script theo đúng DNA kênh",
            objectName="page_desc"
        ))
        header.addLayout(vbox_h)
        header.addStretch()
        header.addWidget(QLabel("Tool 1", objectName="page_badge"),
                         alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        # ==========================================
        # 2. SCROLL AREA
        # ==========================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(12)

        # --- CONTEXT FILES ---
        lay.addWidget(QLabel("CONTEXT FILES", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)

        self.dz_style = DropZoneWidget("📋", "STYLE GUIDE",         "Upload .md hoặc .txt")
        self.dz_dna   = DropZoneWidget("🧬", "DNA KÊNH",            "Upload .md hoặc .txt")
        self.dz_topic = DropZoneWidget("📝", "CHỦ ĐỀ (OPTIONAL)",   "Upload .md hoặc .txt")

        self.dz_style.file_loaded.connect(lambda p, c: setattr(self, 'style_content', c))
        self.dz_dna.file_loaded.connect(lambda p, c:   setattr(self, 'dna_content',   c))

        ctx_lay.addWidget(self.dz_style)
        ctx_lay.addWidget(self.dz_dna)
        ctx_lay.addWidget(self.dz_topic)
        lay.addLayout(ctx_lay)

        # --- CHỦ ĐỀ VIDEO ---
        lay.addWidget(QLabel("CHỦ ĐỀ VIDEO", objectName="section_label"))
        h_topic = QHBoxLayout()
        self.txt_topic = QLineEdit()
        self.txt_topic.setPlaceholderText("VD: Bạn Hiểu Vì Sao 10 Năm Tiết Kiệm = Đứng Yên Tại Chỗ")
        
        self.btn_get_topic = QPushButton("📂 Load Topic")
        self.btn_get_topic.setObjectName("btn_sec")
        self.btn_get_topic.clicked.connect(self._load_topic_from_profile)
        
        self.btn_save_script = QPushButton("💾 Lưu Kịch Bản")
        self.btn_save_script.setObjectName("btn_primary")
        self.btn_save_script.clicked.connect(self._save_script_to_profile)
        
        h_topic.addWidget(self.txt_topic)
        h_topic.addWidget(self.btn_get_topic)
        h_topic.addWidget(self.btn_save_script)
        lay.addLayout(h_topic)

        # --- CÀI ĐẶT ---
        lay.addWidget(QLabel("CÀI ĐẶT", objectName="section_label"))
        grid = QGridLayout()
        grid.setSpacing(14)

        grid.addWidget(QLabel("NGÔN NGỮ",    objectName="muted"), 0, 0)
        grid.addWidget(QLabel("CẤU TRÚC",    objectName="muted"), 0, 1)
        grid.addWidget(QLabel("POV STYLE",   objectName="muted"), 0, 2)
        grid.addWidget(QLabel("SỐ PHẦN",     objectName="muted"), 0, 3)
        grid.addWidget(QLabel("TARGET PHÚT", objectName="muted"), 0, 4)

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Tiếng Việt", "English", "Español", "Portuguese", "Deutsch"])
        grid.addWidget(self.cmb_lang, 1, 0)

        self.cmb_struct = QComboBox()
        self.cmb_struct.addItems([
            "Auto",
            "Levels — Escalation (POV)",
            "Acts — Story Arc (Narrative)",
            "Timeline — Chronological",
            "Chapters — Topic-based",
            "Parts — Flexible",
            "Custom — Tự nhập structure",
        ])
        self.cmb_struct.currentTextChanged.connect(self._update_structure_hint)
        grid.addWidget(self.cmb_struct, 1, 1)

        self.cmb_pov = QComboBox()
        self.cmb_pov.addItems([
            "Ngôi thứ 2 (Bạn)",
            "Ngôi 1 hỗn hợp",
            "Mixed",
            "Ngôi thứ 3",
            "Narrator",
            "Custom",
        ])
        grid.addWidget(self.cmb_pov, 1, 2)

        self.cmb_parts = QComboBox()
        self.cmb_parts.addItems(["Auto"] + [str(i) for i in range(3, 13)])
        grid.addWidget(self.cmb_parts, 1, 3)

        h_target = QHBoxLayout()
        self.spin_mins = QSpinBox()
        self.spin_mins.setRange(1, 60)
        self.spin_mins.setValue(10)
        self.lbl_words = QLabel("(~1550 từ)")
        self.lbl_words.setStyleSheet("color: #3AD68A; font-weight: bold; font-size: 11px;")
        self.spin_mins.valueChanged.connect(self._update_word_count)
        h_target.addWidget(self.spin_mins)
        h_target.addWidget(self.lbl_words)
        grid.addLayout(h_target, 1, 4)

        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(4, 2)
        lay.addLayout(grid)

        self.lbl_structure_hint = QLabel("")
        self.lbl_structure_hint.setWordWrap(True)
        self.lbl_structure_hint.setStyleSheet("color: #8A8AA0; font-size: 12px; font-style: italic;")
        lay.addWidget(self.lbl_structure_hint)
        self._update_structure_hint(self.cmb_struct.currentText())

        # --- AI MODEL & CONTEXT BỔ SUNG ---
        lay.addWidget(QLabel("AI MODEL & CONTEXT BỔ SUNG (OPTIONAL)", objectName="section_label"))

        self.cmb_ai = QComboBox()
        self.cmb_ai.addItems(["Gemini 3.5 Flash"])
        self.cmb_ai.setFixedWidth(220)
        lay.addWidget(self.cmb_ai)

        self.txt_extra = QTextEdit()
        self.txt_extra.setPlaceholderText(
            "Nhân vật, bối cảnh, twist muốn có, tone cụ thể...\n"
            "Tip: Nếu chọn Auto structure, Gemini sẽ tự quyết cấu trúc và số phần phù hợp."
        )
        self.txt_extra.setMaximumHeight(60)
        lay.addWidget(self.txt_extra)

        # ==========================================
        # 3. ACTION BUTTONS (2 nút riêng biệt)
        # ==========================================
        lay.addWidget(QLabel("CHẠY", objectName="section_label"))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # Nút 1 — Research
        self.btn_research = QPushButton("🔍  RESEARCH TRƯỚC")
        self.btn_research.setObjectName("btn_sec")
        self.btn_research.setFixedHeight(40)
        self.btn_research.setToolTip(
            "Thu thập facts & số liệu trước.\n"
            "Kiểm tra research notes, rồi bấm Viết Kịch Bản."
        )
        self.btn_research.clicked.connect(self._run_research)

        # Nút 2 — Viết kịch bản (disabled cho đến khi có research HOẶC user chọn viết ngay)
        self.btn_write = QPushButton("✍️  VIẾT KỊCH BẢN")
        self.btn_write.setObjectName("btn_primary")
        self.btn_write.setFixedHeight(40)
        self.btn_write.setToolTip(
            "Viết script ngay (không research).\n"
            "Sau khi research xong, nút này sẽ dùng cả research notes."
        )
        self.btn_write.clicked.connect(self._run_write)

        # Label trạng thái research
        self.lbl_research_state = QLabel("💡 Chưa có research — có thể viết thẳng hoặc research trước")
        self.lbl_research_state.setStyleSheet("color: #606075; font-size: 11px; font-style: italic;")

        btn_row.addWidget(self.btn_research)
        btn_row.addWidget(self.btn_write)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        lay.addWidget(self.lbl_research_state)

        # --- STATUS BAR ---
        status_lay = QHBoxLayout()
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet("color: #606075; font-style: italic;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        status_lay.addWidget(self.lbl_status)
        status_lay.addWidget(self.progress_bar)
        lay.addLayout(status_lay)

        # ==========================================
        # 4. OUTPUT SPLITTER
        # ==========================================
        self.output_splitter = QSplitter(Qt.Orientation.Vertical)
        self.output_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # BOX 1 — RESEARCH NOTES
        box_research = QWidget()
        lay_res = QVBoxLayout(box_research)
        lay_res.setContentsMargins(0, 0, 0, 0)

        res_header = QHBoxLayout()
        res_header.addWidget(QLabel("🔍 RESEARCH NOTES", objectName="section_label"))
        res_header.addStretch()
        self.btn_clear_research = QPushButton("✕ Xoá research")
        self.btn_clear_research.setObjectName("btn_sec")
        self.btn_clear_research.setFixedHeight(22)
        self.btn_clear_research.clicked.connect(self._clear_research)
        res_header.addWidget(self.btn_clear_research)
        lay_res.addLayout(res_header)

        self.txt_research = QTextEdit()
        self.txt_research.setPlaceholderText(
            "Bấm 🔍 RESEARCH TRƯỚC để AI thu thập facts & số liệu.\n"
            "Kiểm tra xong, bấm ✍️ VIẾT KỊCH BẢN — research notes sẽ được đính kèm tự động."
        )
        self.txt_research.setMinimumHeight(120)
        self.txt_research.setStyleSheet(
            "font-size: 13px; line-height: 1.5; background-color: #1a1a24; color: #a1a1aa;"
        )
        # Cho phép user chỉnh sửa research notes trước khi viết
        self.txt_research.textChanged.connect(self._on_research_edited)
        lay_res.addWidget(self.txt_research)

        # BOX 2 — SCRIPT OUTPUT
        box_script = QWidget()
        lay_scr = QVBoxLayout(box_script)
        lay_scr.setContentsMargins(0, 0, 0, 0)
        lay_scr.addWidget(QLabel("📝 SCRIPT OUTPUT", objectName="section_label"))

        self.txt_output = QTextEdit()
        self.txt_output.setPlaceholderText(
            "Kịch bản hoàn chỉnh sẽ hiển thị ở đây.\n"
            "Bạn có thể chỉnh sửa trực tiếp sau khi generate."
        )
        self.txt_output.setMinimumHeight(320)
        self.txt_output.setStyleSheet("font-size: 15px; line-height: 1.6;")
        lay_scr.addWidget(self.txt_output)

        self.output_splitter.addWidget(box_research)
        self.output_splitter.addWidget(box_script)
        self.output_splitter.setMinimumHeight(520)
        self.output_splitter.setSizes([170, 430])

        lay.addWidget(self.output_splitter)
        lay.setStretchFactor(self.output_splitter, 1)

        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

    def apply_profile(self, profile_data):
        self.style_content = profile_data.get("style_content", "")
        self.dna_content = profile_data.get("dna_content", "")
        topic_content = profile_data.get("topic_content", "")
        
        if self.style_content:
            self.dz_style.lbl_desc.setText("Đã nạp từ Profile")
            self.dz_style.lbl_desc.setStyleSheet("color: #3AD68A;")
        else:
            self.dz_style.lbl_desc.setText("Upload .md hoặc .txt")
            self.dz_style.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
            
        if self.dna_content:
            self.dz_dna.lbl_desc.setText("Đã nạp từ Profile")
            self.dz_dna.lbl_desc.setStyleSheet("color: #3AD68A;")
        else:
            self.dz_dna.lbl_desc.setText("Upload .md hoặc .txt")
            self.dz_dna.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
            
        if topic_content:
            self.dz_topic.lbl_desc.setText("Đã nạp từ Profile")
            self.dz_topic.lbl_desc.setStyleSheet("color: #3AD68A;")
        else:
            self.dz_topic.lbl_desc.setText("Upload .md hoặc .txt")
            self.dz_topic.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
                
        lang = profile_data.get("lang", "Tiếng Việt")
        for i in range(self.cmb_lang.count()):
            if lang.lower() in self.cmb_lang.itemText(i).lower() or self.cmb_lang.itemText(i).lower() in lang.lower():
                self.cmb_lang.setCurrentIndex(i)
                break
                
        pov = profile_data.get("pov", "Ngôi thứ 2")
        for i in range(self.cmb_pov.count()):
            if pov.lower() in self.cmb_pov.itemText(i).lower() or self.cmb_pov.itemText(i).lower() in pov.lower():
                self.cmb_pov.setCurrentIndex(i)
                break

    # ============================================================
    #  HELPERS
    # ============================================================

    def _update_word_count(self, mins: int):
        self.lbl_words.setText(f"(~{mins * 155} từ)")

    def _update_structure_hint(self, structure: str):
        hints = {
            "Auto": "Auto: dùng khi chưa chắc cấu trúc nào hợp. Gemini sẽ chọn giữa Levels/Acts/Timeline/Chapters/Parts dựa trên topic, target phút và DNA kênh.",
            "Levels — Escalation (POV)": "Levels: hợp với video đào sâu từng tầng nhận thức, sự thật ẩn, mindset, tâm lý, tài chính cá nhân, các chủ đề cần tăng độ nặng theo từng phần.",
            "Acts — Story Arc (Narrative)": "Acts: hợp với câu chuyện có hành trình, xung đột, biến cố, case study, tiểu sử, hoặc topic cần cảm xúc kiểu mở đầu → khủng hoảng → chuyển hóa.",
            "Timeline — Chronological": "Timeline: hợp với lịch sử, tiến trình, sự kiện theo năm/tháng, quá trình hình thành vấn đề, hoặc 'mọi chuyện đã đi đến đây như thế nào'.",
            "Chapters — Topic-based": "Chapters: hợp với nội dung phân tích nhiều góc ngang hàng, listicle, breakdown từng khía cạnh, mỗi chương là một ý độc lập.",
            "Parts — Flexible": "Parts: hợp khi topic không cần tăng cấp rõ, không phải câu chuyện, không theo thời gian; cần chia phần linh hoạt để giải thích mạch lạc.",
            "Custom — Tự nhập structure": "Custom: dùng khi bạn đã có cấu trúc riêng trong Extra Context. Nếu không nhập cấu trúc rõ, nên chọn Auto."
        }
        if hasattr(self, "lbl_structure_hint"):
            self.lbl_structure_hint.setText(hints.get(structure, hints["Auto"]))

    def _build_config(self) -> dict | None:
        """Validate inputs and return config dict. Returns None if invalid."""
        topic = self.txt_topic.text().strip()
        if not topic:
            self.lbl_status.setText("❌ Vui lòng nhập tiêu đề video!")
            return None

        target_mins = self.spin_mins.value()
        parts_raw   = self.cmb_parts.currentText()
        parts       = parts_raw if parts_raw == "Auto" else int(parts_raw)
        topic_strategy = self.current_topic_strategy
        if topic_strategy and topic_strategy.get("selected_title_text") != topic:
            topic_strategy = {}

        return {
            "topic"         : topic,
            "dna_content"   : self.dna_content,
            "style_content" : self.style_content,
            "lang"          : self.cmb_lang.currentText(),
            "structure"     : self.cmb_struct.currentText(),
            "pov"           : self.cmb_pov.currentText(),
            "parts"         : parts,
            "target_mins"   : target_mins,
            "target_words"  : target_mins * 155,
            "extra_context" : self.txt_extra.toPlainText().strip(),
            "topic_strategy": topic_strategy,
            # research_notes injected separately
        }

    def _set_buttons_busy(self, busy: bool):
        self.btn_research.setEnabled(not busy)
        self.btn_write.setEnabled(not busy)

    def _on_research_edited(self):
        """Keep internal _research_notes in sync when user edits the box."""
        self._research_notes = self.txt_research.toPlainText()

    def _clear_research(self):
        self._research_notes = ""
        self.txt_research.clear()
        self.lbl_research_state.setText(
            "💡 Research đã xoá — viết tiếp sẽ không có research"
        )
        self.lbl_research_state.setStyleSheet(
            "color: #606075; font-size: 11px; font-style: italic;"
        )

    # ============================================================
    #  FLOW 1 — RESEARCH
    # ============================================================

    def _run_research(self):
        config = self._build_config()
        if config is None:
            return

        self._last_config = config
        self._set_buttons_busy(True)
        self.txt_research.clear()
        self.progress_bar.setValue(10)
        self.lbl_status.setText("🔍 Đang research...")
        self.lbl_research_state.setText("⏳ Đang thu thập dữ liệu...")
        self.lbl_research_state.setStyleSheet(
            "color: #F5A623; font-size: 11px; font-style: italic;"
        )

        self._research_worker = ResearchWorker(config)
        self._research_worker.progress_signal.connect(self.lbl_status.setText)
        self._research_worker.research_signal.connect(self._on_research_done)
        self._research_worker.error_signal.connect(self._on_research_error)
        self._research_worker.finished_signal.connect(self._on_research_finished)
        self._research_worker.start()

    def _on_research_done(self, notes: str):
        self._research_notes = notes
        self.txt_research.setPlainText(notes)
        self.lbl_research_state.setText(
            "✅ Research xong — kiểm tra notes rồi bấm ✍️ VIẾT KỊCH BẢN"
        )
        self.lbl_research_state.setStyleSheet(
            "color: #3AD68A; font-size: 11px; font-weight: bold;"
        )
        self.progress_bar.setValue(60)

    def _on_research_error(self, msg: str):
        self.txt_research.setPlainText(msg)
        self.lbl_research_state.setText("❌ Research thất bại — xem lỗi ở research box")
        self.lbl_research_state.setStyleSheet(
            "color: #FF4D4D; font-size: 11px; font-style: italic;"
        )

    def _on_research_finished(self):
        self._set_buttons_busy(False)
        self.progress_bar.setValue(0)

    # ============================================================
    #  FLOW 2 — WRITE SCRIPT
    # ============================================================

    def _run_write(self):
        config = self._build_config()
        if config is None:
            return

        # Attach research notes (may be empty → no research injected)
        config["research_notes"] = self._research_notes

        self._set_buttons_busy(True)
        self.txt_output.clear()
        self.progress_bar.setValue(10)

        if self._research_notes.strip():
            self.lbl_status.setText("✍️ Đang viết kịch bản (có research)...")
        else:
            self.lbl_status.setText("✍️ Đang viết kịch bản (không research)...")

        self._script_worker = ScriptWorker(config)
        self._script_worker.progress_signal.connect(self.lbl_status.setText)
        self._script_worker.result_signal.connect(self.txt_output.setPlainText)
        self._script_worker.finished_signal.connect(self._on_write_finished)
        self._script_worker.start()

    def _on_write_finished(self):
        self._set_buttons_busy(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("✅ Hoàn thành")

    def _load_topic_from_profile(self):
        ACTIVE_PROFILE_FILE = "active_profile.json"
        if not os.path.exists(ACTIVE_PROFILE_FILE):
            QMessageBox.warning(self, "Chưa có Profile", "Vui lòng chọn một Profile đang hoạt động trước.")
            return
        try:
            with open(ACTIVE_PROFILE_FILE, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            QMessageBox.critical(self, "Lỗi Profile", "Không thể đọc file active_profile.json.")
            return
            
        topics = profile_data.get("topics", [])
        if not topics:
            QMessageBox.information(self, "Trống", "Profile hiện tại chưa có topic nào được lưu từ Tool 0.")
            return
            
        selection_items = []
        self.topic_map = {} 
        
        for t in topics:
            topic_name = t.get("title", "Không tên")
            sub_titles = t.get("titles", [])
            for st in sub_titles:
                st_text = st.get("text", "")
                if st_text:
                    display_text = f"[{topic_name[:30]}...] {st_text}"
                    selection_items.append(display_text)
                    topic_strategy = t.copy()
                    topic_strategy["selected_title"] = st
                    topic_strategy["selected_title_text"] = st_text
                    self.topic_map[display_text] = {
                        "topic_title": topic_name,
                        "selected_subtitle": st_text,
                        "topic_strategy": topic_strategy
                    }
            
        if not selection_items:
            QMessageBox.information(self, "Trống", "Không tìm thấy tiêu đề phụ nào trong các topic đã lưu.")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Chọn Tiêu Đề")
        dialog.resize(600, 450)
        dialog.setStyleSheet("""
            QDialog { background-color: #0F0F18; border: 1px solid #252535; }
            QLabel { color: #E8E8F0; font-size: 14px; font-weight: bold; margin-bottom: 5px; }
            QListWidget { background-color: #18182B; border: 1px solid #282840; border-radius: 8px; padding: 5px; color: #E8E8F0; font-size: 14px; outline: none; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #252535; }
            QListWidget::item:hover { background-color: #202035; }
            QListWidget::item:selected { background-color: rgba(90, 79, 204, 0.3); border-radius: 6px; border: 1px solid #5A4FCC; color: #FFF; }
            QPushButton { background: #282840; color: #D0D0E0; border-radius: 6px; padding: 8px 20px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background: #353545; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Chọn 1 tiêu đề (từ các Topic đã lưu):"))
        
        list_widget = QListWidget()
        list_widget.setWordWrap(True)
        list_widget.addItems(selection_items)
        layout.addWidget(list_widget)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        
        btn_ok = btn_box.button(QDialogButtonBox.StandardButton.Ok)
        btn_ok.setText("Chọn Tiêu Đề")
        btn_ok.setStyleSheet("background: #E8742A; color: #000; border-radius: 6px; padding: 8px 20px; font-weight: bold;")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        
        layout.addWidget(btn_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            current_item = list_widget.currentItem()
            if current_item:
                selected_item = current_item.text()
                mapped_data = self.topic_map.get(selected_item)
                if mapped_data:
                    self.txt_topic.setText(mapped_data["selected_subtitle"])
                    self.current_topic_title = mapped_data["topic_title"]
                    self.current_topic_strategy = mapped_data.get("topic_strategy", {})

    def _save_script_to_profile(self):
        script_title = self.txt_topic.text().strip()
        if not script_title:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập hoặc chọn Chủ đề video trước khi lưu!")
            return

        topic_title_to_save = getattr(self, 'current_topic_title', script_title)
        if not topic_title_to_save:
            topic_title_to_save = script_title

        script_content = self.txt_output.toPlainText().strip()
        if not script_content:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy nội dung kịch bản để lưu. Hãy đảm bảo bạn đã tạo kịch bản xong!")
            return
            
        research_content = self._research_notes

        ACTIVE_PROFILE_FILE = "active_profile.json"
        try:
            with open(ACTIVE_PROFILE_FILE, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
        except Exception:
            profile_data = {"topics": []}
            
        topics = profile_data.get("topics", [])
        topic_found = False
        for t in topics:
            if t.get("title") == topic_title_to_save:
                t["script"] = {
                    "title": script_title,
                    "content": script_content,
                    "research": research_content
                }
                topic_found = True
                break
                
        if not topic_found:
            profile_data.setdefault("topics", []).append({
                "title": topic_title_to_save,
                "script": {"title": script_title, "content": script_content, "research": research_content}
            })
            
        try:
            with open(ACTIVE_PROFILE_FILE, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Thành công", f"Đã lưu kịch bản và research cho topic:\n'{topic_title_to_save[:30]}...' \nvào Profile!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu file:\n{e}")
