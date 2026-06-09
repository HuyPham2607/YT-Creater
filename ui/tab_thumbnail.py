import json

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from threads.thumbnail_worker import ThumbnailWorker


class ThumbnailTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.profile_data = {}
        self._result = {}

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 12, 15, 12)
        main_lay.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 6)
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("Thumbnail Prompter", objectName="page_title"))
        title_box.addWidget(QLabel("Analyze topic and create thumbnail concepts, overlay text, and G-Labs prompts", objectName="page_desc"))
        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(QLabel("Tool 5", objectName="page_badge"), alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(10)

        hint = QLabel(
            "<b>Workflow:</b> enter/load the video topic and title, set thumbnail text or let AI choose, "
            "then generate 3 G-Labs thumbnail variations. Text is added later in Canva, not rendered by G-Labs."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "background: rgba(232,116,42,0.06); border: 1px solid rgba(232,116,42,0.15); "
            "border-radius: 8px; padding: 10px 14px; color: #E8742A; font-size: 13px;"
        )
        lay.addWidget(hint)

        context = QFrame()
        context.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        ctx_lay = QVBoxLayout(context)
        ctx_lay.setContentsMargins(12, 10, 12, 12)
        ctx_lay.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(QLabel("VIDEO TOPIC", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("CANDIDATE TITLE", objectName="muted"), 0, 1)
        self.txt_topic = QLineEdit()
        self.txt_topic.setPlaceholderText("Topic or main angle of the video")
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Main video title or title candidate")
        grid.addWidget(self.txt_topic, 1, 0)
        grid.addWidget(self.txt_title, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        ctx_lay.addLayout(grid)

        ctx_lay.addWidget(QLabel("SCRIPT SUMMARY / HOOK", objectName="muted"))
        self.txt_summary = QTextEdit()
        self.txt_summary.setPlaceholderText("Optional: short hook, summary, or emotional promise of the video")
        self.txt_summary.setFixedHeight(62)
        ctx_lay.addWidget(self.txt_summary)
        lay.addWidget(context)

        settings = QFrame()
        settings.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        set_lay = QVBoxLayout(settings)
        set_lay.setContentsMargins(12, 10, 12, 12)
        set_lay.setSpacing(10)

        grid2 = QGridLayout()
        grid2.setSpacing(10)
        grid2.addWidget(QLabel("FORMAT", objectName="muted"), 0, 0)
        grid2.addWidget(QLabel("PALETTE", objectName="muted"), 0, 1)
        grid2.addWidget(QLabel("BACKGROUND / SETTING", objectName="muted"), 2, 0)
        grid2.addWidget(QLabel("CHARACTER / KEY PROP", objectName="muted"), 2, 1)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "AI choose",
            "Single silhouette + big text",
            "Object close-up + big text",
            "Split contrast before/after",
            "Dark empty space + huge text",
        ])
        self.cmb_palette = QComboBox()
        self.cmb_palette.addItems([
            "AI choose from profile",
            "Black + bronze gold + ivory",
            "Dark blue-grey + amber",
            "High contrast black + white",
            "Custom from fields",
        ])
        self.txt_background = QLineEdit()
        self.txt_background.setPlaceholderText("dark cafe, rainy window, rooftop night...")
        self.txt_character = QLineEdit()
        self.txt_character.setPlaceholderText("anonymous silhouette, notebook, watch, coffee cup...")
        grid2.addWidget(self.cmb_format, 1, 0)
        grid2.addWidget(self.cmb_palette, 1, 1)
        grid2.addWidget(self.txt_background, 3, 0)
        grid2.addWidget(self.txt_character, 3, 1)
        set_lay.addLayout(grid2)

        text_grid = QGridLayout()
        text_grid.setSpacing(10)
        text_grid.addWidget(QLabel("TEXT LINE 1", objectName="muted"), 0, 0)
        text_grid.addWidget(QLabel("TEXT LINE 2", objectName="muted"), 0, 1)
        self.txt_line1 = QLineEdit()
        self.txt_line1.setPlaceholderText("AI choose, or e.g. TIEP TUC")
        self.txt_line2 = QLineEdit()
        self.txt_line2.setPlaceholderText("Optional")
        text_grid.addWidget(self.txt_line1, 1, 0)
        text_grid.addWidget(self.txt_line2, 1, 1)
        set_lay.addLayout(text_grid)

        set_lay.addWidget(QLabel("REFERENCE THUMBNAIL ANALYSIS (OPTIONAL)", objectName="muted"))
        self.txt_reference = QTextEdit()
        self.txt_reference.setPlaceholderText("Paste reference analysis here if you already analyzed competitor thumbnails")
        self.txt_reference.setFixedHeight(58)
        set_lay.addWidget(self.txt_reference)
        lay.addWidget(settings)

        actions = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Thumbnail Prompts")
        self.btn_generate.setObjectName("btn_primary")
        self.btn_generate.clicked.connect(self._generate)
        self.btn_copy = QPushButton("Copy Tab")
        self.btn_copy.setObjectName("btn_sec")
        self.btn_copy.clicked.connect(self._copy_tab)
        self.btn_export = QPushButton("Export Tab")
        self.btn_export.setObjectName("btn_sec")
        self.btn_export.clicked.connect(self._export_tab)
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("muted")
        actions.addWidget(self.btn_generate)
        actions.addWidget(self.lbl_status)
        actions.addStretch()
        actions.addWidget(self.btn_copy)
        actions.addWidget(self.btn_export)
        lay.addLayout(actions)

        self.tabs = QTabBar()
        for name in ["Concepts", "G-Labs Prompts", "Canva Guide", "Raw JSON"]:
            self.tabs.addTab(name)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(
            "QTabBar::tab { background: #171724; color: #A1A1AA; padding: 7px 14px; border: 1px solid #252535; }"
            "QTabBar::tab:selected { color: #E8742A; border-bottom: 2px solid #E8742A; }"
        )
        lay.addWidget(self.tabs)

        self.stack = QStackedWidget()
        self.txt_concepts = self._output_box()
        self.txt_prompts = self._output_box()
        self.txt_canva = self._output_box()
        self.txt_json = self._output_box()
        for txt in [self.txt_concepts, self.txt_prompts, self.txt_canva, self.txt_json]:
            self.stack.addWidget(txt)
        lay.addWidget(self.stack)

        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

    def _output_box(self):
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setMinimumHeight(230)
        txt.setStyleSheet(
            "background: #08080D; border: 1px solid #252535; border-radius: 6px; "
            "color: #E8E8F0; font-family: 'Space Mono', monospace; font-size: 12px; padding: 10px;"
        )
        return txt

    def apply_profile(self, profile_data):
        self.profile_data = profile_data or {}
        if not self.txt_topic.text().strip():
            topic_content = self.profile_data.get("topic_content", "")
            if topic_content:
                self.txt_topic.setText(topic_content.splitlines()[0][:160])
        if not self.txt_character.text().strip():
            self.txt_character.setText("anonymous Vietnamese male silhouette, simple watch, dark notebook, coffee cup")
        if not self.txt_background.text().strip():
            self.txt_background.setText("dark Vietnamese cafe at night, rainy window, rooftop, quiet street")

    def _config(self):
        profile = self.profile_data or {}
        return {
            "topic": self.txt_topic.text().strip(),
            "title": self.txt_title.text().strip(),
            "summary": self.txt_summary.toPlainText().strip(),
            "audience": profile.get("target_audience", ""),
            "channel_name": profile.get("name", ""),
            "niche": profile.get("niche", ""),
            "visual": profile.get("visual", ""),
            "dna_content": profile.get("dna_content", ""),
            "style_guide": profile.get("style_content", ""),
            "format": self.cmb_format.currentText(),
            "palette": self.cmb_palette.currentText(),
            "background": self.txt_background.text().strip(),
            "character": self.txt_character.text().strip(),
            "text_line_1": self.txt_line1.text().strip(),
            "text_line_2": self.txt_line2.text().strip(),
            "reference_analysis": self.txt_reference.toPlainText().strip(),
        }

    def _generate(self):
        cfg = self._config()
        if not cfg["topic"] and not cfg["title"]:
            QMessageBox.warning(self, "Missing context", "Enter at least a video topic or candidate title.")
            return
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Generating...")
        self.lbl_status.setText("Calling AI...")
        self.worker = ThumbnailWorker(cfg)
        self.worker.progress_signal.connect(self.lbl_status.setText)
        self.worker.result_signal.connect(self._on_success)
        self.worker.error_signal.connect(self._on_error)
        self.worker.finished.connect(lambda: [self.btn_generate.setEnabled(True), self.btn_generate.setText("Generate Thumbnail Prompts")])
        self.worker.start()

    def _on_success(self, result):
        self._result = result or {}
        self.txt_concepts.setPlainText(self._format_concepts(self._result))
        self.txt_prompts.setPlainText(self._format_prompts(self._result))
        self.txt_canva.setPlainText(self._format_canva(self._result))
        self.txt_json.setPlainText(json.dumps(self._result, ensure_ascii=False, indent=2))
        rec = self._result.get("recommendation", {})
        self.lbl_status.setText(f"Done: {rec.get('thumbnail_text', 'thumbnail concepts ready')}")
        self.tabs.setCurrentIndex(0)

    def _on_error(self, message):
        self.lbl_status.setText("Generate failed.")
        QMessageBox.critical(self, "AI Error", message)

    def _format_concepts(self, data):
        rec = data.get("recommendation", {})
        lines = [
            "RECOMMENDATION",
            f"Format: {rec.get('format', '')}",
            f"Thumbnail text: {rec.get('thumbnail_text', '')}",
            f"Reason: {rec.get('reason', '')}",
            "",
            "TITLE / TEXT OPTIONS",
        ]
        for item in data.get("title_suggestions", []):
            lines.append(f"- {item}")
        lines.extend(["", "CONCEPTS"])
        for i, concept in enumerate(data.get("concepts", []), 1):
            lines.extend([
                f"{i}. {concept.get('name', 'Concept')}",
                f"Hook visual: {concept.get('hook_visual', '')}",
                f"Emotion: {concept.get('emotion', '')}",
                f"Text: {concept.get('thumbnail_text', '')}",
                f"Layout: {concept.get('layout_notes', '')}",
                f"Why it clicks: {concept.get('why_it_clicks', '')}",
                "",
            ])
        return "\n".join(lines).strip()

    def _format_prompts(self, data):
        lines = []
        for i, item in enumerate(data.get("variations", []), 1):
            lines.extend([
                f"--- Variation {i}: {item.get('name', '')} ---",
                f"Text line 1: {item.get('text_line_1', '')}",
                f"Text line 2: {item.get('text_line_2', '')}",
                f"Layout notes: {item.get('layout_notes', '')}",
                "G-Labs prompt:",
                item.get("glabs_prompt", ""),
                "",
            ])
        return "\n".join(lines).strip()

    def _format_canva(self, data):
        lines = ["CANVA SETUP GUIDE"]
        for i, step in enumerate(data.get("canva_guide", []), 1):
            lines.append(f"{i}. {step}")
        lines.extend(["", "MOBILE QC"])
        for item in data.get("mobile_qc", []):
            lines.append(f"- {item}")
        return "\n".join(lines).strip()

    def _on_tab_changed(self, index):
        self.stack.setCurrentIndex(index)

    def _current_text(self):
        return [self.txt_concepts, self.txt_prompts, self.txt_canva, self.txt_json][self.tabs.currentIndex()].toPlainText().strip()

    def _copy_tab(self):
        text = self._current_text()
        if not text:
            QMessageBox.warning(self, "Empty", "Generate thumbnail output first.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Copied current tab.")

    def _export_tab(self):
        text = self._current_text()
        if not text:
            QMessageBox.warning(self, "Empty", "Generate thumbnail output first.")
            return
        names = ["thumbnail-concepts.txt", "thumbnail-glabs-prompts.txt", "thumbnail-canva-guide.txt", "thumbnail-output.json"]
        path, _ = QFileDialog.getSaveFileName(self, "Export thumbnail output", names[self.tabs.currentIndex()], "Text/JSON Files (*.txt *.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        QMessageBox.information(self, "Exported", path)
