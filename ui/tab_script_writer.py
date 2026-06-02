from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea, QFrame, QSpinBox, 
                             QRadioButton, QButtonGroup, QProgressBar)
from PyQt6.QtCore import Qt
from ui.components import DropZoneWidget
from threads.script_worker import ScriptWorker

class ScriptWriterTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 0, 10, 0) # Xóa lề dọc để tiết kiệm không gian
        
        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        vbox_h = QVBoxLayout()
        vbox_h.setSpacing(0)
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
        lay.setSpacing(2) # Nén khoảng cách giữa các hàng cực hạn

        # --- CONTEXT FILES ---
        self.style_content = ""
        self.dna_content = ""

        lay.addWidget(QLabel("CONTEXT FILES", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)
        
        self.dz_style = DropZoneWidget("📋", "STYLE GUIDE", "Upload .md hoặc .txt")
        self.dz_dna = DropZoneWidget("🧬", "DNA KÊNH", "Upload .md hoặc .txt")
        self.dz_topic = DropZoneWidget("📝", "CHỦ ĐỀ (OPTIONAL)", "Upload .md hoặc .txt")
        
        self.dz_style.file_loaded.connect(lambda p, c: setattr(self, 'style_content', c))
        self.dz_dna.file_loaded.connect(lambda p, c: setattr(self, 'dna_content', c))
        
        ctx_lay.addWidget(self.dz_style)
        ctx_lay.addWidget(self.dz_dna)
        ctx_lay.addWidget(self.dz_topic)
        lay.addLayout(ctx_lay)

        # --- CHỦ ĐỀ VIDEO ---
        lay.addWidget(QLabel("CHỦ ĐỀ VIDEO", objectName="section_label"))
        h_topic = QHBoxLayout()
        self.txt_topic = QLineEdit()
        self.txt_topic.setPlaceholderText("VD: POV: Bạn là đặc vụ CIA bị phản bội...")
        self.btn_get_topic = QPushButton("Lấy từ Tool 0")
        self.btn_get_topic.setObjectName("btn_sec")
        h_topic.addWidget(self.txt_topic)
        h_topic.addWidget(self.btn_get_topic)
        lay.addLayout(h_topic)

        # --- CÀI ĐẶT ---
        lay.addWidget(QLabel("CÀI ĐẶT", objectName="section_label"))
        grid = QGridLayout()
        grid.setSpacing(14)
        
        grid.addWidget(QLabel("NGÔN NGỮ", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("CẤU TRÚC", objectName="muted"), 0, 1)
        grid.addWidget(QLabel("POV STYLE", objectName="muted"), 0, 2)
        grid.addWidget(QLabel("SỐ PHẦN", objectName="muted"), 0, 3)
        grid.addWidget(QLabel("TARGET PHÚT", objectName="muted"), 0, 4)
        
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Tiếng Việt", "English", "Español", "Portuguese", "Deutsch"])
        grid.addWidget(self.cmb_lang, 1, 0)

        self.cmb_struct = QComboBox()
        self.cmb_struct.addItems(["Auto", "Levels - Escalation", "Acts - Story Arc", "Timeline", "Chapters", "Parts", "Custom"])
        grid.addWidget(self.cmb_struct, 1, 1)

        self.cmb_pov = QComboBox()
        self.cmb_pov.addItems(["Ngôi thứ 2 (Bạn)", "Ngôi 1 hỗn hợp", "Mixed", "Ngôi thứ 3", "Narrator", "Custom"])
        grid.addWidget(self.cmb_pov, 1, 2)

        self.cmb_parts = QComboBox()
        self.cmb_parts.addItems(["Auto"] + [f"{i} phần" for i in range(5, 13)])
        grid.addWidget(self.cmb_parts, 1, 3)

        h_target = QHBoxLayout()
        self.spin_mins = QSpinBox()
        self.spin_mins.setRange(1, 60)
        self.spin_mins.setValue(10)
        self.lbl_words = QLabel("(Khoảng 1550 từ)")
        self.lbl_words.setStyleSheet("color: #3AD68A; font-weight: bold; font-size: 11px;")
        self.spin_mins.valueChanged.connect(self._update_word_count)
        
        h_target.addWidget(self.spin_mins)
        h_target.addWidget(self.lbl_words)
        grid.addLayout(h_target, 1, 4)
        
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
        self.cmb_ai.setFixedWidth(220) # Thu nhỏ chiều rộng combobox
        
        ai_lay = QHBoxLayout()
        ai_lay.addWidget(self.cmb_ai)
        ai_lay.addStretch()
        lay.addLayout(ai_lay)

        # --- CONTEXT BỔ SUNG ---
        lay.addWidget(QLabel("CONTEXT BỔ SUNG (OPTIONAL)", objectName="section_label"))
        self.txt_extra = QTextEdit()
        self.txt_extra.setPlaceholderText("Nhân vật, bối cảnh, twist muốn có, tone cụ thể...\n\nTip: Nếu chọn Auto structure, Claude sẽ tự quyết định số phần và tên từng phần phù hợp nhất với topic.")
        self.txt_extra.setMinimumHeight(40) # Thu nhỏ ô context
        lay.addWidget(self.txt_extra)

        # --- TOKEN COUNTER ---
        lbl_token = QLabel("✓ Input ~14k tokens / 28K")
        lbl_token.setStyleSheet("background-color: rgba(58,214,138,0.1); color: #3AD68A; border: 1px solid rgba(58,214,138,0.3); border-radius: 6px; padding: 12px 16px; font-weight: bold; font-size: 13px;")
        
        token_lay = QHBoxLayout()
        token_lay.addWidget(lbl_token)
        token_lay.addStretch() # Chặn để ô token không bị kéo dài ra toàn màn hình
        lay.addLayout(token_lay)

        # --- CHẾ ĐỘ CHẠY ---
        lay.addWidget(QLabel("CHẾ ĐỘ CHẠY", objectName="section_label"))
        exec_lay = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.radio_write = QRadioButton("Viết ngay (Không cần research)")
        self.radio_research = QRadioButton("Research thông tin trước khi viết")
        self.radio_research.setChecked(True)
        self.mode_group.addButton(self.radio_write)
        self.mode_group.addButton(self.radio_research)
        exec_lay.addWidget(self.radio_write)
        exec_lay.addWidget(self.radio_research)
        exec_lay.addStretch()
        lay.addLayout(exec_lay)

        # --- XỬ LÝ & KẾT QUẢ ---
        lay.addWidget(QLabel("TRẠNG THÁI & KẾT QUẢ", objectName="section_label"))
        
        status_lay = QHBoxLayout()
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet("color: #606075; font-style: italic;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        status_lay.addWidget(self.lbl_status)
        status_lay.addWidget(self.progress_bar)
        lay.addLayout(status_lay)

        self.btn_generate = QPushButton("✍️ VIẾT KỊCH BẢN", objectName="btn_primary")
        self.btn_generate.setFixedHeight(35) # Giảm chiều cao nút bấm chính
        self.btn_generate.clicked.connect(self._generate_script)
        lay.addWidget(self.btn_generate)

        self.txt_output = QTextEdit()
        self.txt_output.setPlaceholderText("Kịch bản hoàn chỉnh sẽ hiển thị ở đây. Bạn có thể chỉnh sửa trực tiếp...")
        self.txt_output.setMinimumHeight(60) # Ép thanh cuộn hoạt động sớm hơn
        self.txt_output.setStyleSheet("font-size: 15px; line-height: 1.6;")
        lay.addWidget(self.txt_output)

        # Ép tất cả các thẻ lên trên cùng để gọn gàng
        lay.addStretch() 
        
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

    def _update_word_count(self, mins):
        self.lbl_words.setText(f"(Khoảng {mins * 155} từ)")

    def _generate_script(self):
        topic = self.txt_topic.text().strip()
        if not topic:
            self.lbl_status.setText("❌ Vui lòng nhập tiêu đề!")
            return

        self.btn_generate.setEnabled(False)
        self.txt_output.clear()
        self.progress_bar.setValue(10)
        self.lbl_status.setText("🤖 Đang khởi tạo AI...")

        target_mins = self.spin_mins.value()

        config = {
            "topic": topic,
            "dna_content": getattr(self, 'dna_content', ''),
            "style_content": getattr(self, 'style_content', ''),
            "lang": self.cmb_lang.currentText(),
            "structure": self.cmb_struct.currentText(),
            "pov": self.cmb_pov.currentText(),
            "parts": self.cmb_parts.currentText(),
            "target_mins": target_mins,
            "target_words": target_mins * 155,
            "research": self.radio_research.isChecked()
        }

        self.worker = ScriptWorker(config)
        self.worker.progress_signal.connect(lambda msg: self.lbl_status.setText(msg))
        self.worker.result_signal.connect(lambda txt: self.txt_output.setPlainText(txt))
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self):
        self.btn_generate.setEnabled(True)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("✅ Hoàn thành")