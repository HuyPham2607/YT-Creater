import os
import subprocess
import sys

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
            size, font_size = 150, 28
        elif expected_images == 2:
            size, font_size = 112, 24
        else:
            size, font_size = 78, 18

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
            QWidget { background:#0B0D13; color:#D8DDF0; font-family:'Segoe UI', sans-serif; font-size:13px; }
            QLabel#title { color:#FFFFFF; font-size:20px; font-weight:700; }
            QLabel#subtitle { color:#7F89AA; font-size:12px; }
            QLabel#section { color:#9AA5C7; font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
            QLabel#hint { color:#7F89AA; font-size:12px; }
            QLabel#badge_ok { background:#143828; color:#42E6A4; border:1px solid #1E6A4C; border-radius:10px; padding:4px 10px; font-weight:700; }
            QLabel#badge_warn { background:#352214; color:#FFB45D; border:1px solid #6E4422; border-radius:10px; padding:4px 10px; font-weight:700; }
            QFrame#panel { background:#121622; border:1px solid #252B3E; border-radius:8px; }
            QLineEdit, QComboBox, QTextEdit {
                background:#0F121C; border:1px solid #2B3146; border-radius:6px; color:#F1F4FF; padding:8px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border-color:#FF8A2A; }
            QTextEdit { line-height:1.35; }
            QCheckBox { color:#D8DDF0; spacing:8px; }
            QCheckBox::indicator { width:16px; height:16px; border:1px solid #343B54; border-radius:4px; background:#0F121C; }
            QCheckBox::indicator:checked { background:#FF8A2A; border-color:#FF8A2A; }
            QPushButton { background:#1B2130; border:1px solid #31384F; border-radius:6px; color:#E9EDFF; padding:8px 12px; font-weight:600; }
            QPushButton:hover { border-color:#FF8A2A; }
            QPushButton:disabled { color:#69718D; border-color:#242A3B; background:#111521; }
            QPushButton#run { background:#FF7A1A; border-color:#FF7A1A; color:#101010; padding:11px 14px; font-weight:800; }
            QPushButton#secondary { background:#101521; }
            QPushButton#danger { background:#24161A; border-color:#53303A; color:#FF9AAE; }
            QTableWidget { background:#0F121C; border:1px solid #252B3E; border-radius:8px; gridline-color:#1D2333; }
            QHeaderView::section { background:#151A28; color:#9AA5C7; border:none; border-right:1px solid #252B3E; padding:10px; font-weight:700; }
            QTableWidget::item { border-bottom:1px solid #1D2333; padding:8px; }
            QTableWidget::item:selected { background:#1D2638; }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)
        root.addLayout(left, 0)

        header = QFrame()
        header.setObjectName("panel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("G-Labs Batch Runner")
        title.setObjectName("title")
        subtitle = QLabel("Tool 8 | Tao anh hang loat tu danh sach prompt")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_row.addLayout(title_box)
        title_row.addStretch()
        self.lbl_engine = QLabel("Engine ready" if ENGINE_OK else "Engine missing")
        self.lbl_engine.setObjectName("badge_ok" if ENGINE_OK else "badge_warn")
        title_row.addWidget(self.lbl_engine, alignment=Qt.AlignmentFlag.AlignTop)
        header_layout.addLayout(title_row)

        note = QLabel(
            "Che do hien tai dung Chrome debug profile. Hay dang nhap Google/G-Labs mot lan trong cua so Chrome ma tool mo ra."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        header_layout.addWidget(note)
        left.addWidget(header)

        prompt_panel = self._panel("1. Prompts")
        prompt_lay = prompt_panel.layout()
        prompt_toolbar = QHBoxLayout()
        self.btn_import = QPushButton("Import TXT/Excel")
        self.btn_import.setObjectName("secondary")
        self.lbl_prompt_count = QLabel("0 prompts")
        self.lbl_prompt_count.setObjectName("hint")
        prompt_toolbar.addWidget(self.btn_import)
        prompt_toolbar.addStretch()
        prompt_toolbar.addWidget(self.lbl_prompt_count)
        prompt_lay.addLayout(prompt_toolbar)

        self.txt_prompts = QTextEdit()
        self.txt_prompts.setMinimumHeight(220)
        self.txt_prompts.setPlaceholderText(
            "Moi dong la 1 prompt.\nVi du:\nA 2D cinematic Vietnamese cafe interior at night, 16:9, no text, no people..."
        )
        prompt_lay.addWidget(self.txt_prompts)
        left.addWidget(prompt_panel, 1)

        settings_panel = self._panel("2. Settings")
        settings_lay = settings_panel.layout()

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
        grid.addWidget(self._field_label("Quality / upscale"), 2, 1)
        grid.addWidget(self.cmb_quality, 3, 1)
        settings_lay.addLayout(grid)

        self.chk_seed = QCheckBox("Lock seed")
        self.txt_seed = QLineEdit()
        self.txt_seed.setPlaceholderText("Optional seed")
        seed_row = QHBoxLayout()
        seed_row.addWidget(self.chk_seed)
        seed_row.addWidget(self.txt_seed, 1)
        settings_lay.addLayout(seed_row)

        self.chk_task_folder = QCheckBox("Create subfolder for this run")
        self.chk_task_folder.setChecked(True)
        settings_lay.addWidget(self.chk_task_folder)

        settings_lay.addWidget(self._field_label("Auto reference folder"))
        ref_row = QHBoxLayout()
        self.txt_ref_dir = QLineEdit("")
        self.txt_ref_dir.setPlaceholderText("Optional: auto match image filename from prompt")
        self.btn_choose_ref = QPushButton("Browse")
        ref_row.addWidget(self.txt_ref_dir, 1)
        ref_row.addWidget(self.btn_choose_ref)
        settings_lay.addLayout(ref_row)

        ref_hint = QLabel("Manual references are added per row in the queue. This folder is only for filename auto-match fallback.")
        ref_hint.setWordWrap(True)
        ref_hint.setObjectName("hint")
        settings_lay.addWidget(ref_hint)

        settings_lay.addWidget(self._field_label("Output folder"))
        out_row = QHBoxLayout()
        self.txt_out_dir = QLineEdit("outputs/glabs_images")
        self.btn_choose_out = QPushButton("Browse")
        out_row.addWidget(self.txt_out_dir, 1)
        out_row.addWidget(self.btn_choose_out)
        settings_lay.addLayout(out_row)

        api_note = QLabel("Webhook API / extension helper: planned. UI nay truoc mat chay bang local engine hien co.")
        api_note.setWordWrap(True)
        api_note.setObjectName("hint")
        settings_lay.addWidget(api_note)

        left.addWidget(settings_panel)

        run_row = QHBoxLayout()
        self.btn_run = QPushButton("Run Batch")
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
        output_header.setObjectName("panel")
        output_lay = QHBoxLayout(output_header)
        output_lay.setContentsMargins(14, 10, 14, 10)
        output_title = QLabel("Run Queue & Outputs")
        output_title.setObjectName("section")
        self.lbl_run_status = QLabel("Idle")
        self.lbl_run_status.setObjectName("hint")
        output_lay.addWidget(output_title)
        output_lay.addStretch()
        output_lay.addWidget(self.lbl_run_status)
        right.addWidget(output_header)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["", "#", "Reference", "Prompt", "Settings", "Output", "Status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 38)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 44)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 310)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 300)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 160)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 260)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 120)

        right.addWidget(self.table, 1)

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
        label.setObjectName("section")
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
        }

        self._sync_queue_preview(config)
        start_row_idx = 0
        self.is_running = True
        self.btn_run.setEnabled(False)
        self.btn_run.setText("Running...")
        self.lbl_run_status.setText(f"Running {len(prompts)} prompt(s)")

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
            self.table.setRowHeight(row, 176 if config["expected_images"] <= 2 else 210)

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

            settings = QTableWidgetItem(
                f"{config['model']}\n{config['aspect_ratio']} | {config['expected_images']}x\n"
                f"{config['task_name'] or 'No subfolder'}"
            )
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

        for idx in range(5):
            path = refs[idx] if idx < len(refs) else None
            thumb = ClickableImageLabel()
            thumb.setFixedSize(34, 34)
            if path:
                thumb.filepath = path
                thumb.setToolTip(path)
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    thumb.setPixmap(
                        pixmap.scaled(
                            32,
                            32,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                    thumb.setStyleSheet("background:#111421; border:1px solid #FF8A2A; border-radius:5px; padding:1px;")
                else:
                    thumb.setText("img")
                    thumb.setStyleSheet("background:#111421; border:1px solid #FF8A2A; border-radius:5px; color:#FFB45D;")
            else:
                thumb.setText(str(idx + 1))
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
        self.btn_run.setText("Run Batch")
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
        self.config["on_gen_start"] = lambda idx, prompt: self.status_signal.emit(
            self.start_row_idx + idx, "Starting"
        )
        self.config["on_gen_progress"] = lambda idx, pct: self.progress_signal.emit(self.start_row_idx + idx, pct)
        self.config["on_image_saved"] = lambda idx, fp: self.image_signal.emit(self.start_row_idx + idx, fp)

        run_auto(**self.config, log_fn=print)
        self.finished_signal.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GLabsAutomationTab()
    win.setWindowTitle("G-Labs Batch Runner")
    win.resize(1320, 820)
    win.show()
    sys.exit(app.exec())
