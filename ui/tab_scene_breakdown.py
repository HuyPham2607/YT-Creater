from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QGridLayout,
                             QComboBox, QScrollArea, QFrame, QSplitter,
                             QInputDialog, QMessageBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QTabBar,
                             QStackedWidget, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QColor, QBrush, QFont
from ui.components import DropZoneWidget
import json
import os
import re
from threads.scene_worker import SceneWorker


# ══════════════════════════════════════════════════════════════════════
#  HELPER: Tạo tên an toàn cho G-Labs (tránh tên thương hiệu/nhạy cảm)
# ══════════════════════════════════════════════════════════════════════
_BRAND_KEYWORDS = [
    "vietcombank", "techcombank", "bidv", "agribank", "vpbank",
    "momo", "zalopay", "grab", "shopee", "lazada", "tiki",
    "facebook", "google", "youtube", "tiktok", "instagram",
    "apple", "samsung", "iphone", "android",
    "coca", "pepsi", "heineken", "tiger",
]

def make_glabs_safe_name(kebab_name: str, location_index: int) -> str:
    """
    Chuyển kebab-name sang tên an toàn cho G-Labs prompt.
    - Nếu chứa brand keyword → 'Location{N:02d}'
    - Nếu tên Việt bình thường  → PascalCase (QuanPhoSang)
    - Nhân vật                  → 'Protagonist' / 'Character{N}'
    """
    lower = kebab_name.lower()
    for brand in _BRAND_KEYWORDS:
        if brand in lower:
            return f"Location{location_index:02d}"
    # PascalCase từ kebab
    return "".join(word.capitalize() for word in kebab_name.split("-"))


def build_glabs_prompt(scene_style: str, camera: str,
                       char_safe: str, bg_safe: str,
                       action_desc: str) -> str:
    """
    Ghép full G-Labs prompt theo đúng cấu trúc:
    [sceneStyle] A [camera] captures [Char] at [Bg] as [action]. NO TEXT NO WORDS on image.
    """
    # ── Normalize camera → luôn dạng "A X shot" ──
    raw = camera.strip() if camera.strip() else "medium shot"
    raw_lower = raw.lower()

    # Map các tên camera phổ biến sang phrase chuẩn
    _CAM_MAP = {
        "close-up":            "close-up shot",
        "close up":            "close-up shot",
        "extreme close-up":    "extreme close-up shot",
        "extreme close up":    "extreme close-up shot",
        "wide shot":           "wide shot",
        "wide":                "wide shot",
        "medium shot":         "medium shot",
        "medium":              "medium shot",
        "medium close":        "medium close-up shot",
        "establishing shot":   "wide establishing shot",
        "establishing":        "wide establishing shot",
        "over-the-shoulder":   "over-the-shoulder shot",
        "over the shoulder":   "over-the-shoulder shot",
        "pov":                 "POV shot",
    }

    normalized = raw  # fallback giữ nguyên
    for key, val in _CAM_MAP.items():
        if key in raw_lower:
            normalized = val
            break

    # Thêm "A " ở đầu nếu chưa có
    if not normalized.lower().startswith("a "):
        cam_phrase = f"A {normalized}"
    else:
        cam_phrase = normalized

    # ── Đảm bảo sceneStyle không trống ──
    style = scene_style.strip()
    if not style:
        style = DEFAULT_SCENE_STYLE

    # ── Ghép prompt cuối ──
    return (
        f"{style} "
        f"{cam_phrase} captures [{char_safe}] at [{bg_safe}] "
        f"as {action_desc.strip().rstrip('.')}. "
        f"NO TEXT NO WORDS on image."
    )


# Default sceneStyle dùng khi field trống — user nên override bằng style của kênh mình
DEFAULT_SCENE_STYLE = (
    "Across all scenes in this video. "
    "Cinematic 2D cartoon with bold uniform 3 to 4 pixel black outlines "
    "and flat cell-shading using one soft directional shadow pass, no gradients. "
    "All characters share 1:2 head-to-body proportion with round oval heads, "
    "warm cream beige Vietnamese skin tone, simple solid black dot eyes with no sclera, "
    "thin expressive black eyebrow strokes, tiny pink mouth. "
    "Color palette of deep night blue, copper gold, soft cream white, cool grey. "
    "Moderate-detail Vietnamese urban backgrounds, directional warm copper-gold lighting "
    "from upper-left corner casting long soft shadows, "
    "contemplative quietly-tense documentary mood. Same art style in every frame."
)


# ══════════════════════════════════════════════════════════════════════
#  TAB WIDGETS (các tab con trong QStackedWidget)
# ══════════════════════════════════════════════════════════════════════

