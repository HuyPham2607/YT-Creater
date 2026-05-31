"""
glabs_ui.py — G-Labs Auto Generator UI v2
Giao diện PyQt6 tích hợp glabs_engine.py v2
"""

import sys, os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGridLayout, QComboBox, QScrollArea,
    QFileDialog, QFrame, QSizePolicy, QCheckBox, QLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint, QSize, QTimer
from PyQt6.QtGui import QPixmap, QColor, QPalette

try:
    from .glabs_engine import run_auto
    ENGINE_OK = True
except ImportError:
    ENGINE_OK = False


# ──────────────────────────────────────────────────────
# WORKER THREAD
# ──────────────────────────────────────────────────────
class AutoWorker(QThread):
    log_signal   = pyqtSignal(str)
    image_signal = pyqtSignal(str)
    gen_start_signal = pyqtSignal(str)
    gen_progress_signal = pyqtSignal(int)
    done_signal  = pyqtSignal(int)

    def __init__(self, prompts, save_dir, tool, new_project, expected_images=2, aspect_ratio="16:9", model="Nano Banana 2", output_type="Hình ảnh"):
        super().__init__()
        self.prompts     = prompts
        self.save_dir    = save_dir
        self.tool        = tool
        self.new_project = new_project
        self.expected_images = expected_images
        self.aspect_ratio = aspect_ratio
        self.model = model
        self.output_type = output_type
        self._stop       = False

    def run(self):
        if not ENGINE_OK:
            self.log_signal.emit("❌ Không tìm thấy glabs_engine.py!")
            self.done_signal.emit(0)
            return
        paths = run_auto(
            prompts              = self.prompts,
            save_dir             = self.save_dir,
            tool                 = self.tool,
            log_fn               = self.log_signal.emit,
            stop_fn              = lambda: self._stop,
            on_image_saved       = self.image_signal.emit,
            on_gen_start         = self.gen_start_signal.emit,
            on_gen_progress      = self.gen_progress_signal.emit,
            new_project_each_run = self.new_project,
            expected_images      = self.expected_images,
            aspect_ratio         = self.aspect_ratio,
            model                = self.model,
            output_type          = self.output_type,
        )
        self.done_signal.emit(len(paths))

    def stop(self):
        self._stop = True


