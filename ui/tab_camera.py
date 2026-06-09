import csv
import io
import re

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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


class CameraMovementTab(QWidget):
    request_load_tool2 = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._scene_data: list[dict] = []
        self._outputs = {"capcut": "", "ai": "", "csv": ""}

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 12, 15, 12)
        main_lay.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 6)
        vbox_h = QVBoxLayout()

        lbl_title = QLabel("Production Motion Sheet")
        lbl_title.setObjectName("page_title")
        vbox_h.addWidget(lbl_title)

        lbl_desc = QLabel("Create CapCut keyframes and AI video motion prompts from Tool 2 scenes")
        lbl_desc.setObjectName("page_desc")
        vbox_h.addWidget(lbl_desc)

        header.addLayout(vbox_h)
        header.addStretch()

        lbl_badge = QLabel("Tool 4")
        lbl_badge.setObjectName("page_badge")
        header.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        hint = QLabel(
            "<b>Workflow:</b> Run Tool 2 through Assign Assets/Deduplicate, load the scenes here, "
            "then generate a motion sheet for CapCut or AI video tools."
        )
        hint.setStyleSheet(
            "background: rgba(155,127,255,0.06); border: 1px solid rgba(155,127,255,0.18); "
            "border-radius: 8px; padding: 10px 14px; color: #9B7FFF; font-size: 13px;"
        )
        hint.setWordWrap(True)
        main_lay.addWidget(hint)

        controls = QFrame()
        controls.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        control_lay = QVBoxLayout(controls)
        control_lay.setContentsMargins(12, 10, 12, 12)
        control_lay.setSpacing(10)

        top_bar = QHBoxLayout()
        self.lbl_loaded = QLabel("0 scenes loaded")
        self.lbl_loaded.setObjectName("muted")
        self.btn_load_tool2 = QPushButton("Load Scenes from Tool 2")
        self.btn_load_tool2.setObjectName("btn_sec")
        self.btn_load_tool2.clicked.connect(lambda: self.request_load_tool2.emit())
        top_bar.addWidget(self.lbl_loaded)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_load_tool2)
        control_lay.addLayout(top_bar)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.addWidget(QLabel("TARGET", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("MOTION STYLE", objectName="muted"), 0, 1)
        grid.addWidget(QLabel("DEFAULT DURATION", objectName="muted"), 0, 2)

        self.cmb_target = QComboBox()
        self.cmb_target.addItems(["CapCut", "Runway", "Kling", "Luma", "Veo"])
        grid.addWidget(self.cmb_target, 1, 0)

        self.cmb_motion_style = QComboBox()
        self.cmb_motion_style.addItems(["Subtle Cinematic", "Standard Documentary", "Dynamic Emotional"])
        grid.addWidget(self.cmb_motion_style, 1, 1)

        self.cmb_duration = QComboBox()
        self.cmb_duration.addItems(["Use Tool 2 duration", "4s", "5s", "6s", "8s"])
        grid.addWidget(self.cmb_duration, 1, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        control_lay.addLayout(grid)

        actions = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Motion Sheet")
        self.btn_generate.setObjectName("btn_primary")
        self.btn_generate.clicked.connect(self._generate_outputs)
        self.btn_copy = QPushButton("Copy Tab")
        self.btn_copy.setObjectName("btn_sec")
        self.btn_copy.clicked.connect(self._copy_current_tab)
        self.btn_export = QPushButton("Export Tab")
        self.btn_export.setObjectName("btn_sec")
        self.btn_export.clicked.connect(self._export_current_tab)
        actions.addWidget(self.btn_generate)
        actions.addStretch()
        actions.addWidget(self.btn_copy)
        actions.addWidget(self.btn_export)
        control_lay.addLayout(actions)
        main_lay.addWidget(controls)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Loaded Tool 2 scenes will appear here.")
        self.preview.setFixedHeight(92)
        self.preview.setStyleSheet(
            "background: #08080D; border: 1px solid #252535; border-radius: 6px; "
            "color: #A1A1AA; font-family: 'Space Mono', monospace; font-size: 12px;"
        )
        main_lay.addWidget(self.preview)

        self.tabs = QTabBar()
        for name in ["CapCut Sheet", "AI Video Prompts", "CSV"]:
            self.tabs.addTab(name)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setStyleSheet(
            "QTabBar::tab { background: #171724; color: #A1A1AA; padding: 7px 14px; border: 1px solid #252535; }"
            "QTabBar::tab:selected { color: #E8742A; border-bottom: 2px solid #E8742A; }"
        )
        main_lay.addWidget(self.tabs)

        self.stack = QStackedWidget()
        self.txt_capcut = self._make_output_box()
        self.txt_ai = self._make_output_box()
        self.txt_csv = self._make_output_box()
        self.stack.addWidget(self.txt_capcut)
        self.stack.addWidget(self.txt_ai)
        self.stack.addWidget(self.txt_csv)
        main_lay.addWidget(self.stack)

    def _make_output_box(self):
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setStyleSheet(
            "background: #08080D; border: 1px solid #252535; border-radius: 6px; "
            "color: #E8E8F0; font-family: 'Space Mono', monospace; font-size: 12px; padding: 10px;"
        )
        return txt

    def load_data(self, scene_data: list[dict]):
        self._scene_data = [dict(scene) for scene in scene_data or []]
        self.lbl_loaded.setText(f"{len(self._scene_data)} scenes loaded")
        lines = []
        for scene in self._scene_data[:6]:
            lines.append(
                f"{int(scene.get('id', len(lines) + 1)):03d} | "
                f"{scene.get('camera', 'Medium shot')} | "
                f"{scene.get('character', 'none')} @ {scene.get('background', '')} | "
                f"{scene.get('dur', '5s')}"
            )
        if len(self._scene_data) > 6:
            lines.append(f"... +{len(self._scene_data) - 6} scenes")
        self.preview.setPlainText("\n".join(lines))

    def _duration_for_scene(self, scene):
        selected = self.cmb_duration.currentText()
        if selected != "Use Tool 2 duration":
            return selected
        return scene.get("dur", "5s") or "5s"

    def _motion_for_scene(self, scene):
        camera = (scene.get("camera", "") or "").lower()
        action = (scene.get("action_desc", "") or scene.get("vo_text", "") or "").lower()
        style = self.cmb_motion_style.currentText()

        if "extreme close" in camera:
            motion = ("Push IN Fast", "Scale 100% -> 122%, slight handheld drift")
        elif "close" in camera:
            motion = ("Slow Zoom IN", "Scale 100% -> 112%")
        elif "establishing" in camera or "wide" in camera:
            motion = ("Slow Pan L->R", "Scale 110%, X -5% -> X +5%")
        elif "pov" in camera:
            motion = ("Subtle Handheld Drift", "Scale 108%, X/Y drift within 3%")
        elif "over-the-shoulder" in camera or "shoulder" in camera:
            motion = ("Dolly IN", "Scale 102% -> 114%, keep foreground shoulder on edge")
        elif any(word in action for word in ["fall", "lose", "alone", "empty", "sad", "mất", "cô đơn", "thất vọng"]):
            motion = ("Slow Zoom OUT", "Scale 114% -> 100%")
        elif any(word in action for word in ["rise", "win", "realize", "success", "thành công", "nhận ra"]):
            motion = ("Tilt UP", "Scale 110%, Y +4% -> Y 0%")
        else:
            motion = ("Ken Burns", "Scale 100% -> 108%")

        if style == "Subtle Cinematic":
            motion = (motion[0], motion[1] + ", ease in-out, very slow")
        elif style == "Dynamic Emotional":
            motion = (motion[0], motion[1] + ", stronger ease, add 1-2% parallax if possible")
        return motion

    def _emotion_note(self, scene, motion_name):
        text = f"{scene.get('action_desc', '')} {scene.get('vo_text', '')}".lower()
        if "silence" in text or "im lặng" in text:
            return "Hold weight; avoid flashy movement."
        if "alone" in text or "cô đơn" in text:
            return "Make the frame feel wider and emptier."
        if "realize" in text or "nhận ra" in text:
            return "Let the movement reveal the emotional turn."
        if "Zoom OUT" in motion_name:
            return "Use distance to emphasize loss or isolation."
        if "Push" in motion_name:
            return "Use impact only for a strong beat."
        return "Keep motion invisible and cinematic."

    def _ai_prompt_for_scene(self, scene, motion_name, duration):
        target = self.cmb_target.currentText()
        char = scene.get("char_safe") or scene.get("character") or "Protagonist"
        bg = scene.get("bg_safe") or scene.get("background") or "Location01"
        action = scene.get("action_desc") or scene.get("vo_text") or "quiet emotional moment"
        camera = scene.get("camera", "Medium shot")
        return (
            f"Scene {int(scene.get('id', 1)):03d} ({target}, {duration}): "
            f"{motion_name.lower()} on a {camera.lower()} of [{char}] at [{bg}], "
            f"{action}. Subtle cinematic motion, preserve the original composition and character identity, "
            f"no new objects, no text, no logos, no face distortion."
        )

    def _generate_outputs(self):
        if not self._scene_data:
            QMessageBox.warning(self, "Missing scenes", "Load scenes from Tool 2 first.")
            return

        capcut_lines = []
        ai_lines = []
        csv_rows = []
        for index, scene in enumerate(self._scene_data, 1):
            scene_id = int(scene.get("id", index))
            duration = self._duration_for_scene(scene)
            motion_name, keyframe = self._motion_for_scene(scene)
            note = self._emotion_note(scene, motion_name)
            image_name = f"scene_{scene_id:03d}.png"

            capcut_lines.append(
                f"Scene {scene_id:03d} | {image_name}\n"
                f"Duration: {duration}\n"
                f"Motion: {motion_name}\n"
                f"Keyframe: {keyframe}\n"
                f"Keep safe: do not crop important face/hands; keep subject readable.\n"
                f"Emotion note: {note}\n"
            )
            ai_lines.append(self._ai_prompt_for_scene(scene, motion_name, duration))
            csv_rows.append({
                "scene": f"{scene_id:03d}",
                "image": image_name,
                "duration": duration,
                "motion": motion_name,
                "keyframe": keyframe,
                "camera": scene.get("camera", ""),
                "character": scene.get("character", ""),
                "background": scene.get("background", ""),
                "note": note,
            })

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

        self._outputs = {
            "capcut": "\n".join(capcut_lines),
            "ai": "\n\n".join(ai_lines),
            "csv": csv_buffer.getvalue(),
        }
        self.txt_capcut.setPlainText(self._outputs["capcut"])
        self.txt_ai.setPlainText(self._outputs["ai"])
        self.txt_csv.setPlainText(self._outputs["csv"])
        self.tabs.setCurrentIndex(0)

    def _on_tab_changed(self, index):
        self.stack.setCurrentIndex(index)

    def _current_text(self):
        return [self.txt_capcut, self.txt_ai, self.txt_csv][self.tabs.currentIndex()].toPlainText().strip()

    def _copy_current_tab(self):
        text = self._current_text()
        if not text:
            QMessageBox.warning(self, "Empty", "Generate a motion sheet first.")
            return
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", "Copied current tab.")

    def _export_current_tab(self):
        text = self._current_text()
        if not text:
            QMessageBox.warning(self, "Empty", "Generate a motion sheet first.")
            return
        default_names = ["capcut-motion-sheet.txt", "ai-video-motion-prompts.txt", "motion-sheet.csv"]
        filters = ["Text Files (*.txt)", "Text Files (*.txt)", "CSV Files (*.csv)"]
        idx = self.tabs.currentIndex()
        path, _ = QFileDialog.getSaveFileName(self, "Export motion sheet", default_names[idx], filters[idx])
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        QMessageBox.information(self, "Exported", path)
