from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


QC_GROUPS = [
    (
        "Content",
        [
            "Script reviewed and final.",
            "Voiceover created and exported.",
            "All scenes have images/video assets.",
            "Video edited and assembled in CapCut/editor.",
        ],
    ),
    (
        "Quality",
        [
            "Full playback reviewed from start to finish.",
            "Audio sync matches visuals.",
            "Text overlays are not cut and readable on mobile.",
            "Background music supports the voiceover and does not overpower it.",
            "First 30 seconds have a strong enough hook.",
        ],
    ),
    (
        "Thumbnail & Metadata",
        [
            "Thumbnail created at 1280x720 and readable at mobile size.",
            "Final title selected and checked.",
            "Description pasted from Tool 6.",
            "Tags pasted from Tool 6.",
            "Chapters/timestamps added to the description.",
        ],
    ),
    (
        "YouTube Settings",
        [
            "Visibility is correct: Public or Scheduled.",
            "Category is correct.",
            "Monetization is ON if eligible.",
            "End screen added.",
            "Cards added if needed.",
            "Scheduled time is correct if scheduling.",
        ],
    ),
]


class UploadQCTab(QWidget):
    def __init__(self):
        super().__init__()
        self.checkboxes: list[QCheckBox] = []
        self.profile_data = {}

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 12, 15, 12)
        main_lay.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.addWidget(QLabel("Pre-Upload QC Checklist", objectName="page_title"))
        title_box.addWidget(QLabel("Final manual checks before publishing or scheduling on YouTube", objectName="page_desc"))
        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(QLabel("Tool 7", objectName="page_badge"), alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        setup = QFrame()
        setup.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        setup_lay = QVBoxLayout(setup)
        setup_lay.setContentsMargins(12, 10, 12, 12)
        setup_lay.setSpacing(10)

        row = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.addWidget(QLabel("VIDEO TITLE", objectName="muted"))
        self.txt_video_title = QLineEdit()
        self.txt_video_title.setPlaceholderText("Final video title")
        v_title.addWidget(self.txt_video_title)

        v_channel = QVBoxLayout()
        v_channel.addWidget(QLabel("CHANNEL", objectName="muted"))
        self.txt_channel = QLineEdit()
        self.txt_channel.setPlaceholderText("Channel name")
        v_channel.addWidget(self.txt_channel)
        row.addLayout(v_title)
        row.addLayout(v_channel)
        setup_lay.addLayout(row)

        progress_row = QHBoxLayout()
        self.lbl_progress = QLabel("0 / 20 complete")
        self.lbl_progress.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 20)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar { background: #08080D; border: 1px solid #252535; border-radius: 6px; height: 10px; }"
            "QProgressBar::chunk { background: #3AD68A; border-radius: 6px; }"
        )
        self.lbl_status = QLabel("Not ready")
        self.lbl_status.setStyleSheet("color: #E8742A; font-weight: bold;")
        progress_row.addWidget(self.lbl_progress)
        progress_row.addWidget(self.progress, stretch=1)
        progress_row.addWidget(self.lbl_status)
        setup_lay.addLayout(progress_row)
        main_lay.addWidget(setup)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        widget = QWidget()
        checklist_lay = QVBoxLayout(widget)
        checklist_lay.setSpacing(10)

        for group_name, items in QC_GROUPS:
            checklist_lay.addWidget(self._build_group(group_name, items))
        checklist_lay.addStretch()
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        actions = QHBoxLayout()
        self.btn_reset = QPushButton("Reset Checklist")
        self.btn_reset.setObjectName("btn_sec")
        self.btn_reset.clicked.connect(self._reset)
        self.btn_copy = QPushButton("Copy QC Report")
        self.btn_copy.setObjectName("btn_sec")
        self.btn_copy.clicked.connect(self._copy_report)
        self.btn_export = QPushButton("Export QC Report")
        self.btn_export.setObjectName("btn_sec")
        self.btn_export.clicked.connect(self._export_report)
        actions.addWidget(self.btn_reset)
        actions.addStretch()
        actions.addWidget(self.btn_copy)
        actions.addWidget(self.btn_export)
        main_lay.addLayout(actions)

    def _build_group(self, group_name, items):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(7)

        title = QLabel(group_name.upper())
        title.setStyleSheet("color: #E8742A; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        lay.addWidget(title)

        for text in items:
            chk = QCheckBox(text)
            chk.setStyleSheet(
                "QCheckBox { color: #E8E8F0; font-size: 13px; spacing: 8px; }"
                "QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #353545; border-radius: 4px; background: #08080D; }"
                "QCheckBox::indicator:checked { background: #3AD68A; border-color: #3AD68A; }"
            )
            chk.stateChanged.connect(self._update_progress)
            lay.addWidget(chk)
            self.checkboxes.append(chk)
        return frame

    def apply_profile(self, profile_data):
        self.profile_data = profile_data or {}
        if not self.txt_channel.text().strip() and self.profile_data.get("name"):
            self.txt_channel.setText(self.profile_data.get("name", ""))

    def load_context(self, title="", channel=""):
        if title:
            self.txt_video_title.setText(title)
        if channel:
            self.txt_channel.setText(channel)

    def _update_progress(self):
        total = len(self.checkboxes)
        done = sum(1 for chk in self.checkboxes if chk.isChecked())
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.lbl_progress.setText(f"{done} / {total} complete")
        if done == total:
            self.lbl_status.setText("Ready to publish")
            self.lbl_status.setStyleSheet("color: #3AD68A; font-weight: bold;")
            QMessageBox.information(self, "QC complete", "All QC checks are complete. The video is ready to publish or schedule.")
        else:
            self.lbl_status.setText("Not ready")
            self.lbl_status.setStyleSheet("color: #E8742A; font-weight: bold;")

    def _reset(self):
        for chk in self.checkboxes:
            chk.setChecked(False)
        self._update_progress()

    def _report_text(self):
        done = sum(1 for chk in self.checkboxes if chk.isChecked())
        total = len(self.checkboxes)
        status = "READY TO PUBLISH" if done == total else "NOT READY"
        lines = [
            "QC REPORT",
            f"Video: {self.txt_video_title.text().strip() or '-'}",
            f"Channel: {self.txt_channel.text().strip() or '-'}",
            f"Progress: {done}/{total}",
            f"Status: {status}",
            "",
        ]
        index = 0
        for group_name, items in QC_GROUPS:
            lines.append(f"=== {group_name.upper()} ===")
            for item in items:
                checked = self.checkboxes[index].isChecked()
                lines.append(f"[{'x' if checked else ' '}] {item}")
                index += 1
            lines.append("")
        remaining = [chk.text() for chk in self.checkboxes if not chk.isChecked()]
        lines.append("=== REMAINING ===")
        if remaining:
            lines.extend(f"- {item}" for item in remaining)
        else:
            lines.append("None")
        return "\n".join(lines).strip()

    def _copy_report(self):
        QApplication.clipboard().setText(self._report_text())
        QMessageBox.information(self, "Copied", "QC report copied.")

    def _export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export QC report", "upload-qc-report.txt", "Text Files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._report_text())
        QMessageBox.information(self, "Exported", path)