# ──────────────────────────────────────────────────────
# PROGRESS CARD (Khung ảnh chờ)
# ──────────────────────────────────────────────────────
class ProgressCard(QFrame):
    def __init__(self, prompt: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(156, 156)
        self.setStyleSheet("""
            QFrame { border: 1px dashed #5A4FCC; border-radius: 10px; background: #0C0C18; }
        """)
        lay = QVBoxLayout(self)
        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setStyleSheet("font-size: 20px; font-weight: bold; color: #5A4FCC;")
        self.lbl_pct.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_msg = QLabel("Đang tạo...")
        self.lbl_msg.setStyleSheet("font-size: 10px; color: #484870;")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lay.addStretch()
        lay.addWidget(self.lbl_pct)
        lay.addWidget(self.lbl_msg)
        lay.addStretch()

    def set_progress(self, val):
        self.lbl_pct.setText(f"{val}%")
        if val >= 100:
            self.lbl_msg.setText("Đang hoàn thiện...")


# ──────────────────────────────────────────────────────
# THUMBNAIL
# ──────────────────────────────────────────────────────
class ThumbCard(QFrame):
    def __init__(self, img_path: str, parent=None):
        super().__init__(parent)
        self.img_path = img_path
        self.setFixedSize(156, 156)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(os.path.basename(img_path))
        self.setStyleSheet("""
            QFrame { border: 1px solid #1E1E2E; border-radius: 10px; background: #0C0C18; }
            QFrame:hover { border-color: #5A4FCC; }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lbl = QLabel()
        pix = QPixmap(img_path)
        if pix.isNull():
            pix = QPixmap(150, 150); pix.fill(QColor("#161628"))
        else:
            pix = pix.scaled(150, 150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
        lbl.setPixmap(pix)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

    def mouseDoubleClickEvent(self, _):
        import subprocess, platform
        if platform.system() == "Windows":   os.startfile(self.img_path)
        elif platform.system() == "Darwin":  subprocess.call(["open", self.img_path])
        else:                                subprocess.call(["xdg-open", self.img_path])


# ──────────────────────────────────────────────────────
# FLOW LAYOUT (wrap thumbnails)
# ──────────────────────────────────────────────────────
class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._spacing = spacing
        self._items   = []
        if parent:
            self.setContentsMargins(10, 10, 10, 10)

    def addItem(self, item):  self._items.append(item)
    def count(self):          return len(self._items)
    def itemAt(self, i):      return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i):      return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self):   return True
    def heightForWidth(self, w):   return self._layout(QRect(0,0,w,0), test=True)
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, test=False)
    def sizeHint(self):  return self.minimumSize()
    def minimumSize(self):
        s = QSize(0, 0)
        for item in self._items: s = s.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return QSize(s.width()+m.left()+m.right(), s.height()+m.top()+m.bottom())

    def _layout(self, rect, test):
        m  = self.contentsMargins()
        x  = rect.x() + m.left()
        y  = rect.y() + m.top()
        rh = 0
        R  = rect.right() - m.right()
        for item in self._items:
            w = item.sizeHint()
            if x + w.width() > R and x > rect.x() + m.left():
                x = rect.x() + m.left(); y += rh + self._spacing; rh = 0
            if not test:
                item.setGeometry(QRect(QPoint(x, y), w))
            x += w.width() + self._spacing
            rh = max(rh, w.height())
        return y + rh - rect.y() + m.bottom()


# ──────────────────────────────────────────────────────
# MAIN WINDOW
# ──────────────────────────────────────────────────────
class GLabsAutomationTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker     = None
        self.current_prog_card = None
        self.thumb_count = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(self._css())
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── HEADER ───────────────────────────────────────
        hdr = QWidget(); hdr.setObjectName("hdr")
        hl  = QHBoxLayout(hdr); hl.setContentsMargins(28, 16, 28, 16)
        col = QVBoxLayout(); col.setSpacing(2)
        col.addWidget(self._lbl("G-Labs Auto Generator", "htitle"))
        col.addWidget(self._lbl("Tự động tạo ảnh · Google Flow / ImageFX", "hsub"))
        hl.addLayout(col); hl.addStretch()
        dot = QLabel("⬤ Flow  ⬤ ImageFX"); dot.setObjectName("badge")
        hl.addWidget(dot)
        root.addWidget(hdr)

        # ── CONTENT ──────────────────────────────────────
        content = QHBoxLayout()
        content.setContentsMargins(24, 20, 24, 20)
        content.setSpacing(20)

        # ─── LEFT: Controls ──────────────────────────────
        left = QVBoxLayout(); left.setSpacing(14)

        # Tool
        left.addWidget(self._lbl("CÔNG CỤ", "sec"))
        self.cmb_tool = QComboBox(); self.cmb_tool.setObjectName("cmb")
        self.cmb_tool.addItems(["Flow (Ảnh + Video)", "ImageFX (Chỉ ảnh)"])
        left.addWidget(self.cmb_tool)

        # Thư mục
        left.addWidget(self._lbl("THƯ MỤC LƯU", "sec"))
        dr = QHBoxLayout(); dr.setSpacing(8)
        self.lbl_dir = QLabel(str(Path.home()/"Downloads"/"GLabs"))
        self.lbl_dir.setObjectName("dirlbl")
        self.lbl_dir.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_d = QPushButton("📂"); btn_d.setObjectName("btnico"); btn_d.setFixedWidth(38)
        btn_d.clicked.connect(self._pick_dir)
        dr.addWidget(self.lbl_dir); dr.addWidget(btn_d)
        left.addLayout(dr)

        # Option dự án
        left.addWidget(self._lbl("TÙY CHỌN DỰ ÁN & RENDER", "sec"))

        self.chk_new_proj = QCheckBox("Luôn tạo dự án mới khi bắt đầu")
        self.chk_new_proj.setObjectName("chk")
        self.chk_new_proj.setToolTip(
            "Bỏ chọn (mặc định): dùng lại dự án đang mở hoặc dự án đầu tiên\n"
            "Chọn: mỗi lần nhấn Start sẽ tạo 1 dự án mới hoàn toàn"
        )
        left.addWidget(self.chk_new_proj)

        opt_grid = QGridLayout()
        opt_grid.setSpacing(10)
        
        lbl_type = QLabel("LOẠI OUTPUT"); lbl_type.setStyleSheet("color: #7070A0; font-size: 10px; font-weight: bold;")
        self.cmb_type = QComboBox(); self.cmb_type.setObjectName("cmb")
        self.cmb_type.addItems(["Hình ảnh", "Video"]); self.cmb_type.setCurrentText("Hình ảnh")
        
        lbl_count = QLabel("SỐ ẢNH / LƯỢT"); lbl_count.setStyleSheet("color: #7070A0; font-size: 10px; font-weight: bold;")
        self.cmb_count = QComboBox(); self.cmb_count.setObjectName("cmb")
        self.cmb_count.addItems(["1", "2", "3", "4"]); self.cmb_count.setCurrentText("2")
        
        lbl_aspect = QLabel("TỶ LỆ ẢNH"); lbl_aspect.setStyleSheet("color: #7070A0; font-size: 10px; font-weight: bold;")
        self.cmb_aspect = QComboBox(); self.cmb_aspect.setObjectName("cmb")
        self.cmb_aspect.addItems(["16:9", "4:3", "1:1", "3:4", "9:16"])
        
        lbl_model = QLabel("MÔ HÌNH AI"); lbl_model.setStyleSheet("color: #7070A0; font-size: 10px; font-weight: bold;")
        self.cmb_model = QComboBox(); self.cmb_model.setObjectName("cmb")
        self.cmb_model.addItems(["Nano Banana 2", "Imagen 4", "Nano Banana Pro"])
        
        opt_grid.addWidget(lbl_type, 0, 0); opt_grid.addWidget(self.cmb_type, 1, 0)
        opt_grid.addWidget(lbl_count, 0, 1); opt_grid.addWidget(self.cmb_count, 1, 1)
        opt_grid.addWidget(lbl_aspect, 0, 2); opt_grid.addWidget(self.cmb_aspect, 1, 2)
        opt_grid.addWidget(lbl_model, 0, 3); opt_grid.addWidget(self.cmb_model, 1, 3)
        
        left.addLayout(opt_grid)

        info = QLabel(
            "ℹ  Mặc định: dùng lại dự án đã có.\n"
            "   Mỗi prompt là 1 lượt chat trong cùng dự án."
        )
        info.setObjectName("info")
        info.setWordWrap(True)
        left.addWidget(info)

        # Prompts
        left.addWidget(self._lbl("DANH SÁCH PROMPTS  (mỗi dòng = 1 ảnh)", "sec"))
        self.txt_p = QTextEdit(); self.txt_p.setObjectName("txtp")
        self.txt_p.setPlaceholderText(
            "Nhập prompts, mỗi dòng 1 cái:\n\n"
            "A cinematic lotus flower in rain, macro photography\n"
            "Futuristic HCMC skyline at night, neon lights, 8K\n"
            "Vietnamese rice field at golden hour, drone shot"
        )
        self.txt_p.setMinimumHeight(180)
        left.addWidget(self.txt_p)

        # Buttons
        br = QHBoxLayout(); br.setSpacing(10)
        self.btn_start = QPushButton("▶  Bắt đầu Generate"); self.btn_start.setObjectName("btnp")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop  = QPushButton("■  Dừng");             self.btn_stop.setObjectName("btns")
        self.btn_stop.clicked.connect(self._stop); self.btn_stop.setEnabled(False)
        br.addWidget(self.btn_start, 2); br.addWidget(self.btn_stop, 1)
        left.addLayout(br)

        # Log
        left.addWidget(self._lbl("NHẬT KÝ", "sec"))
        self.txt_log = QTextEdit(); self.txt_log.setObjectName("txtlog")
        self.txt_log.setReadOnly(True)
        self.txt_log.setMinimumHeight(160)
        self.txt_log.setText(
            "> Chờ lệnh...\n"
            "> Bước 1: Chạy launch_chrome.py và đăng nhập Google.\n"
            "> Bước 2: Nhập prompt → nhấn Bắt đầu."
        )
        left.addWidget(self.txt_log)
        left.addStretch()

        lw = QWidget(); lw.setLayout(left); lw.setFixedWidth(440)
        content.addWidget(lw)

        # ─── RIGHT: Gallery ───────────────────────────────
        right = QVBoxLayout(); right.setSpacing(10)

        tr = QHBoxLayout()
        tr.addWidget(self._lbl("ẢNH ĐÃ TẠO", "sec"))
        tr.addStretch()
        self.lbl_cnt = QLabel("0 ảnh"); self.lbl_cnt.setObjectName("cnt")
        tr.addWidget(self.lbl_cnt)
        bc = QPushButton("Xoá"); bc.setObjectName("btnlnk"); bc.clicked.connect(self._clear)
        tr.addWidget(bc)
        right.addLayout(tr)

        self.g_scroll = QScrollArea()
        self.g_scroll.setWidgetResizable(True); self.g_scroll.setObjectName("gscroll")
        self.g_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.g_widget = QWidget()
        self.g_layout = FlowLayout(self.g_widget, spacing=8)
        self.ph = QLabel("Ảnh sẽ xuất hiện ở đây\n(double-click để mở)")
        self.ph.setObjectName("ph"); self.ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.g_layout.addWidget(self.ph)
        self.g_scroll.setWidget(self.g_widget)
        right.addWidget(self.g_scroll)

        rw = QWidget(); rw.setLayout(right)
        content.addWidget(rw, 1)

        root.addLayout(content, 1)

    # ── SLOTS ─────────────────────────────────────────
    def _start(self):
        raw = self.txt_p.toPlainText().strip()
        if not raw:
            self._log("❌ Chưa nhập prompt!"); return

        prompts = [p for p in raw.split("\n") if p.strip()]
        save_dir    = self.lbl_dir.text()
        tool        = "flow" if "Flow" in self.cmb_tool.currentText() else "imagefx"
        new_project = self.chk_new_proj.isChecked()
        img_count   = int(self.cmb_count.currentText())
        aspect_ratio = self.cmb_aspect.currentText()
        model       = self.cmb_model.currentText()
        output_type = self.cmb_type.currentText()

        self._log(f"\n{'═'*44}")
        self._log(f"🎯 Công cụ : {self.cmb_tool.currentText()}")
        self._log(f"📁 Lưu vào: {save_dir}")
        self._log(f"📝 Prompts : {len(prompts)}")
        self._log(f"🗂  Dự án  : {'Tạo mới' if new_project else 'Dùng lại / tự động'}")
        self._log(f"🖼️  Cấu hình: {output_type} | {img_count} lượt | {aspect_ratio} | {model}")
        self._log(f"{'═'*44}")

        self.btn_start.setEnabled(False); self.btn_start.setText("⏳ Đang chạy...")
        self.btn_stop.setEnabled(True)

        self.worker = AutoWorker(prompts, save_dir, tool, new_project, img_count, aspect_ratio, model, output_type)
        self.worker.log_signal.connect(self._log)
        self.worker.gen_start_signal.connect(self._on_gen_start)
        self.worker.gen_progress_signal.connect(self._on_gen_progress)
        self.worker.image_signal.connect(self._add_thumb)
        self.worker.done_signal.connect(self._done)
        self.worker.start()

    def _on_gen_start(self, prompt):
        if self.ph.isVisible(): self.ph.hide()
        # Xoá card cũ nếu có
        if self.current_prog_card:
            self.current_prog_card.deleteLater()
        self.current_prog_card = ProgressCard(prompt)
        self.g_layout.addWidget(self.current_prog_card)
        self.g_scroll.verticalScrollBar().setValue(self.g_scroll.verticalScrollBar().maximum())

    def _on_gen_progress(self, val):
        if self.current_prog_card:
            self.current_prog_card.set_progress(val)

    def _stop(self):
        if self.worker:
            self.worker.stop()
            self._log("⏳ Đang dừng..."); self.btn_stop.setEnabled(False)

    def _done(self, n):
        if self.current_prog_card:
            self.current_prog_card.deleteLater()
            self.current_prog_card = None
        self.btn_start.setEnabled(True); self.btn_start.setText("▶  Bắt đầu Generate")
        self.btn_stop.setEnabled(False)
        self._log(f"\n✅ Xong! Tổng: {n} ảnh.")

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục", self.lbl_dir.text())
        if d: self.lbl_dir.setText(d)

    def _log(self, t):
        self.txt_log.append(t)
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    def _add_thumb(self, path):
        if self.ph.isVisible(): self.ph.hide()
        # Khi có ảnh thật về, card tiến độ sẽ tự bị đẩy đi hoặc ta có thể ẩn nó ở đây
        # Trong luồng này, ảnh sẽ xuất hiện ngay sau card tiến độ
        self.g_layout.addWidget(ThumbCard(path))
        self.thumb_count += 1
        self.lbl_cnt.setText(f"{self.thumb_count} ảnh")
        self.g_scroll.verticalScrollBar().setValue(
            self.g_scroll.verticalScrollBar().maximum())

    def _clear(self):
        for i in reversed(range(self.g_layout.count())):
            w = self.g_layout.itemAt(i).widget()
            if w and w is not self.ph: w.deleteLater()
        self.thumb_count = 0; self.lbl_cnt.setText("0 ảnh"); self.ph.show()

    def _lbl(self, t, obj=""):
        l = QLabel(t)
        if obj: l.setObjectName(obj)
        return l

    # ── CSS ────────────────────────────────────────────
    def _css(self):
        return """
        QWidget          { background:#09090F; color:#C4C4DC;
                           font-family:'Segoe UI','SF Pro Text',sans-serif; font-size:13px; }
        #hdr             { background:#0C0C18; border-bottom:1px solid #181828; }
        #htitle          { font-size:17px; font-weight:700; color:#E8E8FF; letter-spacing:.3px; }
        #hsub            { font-size:12px; color:#484870; }
        #badge           { font-size:11px; color:#383878; letter-spacing:1px;
                           padding:4px 10px; border:1px solid #1E1E38; border-radius:16px; }
        #sec             { font-size:10px; font-weight:700; color:#323258;
                           letter-spacing:1.4px; margin-top:6px; }
        #dirlbl          { background:#0D0D1C; border:1px solid #1C1C30; border-radius:7px;
                           padding:7px 10px; color:#6A6A90; font-size:12px; }
        #info            { background:#0C0C1A; border:1px solid #181828; border-radius:8px;
                           padding:8px 12px; color:#404068; font-size:12px; line-height:1.6; }
        QCheckBox#chk    { color:#7070A0; spacing:8px; }
        QCheckBox#chk::indicator { width:16px; height:16px; border:1px solid #2A2A48;
                                   border-radius:4px; background:#0D0D1C; }
        QCheckBox#chk::indicator:checked { background:#5A4FCC; border-color:#5A4FCC; }
        QComboBox#cmb    { background:#0D0D1C; border:1px solid #1C1C30; border-radius:7px;
                           padding:7px 12px; color:#B0B0D0; }
        QComboBox#cmb:hover { border-color:#383870; }
        QComboBox#cmb::drop-down { border:none; width:24px; }
        QComboBox QAbstractItemView { background:#12121E; border:1px solid #28283C;
                                       selection-background-color:#5A4FCC; color:#C0C0E0; }
        QTextEdit#txtp   { background:#0C0C1C; border:1px solid #1C1C30; border-radius:8px;
                           color:#D0D0F0; padding:10px; font-size:13px; }
        QTextEdit#txtp:focus { border-color:#5A4FCC; }
        QTextEdit#txtlog { background:#060610; border:1px solid #141420; border-radius:8px;
                           color:#38D086; padding:10px;
                           font-family:'Consolas','Courier New',monospace; font-size:12px; }
        QPushButton#btnp { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                             stop:0 #4E45C0,stop:1 #7232E0);
                           border:none; border-radius:8px; padding:11px 18px;
                           color:#FFF; font-weight:700; }
        QPushButton#btnp:hover    { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
                                      stop:0 #5F55D0,stop:1 #8342F0); }
        QPushButton#btnp:disabled { background:#1E1E30; color:#383850; }
        QPushButton#btns { background:transparent; border:1px solid #2E1414;
                           border-radius:8px; padding:11px 14px; color:#B03030; font-weight:600; }
        QPushButton#btns:hover    { background:#160A0A; border-color:#B03030; }
        QPushButton#btns:disabled { color:#2A1818; border-color:#1C1010; }
        QPushButton#btnico { background:#0D0D1C; border:1px solid #1C1C30;
                             border-radius:7px; color:#6868A0; font-size:15px; }
        QPushButton#btnico:hover { border-color:#48489A; color:#A0A0CC; }
        QPushButton#btnlnk { background:transparent; border:none;
                             color:#2C2C50; font-size:12px; padding:2px 6px; }
        QPushButton#btnlnk:hover { color:#5A4FCC; }
        #gscroll         { background:#07070E; border:none; border-left:1px solid #111120; }
        QScrollBar:vertical   { background:#09090F; width:5px; }
        QScrollBar::handle:vertical { background:#1C1C30; border-radius:3px; min-height:28px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        #ph  { color:#1C1C30; font-size:14px; line-height:2.2; }
        #cnt { font-size:12px; color:#383858; }
        """


# ──────────────────────────────────────────────────────
# ENTRY
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,     QColor("#09090F"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#C4C4DC"))
    pal.setColor(QPalette.ColorRole.Base,       QColor("#0C0C1C"))
    pal.setColor(QPalette.ColorRole.Text,       QColor("#C4C4DC"))
    app.setPalette(pal)

    win = GLabsAutomationTab()
    win.setWindowTitle("G-Labs Auto Generator")
    win.resize(1080, 760)
    win.show()
    sys.exit(app.exec())