class GLabsPromptsWidget(QWidget):
    """Tab: G-LABS IMAGE PROMPTS"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(8)

        # Toolbar
        bar = QHBoxLayout()
        self.lbl_info = QLabel("0 prompts")
        self.lbl_info.setStyleSheet("color: #606075; font-size: 12px;")

        self.lbl_rename_hint = QLabel("")
        self.lbl_rename_hint.setStyleSheet(
            "color: #E8742A; font-size: 11px; "
            "background: rgba(232,116,42,0.06); "
            "border: 1px solid rgba(232,116,42,0.2); "
            "border-radius: 4px; padding: 4px 8px;")
        self.lbl_rename_hint.hide()

        btn_copy_all = QPushButton("📋 Copy All")
        btn_copy_all.setStyleSheet(
            "background: #252535; color: #E8E8F0; border: 1px solid #353545; "
            "border-radius: 4px; padding: 5px 12px; font-size: 12px;")
        btn_copy_all.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_copy_all.clicked.connect(self._copy_all)

        btn_export = QPushButton("⬇ Export TXT")
        btn_export.setStyleSheet(
            "background: #252535; color: #E8E8F0; border: 1px solid #353545; "
            "border-radius: 4px; padding: 5px 12px; font-size: 12px;")
        btn_export.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_export.clicked.connect(self._export_txt)

        bar.addWidget(self.lbl_info)
        bar.addWidget(self.lbl_rename_hint)
        bar.addStretch()
        bar.addWidget(btn_copy_all)
        bar.addWidget(btn_export)
        lay.addLayout(bar)

        # Danh sách prompts
        self.prompt_list = QTextEdit()
        self.prompt_list.setReadOnly(True)
        self.prompt_list.setStyleSheet(
            "background: #0A0A12; border: 1px solid #252535; border-radius: 6px; "
            "color: #C8C8D8; font-family: 'Space Mono', monospace; font-size: 12px; "
            "padding: 14px; line-height: 1.6;")
        lay.addWidget(self.prompt_list)

        self._prompts: list[str] = []
        self._rename_map: dict[str, str] = {}  # original → safe name

    def load_prompts(self, prompts: list[str], rename_map: dict[str, str]):
        self._prompts = prompts
        self._rename_map = rename_map

        self.lbl_info.setText(f"{len(prompts)} prompts")

        # Hiển thị rename hint nếu có brand được đổi tên
        renamed = {k: v for k, v in rename_map.items() if k != v}
        if renamed:
            hints = " | ".join(f"{k} → {v}" for k, v in renamed.items())
            self.lbl_rename_hint.setText(f"⚠ TÊN ĐÃ ĐỔI CHO G-LABS (TRÁNH VI PHẠM CHÍNH SÁCH): {hints}")
            self.lbl_rename_hint.show()
        else:
            self.lbl_rename_hint.hide()

        # Render từng prompt với số thứ tự
        lines = []
        for i, p in enumerate(prompts, 1):
            lines.append(f"── Scene {i:03d} ──────────────────────────")
            lines.append(p)
            lines.append("")
        self.prompt_list.setPlainText("\n".join(lines))

    def _copy_all(self):
        if not self._prompts:
            return
        text = "\n".join(self._prompts)
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Đã copy", f"Đã copy {len(self._prompts)} prompts vào clipboard!")

    def _export_txt(self):
        if not self._prompts:
            QMessageBox.warning(self, "Trống", "Chưa có prompts để export.")
            return
        path = "glabs_prompts.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self._prompts))
        QMessageBox.information(self, "Đã xuất", f"File đã lưu: {os.path.abspath(path)}")


class Veo3PromptsWidget(QWidget):
    """Tab: VEO3 VIDEO PROMPTS — prompt cho video AI (khác với ảnh tĩnh)"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(8)

        hint = QLabel(
            "💡 <b>VEO3 Prompts</b> = phiên bản motion cho từng scene. "
            "Thêm motion keywords: camera pan, zoom, character walks, etc.")
        hint.setStyleSheet(
            "background: rgba(90,155,255,0.06); border: 1px solid rgba(90,155,255,0.15); "
            "border-radius: 6px; padding: 10px 14px; color: #5A9BFF; font-size: 12px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        bar = QHBoxLayout()
        self.lbl_info = QLabel("0 prompts")
        self.lbl_info.setStyleSheet("color: #606075; font-size: 12px;")
        btn_copy = QPushButton("📋 Copy All")
        btn_copy.setStyleSheet(
            "background: #252535; color: #E8E8F0; border: 1px solid #353545; "
            "border-radius: 4px; padding: 5px 12px; font-size: 12px;")
        btn_copy.clicked.connect(self._copy_all)
        bar.addWidget(self.lbl_info); bar.addStretch(); bar.addWidget(btn_copy)
        lay.addLayout(bar)

        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setStyleSheet(
            "background: #0A0A12; border: 1px solid #252535; border-radius: 6px; "
            "color: #C8C8D8; font-family: 'Space Mono', monospace; font-size: 12px; padding: 14px;")
        lay.addWidget(self.txt)
        self._prompts: list[str] = []

    def load_prompts(self, scene_data: list[dict], scene_style: str):
        """
        Tạo VEO3 prompt từ scene data.
        VEO3 thêm motion layer: camera movement + character action.
        """
        MOTION_MAP = {
            "Close-up":         "slow push-in",
            "Extreme Close-up": "very slow push-in, slight shake",
            "Wide shot":        "slow pan left to right",
            "Establishing shot":"slow aerial drift downward",
            "Medium shot":      "static with subtle zoom",
            "Over-the-shoulder":"slight dolly forward",
            "POV":              "handheld first-person drift",
        }
        self._prompts = []
        lines = []

        for i, scene in enumerate(scene_data, 1):
            camera   = scene.get("camera", "Medium shot")
            char     = scene.get("char_safe", "Protagonist")
            bg       = scene.get("bg_safe", "Location01")
            action   = scene.get("action_desc", "standing still")
            motion   = MOTION_MAP.get(camera, "slow zoom")
            duration = scene.get("dur", "5s")

            prompt = (
                f"{scene_style.strip()} "
                f"[{char}] at [{bg}]: {action} "
                f"Camera: {motion}. Duration: {duration}. "
                f"Cinematic mood, no dialogue, no text on screen."
            )
            self._prompts.append(prompt)
            lines.append(f"── Scene {i:03d} ──────────────────────────")
            lines.append(prompt)
            lines.append("")

        self.lbl_info.setText(f"{len(self._prompts)} prompts")
        self.txt.setPlainText("\n".join(lines))

    def _copy_all(self):
        if self._prompts:
            QApplication.clipboard().setText("\n".join(self._prompts))
            QMessageBox.information(self, "Đã copy", f"Đã copy {len(self._prompts)} VEO3 prompts!")


class AssetsWidget(QWidget):
    """Tab: ASSETS — bảng tổng hợp tất cả nhân vật + background xuất hiện"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        # Giải thích tab
        hint = QLabel(
            "📦 <b>ASSETS</b> = danh sách tất cả nhân vật và bối cảnh được dùng trong video. "
            "Hiển thị số lần xuất hiện và scenes liên quan. "
            "Dùng để biết cần tạo bao nhiêu reference images cho Tool 3.")
        hint.setStyleSheet(
            "background: rgba(58,214,138,0.06); border: 1px solid rgba(58,214,138,0.15); "
            "border-radius: 6px; padding: 10px 14px; color: #3AD68A; font-size: 12px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        cols_lay = QHBoxLayout()
        cols_lay.setSpacing(16)

        # Cột Characters
        char_box = QFrame()
        char_box.setStyleSheet(
            "QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        char_inner = QVBoxLayout(char_box)
        char_inner.setContentsMargins(0, 0, 0, 0)

        char_head = QFrame()
        char_head.setStyleSheet(
            "background: #171724; border: none; border-bottom: 1px solid #252535; "
            "border-top-left-radius: 8px; border-top-right-radius: 8px;")
        ch_lay = QHBoxLayout(char_head); ch_lay.setContentsMargins(14, 10, 14, 10)
        ch_lay.addWidget(QLabel("🎭 NHÂN VẬT", styleSheet="color: #3AD68A; font-weight: bold; font-size: 11px;"))
        char_inner.addWidget(char_head)

        self.tbl_chars = self._make_asset_table(["NHÂN VẬT", "XUẤT HIỆN", "SCENES"])
        char_inner.addWidget(self.tbl_chars)
        cols_lay.addWidget(char_box)

        # Cột Backgrounds
        bg_box = QFrame()
        bg_box.setStyleSheet(
            "QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        bg_inner = QVBoxLayout(bg_box)
        bg_inner.setContentsMargins(0, 0, 0, 0)

        bg_head = QFrame()
        bg_head.setStyleSheet(
            "background: #171724; border: none; border-bottom: 1px solid #252535; "
            "border-top-left-radius: 8px; border-top-right-radius: 8px;")
        bh_lay = QHBoxLayout(bg_head); bh_lay.setContentsMargins(14, 10, 14, 10)
        bh_lay.addWidget(QLabel("🌆 BỐI CẢNH", styleSheet="color: #5A9BFF; font-weight: bold; font-size: 11px;"))
        bg_inner.addWidget(bg_head)

        self.tbl_bgs = self._make_asset_table(["BỐI CẢNH", "XUẤT HIỆN", "SCENES"])
        bg_inner.addWidget(self.tbl_bgs)
        cols_lay.addWidget(bg_box)

        lay.addLayout(cols_lay)

    def _make_asset_table(self, headers: list[str]) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setStyleSheet(
            "QTableWidget { background: transparent; border: none; color: #E8E8F0; font-size: 13px; gridline-color: #1F1F2E; }"
            "QHeaderView::section { background: #171724; color: #606075; font-weight: bold; font-size: 10px; padding: 6px; border: none; border-bottom: 1px solid #252535; }"
            "QTableWidget::item { padding: 8px; }")
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl.setColumnWidth(1, 90)
        tbl.verticalHeader().setVisible(False)
        return tbl

    def load_assets(self, scene_data: list[dict]):
        """Tổng hợp thống kê từ scene_data đã assign."""
        from collections import defaultdict
        char_scenes = defaultdict(list)
        bg_scenes   = defaultdict(list)

        for scene in scene_data:
            idx  = scene.get("id", 0)
            char = scene.get("character", "none")
            bg   = scene.get("background", "")
            if char and char != "none":
                char_scenes[char].append(str(idx))
            if bg:
                bg_scenes[bg].append(str(idx))

        self._fill_table(self.tbl_chars, char_scenes, "#3AD68A")
        self._fill_table(self.tbl_bgs,   bg_scenes,   "#5A9BFF")

    def _fill_table(self, tbl: QTableWidget, data: dict, color: str):
        tbl.setRowCount(len(data))
        for row, (name, scenes) in enumerate(sorted(data.items())):
            count_item = QTableWidgetItem(str(len(scenes)))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            count_item.setForeground(QBrush(QColor(color)))
            font = count_item.font(); font.setBold(True); count_item.setFont(font)

            scene_preview = ", ".join(scenes[:8])
            if len(scenes) > 8:
                scene_preview += f" +{len(scenes)-8}"

            tbl.setItem(row, 0, QTableWidgetItem(name))
            tbl.setItem(row, 1, count_item)
            tbl.setItem(row, 2, QTableWidgetItem(scene_preview))


class CameraGuideWidget(QWidget):
    """Tab: CAMERA GUIDE — thống kê camera angles và gợi ý placement"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        hint = QLabel(
            "🎬 <b>CAMERA GUIDE</b> = phân tích phân bổ camera angles trong video. "
            "Giúp kiểm tra xem video có đa dạng góc quay không, "
            "tránh dùng cùng 1 góc quá nhiều lần liên tiếp.")
        hint.setStyleSheet(
            "background: rgba(155,127,255,0.06); border: 1px solid rgba(155,127,255,0.15); "
            "border-radius: 6px; padding: 10px 14px; color: #9B7FFF; font-size: 12px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # Stats bar camera
        self.stats_bar = QHBoxLayout()
        self.stats_bar.setSpacing(10)
        lay.addLayout(self.stats_bar)

        # Bảng chi tiết
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["SCENE", "CAMERA", "CHARACTER", "BACKGROUND"])
        self.tbl.setStyleSheet(
            "QTableWidget { background: #0A0A12; border: 1px solid #252535; border-radius: 6px; color: #E8E8F0; font-size: 12px; gridline-color: #1F1F2E; }"
            "QHeaderView::section { background: #171724; color: #606075; font-weight: bold; font-size: 10px; padding: 6px; border: none; border-bottom: 1px solid #252535; }"
            "QTableWidget::item { padding: 7px; }")
        hdr = self.tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnWidth(0, 65)
        self.tbl.setColumnWidth(1, 160)
        self.tbl.verticalHeader().setVisible(False)
        lay.addWidget(self.tbl)

    _CAMERA_COLORS = {
        "close-up":         "#E8742A",
        "extreme close-up": "#FF6060",
        "wide shot":        "#5A9BFF",
        "establishing":     "#3AD68A",
        "medium":           "#9B7FFF",
        "over-the-shoulder":"#C9A84C",
        "pov":              "#FF9F40",
    }

    def load_data(self, scene_data: list[dict]):
        from collections import Counter
        cameras = [s.get("camera", "").lower() for s in scene_data]
        counter = Counter(cameras)

        # Xóa stats bar cũ
        while self.stats_bar.count():
            item = self.stats_bar.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for cam, cnt in counter.most_common():
            color = next((v for k, v in self._CAMERA_COLORS.items() if k in cam), "#606075")
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background: #171724; border: 1px solid #252535; border-radius: 6px; }}")
            c_lay = QVBoxLayout(card); c_lay.setContentsMargins(12, 8, 12, 8); c_lay.setSpacing(2)
            lbl_name = QLabel(cam.upper() if cam else "—")
            lbl_name.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold;")
            lbl_cnt = QLabel(str(cnt))
            lbl_cnt.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold; font-family: monospace;")
            c_lay.addWidget(lbl_name); c_lay.addWidget(lbl_cnt)
            self.stats_bar.addWidget(card)
        self.stats_bar.addStretch()

        # Fill table
        self.tbl.setRowCount(len(scene_data))
        for row, scene in enumerate(scene_data):
            cam   = scene.get("camera", "")
            color = next((v for k, v in self._CAMERA_COLORS.items() if k in cam.lower()), "#C8C8D8")

            stt_item = QTableWidgetItem(f"{scene.get('id',row+1):03d}")
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stt_item.setForeground(QBrush(QColor("#E8742A")))

            cam_item = QTableWidgetItem(cam)
            cam_item.setForeground(QBrush(QColor(color)))
            cam_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.tbl.setItem(row, 0, stt_item)
            self.tbl.setItem(row, 1, cam_item)
            self.tbl.setItem(row, 2, QTableWidgetItem(scene.get("character", "")))
            self.tbl.setItem(row, 3, QTableWidgetItem(scene.get("background", "")))


