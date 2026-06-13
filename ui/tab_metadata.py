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
from PyQt6.QtCore import Qt, pyqtSignal
from core.srt_chapters import srt_to_chapter_lines

from threads.metadata_worker import MetadataWorker


class VideoMetadataTab(QWidget):
    request_load_script = pyqtSignal()
    request_load_chapters_from_voice = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.profile_data = {}
        self.worker = None
        self._result = {}

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 12, 15, 12)
        main_lay.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("Video Metadata Drafting Assistant", objectName="page_title"))
        title_box.addWidget(QLabel("Create upload-ready titles, description, tags, chapters, and pinned comment from your script and SEO notes", objectName="page_desc"))
        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(QLabel("Tool 6", objectName="page_badge"), alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(10)

        hint = QLabel(
            "<b>Important:</b> Tool 6 does not research YouTube by itself. Paste your keyword/title research notes below. "
            "If notes are missing, AI must mark SEO confidence as unverified."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "background: rgba(52,211,153,0.06); border: 1px solid rgba(52,211,153,0.18); "
            "border-radius: 8px; padding: 10px 14px; color: #3AD68A; font-size: 13px;"
        )
        lay.addWidget(hint)

        top = QFrame()
        top.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(12, 10, 12, 12)
        top_lay.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(QLabel("WORKING TITLE", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("VIDEO TOPIC", objectName="muted"), 0, 1)
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Chosen or working YouTube title")
        self.txt_topic = QLineEdit()
        self.txt_topic.setPlaceholderText("Main topic / angle")
        grid.addWidget(self.txt_title, 1, 0)
        grid.addWidget(self.txt_topic, 1, 1)

        grid.addWidget(QLabel("LANGUAGE", objectName="muted"), 2, 0)
        grid.addWidget(QLabel("THUMBNAIL CONTEXT", objectName="muted"), 2, 1)
        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["Vietnamese", "English", "Vietnamese with English keywords"])
        self.txt_thumbnail = QLineEdit()
        self.txt_thumbnail.setPlaceholderText("Thumbnail text/concept from Tool 5, optional")
        grid.addWidget(self.cmb_language, 3, 0)
        grid.addWidget(self.txt_thumbnail, 3, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        top_lay.addLayout(grid)

        script_bar = QHBoxLayout()
        script_bar.addWidget(QLabel("FINAL SCRIPT", objectName="muted"))
        script_bar.addStretch()
        self.btn_load_script = QPushButton("Load Script from Tool 1")
        self.btn_load_script.setObjectName("btn_sec")
        self.btn_load_script.clicked.connect(lambda: self.request_load_script.emit())
        self.btn_load_chapters = QPushButton("Chapters từ Voice SRT")
        self.btn_load_chapters.setObjectName("btn_sec")
        self.btn_load_chapters.clicked.connect(lambda: self.request_load_chapters_from_voice.emit())
        script_bar.addWidget(self.btn_load_script)
        script_bar.addWidget(self.btn_load_chapters)
        top_lay.addLayout(script_bar)

        self.txt_script = QTextEdit()
        self.txt_script.setPlaceholderText("Paste the final script here, or load it from Tool 1.")
        self.txt_script.setFixedHeight(150)
        top_lay.addWidget(self.txt_script)
        lay.addWidget(top)

        research = QFrame()
        research.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        research_lay = QVBoxLayout(research)
        research_lay.setContentsMargins(12, 10, 12, 12)
        research_lay.setSpacing(8)
        research_lay.addWidget(QLabel("USER SEO RESEARCH NOTES", objectName="muted"))
        self.txt_seo = QTextEdit()
        self.txt_seo.setPlaceholderText(
            "Paste your manual SEO research here: primary keyword, secondary keywords, competitor titles, autocomplete notes, chosen title rationale..."
        )
        self.txt_seo.setFixedHeight(110)
        research_lay.addWidget(self.txt_seo)
        lay.addWidget(research)

        actions = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Metadata")
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
        for name in ["Analysis", "Titles", "Description", "Tags", "Chapters", "All", "Raw JSON"]:
            self.tabs.addTab(name)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(
            "QTabBar::tab { background: #171724; color: #A1A1AA; padding: 7px 14px; border: 1px solid #252535; }"
            "QTabBar::tab:selected { color: #E8742A; border-bottom: 2px solid #E8742A; }"
        )
        lay.addWidget(self.tabs)

        self.stack = QStackedWidget()
        self.txt_analysis = self._output_box()
        self.txt_titles = self._output_box()
        self.txt_desc = self._output_box()
        self.txt_tags = self._output_box()
        self.txt_chapters = self._output_box()
        self.txt_all = self._output_box()
        self.txt_json = self._output_box()
        for txt in [self.txt_analysis, self.txt_titles, self.txt_desc, self.txt_tags, self.txt_chapters, self.txt_all, self.txt_json]:
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

    def load_chapters_from_srt(self, srt_path: str):
        try:
            chapters = srt_to_chapter_lines(srt_path)
            if not chapters:
                QMessageBox.warning(self, "Trống", "Không đọc được chapter từ file SRT.")
                return
            self.txt_chapters.setPlainText(chapters)
            self.tabs.setCurrentIndex(4)
            QMessageBox.information(self, "Đã nạp", f"Đã tạo {len(chapters.splitlines())} chapter từ SRT.")
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi SRT", str(exc))

    def load_script_data(self, title="", script="", topic=""):
        if title:
            self.txt_title.setText(title)
        if topic and not self.txt_topic.text().strip():
            self.txt_topic.setText(topic)
        if script:
            self.txt_script.setPlainText(script)

    def _config(self):
        profile = self.profile_data or {}
        return {
            "title": self.txt_title.text().strip(),
            "topic": self.txt_topic.text().strip(),
            "language": self.cmb_language.currentText(),
            "thumbnail_context": self.txt_thumbnail.text().strip(),
            "script": self.txt_script.toPlainText().strip(),
            "seo_notes": self.txt_seo.toPlainText().strip(),
            "channel_name": profile.get("name", ""),
            "niche": profile.get("niche", ""),
            "audience": profile.get("target_audience", ""),
            "dna_content": profile.get("dna_content", ""),
            "style_guide": profile.get("style_content", ""),
        }

    def _generate(self):
        cfg = self._config()
        if not cfg["script"]:
            QMessageBox.warning(self, "Missing script", "Paste or load the final script first.")
            return
        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("Generating...")
        self.lbl_status.setText("Calling AI...")
        self.worker = MetadataWorker(cfg)
        self.worker.progress_signal.connect(self.lbl_status.setText)
        self.worker.result_signal.connect(self._on_success)
        self.worker.error_signal.connect(self._on_error)
        self.worker.finished.connect(lambda: [self.btn_generate.setEnabled(True), self.btn_generate.setText("Generate Metadata")])
        self.worker.start()

    def _on_success(self, result):
        self._result = result or {}
        self.txt_analysis.setPlainText(self._format_analysis(self._result))
        self.txt_titles.setPlainText(self._format_titles(self._result))
        self.txt_desc.setPlainText(self._format_description(self._result))
        self.txt_tags.setPlainText(self._format_tags(self._result))
        self.txt_chapters.setPlainText(self._format_chapters(self._result))
        self.txt_all.setPlainText(self._format_all(self._result))
        self.txt_json.setPlainText(json.dumps(self._result, ensure_ascii=False, indent=2))
        confidence = self._result.get("analysis", {}).get("seo_confidence", "done")
        self.lbl_status.setText(f"Done: SEO confidence = {confidence}")
        self.tabs.setCurrentIndex(0)

    def _on_error(self, message):
        self.lbl_status.setText("Generate failed.")
        QMessageBox.critical(self, "AI Error", message)

    def _format_analysis(self, data):
        a = data.get("analysis", {})
        lines = [
            f"Core promise: {a.get('core_promise', '')}",
            f"SEO confidence: {a.get('seo_confidence', '')}",
            f"Reason: {a.get('seo_confidence_reason', '')}",
            "",
            "Viewer intent:",
            *[f"- {x}" for x in a.get("viewer_intent", [])],
            "",
            "Emotional triggers:",
            *[f"- {x}" for x in a.get("emotional_triggers", [])],
            "",
            "Primary keywords from your research:",
            *[f"- {x}" for x in a.get("primary_keywords_from_user_research", [])],
            "",
            "Metadata risks:",
            *[f"- {x}" for x in a.get("metadata_risks", [])],
        ]
        return "\n".join(lines).strip()

    def _format_titles(self, data):
        lines = []
        for i, item in enumerate(data.get("title_options", []), 1):
            lines.extend([
                f"{i}. {item.get('title', '')}",
                f"Angle: {item.get('angle', '')}",
                f"Keywords: {', '.join(item.get('keywords_used', []))}",
                f"Channel fit: {item.get('channel_fit_reason', '')}",
                f"SEO note: {item.get('seo_note', '')}",
                "",
            ])
        return "\n".join(lines).strip()

    def _format_description(self, data):
        desc = data.get("description", {})
        return desc.get("full_text") or "\n\n".join(
            part for part in [desc.get("hook", ""), desc.get("body", ""), desc.get("cta", "")] if part
        )

    def _format_tags(self, data):
        tags = data.get("tags", {})
        lines = [
            "BROAD",
            ", ".join(tags.get("broad", [])),
            "",
            "SPECIFIC",
            ", ".join(tags.get("specific", [])),
            "",
            "LONG TAIL",
            ", ".join(tags.get("long_tail", [])),
            "",
            "ALL TAGS",
            tags.get("all_comma_separated", ""),
            "",
            "HASHTAGS",
            " ".join(data.get("hashtags", [])),
        ]
        return "\n".join(lines).strip()

    def _format_chapters(self, data):
        return "\n".join(f"{item.get('time', '')} {item.get('title', '')}" for item in data.get("chapters", []))

    def _format_all(self, data):
        sections = [
            "=== ANALYSIS ===",
            self._format_analysis(data),
            "",
            "=== TITLES ===",
            self._format_titles(data),
            "",
            "=== DESCRIPTION ===",
            self._format_description(data),
            "",
            "=== TAGS ===",
            self._format_tags(data),
            "",
            "=== CHAPTERS ===",
            self._format_chapters(data),
            "",
            "=== PINNED COMMENT ===",
            data.get("pinned_comment", ""),
            "",
            "=== UPLOAD NOTES ===",
            "\n".join(f"- {x}" for x in data.get("upload_notes", [])),
        ]
        return "\n".join(sections).strip()

    def _on_tab_changed(self, index):
        self.stack.setCurrentIndex(index)

    def _current_text(self):
        return [
            self.txt_analysis, self.txt_titles, self.txt_desc, self.txt_tags,
            self.txt_chapters, self.txt_all, self.txt_json
        ][self.tabs.currentIndex()].toPlainText().strip()

    def _copy_tab(self):
        text = self._current_text()
        if not text:
            QMessageBox.warning(self, "Empty", "Generate metadata first.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Copied current tab.")

    def _export_tab(self):
        text = self._current_text()
        if not text:
            QMessageBox.warning(self, "Empty", "Generate metadata first.")
            return
        names = [
            "metadata-analysis.txt", "metadata-titles.txt", "metadata-description.txt",
            "metadata-tags.txt", "metadata-chapters.txt", "metadata-all.txt", "metadata-output.json"
        ]
        path, _ = QFileDialog.getSaveFileName(self, "Export metadata", names[self.tabs.currentIndex()], "Text/JSON Files (*.txt *.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        QMessageBox.information(self, "Exported", path)
