import os
import subprocess
import sys
import threading

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from .glabs_engine import run_auto

    ENGINE_OK = True
except ImportError:
    ENGINE_OK = False


class ClickableImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.filepath:
            try:
                if sys.platform == "win32":
                    os.startfile(self.filepath)
                elif sys.platform == "darwin":
                    subprocess.call(["open", self.filepath])
                else:
                    subprocess.call(["xdg-open", self.filepath])
            except Exception as exc:
                print(f"Cannot open image: {exc}")
        super().mousePressEvent(event)


class OutputImageContainer(QWidget):
    def __init__(self, expected_images=2, parent=None):
        super().__init__(parent)
        self.current_fill_idx = 0
        self.image_labels = []

        layout = QGridLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        if expected_images == 1:
            size, font_size = 78, 20
        elif expected_images == 2:
            size, font_size = 68, 18
        else:
            size, font_size = 52, 16

        for idx in range(expected_images):
            label = ClickableImageLabel()
            label.setFixedSize(size, size)
            label.setText("...")
            label.setStyleSheet(
                f"background:#111421; border:1px dashed #30344F; border-radius:8px; "
                f"color:#6E789A; font-size:{font_size}px;"
            )

            if expected_images == 1:
                layout.addWidget(label, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            elif expected_images == 2:
                layout.addWidget(label, 0, idx, alignment=Qt.AlignmentFlag.AlignCenter)
            elif expected_images == 3:
                if idx < 2:
                    layout.addWidget(label, 0, idx, alignment=Qt.AlignmentFlag.AlignCenter)
                else:
                    layout.addWidget(label, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                row, col = divmod(idx, 2)
                layout.addWidget(label, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

            self.image_labels.append(label)

    def add_loaded_image(self, filepath):
        if self.current_fill_idx >= len(self.image_labels):
            return

        label = self.image_labels[self.current_fill_idx]
        label.filepath = filepath

        try:
            pixmap = QPixmap(filepath)
            scaled = pixmap.scaled(
                label.width() - 4,
                label.height() - 4,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            label.setPixmap(scaled)
            label.setText("")
            label.setStyleSheet("background:#111421; border:2px solid #29D391; border-radius:8px; padding:2px;")
        except Exception:
            label.setText("ERR")
            label.setStyleSheet("background:#241515; border:2px solid #E05252; border-radius:8px; color:#E05252;")

        self.current_fill_idx += 1


class GLabsAutomationTab(QWidget):
    def __init__(self):
        super().__init__()
        self.engine_thread = None
        self.is_running = False
        self.manual_references = {}
        self._setup_ui()
        self._connect_signals()
        self._refresh_prompt_count()

    def _connect_signals(self):
        self.btn_import.clicked.connect(self._import_file)
        self.btn_choose_ref.clicked.connect(lambda: self._choose_dir(self.txt_ref_dir))
        self.btn_choose_out.clicked.connect(lambda: self._choose_dir(self.txt_out_dir))
        self.btn_run.clicked.connect(self._start_engine)
        self.btn_clear.clicked.connect(self._clear_inputs)
        self.txt_prompts.textChanged.connect(self._refresh_prompt_count)
        self.cmb_model.currentTextChanged.connect(lambda: self._sync_queue_preview() if not self.is_running else None)
        self.cmb_ratio.currentTextChanged.connect(lambda: self._sync_queue_preview() if not self.is_running else None)
        self.cmb_amt.currentTextChanged.connect(lambda: self._sync_queue_preview() if not self.is_running else None)

    def _setup_ui(self):
        self.setStyleSheet(
            """
            QWidget { background:#121B2D; color:#F3F7FF; font-family:'Segoe UI', sans-serif; font-size:13px; }
            QLabel#title { color:#FFFFFF; font-size:22px; font-weight:800; }
            QLabel#subtitle { color:#DCEAFF; font-size:11px; font-weight:700; }
            QLabel#section { color:#D8E6FF; font-size:12px; font-weight:700; }
            QLabel#field { color:#F3F7FF; font-size:12px; }
            QLabel#hint { color:#91A5C8; font-size:12px; }
            QLabel#badge_ok { background:#E93E32; color:#FFFFFF; border:none; border-radius:14px; padding:7px 14px; font-weight:800; }
            QLabel#badge_warn { background:#A56A22; color:#FFFFFF; border:none; border-radius:14px; padding:7px 14px; font-weight:800; }
            QFrame#panel { background:#16243C; border:1px solid #2C4268; border-radius:10px; }
            QFrame#subpanel { background:#1A2944; border:1px solid #2E456F; border-radius:8px; }
            QLineEdit, QComboBox, QTextEdit {
                background:#1B2B48; border:1px solid #35527F; border-radius:8px; color:#FFFFFF; padding:8px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border-color:#7D8CFF; }
            QTextEdit { line-height:1.35; }
            QCheckBox { color:#F3F7FF; spacing:8px; }
            QCheckBox::indicator { width:17px; height:17px; border:1px solid #6F86AD; border-radius:4px; background:#17233A; }
            QCheckBox::indicator:checked { background:#23C75A; border-color:#23C75A; }
            QPushButton { background:#213555; border:1px solid #3B5A89; border-radius:8px; color:#FFFFFF; padding:8px 12px; font-weight:700; }
            QPushButton:hover { border-color:#83A2FF; background:#263D62; }
            QPushButton:disabled { color:#6F7C8D; border-color:#3A4657; background:#CBD2D9; }
            QPushButton#run { background:#19D885; border:none; color:#FFFFFF; padding:13px 16px; font-size:15px; font-weight:900; }
            QPushButton#pause { background:#CBD2D9; border:none; color:#6E7B86; padding:13px 16px; font-weight:900; }
            QPushButton#secondary { background:#7D55C7; border:none; }
            QPushButton#outline { background:#1B2B48; border:1px solid #455F91; }
            QPushButton#danger { background:#213555; border:1px solid #3B5A89; color:#FFFFFF; }
            QPushButton#accordion { background:#1A2944; border:1px solid #2E456F; border-radius:8px; color:#FFFFFF; padding:9px 10px; text-align:left; font-weight:800; }
            QPushButton#accordion:checked { border-color:#25C8E8; }
            QTabWidget::pane { border:none; background:#121B2D; }
            QTabBar::tab { background:#18253C; color:#91A5C8; border:1px solid #2D4268; padding:10px 18px; min-width:120px; font-weight:800; }
            QTabBar::tab:selected { background:#1B2F52; color:#FFFFFF; border-color:#7D8CFF; }
            QTableWidget { background:#15233A; border:1px solid #2C4268; border-radius:8px; gridline-color:#263A5C; }
            QHeaderView::section { background:#192943; color:#FFFFFF; border:none; border-right:1px solid #2C4268; border-bottom:2px solid #7D8CFF; padding:10px; font-weight:800; }
            QTableWidget::item { border-bottom:1px solid #263A5C; padding:8px; }
            QTableWidget::item:selected { background:#243D66; }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)

        self.flow_tabs = QTabWidget()
        self.flow_tabs.addTab(self._build_image_flow_page(), "Flow Image")
        self.flow_tabs.addTab(self._build_video_flow_page(), "Flow Video")
        root.addWidget(self.flow_tabs, 1)

    def _build_image_flow_page(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 10, 0, 0)
        root.setSpacing(12)

        left_widget = QWidget()
        left_widget.setFixedWidth(390)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        root.addWidget(left_widget, 0)

        self.lbl_engine = QLabel("Ready" if ENGINE_OK else "Engine missing")
        self.lbl_engine.setObjectName("badge_ok" if ENGINE_OK else "badge_warn")

        prompt_panel = self._panel("Configuration & Prompts")
        prompt_lay = prompt_panel.layout()

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["Nano Banana 2", "Nano Banana Pro", "Imagen 4"])
        self.cmb_ratio = QComboBox()
        self.cmb_ratio.addItems(["16:9", "9:16", "1:1", "4:3", "3:4"])
        self.cmb_amt = QComboBox()
        self.cmb_amt.addItems(["1x", "2x", "3x", "4x"])
        self.cmb_amt.setCurrentText("2x")
        self.cmb_quality = QComboBox()
        self.cmb_quality.addItems(["Default", "1K", "2K", "4K"])
        self.cmb_quality.setEnabled(False)

        grid.addWidget(self._field_label("Model"), 0, 0)
        grid.addWidget(self.cmb_model, 1, 0)
        grid.addWidget(self._field_label("Aspect ratio"), 0, 1)
        grid.addWidget(self.cmb_ratio, 1, 1)
        grid.addWidget(self._field_label("Images / prompt"), 2, 0)
        grid.addWidget(self.cmb_amt, 3, 0)
        grid.addWidget(self._field_label("Quality"), 2, 1)
        grid.addWidget(self.cmb_quality, 3, 1)

        self.txt_concurrency = QLineEdit("1")
        self.txt_delay_min = QLineEdit("5 s")
        self.txt_delay_max = QLineEdit("10 s")
        self.cmb_ref_mode = QComboBox()
        self.cmb_ref_mode.addItems(["Default", "Manual per row", "Auto match"])
        grid.addWidget(self._field_label("Concurrent runs"), 4, 0)
        grid.addWidget(self.txt_concurrency, 5, 0)
        grid.addWidget(self._field_label("Delay between runs"), 4, 1)
        delay_row = QHBoxLayout()
        delay_row.addWidget(self.txt_delay_min)
        delay_row.addWidget(QLabel("-"))
        delay_row.addWidget(self.txt_delay_max)
        grid.addLayout(delay_row, 5, 1)
        grid.addWidget(self._field_label("Reference mode"), 6, 0)
        grid.addWidget(self.cmb_ref_mode, 7, 0)
        prompt_lay.addLayout(grid)

        self.chk_seed = QCheckBox("Lock seed")
        self.txt_seed = QLineEdit()
        self.txt_seed.setPlaceholderText("Optional seed")
        seed_row = QHBoxLayout()
        seed_row.addWidget(self.txt_seed, 1)
        seed_row.addWidget(self.chk_seed)
        prompt_lay.addLayout(seed_row)

        import_row = QHBoxLayout()
        self.btn_import = QPushButton("Import TXT/Excel")
        self.btn_import.setObjectName("secondary")
        self.lbl_prompt_count = QLabel("0 prompt")
        self.lbl_prompt_count.setObjectName("hint")
        import_row.addWidget(self.btn_import, 1)
        import_row.addWidget(self.lbl_prompt_count, 1)
        prompt_lay.addLayout(import_row)

        self.txt_prompts = QTextEdit()
        self.txt_prompts.setMinimumHeight(150)
        self.txt_prompts.setPlaceholderText("Enter prompts here")
        prompt_lay.addWidget(self.txt_prompts, 1)

        self.chk_task_folder = QCheckBox("Create task folder")
        self.chk_task_folder.setChecked(True)
        prompt_lay.addWidget(self.chk_task_folder)

        prompt_lay.addWidget(self._field_label("Reference folder"))
        ref_row = QHBoxLayout()
        self.txt_ref_dir = QLineEdit("")
        self.txt_ref_dir.setPlaceholderText("reference_image")
        self.btn_choose_ref = QPushButton("Open")
        ref_row.addWidget(self.txt_ref_dir, 1)
        ref_row.addWidget(self.btn_choose_ref)
        prompt_lay.addLayout(ref_row)

        prompt_lay.addWidget(self._field_label("Output folder"))
        out_row = QHBoxLayout()
        self.txt_out_dir = QLineEdit("outputs/glabs_images")
        self.btn_choose_out = QPushButton("Open")
        out_row.addWidget(self.txt_out_dir, 1)
        out_row.addWidget(self.btn_choose_out)
        prompt_lay.addLayout(out_row)
        left.addWidget(prompt_panel, 1)

        run_row = QHBoxLayout()
        self.btn_run = QPushButton("RUN NOW")
        self.btn_run.setObjectName("run")
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("danger")
        run_row.addWidget(self.btn_run, 2)
        run_row.addWidget(self.btn_clear, 1)
        left.addLayout(run_row)

        right = QVBoxLayout()
        right.setSpacing(10)
        root.addLayout(right, 1)

        output_header = QFrame()
        output_header.setObjectName("subpanel")
        output_lay = QHBoxLayout(output_header)
        output_lay.setContentsMargins(14, 10, 14, 10)
        output_title = QLabel("Queue & Results")
        output_title.setObjectName("section")
        self.lbl_run_status = QLabel("Idle")
        self.lbl_run_status.setObjectName("hint")
        output_lay.addWidget(output_title)
        output_lay.addStretch()
        output_lay.addWidget(self.lbl_run_status)
        right.addWidget(output_header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["", "No.", "Reference", "Prompt", "Settings", "Output", "Progress"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(32)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 38)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 44)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 220)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 150)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 165)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 105)

        right.addWidget(self.table, 1)
        return page

    def _build_video_flow_page(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(0, 10, 0, 0)
        root.setSpacing(12)

        left_widget = QWidget()
        left_widget.setFixedWidth(390)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        root.addWidget(left_widget, 0)

        panel = self._panel("Configuration & Prompts")
        lay = panel.layout()

        basic_btn = QPushButton("Basic settings  [open]")
        basic_btn.setObjectName("accordion")
        basic_btn.setCheckable(True)
        basic_btn.setChecked(True)
        lay.addWidget(basic_btn)

        basic_content = QFrame()
        basic_content.setObjectName("subpanel")
        basic_lay = QVBoxLayout(basic_content)
        basic_lay.setContentsMargins(10, 10, 10, 10)
        basic_grid = QGridLayout()
        basic_grid.setHorizontalSpacing(8)
        basic_grid.setVerticalSpacing(8)
        video_model = QComboBox()
        video_model.addItems(["Veo3 Fast [10 Credit]", "Veo3 Quality", "Veo2"])
        video_ratio = QComboBox()
        video_ratio.addItems(["16:9 Landscape", "9:16 Portrait", "1:1 Square"])
        video_concurrency = QLineEdit("1")
        video_count = QLineEdit("1")
        video_output = QLineEdit("outputs/glabs_videos")
        video_output_btn = QPushButton("Open")
        basic_grid.addWidget(self._field_label("Model"), 0, 0)
        basic_grid.addWidget(self._field_label("Video ratio"), 0, 1)
        basic_grid.addWidget(video_model, 1, 0)
        basic_grid.addWidget(video_ratio, 1, 1)
        basic_grid.addWidget(self._field_label("Concurrent runs"), 2, 0)
        basic_grid.addWidget(self._field_label("Videos / prompt"), 2, 1)
        basic_grid.addWidget(video_concurrency, 3, 0)
        basic_grid.addWidget(video_count, 3, 1)
        basic_grid.addWidget(self._field_label("Output folder"), 4, 0, 1, 2)
        output_row = QHBoxLayout()
        output_row.addWidget(video_output, 1)
        output_row.addWidget(video_output_btn)
        basic_grid.addLayout(output_row, 5, 0, 1, 2)
        basic_lay.addLayout(basic_grid)
        lay.addWidget(basic_content)

        advanced_btn = QPushButton("Advanced settings  [closed]")
        advanced_btn.setObjectName("accordion")
        advanced_btn.setCheckable(True)
        advanced_btn.setChecked(False)
        lay.addWidget(advanced_btn)

        advanced_content = QFrame()
        advanced_content.setObjectName("subpanel")
        advanced_lay = QVBoxLayout(advanced_content)
        advanced_lay.setContentsMargins(10, 10, 10, 10)
        advanced_grid = QGridLayout()
        advanced_grid.setHorizontalSpacing(8)
        advanced_grid.setVerticalSpacing(8)
        quality = QComboBox()
        quality.addItems(["HD", "FHD", "4K"])
        seed = QLineEdit("503233")
        lock_seed = QCheckBox("Lock seed")
        ref_type = QComboBox()
        ref_type.addItems(["Default", "First frame", "First & last frame"])
        delay_min = QLineEdit("10 s")
        delay_max = QLineEdit("20 s")
        duration = QComboBox()
        duration.addItems(["4s", "6s", "8s", "10s"])
        ref_folder = QLineEdit("reference_image")
        ref_folder_btn = QPushButton("Open")
        advanced_grid.addWidget(self._field_label("Quality"), 0, 0)
        advanced_grid.addWidget(self._field_label("Seed"), 0, 1)
        advanced_grid.addWidget(quality, 1, 0)
        seed_row = QHBoxLayout()
        seed_row.addWidget(seed, 1)
        seed_row.addWidget(lock_seed)
        advanced_grid.addLayout(seed_row, 1, 1)
        advanced_grid.addWidget(self._field_label("Reference type"), 2, 0)
        advanced_grid.addWidget(self._field_label("Delay between runs"), 2, 1)
        advanced_grid.addWidget(ref_type, 3, 0)
        video_delay_row = QHBoxLayout()
        video_delay_row.addWidget(delay_min)
        video_delay_row.addWidget(QLabel("-"))
        video_delay_row.addWidget(delay_max)
        advanced_grid.addLayout(video_delay_row, 3, 1)
        advanced_grid.addWidget(self._field_label("Video duration"), 4, 0)
        advanced_grid.addWidget(duration, 5, 0)
        advanced_grid.addWidget(self._field_label("Reference folder"), 6, 0, 1, 2)
        ref_video_row = QHBoxLayout()
        ref_video_row.addWidget(ref_folder, 1)
        ref_video_row.addWidget(ref_folder_btn)
        advanced_grid.addLayout(ref_video_row, 7, 0, 1, 2)
        advanced_lay.addLayout(advanced_grid)
        advanced_content.setVisible(False)
        lay.addWidget(advanced_content)

        def set_video_settings_open(section):
            basic_open = section == "basic"
            basic_content.setVisible(basic_open)
            advanced_content.setVisible(not basic_open)
            basic_btn.setChecked(basic_open)
            advanced_btn.setChecked(not basic_open)
            basic_btn.setText("Basic settings  [open]" if basic_open else "Basic settings  [closed]")
            advanced_btn.setText("Advanced settings  [open]" if not basic_open else "Advanced settings  [closed]")

        basic_btn.clicked.connect(lambda checked=False: set_video_settings_open("basic"))
        advanced_btn.clicked.connect(lambda checked=False: set_video_settings_open("advanced"))

        import_row = QHBoxLayout()
        btn_import_video = QPushButton("Import TXT/Excel")
        btn_import_video.setObjectName("secondary")
        import_row.addWidget(btn_import_video, 1)
        import_row.addWidget(QLabel("0 rows / 0 prompts"), 1)
        lay.addLayout(import_row)

        txt_video_prompts = QTextEdit()
        txt_video_prompts.setMinimumHeight(180)
        txt_video_prompts.setPlaceholderText("Enter prompts here")
        lay.addWidget(txt_video_prompts, 1)
        lay.addWidget(QCheckBox("Use one prompt for all rows"))
        left.addWidget(panel, 1)

        row = QHBoxLayout()
        btn_add = QPushButton("Add to queue")
        btn_add.setObjectName("outline")
        btn_manage = QPushButton("Manage queue (0)")
        btn_manage.setObjectName("outline")
        row.addWidget(btn_add)
        row.addWidget(btn_manage)
        left.addLayout(row)

        controls = QHBoxLayout()
        run = QPushButton("RUN NOW")
        run.setObjectName("run")
        pause = QPushButton("PAUSE")
        pause.setObjectName("pause")
        stop = QPushButton("STOP")
        stop.setObjectName("pause")
        run.setEnabled(False)
        pause.setEnabled(False)
        stop.setEnabled(False)
        controls.addWidget(run)
        controls.addWidget(pause)
        controls.addWidget(stop)
        left.addLayout(controls)

        right = QVBoxLayout()
        root.addLayout(right, 1)
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["", "No.", "Type", "Start - End Image", "Prompt", "Output", "Progress"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(32)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, 38)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 52)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 64)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(3, 220)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(5, 165)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(6, 105)
        right.addWidget(table, 1)

        bottom = QHBoxLayout()
        for text in ["Start image", "End image", "Delete", "Clear all", "Clear cache", "Retry failed", "Run selected", "Open session"]:
            btn = QPushButton(text)
            btn.setObjectName("outline")
            bottom.addWidget(btn)
        right.addLayout(bottom)
        return page

    def _panel(self, title_text):
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title = QLabel(title_text)
        title.setObjectName("section")
        layout.addWidget(title)
        return panel

    def _field_label(self, text):
        label = QLabel(text)
        label.setObjectName("field")
        return label

    def _refresh_prompt_count(self):
        if not hasattr(self, "txt_prompts"):
            return
        count = len(self._prompt_lines())
        self.lbl_prompt_count.setText(f"{count} prompt" if count == 1 else f"{count} prompts")
        if not self.is_running:
            self._sync_queue_preview()

    def _prompt_lines(self):
        return [line.strip() for line in self.txt_prompts.toPlainText().splitlines() if line.strip()]

    def _clear_inputs(self):
        self.txt_prompts.clear()
        self.manual_references.clear()
        self.table.setRowCount(0)
        self.lbl_run_status.setText("Idle")

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose prompt file",
            "",
            "Prompt Files (*.txt *.xlsx *.xls);;Text Files (*.txt);;Excel Files (*.xlsx *.xls)",
        )
        if not path:
            return

        if path.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8") as handle:
                self.txt_prompts.setPlainText(handle.read())
            return

        try:
            import pandas as pd

            df = pd.read_excel(path)
            prompts = "\n".join(df.iloc[:, 0].dropna().astype(str).tolist())
            self.txt_prompts.setPlainText(prompts)
        except ImportError:
            QMessageBox.warning(self, "Missing dependency", "Install pandas to import Excel prompt files.")
        except Exception as exc:
            QMessageBox.warning(self, "Import failed", str(exc))

    def _choose_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if dir_path:
            line_edit.setText(dir_path)

    def _start_engine(self):
        if not ENGINE_OK:
            QMessageBox.critical(self, "Engine missing", "Cannot load ui/glabs_engine.py.")
            return

        prompts = self._prompt_lines()
        if not prompts:
            QMessageBox.warning(self, "Missing prompts", "Paste or import at least one prompt.")
            return

        try:
            expected_images = int(self.cmb_amt.currentText().replace("x", ""))
        except ValueError:
            expected_images = 2
        try:
            worker_count = max(1, min(3, int(self.txt_concurrency.text().strip())))
        except ValueError:
            worker_count = 1

        task_name = os.path.basename(self.txt_out_dir.text().strip())
        if not task_name or task_name == "glabs_images":
            import datetime

            task_name = datetime.datetime.now().strftime("Task_%m%d_%H%M")

        config = {
            "prompts": prompts,
            "save_dir": self.txt_out_dir.text().strip() or "outputs/glabs_images",
            "expected_images": expected_images,
            "aspect_ratio": self.cmb_ratio.currentText(),
            "model": self.cmb_model.currentText(),
            "seed": self.txt_seed.text().strip() if self.chk_seed.isChecked() else None,
            "task_name": task_name if self.chk_task_folder.isChecked() else None,
            "reference_mode": "Auto match by filename",
            "reference_dir": self.txt_ref_dir.text().strip(),
            "manual_reference_paths": [self.manual_references.get(i, []) for i in range(len(prompts))],
            "worker_count": worker_count,
            "new_project_each_run": worker_count > 1,
        }

        self._sync_queue_preview(config)
        start_row_idx = 0
        self.is_running = True
        self.btn_run.setEnabled(False)
        self.btn_run.setText("RUNNING...")
        self.lbl_run_status.setText(f"Running {len(prompts)} prompt(s) on {worker_count} worker(s)")

        self.engine_thread = EngineThread(config, start_row_idx)
        self.engine_thread.progress_signal.connect(self._update_row_progress)
        self.engine_thread.status_signal.connect(self._update_row_status)
        self.engine_thread.image_signal.connect(self._add_image_to_row)
        self.engine_thread.finished_signal.connect(self._on_engine_finished)
        self.engine_thread.start()

    def _current_config_preview(self):
        try:
            expected_images = int(self.cmb_amt.currentText().replace("x", ""))
        except ValueError:
            expected_images = 2
        return {
            "expected_images": expected_images,
            "aspect_ratio": self.cmb_ratio.currentText(),
            "model": self.cmb_model.currentText(),
            "task_name": None,
            "reference_mode": "Auto match by filename",
            "reference_dir": self.txt_ref_dir.text().strip(),
        }

    def _sync_queue_preview(self, config=None):
        prompts = self._prompt_lines()
        config = config or self._current_config_preview()
        self._prepare_table_for_run(prompts, config)

    def _prepare_table_for_run(self, prompts, config):
        self.table.setRowCount(len(prompts))

        for idx, prompt_text in enumerate(prompts):
            row = idx
            self.table.setRowHeight(row, 96 if config["expected_images"] <= 2 else 118)

            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.addWidget(QCheckBox(), alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 0, chk_widget)

            number = QTableWidgetItem(str(row + 1))
            number.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            number.setForeground(QColor("#9AA5C7"))
            self.table.setItem(row, 1, number)

            self.table.setCellWidget(row, 2, self._reference_cell(row))

            prompt = QTableWidgetItem(prompt_text)
            prompt.setForeground(QColor("#F1F4FF"))
            self.table.setItem(row, 3, prompt)

            settings = QTableWidgetItem(f"{config['model']}\n{config['aspect_ratio']} | {config['expected_images']}x")
            settings.setForeground(QColor("#C8D0EA"))
            settings.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, settings)

            self.table.setCellWidget(row, 5, OutputImageContainer(config["expected_images"]))

            status = QLabel("Queued")
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setStyleSheet("color:#9AA5C7; font-weight:700;")
            self.table.setCellWidget(row, 6, status)

        return 0

    def _reference_cell(self, row):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        refs = self.manual_references.get(row, [])[:5]
        add_btn = QPushButton("+")
        add_btn.setFixedSize(30, 30)
        add_btn.setToolTip("Add up to 5 reference images for this prompt")
        add_btn.clicked.connect(lambda checked=False, r=row: self._choose_row_references(r))
        layout.addWidget(add_btn)

        visible_slots = 3
        for idx in range(visible_slots):
            path = refs[idx] if idx < len(refs) else None
            thumb = ClickableImageLabel()
            thumb.setFixedSize(38, 38)
            if path:
                thumb.filepath = path
                thumb.setToolTip(path)
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    thumb.setPixmap(
                        pixmap.scaled(
                            36,
                            36,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    thumb.setStyleSheet("background:#111421; border:1px solid #FF8A2A; border-radius:5px; padding:1px;")
                else:
                    thumb.setText("img")
                    thumb.setStyleSheet("background:#111421; border:1px solid #FF8A2A; border-radius:5px; color:#FFB45D;")
            else:
                if idx == visible_slots - 1:
                    thumb.setText(f"+{5 - visible_slots}" if len(refs) <= visible_slots else f"+{len(refs) - visible_slots}")
                else:
                    thumb.setText("+")
                thumb.setToolTip("Empty reference slot")
                thumb.setStyleSheet("background:#111421; border:1px dashed #30344F; border-radius:5px; color:#59627E;")
            layout.addWidget(thumb)

        clear_btn = QPushButton("x")
        clear_btn.setFixedSize(26, 30)
        clear_btn.setToolTip("Clear references for this row")
        clear_btn.clicked.connect(lambda checked=False, r=row: self._clear_row_references(r))
        layout.addWidget(clear_btn)
        layout.addStretch()
        return widget

    def _choose_row_references(self, row):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose reference image(s)",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not paths:
            return
        current = self.manual_references.get(row, [])
        merged = []
        seen = set()
        for path in current + paths:
            key = os.path.normcase(os.path.abspath(path))
            if key in seen:
                continue
            seen.add(key)
            merged.append(path)
            if len(merged) >= 5:
                break
        self.manual_references[row] = merged
        self.lbl_run_status.setText(f"Row {row + 1}: {len(merged)}/5 reference slot(s) filled")
        self._sync_queue_preview()

    def _clear_row_references(self, row):
        self.manual_references.pop(row, None)
        self._sync_queue_preview()

    def _reference_preview(self, prompt_text, config):
        mode = config.get("reference_mode", "None")
        ref_dir = config.get("reference_dir", "")
        if mode == "None" or not ref_dir:
            return "None"
        if mode == "Use all images in folder":
            return "All folder images"
        tokens = [part for part in prompt_text.replace("_", "-").split() if len(part) >= 3]
        likely = [token.strip(".,;:()[]{}").lower() for token in tokens if "-" in token or "_" in token]
        return ", ".join(likely[:3]) if likely else "Auto match"

    def _update_row_status(self, row_idx, status):
        label = self.table.cellWidget(row_idx, 6)
        if label:
            label.setText(status or "Starting")
            label.setStyleSheet("color:#FFB45D; font-weight:700;")

    def _update_row_progress(self, row_idx, percent):
        label = self.table.cellWidget(row_idx, 6)
        if not label:
            return

        if percent == -1:
            label.setText("Blocked")
            label.setStyleSheet("color:#FF6B7A; font-weight:700;")
        elif percent >= 100:
            label.setText("Done")
            label.setStyleSheet("color:#42E6A4; font-weight:700;")
        else:
            label.setText(f"{percent}%")
            label.setStyleSheet("color:#42E6A4; font-weight:700;")

    def _add_image_to_row(self, row_idx, filepath):
        container = self.table.cellWidget(row_idx, 5)
        if isinstance(container, OutputImageContainer):
            container.add_loaded_image(filepath)

    def _on_engine_finished(self):
        self.is_running = False
        self.btn_run.setEnabled(True)
        self.btn_run.setText("RUN NOW")
        self.lbl_run_status.setText("Finished")

        for row in range(self.table.rowCount()):
            label = self.table.cellWidget(row, 6)
            if label and ("%" in label.text() or label.text() in {"Queued", "Starting", "Running..."}):
                label.setText("Done")
                label.setStyleSheet("color:#42E6A4; font-weight:700;")


class EngineThread(QThread):
    progress_signal = pyqtSignal(int, int)
    image_signal = pyqtSignal(int, str)
    status_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal()

    def __init__(self, config, start_row_idx=0):
        super().__init__()
        self.config = config
        self.start_row_idx = start_row_idx

    def run(self):
        worker_count = max(1, int(self.config.get("worker_count", 1) or 1))
        worker_count = min(worker_count, len(self.config.get("prompts", [])) or 1)

        if worker_count <= 1:
            config = dict(self.config)
            config.pop("worker_count", None)
            config["on_gen_start"] = lambda idx, prompt: self.status_signal.emit(
                self.start_row_idx + idx, "Starting"
            )
            config["on_gen_progress"] = lambda idx, pct: self.progress_signal.emit(self.start_row_idx + idx, pct)
            config["on_image_saved"] = lambda idx, fp: self.image_signal.emit(self.start_row_idx + idx, fp)
            run_auto(**config, log_fn=print)
            self.finished_signal.emit()
            return

        prompts = self.config.get("prompts", [])
        manual_refs = self.config.get("manual_reference_paths") or [[] for _ in prompts]
        shards = [[] for _ in range(worker_count)]
        for global_idx, prompt in enumerate(prompts):
            worker_slot = global_idx % worker_count
            refs = manual_refs[global_idx] if global_idx < len(manual_refs) else []
            shards[worker_slot].append((global_idx, prompt, refs))

        def run_worker(worker_idx, jobs):
            if not jobs:
                return
            local_prompts = [job[1] for job in jobs]
            local_refs = [job[2] for job in jobs]
            global_indices = [job[0] for job in jobs]
            config = dict(self.config)
            config.pop("worker_count", None)
            config["prompts"] = local_prompts
            config["manual_reference_paths"] = local_refs
            config["new_project_each_run"] = True
            config["worker_id"] = worker_idx + 1
            config["on_gen_start"] = lambda idx, prompt: self.status_signal.emit(
                self.start_row_idx + global_indices[idx], f"Worker {worker_idx + 1}"
            )
            config["on_gen_progress"] = lambda idx, pct: self.progress_signal.emit(
                self.start_row_idx + global_indices[idx], pct
            )
            config["on_image_saved"] = lambda idx, fp: self.image_signal.emit(
                self.start_row_idx + global_indices[idx], fp
            )
            try:
                run_auto(**config, log_fn=lambda msg: print(f"[W{worker_idx + 1}] {msg}"))
            except Exception as exc:
                print(f"[W{worker_idx + 1}] ERROR worker failed: {exc}")
                for global_idx in global_indices:
                    self.progress_signal.emit(self.start_row_idx + global_idx, -1)

        threads = [
            threading.Thread(target=run_worker, args=(idx, jobs), daemon=False)
            for idx, jobs in enumerate(shards)
            if jobs
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.finished_signal.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GLabsAutomationTab()
    win.setWindowTitle("G-Labs Batch Runner")
    win.resize(1320, 820)
    win.show()
    sys.exit(app.exec())