class ProductionNotesWidget(QWidget):
    """Tab: PRODUCTION NOTES — ghi chú tự do cho video"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(8)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("📝 Ghi chú sản xuất",
                             styleSheet="color: #E8E8F0; font-weight: bold; font-size: 13px;"))
        bar.addStretch()
        btn_clear = QPushButton("🗑 Xóa hết")
        btn_clear.setStyleSheet(
            "background: rgba(232,116,42,0.1); color: #E8742A; border: 1px solid rgba(232,116,42,0.25); "
            "border-radius: 4px; padding: 5px 12px; font-size: 12px;")
        btn_clear.clicked.connect(lambda: self.txt.clear())
        bar.addWidget(btn_clear)
        lay.addLayout(bar)

        self.txt = QTextEdit()
        self.txt.setPlaceholderText(
            "Ghi chú tự do cho video này...\n\n"
            "VD:\n"
            "- Nhân vật chính cần mặc áo xanh navy\n"
            "- Cảnh ngân hàng: ánh sáng ấm, ban ngày\n"
            "- Tránh hiển thị logo thương hiệu\n"
            "- Nhạc nền: uplifting, không quá 90 BPM")
        self.txt.setStyleSheet(
            "background: #0A0A12; border: 1px solid #252535; border-radius: 6px; "
            "color: #E8E8F0; font-size: 13px; padding: 14px;")
        lay.addWidget(self.txt)

        # Auto-generated checklist từ assign data
        self.chk_box = QFrame()
        self.chk_box.setStyleSheet(
            "QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 6px; }")
        chk_inner = QVBoxLayout(self.chk_box)
        chk_inner.setContentsMargins(14, 10, 14, 10)
        self.lbl_checklist = QLabel("Chạy Assign Assets để xem checklist tự động.")
        self.lbl_checklist.setStyleSheet("color: #606075; font-size: 12px;")
        self.lbl_checklist.setWordWrap(True)
        chk_inner.addWidget(self.lbl_checklist)
        lay.addWidget(self.chk_box)

    def load_checklist(self, chars: list[str], bgs: list[str]):
        lines = ["✅ CHECKLIST TRƯỚC KHI RENDER:\n"]
        for c in chars:
            lines.append(f"  □ Reference image: nhân vật [{c}]")
        for b in bgs:
            lines.append(f"  □ Reference image: bối cảnh [{b}]")
        lines += [
            "",
            "  □ Kiểm tra tên thương hiệu trong prompts",
            "  □ Xem lại camera variety (tránh lặp)",
            "  □ Export G-Labs TXT",
            "  □ Upload reference images lên G-Labs",
        ]
        self.lbl_checklist.setText("\n".join(lines))
        self.lbl_checklist.setStyleSheet("color: #C8C8D8; font-size: 12px; font-family: monospace;")


# ══════════════════════════════════════════════════════════════════════
#  MAIN TAB CLASS
# ══════════════════════════════════════════════════════════════════════

class SceneBreakdownTab(QWidget):
    transfer_to_tool3 = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(10, 0, 10, 0)

        # ── HEADER ──────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 2)
        vbox_h = QVBoxLayout()
        lbl_title = QLabel("Scene Breakdown"); lbl_title.setObjectName("page_title")
        lbl_desc  = QLabel("Split script → Assign character + background → Tạo G-Labs prompts")
        lbl_desc.setObjectName("page_desc")
        vbox_h.addWidget(lbl_title); vbox_h.addWidget(lbl_desc)
        header.addLayout(vbox_h); header.addStretch()
        lbl_badge = QLabel("Tool 2"); lbl_badge.setObjectName("page_badge")
        header.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignTop)
        main_lay.addLayout(header)

        # ── SCROLL ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 10, 0, 10)
        lay.setSpacing(16)

        # hint
        hint = QLabel(
            "💡 <b>Workflow:</b> Lọc Script → Split Scenes → Pre-scan → Assign Assets "
            "(tự tạo G-Labs prompts) → Export / sang Tool 3")
        hint.setStyleSheet(
            "background: rgba(232,116,42,0.06); border: 1px solid rgba(232,116,42,0.15); "
            "border-radius: 8px; padding: 12px 16px; color: #E8742A; font-size: 13px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # ── SETTINGS ────────────────────────────────────────────────
        grid = QGridLayout(); grid.setSpacing(14)
        for col, lbl in enumerate(["VISUAL STYLE", "NGÔN NGỮ VO", "MIN KÝ TỰ / SCENE", "MAX KÝ TỰ / SCENE"]):
            l = QLabel(lbl); l.setObjectName("muted")
            grid.addWidget(l, 0, col)
        self.txt_style = QLineEdit("Crayon Capital - Dark (cinematic)")
        self.txt_lang  = QLineEdit("Tiếng Việt")
        self.txt_min   = QLineEdit("30")
        self.txt_max   = QLineEdit("100")
        for col, w in enumerate([self.txt_style, self.txt_lang, self.txt_min, self.txt_max]):
            grid.addWidget(w, 1, col)
        lay.addLayout(grid)

        # ── SCENE STYLE (dùng để build G-Labs prompt) ───────────────
        scene_style_head = QHBoxLayout()
        lbl_ss = QLabel("SCENE STYLE PROMPT (dùng cho G-Labs)")
        lbl_ss.setObjectName("muted")
        self.btn_reset_style = QPushButton("↺ Reset về Default")
        self.btn_reset_style.setStyleSheet(
            "background: transparent; color: #606075; border: 1px solid #353545; "
            "border-radius: 4px; padding: 3px 10px; font-size: 11px;")
        self.btn_reset_style.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_reset_style.clicked.connect(
            lambda: self.txt_scene_style.setPlainText(DEFAULT_SCENE_STYLE))
        scene_style_head.addWidget(lbl_ss)
        scene_style_head.addStretch()
        scene_style_head.addWidget(self.btn_reset_style)
        lay.addLayout(scene_style_head)

        self.txt_scene_style = QTextEdit()
        self.txt_scene_style.setFixedHeight(72)
        # Điền sẵn default — user paste style của kênh mình vào đây để override
        self.txt_scene_style.setPlainText(DEFAULT_SCENE_STYLE)
        self.txt_scene_style.setStyleSheet(
            "background: #0F0F18; border: 1px solid #252535; border-radius: 6px; "
            "color: #3AD68A; font-size: 11px; padding: 8px; font-family: 'Space Mono', monospace;")
        lay.addWidget(self.txt_scene_style)

        # ── SPLITTER: KỊCH BẢN & PREVIEW ────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(12)

        left_panel = QFrame()
        left_panel.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        l_lay = QVBoxLayout(left_panel); l_lay.setContentsMargins(0,0,0,0); l_lay.setSpacing(0)
        l_head = QFrame()
        l_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        l_head_lay = QHBoxLayout(l_head); l_head_lay.setContentsMargins(16,12,16,12)
        lbl_kb = QLabel("🔴 KỊCH BẢN")
        lbl_kb.setStyleSheet("font-size: 12px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        self.lbl_char_count = QLabel("0 ký tự"); self.lbl_char_count.setObjectName("muted")
        self.btn_load_script = QPushButton("📂 Load từ Profile")
        self.btn_load_script.setStyleSheet("background: #252535; color: #E8E8F0; border-radius: 4px; padding: 4px 10px; font-size: 11px;")
        self.btn_load_script.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_load_script.clicked.connect(self._load_script_from_profile)
        l_head_lay.addWidget(lbl_kb); l_head_lay.addStretch()
        l_head_lay.addWidget(self.btn_load_script); l_head_lay.addWidget(self.lbl_char_count)
        l_lay.addWidget(l_head)
        self.txt_script = QTextEdit()
        self.txt_script.setPlaceholderText("Paste kịch bản vào đây...")
        self.txt_script.setStyleSheet("border: none; background: transparent; padding: 16px; font-size: 14px; color: #E8E8F0;")
        self.txt_script.textChanged.connect(self._update_char_count)
        l_lay.addWidget(self.txt_script)
        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        r_lay = QVBoxLayout(right_panel); r_lay.setContentsMargins(0,0,0,0); r_lay.setSpacing(0)
        r_head = QFrame()
        r_head.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        r_head_lay = QHBoxLayout(r_head); r_head_lay.setContentsMargins(16,12,16,12)
        lbl_prev = QLabel("🔵 PREVIEW SCENES")
        lbl_prev.setStyleSheet("font-size: 12px; color: #606075; font-weight: bold; letter-spacing: 1px;")
        self.lbl_scene_count = QLabel("0 scenes"); self.lbl_scene_count.setObjectName("muted")
        r_head_lay.addWidget(lbl_prev); r_head_lay.addStretch(); r_head_lay.addWidget(self.lbl_scene_count)
        r_lay.addWidget(r_head)
        self.txt_preview = QTextEdit()
        self.txt_preview.setPlaceholderText("Scenes sẽ hiện ở đây sau khi split...")
        self.txt_preview.setStyleSheet("border: none; background: transparent; padding: 16px; font-family: 'Space Mono', monospace; font-size: 13px; color: #606075;")
        r_lay.addWidget(self.txt_preview)
        splitter.addWidget(right_panel)
        splitter.setMinimumHeight(240)
        lay.addWidget(splitter)

        # ── ACTION BUTTONS ───────────────────────────────────────────
        act_lay = QHBoxLayout(); act_lay.setSpacing(10)
        self.btn_loc    = QPushButton("🧹 Lọc Script")
        self.btn_split  = QPushButton("✂ Split Scenes")
        self.btn_scan   = QPushButton("🔍 Pre-scan")
        self.btn_assign = QPushButton("⚡ Assign Assets")
        self.btn_dedup  = QPushButton("📑 Deduplicate")
        self.btn_run    = QPushButton("🚀 Run Pipeline")

        self.btn_loc.setStyleSheet("background: rgba(90,155,255,0.1); color: #5A9BFF; border: 1px solid rgba(90,155,255,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_split.setObjectName("btn_primary")
        self.btn_scan.setStyleSheet("background: rgba(155,127,255,0.1); color: #9B7FFF; border: 1px solid rgba(155,127,255,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_assign.setObjectName("btn_sec")
        self.btn_dedup.setStyleSheet("background: rgba(232,116,42,0.1); color: #E8742A; border: 1px solid rgba(232,116,42,0.25); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")
        self.btn_run.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(155,127,255,0.25),stop:1 rgba(90,155,255,0.25)); color: #D0D0E0; border: 1px solid rgba(155,127,255,0.4); border-radius: 6px; padding: 10px 16px; font-weight: bold; font-size: 13px;")

        self.btn_loc.clicked.connect(self._clean_script)
        self.btn_split.clicked.connect(self._split_scenes)
        self.btn_scan.clicked.connect(self._pre_scan)
        self.btn_assign.clicked.connect(self._assign_assets)
        self.btn_dedup.clicked.connect(self._deduplicate)
        self.btn_run.clicked.connect(self._run_pipeline)

        for btn in [self.btn_loc, self.btn_split, self.btn_scan,
                    self.btn_assign, self.btn_dedup, self.btn_run]:
            act_lay.addWidget(btn)
        act_lay.addStretch()

        lbl_batch = QLabel("Batch:"); lbl_batch.setObjectName("muted")
        self.txt_batch = QLineEdit("12"); self.txt_batch.setFixedWidth(50)
        lbl_cast = QLabel("Cast:"); lbl_cast.setObjectName("muted")
        self.cmb_cast = QComboBox(); self.cmb_cast.addItems(["Auto (AI quyết)", "Manual"])
        act_lay.addWidget(lbl_batch); act_lay.addWidget(self.txt_batch)
        act_lay.addSpacing(10)
        act_lay.addWidget(lbl_cast); act_lay.addWidget(self.cmb_cast)
        lay.addLayout(act_lay)

        # ── PRE-SCAN PANEL ───────────────────────────────────────────
        self.prescan_panel = QFrame()
        self.prescan_panel.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        self.prescan_panel.hide()
        ps_lay = QVBoxLayout(self.prescan_panel)
        ps_lay.setContentsMargins(16,12,16,12); ps_lay.setSpacing(10)
        lbl_ps = QLabel("PRE-SCAN: DUYỆT DANH SÁCH TRƯỚC KHI ASSIGN")
        lbl_ps.setStyleSheet("color: #9B7FFF; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        ps_lay.addWidget(lbl_ps)
        ps_grid = QHBoxLayout(); ps_grid.setSpacing(20)
        ps_char_lay = QVBoxLayout(); ps_char_lay.setSpacing(4)
        lbl_pc = QLabel("NHÂN VẬT (mỗi dòng 1 tên, kebab-case)")
        lbl_pc.setStyleSheet("color: #3AD68A; font-weight: bold; font-size: 11px;")
        self.txt_prescan_chars = QTextEdit()
        self.txt_prescan_chars.setStyleSheet("background: transparent; border: none; color: #5A9BFF; font-family: monospace; font-size: 13px;")
        self.txt_prescan_chars.setFixedHeight(120)
        ps_char_lay.addWidget(lbl_pc); ps_char_lay.addWidget(self.txt_prescan_chars)
        ps_bg_lay = QVBoxLayout(); ps_bg_lay.setSpacing(4)
        lbl_pb = QLabel("BỐI CẢNH (mỗi dòng 1 tên, kebab-case)")
        lbl_pb.setStyleSheet("color: #5A9BFF; font-weight: bold; font-size: 11px;")
        self.txt_prescan_bgs = QTextEdit()
        self.txt_prescan_bgs.setStyleSheet("background: transparent; border: none; color: #5A9BFF; font-family: monospace; font-size: 13px;")
        self.txt_prescan_bgs.setFixedHeight(120)
        ps_bg_lay.addWidget(lbl_pb); ps_bg_lay.addWidget(self.txt_prescan_bgs)
        ps_grid.addLayout(ps_char_lay); ps_grid.addLayout(ps_bg_lay)
        ps_lay.addLayout(ps_grid)
        lay.addWidget(self.prescan_panel)

        # ── STATS DASHBOARD ──────────────────────────────────────────
        lay.addSpacing(10)
        stats_lay = QHBoxLayout(); stats_lay.setSpacing(12)
        self.card_scenes   = self._create_stat_card("SCENES",      "0",      "#E8742A")
        self.card_assigned = self._create_stat_card("ASSIGNED",    "0",      "#606075")
        self.card_chars    = self._create_stat_card("CHARACTERS",  "-",      "#606075")
        self.card_bgs      = self._create_stat_card("BACKGROUNDS", "-",      "#606075")
        self.card_duration = self._create_stat_card("DURATION",    "00m00s", "#3AD68A")
        for c in [self.card_scenes, self.card_assigned, self.card_chars,
                  self.card_bgs, self.card_duration]:
            stats_lay.addWidget(c)
        lay.addLayout(stats_lay)

        # ── TAB BAR + STACKED WIDGET ─────────────────────────────────
        self.tabs_bar = QTabBar()
        TAB_NAMES = ["SCENE LIST", "G-LABS IMAGE PROMPTS",
                     "VEO3 VIDEO PROMPTS", "ASSETS", "CAMERA GUIDE", "PRODUCTION NOTES"]
        for name in TAB_NAMES:
            self.tabs_bar.addTab(name)
        self.tabs_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tabs_bar.setStyleSheet("""
            QTabBar::tab { background: #0F0F18; color: #606075; font-weight: bold; font-size: 11px;
                           letter-spacing: 0.5px; padding: 10px 18px; border: 1px solid #252535;
                           border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 4px; }
            QTabBar::tab:selected { background: #171724; color: #E8742A; border-top: 2px solid #E8742A; }
            QTabBar::tab:hover:!selected { color: #E8E8F0; background: #161622; }
        """)
        self.tabs_bar.currentChanged.connect(self._on_tab_changed)
        lay.addWidget(self.tabs_bar)

        # Stacked widget chứa nội dung từng tab
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QStackedWidget { background: transparent; }")

        # Tab 0: Scene List (bảng cũ)
        scene_list_widget = QWidget()
        sl_lay = QVBoxLayout(scene_list_widget)
        sl_lay.setContentsMargins(0,0,0,0)

        self.table_scenes = QTableWidget()
        self.table_scenes.setColumnCount(8)
        self.table_scenes.setHorizontalHeaderLabels(["STT","LEVEL","VO","CHARACTER","BACKGROUND","CAMERA","DUR","ACTIONS"])
        self.table_scenes.setMinimumHeight(300)
        self.table_scenes.setStyleSheet("""
            QTableWidget { background-color: #0F0F18; border: 1px solid #252535; border-radius: 6px; gridline-color: #1F1F2E; color: #E8E8F0; font-size: 13px; }
            QHeaderView::section { background-color: #171724; color: #606075; font-weight: bold; font-size: 11px; padding: 8px; border: none; border-bottom: 1px solid #252535; }
            QTableWidget::item { padding: 10px; }""")
        hdr = self.table_scenes.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for col in [3,4,5,6,7]:
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        self.table_scenes.setColumnWidth(0,50); self.table_scenes.setColumnWidth(1,65)
        self.table_scenes.setColumnWidth(3,180); self.table_scenes.setColumnWidth(4,180)
        self.table_scenes.setColumnWidth(5,120); self.table_scenes.setColumnWidth(6,55)
        self.table_scenes.setColumnWidth(7,85)
        self._populate_table([])
        sl_lay.addWidget(self.table_scenes)

        tbl_act = QHBoxLayout()
        for lbl, style in [("⬇ XLSX","background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px;"),
                           ("⬇ G-Labs TXT","background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px;"),
                           ("⬇ VO Only","background: rgba(90,155,255,0.1); color: #5A9BFF; border: 1px solid rgba(90,155,255,0.2); border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px;")]:
            b = QPushButton(lbl); b.setStyleSheet(style)
            b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); tbl_act.addWidget(b)
        self.btn_to_tool3 = QPushButton("→ Assets sang Tool 3")
        self.btn_to_tool3.setStyleSheet("background: rgba(58,214,138,0.1); color: #3AD68A; border: 1px solid rgba(58,214,138,0.2); border-radius: 4px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        self.btn_to_tool3.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_to_tool3.clicked.connect(self._transfer_to_tool3)
        tbl_act.addWidget(self.btn_to_tool3); tbl_act.addStretch()
        sl_lay.addLayout(tbl_act)
        self.stack.addWidget(scene_list_widget)     # index 0

        # Tab 1–5: các widget mới
        self.tab_glabs    = GLabsPromptsWidget();    self.stack.addWidget(self.tab_glabs)     # 1
        self.tab_veo3     = Veo3PromptsWidget();     self.stack.addWidget(self.tab_veo3)      # 2
        self.tab_assets   = AssetsWidget();          self.stack.addWidget(self.tab_assets)    # 3
        self.tab_camera   = CameraGuideWidget();     self.stack.addWidget(self.tab_camera)    # 4
        self.tab_notes    = ProductionNotesWidget(); self.stack.addWidget(self.tab_notes)     # 5

        self.stack.setMinimumHeight(360)
        lay.addWidget(self.stack)

        # ── SCENE RENAMER (giữ nguyên) ───────────────────────────────
        lay.addSpacing(5)
        rh = QHBoxLayout(); rh.setSpacing(6)
        rh.addWidget(QLabel("▶ 📁 Scene Renamer", styleSheet="font-size: 14px; font-weight: bold; color: #E8E8F0;"))
        rh.addWidget(QLabel("— Đổi tên ảnh thành 001, 002...", styleSheet="color: #606075; font-size: 13px;"))
        rh.addStretch(); lay.addLayout(rh)
        ren_hint = QLabel("Flow: Download ảnh từ G-Labs → Kéo vào đây → Tự đổi tên → Download ZIP")
        ren_hint.setStyleSheet("background: rgba(232,116,42,0.04); color: #E8742A; border: 1px solid rgba(232,116,42,0.12); border-radius: 6px; padding: 6px 10px; font-size: 11px;")
        ren_hint.setWordWrap(True); lay.addWidget(ren_hint)

        ren_grid = QGridLayout(); ren_grid.setSpacing(14)
        box_left = QFrame(); box_left.setFixedHeight(180)
        box_left.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        bl = QVBoxLayout(box_left); bl.setContentsMargins(0,0,0,0)
        blh = QFrame(); blh.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        blhl = QVBoxLayout(blh); blhl.setContentsMargins(16,10,16,10)
        blhl.addWidget(QLabel("ẢNH SCENES TỪ G-LABS", styleSheet="font-size: 11px; color: #606075; font-weight: bold; letter-spacing: 1px;"))
        bl.addWidget(blh)
        dz_w = QWidget(); dz_l = QVBoxLayout(dz_w); dz_l.setContentsMargins(12,12,12,12)
        dz_l.addWidget(DropZoneWidget("📂","Kéo thả ảnh vào đây hoặc click để chọn","Tự sort theo tên file"))
        bl.addWidget(dz_w); ren_grid.addWidget(box_left, 0, 0)

        box_right = QFrame(); box_right.setFixedHeight(180)
        box_right.setStyleSheet("QFrame { background: #0F0F18; border: 1px solid #252535; border-radius: 8px; }")
        br = QVBoxLayout(box_right); br.setContentsMargins(0,0,0,0)
        brh = QFrame(); brh.setStyleSheet("background: #171724; border: none; border-bottom: 1px solid #252535; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        brhl = QVBoxLayout(brh); brhl.setContentsMargins(16,10,16,10)
        brhl.addWidget(QLabel("TUỲ CHỌN", styleSheet="font-size: 11px; color: #606075; font-weight: bold;"))
        br.addWidget(brh)
        opt_w = QWidget(); opt_l = QVBoxLayout(opt_w); opt_l.setContentsMargins(16,12,16,12); opt_l.setSpacing(4)
        opt_l.addWidget(QLabel("BẮT ĐẦU TỪ SỐ", objectName="muted"))
        self.txt_ren_start = QLineEdit("1"); self.txt_ren_start.setFixedHeight(28); opt_l.addWidget(self.txt_ren_start)
        opt_l.addWidget(QLabel("SỐ CHỮ SỐ (PADDING)", objectName="muted"))
        self.cmb_ren_pad = QComboBox(); self.cmb_ren_pad.addItems(["001","01","0001"]); self.cmb_ren_pad.setFixedHeight(28); opt_l.addWidget(self.cmb_ren_pad)
        opt_l.addWidget(QLabel("GIỮ EXTENSION GỐC", objectName="muted"))
        self.cmb_ren_ext = QComboBox(); self.cmb_ren_ext.addItems(["Giữ nguyên","Ép sang .jpg","Ép sang .png"]); self.cmb_ren_ext.setFixedHeight(28); opt_l.addWidget(self.cmb_ren_ext)
        br.addWidget(opt_w); ren_grid.addWidget(box_right, 0, 1)
        ren_grid.setColumnStretch(0, 2); ren_grid.setColumnStretch(1, 1)
        lay.addLayout(ren_grid)

        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        # ── STATE ────────────────────────────────────────────────────
        self._assigned_data: list[dict] = []   # cache dữ liệu assign mới nhất
        self._prescan_data:  dict       = {}   # cache prescan enriched

    # ──────────────────────────────────────────────────────────────────
    # TAB SWITCHING
    # ──────────────────────────────────────────────────────────────────
    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

    # ──────────────────────────────────────────────────────────────────
    # STAT CARD HELPER
    # ──────────────────────────────────────────────────────────────────
    def _create_stat_card(self, title, val, val_color):
        card = QFrame()
        card.setStyleSheet("QFrame { background: #171724; border: 1px solid #252535; border-radius: 6px; }")
        lay = QVBoxLayout(card); lay.setContentsMargins(14,10,14,10); lay.setSpacing(4)
        lbl_t = QLabel(title); lbl_t.setStyleSheet("font-size: 10px; font-weight: bold; color: #606075; letter-spacing: 0.5px;")
        lbl_v = QLabel(val);   lbl_v.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {val_color}; font-family: monospace;")
        lay.addWidget(lbl_t); lay.addWidget(lbl_v)
        card.lbl_val = lbl_v
        return card

    # ──────────────────────────────────────────────────────────────────
    # POPULATE TABLE (scene list)
    # ──────────────────────────────────────────────────────────────────
    def _populate_table(self, scenes):
        self.table_scenes.setRowCount(len(scenes))
        total_seconds = 0
        for i, vo_text in enumerate(scenes):
            dur_num = max(3, min(7, len(vo_text) // 16))
            total_seconds += dur_num
            items = [
                (f"{i+1:03d}", "#E8742A", True,  False),
                ("Main",       "#606075", False, False),
                (vo_text,      "#E8E8F0", False, False),
                ("pending...", "#606075", False, True),
                ("pending...", "#606075", False, True),
                ("—",          "#606075", False, False),
                (f"{dur_num}s","#3AD68A", True,  False),
            ]
            for col, (txt, color, bold, italic) in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setForeground(QBrush(QColor(color)))
                if col in [0,1,3,4,5,6]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bold:
                    f = item.font(); f.setBold(True); item.setFont(f)
                if italic:
                    f = item.font(); f.setItalic(True); item.setFont(f)
                self.table_scenes.setItem(i, col, item)

            btn_c = QWidget(); btn_l = QHBoxLayout(btn_c)
            btn_l.setContentsMargins(4,2,4,2); btn_l.setSpacing(6)
            for emoji, tip in [("✂","Cắt/gộp"), ("⟳","Regen prompt")]:
                b = QPushButton(emoji); b.setToolTip(tip)
                b.setStyleSheet("QPushButton { background: #171724; color: #A1A1AA; border: 1px solid #252535; border-radius: 4px; font-size: 11px; max-width: 26px; max-height: 22px; }")
                b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)); btn_l.addWidget(b)
            self.table_scenes.setCellWidget(i, 7, btn_c)

        self.card_scenes.lbl_val.setText(str(len(scenes)))
        mins, secs = divmod(total_seconds, 60)
        self.card_duration.lbl_val.setText(f"{mins:02d}m{secs:02d}s")

    # ──────────────────────────────────────────────────────────────────
    # LOGIC HANDLERS (giữ nguyên các method cũ + bổ sung _refresh_tabs)
    # ──────────────────────────────────────────────────────────────────
    def _update_char_count(self):
        self.lbl_char_count.setText(f"{len(self.txt_script.toPlainText())} ký tự")

    def _load_script_from_profile(self):
        ACTIVE_PROFILE_FILE = "active_profile.json"
        if not os.path.exists(ACTIVE_PROFILE_FILE):
            QMessageBox.warning(self, "Chưa có Profile", "Vui lòng chọn Profile trước."); return
        try:
            with open(ACTIVE_PROFILE_FILE, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
        except Exception:
            QMessageBox.critical(self, "Lỗi", "Không đọc được active_profile.json"); return
        topics = [(t.get("title",""), t["script"]["content"])
                  for t in profile_data.get("topics", [])
                  if isinstance(t.get("script"), dict) and t["script"].get("content")]
        if not topics:
            QMessageBox.information(self, "Trống", "Chưa có kịch bản trong Profile."); return
        title, ok = QInputDialog.getItem(self, "Chọn kịch bản", "Chọn:", [t[0] for t in topics], 0, False)
        if ok:
            for t, c in topics:
                if t == title:
                    self.txt_script.setPlainText(c); break

    def _clean_script(self):
        text = self.txt_script.toPlainText()
        if not text:
            QMessageBox.warning(self, "Trống", "Paste kịch bản trước."); return
        cleaned = []
        in_meta = False
        for line in text.split('\n'):
            s = line.strip()
            if not s: continue
            if s.startswith('=== METADATA') or s.startswith('=== VIDEO TITLE'): in_meta = True; continue
            if in_meta and s.startswith('---'): in_meta = False; continue
            if in_meta: continue
            if (s.startswith('===') and s.endswith('===')) or (s.startswith('---') and s.endswith('---')): continue
            if s.startswith('>>>') or s.startswith('[Estimated'): continue
            s = re.sub(r'\[TEXT OVERLAY:\s*"?([^\]]*?)"?\]', r'\1', s, flags=re.IGNORECASE)
            s = re.sub(r'\[.*?\]', '', s).strip().replace('*', '')
            if s: cleaned.append(s)
        self.txt_script.setPlainText('\n\n'.join(cleaned))
        QMessageBox.information(self, "OK", "Đã lọc script!")

    def _split_scenes(self):
        text = self.txt_script.toPlainText().strip()
        if not text: QMessageBox.warning(self, "Lỗi", "Không có kịch bản."); return
        try:
            min_c, max_c = int(self.txt_min.text()), int(self.txt_max.text())
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Min/Max phải là số."); return
        raw = re.split(r'(?<=[.?!])\s+|\n+', text)
        scenes, cur = [], ""
        for sent in raw:
            sent = sent.strip()
            if not sent: continue
            if not cur: cur = sent
            elif len(cur)+1+len(sent) <= max_c: cur += " "+sent
            else:
                if len(cur) >= min_c: scenes.append(cur); cur = sent
                else: cur += " "+sent
        if cur: scenes.append(cur)
        out = "\n\n".join(f"[Scene {i:03d}]\n{s}" for i, s in enumerate(scenes, 1))
        self.txt_preview.setPlainText(out)
        self.lbl_scene_count.setText(f"{len(scenes)} scenes")
        self._populate_table(scenes)
        QMessageBox.information(self, "OK", f"Đã chia thành {len(scenes)} scenes!")

    def _get_current_scenes_from_table(self):
        return [self.table_scenes.item(r, 2).text()
                for r in range(self.table_scenes.rowCount())
                if self.table_scenes.item(r, 2)]

    def _pre_scan(self):
        scenes = self._get_current_scenes_from_table()
        if not scenes: QMessageBox.warning(self, "Trống", "Split Scenes trước!"); return
        self.btn_scan.setEnabled(False); self.btn_scan.setText("⏳ Đang quét...")
        self.worker = SceneWorker("prescan", {"scenes": scenes})
        self.worker.result_signal.connect(self._handle_worker_result)
        self.worker.error_signal.connect(lambda e: QMessageBox.critical(self, "Lỗi AI", e))
        self.worker.finished_signal.connect(lambda: [self.btn_scan.setEnabled(True), self.btn_scan.setText("🔍 Pre-scan")])
        self.worker.start()

    def _assign_assets(self):
        scenes = self._get_current_scenes_from_table()
        if not scenes: QMessageBox.warning(self, "Trống", "Split Scenes trước!"); return
        chars = self.txt_prescan_chars.toPlainText().strip()
        bgs   = self.txt_prescan_bgs.toPlainText().strip()
        if not chars or not bgs:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chạy Pre-scan trước!"); return
        self.btn_assign.setEnabled(False); self.btn_assign.setText("⏳ Đang Assign...")
        self.worker = SceneWorker("assign", {"scenes": scenes, "characters": chars, "backgrounds": bgs})
        self.worker.result_signal.connect(self._handle_worker_result)
        self.worker.error_signal.connect(lambda e: QMessageBox.critical(self, "Lỗi AI", e))
        self.worker.finished_signal.connect(lambda: [self.btn_assign.setEnabled(True), self.btn_assign.setText("⚡ Assign Assets")])
        self.worker.start()

    # ──────────────────────────────────────────────────────────────────
    # HANDLE WORKER RESULT — điểm trung tâm cập nhật TẤT CẢ tabs
    # ──────────────────────────────────────────────────────────────────
    def _handle_worker_result(self, task_type: str, json_str: str):
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Lỗi JSON", json_str[:300]); return

        if task_type == "prescan":
            self._prescan_data = data

            # Schema mới (enriched) có "characters" dict; schema cũ có "characters_list"
            if "characters" in data and isinstance(data["characters"], dict):
                chars_list = list(data["characters"].keys())
                bgs_list   = list(data["backgrounds"].keys())
            else:
                def to_kebab(t):
                    for a,b in [('à','a'),('á','a'),('ạ','a'),('ả','a'),('ã','a'),('â','a'),('ầ','a'),('ấ','a'),('ậ','a'),('ẩ','a'),('ẫ','a'),('ă','a'),('ằ','a'),('ắ','a'),('ặ','a'),('ẳ','a'),('ẵ','a'),('è','e'),('é','e'),('ẹ','e'),('ẻ','e'),('ẽ','e'),('ê','e'),('ề','e'),('ế','e'),('ệ','e'),('ể','e'),('ễ','e'),('ì','i'),('í','i'),('ị','i'),('ỉ','i'),('ĩ','i'),('ò','o'),('ó','o'),('ọ','o'),('ỏ','o'),('õ','o'),('ô','o'),('ồ','o'),('ố','o'),('ộ','o'),('ổ','o'),('ỗ','o'),('ơ','o'),('ờ','o'),('ớ','o'),('ợ','o'),('ở','o'),('ỡ','o'),('ù','u'),('ú','u'),('ụ','u'),('ủ','u'),('ũ','u'),('ư','u'),('ừ','u'),('ứ','u'),('ự','u'),('ử','u'),('ữ','u'),('ỳ','y'),('ý','y'),('ỵ','y'),('ỷ','y'),('ỹ','y'),('đ','d')]:
                        t = t.lower().replace(a, b)
                    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')
                chars_list = [to_kebab(c) for c in data.get("characters_list", [])]
                bgs_list   = [to_kebab(b) for b in data.get("backgrounds_list", [])]

            self.txt_prescan_chars.setPlainText("\n".join(chars_list))
            self.txt_prescan_bgs.setPlainText("\n".join(bgs_list))
            self.prescan_panel.show()
            self.card_chars.lbl_val.setText(str(len(chars_list)))
            self.card_chars.lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #5A9BFF; font-family: monospace;")
            self.card_bgs.lbl_val.setText(str(len(bgs_list)))
            self.card_bgs.lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #9B7FFF; font-family: monospace;")

        elif task_type == "assign":
            scenes_data = data.get("scenes", [])
            scene_style = self.txt_scene_style.toPlainText().strip()

            # ── 1. Cập nhật bảng Scene List ──
            assigned_count = 0
            bg_location_index: dict[str, int] = {}  # map bg → location index (cho brand names)
            loc_counter = 1

            for item in scenes_data:
                row = item.get("id", 1) - 1
                if not (0 <= row < self.table_scenes.rowCount()):
                    continue
                char = item.get("character", "")
                bg   = item.get("background", "")
                cam  = item.get("camera", "")

                for col, val, color in [(3,char,"#E8E8F0"), (4,bg,"#E8E8F0"), (5,cam,"#C8C8D8")]:
                    cell = self.table_scenes.item(row, col)
                    if cell:
                        cell.setText(val)
                        cell.setForeground(QBrush(QColor(color)))
                        cell.setFont(QFont())

                # Build safe names cho G-Labs
                if bg not in bg_location_index:
                    bg_location_index[bg] = loc_counter
                    loc_counter += 1

                assigned_count += 1

            # ── 2. Build G-Labs prompts ──
            rename_map: dict[str, str] = {}
            glabs_prompts: list[str]   = []
            enriched_scene_data: list[dict] = []

            for item in scenes_data:
                row    = item.get("id", 1) - 1
                char   = item.get("character", "none")
                bg     = item.get("background", "")
                cam    = item.get("camera", "Medium shot")
                vo_txt = self.table_scenes.item(row, 2).text() if 0 <= row < self.table_scenes.rowCount() and self.table_scenes.item(row, 2) else ""

                # Safe names
                char_safe = make_glabs_safe_name(char, 0) if char and char != "none" else "Protagonist"
                bg_safe   = make_glabs_safe_name(bg, bg_location_index.get(bg, 1))

                rename_map[char] = char_safe
                rename_map[bg]   = bg_safe

                # Action description = VO rút gọn xuống ≤ 15 words
                words = vo_txt.split()
                action = " ".join(words[:15]) + ("..." if len(words) > 15 else "")
                action = action.lower().rstrip(".")

                dur_item = self.table_scenes.item(row, 6)
                dur = dur_item.text() if dur_item else "5s"

                prompt = build_glabs_prompt(scene_style, cam, char_safe, bg_safe, action)
                glabs_prompts.append(prompt)

                enriched_scene_data.append({
                    "id": item.get("id", row+1),
                    "character": char, "background": bg, "camera": cam,
                    "char_safe": char_safe, "bg_safe": bg_safe,
                    "action_desc": action, "dur": dur,
                })

            self._assigned_data = enriched_scene_data

            # ── 3. Load tất cả các tab ──
            self.tab_glabs.load_prompts(glabs_prompts, rename_map)
            self.tab_veo3.load_prompts(enriched_scene_data, scene_style)
            self.tab_assets.load_assets(enriched_scene_data)
            self.tab_camera.load_data(enriched_scene_data)

            chars_unique = list({s["character"] for s in enriched_scene_data if s["character"] != "none"})
            bgs_unique   = list({s["background"] for s in enriched_scene_data})
            self.tab_notes.load_checklist(chars_unique, bgs_unique)

            # ── 4. Dashboard ──
            self.card_assigned.lbl_val.setText(str(assigned_count))
            self.card_assigned.lbl_val.setStyleSheet("font-size: 20px; font-weight: bold; color: #E8E8F0; font-family: monospace;")

            QMessageBox.information(self, "✅ Assign hoàn tất",
                f"Đã assign {assigned_count} scenes.\n"
                f"G-Labs prompts: {len(glabs_prompts)} prompts đã sẵn sàng ở tab G-LABS IMAGE PROMPTS.")

            # Auto-switch sang tab G-Labs
            self.tabs_bar.setCurrentIndex(1)

    def _deduplicate(self):
        QMessageBox.information(self, "Deduplicate", "Đang phát triển.")

    def _run_pipeline(self):
        QMessageBox.information(self, "Run Pipeline", "Đang phát triển.")

    def _transfer_to_tool3(self):
        chars = self.txt_prescan_chars.toPlainText().strip()
        bgs   = self.txt_prescan_bgs.toPlainText().strip()
        if not chars and not bgs:
            QMessageBox.warning(self, "Trống", "Chạy Pre-scan trước!"); return
        self.transfer_to_tool3.emit(chars, bgs)
