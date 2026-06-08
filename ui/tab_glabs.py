import sys, os, subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QGridLayout, QComboBox, QScrollArea,
    QFrame, QCheckBox, QRadioButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QPixmap

# Giả lập import Engine
try:
    from .glabs_engine import run_auto
    ENGINE_OK = True
except ImportError:
    ENGINE_OK = False

# =======================================================
# COMPONENT: Cột Ảnh Tham Chiếu
# =======================================================
class RefImageGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.btn_add = QPushButton("Thêm ảnh")
        self.btn_add.setFixedSize(80, 32)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet("""
            QPushButton { background: transparent; color: #8A8AA0; border: 1px solid #2A2A48; border-radius: 6px; font-weight: bold;}
            QPushButton:hover { border-color: #5A4FCC; color: #A0A0D0; background: #1B1B30; }
        """)
        
        layout.addWidget(self.btn_add, alignment=Qt.AlignmentFlag.AlignCenter)

# =======================================================
# COMPONENT: Label Ảnh Có Thể Click
# =======================================================
class ClickableImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False) # Tắt scale tự động để dùng scale chuẩn của QPixmap
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.filepath:
            try:
                if sys.platform == "win32":
                    os.startfile(self.filepath)
                elif sys.platform == "darwin":
                    subprocess.call(["open", self.filepath])
                else:
                    subprocess.call(["xdg-open", self.filepath])
            except Exception as e:
                print(f"Không thể mở ảnh: {e}")
        super().mousePressEvent(event)

# =======================================================
# COMPONENT: Khung chứa ảnh Output
# =======================================================
class OutputImageContainer(QWidget):
    def __init__(self, expected_images=2, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        self.layout.setSpacing(8)
        
        self.image_labels = []
        
        if expected_images == 1:
            size, font_size = 160, 32
        elif expected_images == 2:
            size, font_size = 120, 24
        else:
            size, font_size = 80, 20

        for i in range(expected_images):
            lbl = ClickableImageLabel()
            lbl.setFixedSize(size, size)
            lbl.setStyleSheet(f"background: #131320; border: 1px dashed #2A2A48; border-radius: 8px; color: #505070; font-size: {font_size}px;")
            lbl.setText("⏳")
            
            if expected_images == 1:
                self.layout.addWidget(lbl, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            elif expected_images == 2:
                self.layout.addWidget(lbl, 0, i, alignment=Qt.AlignmentFlag.AlignCenter)
            elif expected_images == 3:
                if i < 2: self.layout.addWidget(lbl, 0, i, alignment=Qt.AlignmentFlag.AlignCenter)
                else: self.layout.addWidget(lbl, 1, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                row, col = divmod(i, 2)
                self.layout.addWidget(lbl, row, col, alignment=Qt.AlignmentFlag.AlignCenter)
                
            self.image_labels.append(lbl)
            
        self.current_fill_idx = 0

    def add_loaded_image(self, filepath):
        if self.current_fill_idx < len(self.image_labels):
            lbl = self.image_labels[self.current_fill_idx]
            lbl.filepath = filepath 
            try:
                # Nạp ảnh và scale giữ nguyên tỷ lệ (KeepAspectRatio), hiển thị trọn vẹn 100% ảnh
                pixmap = QPixmap(filepath)
                scaled_pixmap = pixmap.scaled(
                    lbl.width() - 4, lbl.height() - 4, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )

                lbl.setPixmap(scaled_pixmap)
                lbl.setText("")
                lbl.setStyleSheet("border: 2px solid #00E676; border-radius: 8px; background: #131320; padding: 2px;") 
            except Exception as e:
                lbl.setText("❌")
                lbl.setStyleSheet("border: 2px solid #E84040; border-radius: 8px; font-size: 24px; background: #1A1010;")
                
            self.current_fill_idx += 1


# =======================================================
# GIAO DIỆN CHÍNH
# =======================================================
class GLabsAutomationTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._connect_signals()
        self.engine_thread = None 

    def _connect_signals(self):
        self.btn_import.clicked.connect(self._import_file)
        self.btn_run.clicked.connect(self._start_engine)
        self.btn_d3.clicked.connect(lambda: self._choose_dir(self.txt_out_dir))

    def _setup_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #11111E; color: #C4C4DC; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
            QLabel { color: #D0D0E0; }
            QLabel#lbl_group { color: #8A8AA0; font-size: 12px; font-weight: bold; margin-bottom: 2px; }
            QComboBox, QLineEdit, QSpinBox { background: #18182B; border: 1px solid #282840; border-radius: 6px; padding: 6px 10px; color: #E8E8F0; }
            QComboBox:focus, QLineEdit:focus { border: 1px solid #5A4FCC; }
            QComboBox::drop-down { border: none; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #2A2A48; border-radius: 4px; background: #18182B; }
            QCheckBox::indicator:checked { background: #5A4FCC; border-color: #5A4FCC; }
            QRadioButton { spacing: 8px; }
            QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid #2A2A48; border-radius: 8px; background: #18182B; }
            QRadioButton::indicator:checked { background: #5A4FCC; border-color: #5A4FCC; }
            QTextEdit { background: #18182B; border: 1px solid #282840; border-radius: 8px; padding: 10px; color: #E8E8F0; }
            QPushButton#btn_blue { background: #5A4FCC; color: #FFF; border-radius: 6px; padding: 8px; font-weight: bold; }
            QPushButton#btn_run { background: #00E676; color: #000; border-radius: 8px; padding: 12px; font-weight: bold; font-size: 14px; }
            QPushButton#btn_dark { background: #282840; color: #D0D0E0; border-radius: 8px; padding: 12px; font-weight: bold; }
            QPushButton#btn_footer { background: transparent; border: none; color: #A0A0C0; padding: 6px 12px; font-weight: bold; }
            QPushButton#btn_footer:hover { color: #FFF; background: #18182B; border-radius: 4px; }
            
            QTableWidget { background: #151525; border: 1px solid #282840; border-radius: 8px; gridline-color: #202035; }
            QHeaderView::section { background: #1A1A2E; color: #8A8AA0; padding: 12px; border: none; border-bottom: 1px solid #282840; border-right: 1px solid #282840; font-weight: bold; font-size: 12px; }
            QTableWidget::item { padding: 10px; border-bottom: 1px solid #202035; }
            QTableWidget::item:selected { background-color: #1E1E32; }
        """)

        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(16, 12, 16, 12)
        main_lay.setSpacing(12)

        # LEFT PANEL
        left_panel = QFrame()
        left_panel.setFixedWidth(280) # Thu hẹp panel điều khiển bên trái
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(8)

        title_lay = QHBoxLayout()
        v_title = QVBoxLayout()
        v_title.setSpacing(0)
        lbl_h1 = QLabel("G-Labs")
        lbl_h1.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFF;")
        lbl_h2 = QLabel("IMAGE CREATOR")
        lbl_h2.setStyleSheet("font-size: 11px; font-weight: bold; color: #8A8AA0; letter-spacing: 1px;")
        v_title.addWidget(lbl_h1)
        v_title.addWidget(lbl_h2)
        title_lay.addLayout(v_title)
        
        lbl_status = QLabel("🟢 1 Hoạt động")
        lbl_status.setStyleSheet("background: #00E676; color: #000; border-radius: 12px; padding: 6px 12px; font-weight: bold; font-size: 12px;")
        title_lay.addStretch()
        title_lay.addWidget(lbl_status, alignment=Qt.AlignmentFlag.AlignTop)
        left_lay.addLayout(title_lay)

        box_config = QFrame()
        box_config.setStyleSheet("QFrame { background: #18182B; border: 1px solid #282840; border-radius: 12px; }")
        box_lay = QVBoxLayout(box_config)
        box_lay.setContentsMargins(16, 16, 16, 16)
        box_lay.setSpacing(12)

        lbl_cft = QLabel("Cấu hình & Prompts")
        lbl_cft.setStyleSheet("background: #5A4FCC; color: #FFF; border-radius: 12px; padding: 6px 16px; font-weight: bold; font-size: 12px;")
        box_lay.addWidget(lbl_cft, alignment=Qt.AlignmentFlag.AlignLeft)

        r1 = QHBoxLayout()
        v1 = QVBoxLayout(); v1.addWidget(QLabel("Model:", objectName="lbl_group"))
        self.cmb_model = QComboBox(); self.cmb_model.addItems(["Nano Banana 2", "Nano Banana Pro", "Imagen 4"]); v1.addWidget(self.cmb_model)
        
        v2 = QVBoxLayout(); v2.addWidget(QLabel("Chất lượng:", objectName="lbl_group"))
        h_qual = QHBoxLayout()
        rad_1k = QRadioButton("1K"); rad_1k.setChecked(True)
        h_qual.addWidget(rad_1k)
        h_qual.addWidget(QRadioButton("2K"))
        h_qual.addWidget(QRadioButton("4K"))
        v2.addLayout(h_qual)
        r1.addLayout(v1); r1.addLayout(v2)
        box_lay.addLayout(r1)

        r2 = QHBoxLayout()
        v3 = QVBoxLayout(); v3.addWidget(QLabel("Tỷ lệ ảnh:", objectName="lbl_group"))
        self.cmb_ratio = QComboBox(); self.cmb_ratio.addItems(["16:9 Ngang", "9:16 Dọc", "1:1 Vuông", "4:3", "3:4"]); v3.addWidget(self.cmb_ratio)
        
        v4 = QVBoxLayout(); v4.addWidget(QLabel("Số lượng ảnh / prompt:", objectName="lbl_group"))
        self.cmb_amt = QComboBox(); self.cmb_amt.addItems(["1x", "2x", "3x", "4x"]); self.cmb_amt.setCurrentText("2x"); v4.addWidget(self.cmb_amt)
        r2.addLayout(v3); r2.addLayout(v4)
        box_lay.addLayout(r2)

        r3 = QHBoxLayout()
        v5 = QVBoxLayout(); v5.addWidget(QLabel("Số luồng chạy đồng thời:", objectName="lbl_group"))
        txt_threads = QLineEdit("6"); v5.addWidget(txt_threads)
        
        v6 = QVBoxLayout(); v6.addWidget(QLabel("Độ trễ giữa các luồng (s):", objectName="lbl_group"))
        h_delay = QHBoxLayout()
        h_delay.addWidget(QLineEdit("10 s")); h_delay.addWidget(QLabel("-")); h_delay.addWidget(QLineEdit("20 s"))
        v6.addLayout(h_delay)
        r3.addLayout(v5); r3.addLayout(v6)
        box_lay.addLayout(r3)

        r4 = QHBoxLayout()
        v7 = QVBoxLayout(); v7.addWidget(QLabel("Chế độ tham chiếu:", objectName="lbl_group"))
        cmb_ref = QComboBox(); cmb_ref.addItems(["Mặc định"]); v7.addWidget(cmb_ref)
        
        h_seed = QHBoxLayout()
        self.txt_seed = QLineEdit(""); h_seed.addWidget(self.txt_seed)
        self.chk_seed = QCheckBox("Khóa seed"); self.chk_seed.setStyleSheet("color: #5A4FCC; font-weight: bold;")
        h_seed.addWidget(self.chk_seed)
        r4.addLayout(v7); r4.addLayout(h_seed)
        r4.setAlignment(h_seed, Qt.AlignmentFlag.AlignBottom)
        box_lay.addLayout(r4)

        r5 = QHBoxLayout()
        self.btn_import = QPushButton("ImportFile (TXT, Excel)"); self.btn_import.setObjectName("btn_blue")
        r5.addWidget(self.btn_import); r5.addWidget(QLabel("📄 1 hàng / 1 prompt", styleSheet="color: #8A8AA0;"))
        r5.addStretch()
        box_lay.addLayout(r5)

        self.txt_prompts = QTextEdit()
        self.txt_prompts.setPlaceholderText("Nhập danh sách prompt vào đây")
        self.txt_prompts.setMinimumHeight(80)
        box_lay.addWidget(self.txt_prompts)

        box_lay.addWidget(QLabel("Thư mục ảnh tham chiếu:", objectName="lbl_group"))
        h_dir1 = QHBoxLayout()
        h_dir1.addWidget(QLineEdit("G-LABS-1.0\\reference_image"))
        btn_d1 = QPushButton("📂"); btn_d1.setStyleSheet("background: transparent; font-size: 16px; border: none;"); h_dir1.addWidget(btn_d1)
        box_lay.addLayout(h_dir1)

        h_dir2 = QHBoxLayout()
        h_dir2.addWidget(QLabel("Chế độ lưu:", objectName="lbl_group"))
        self.chk_task_folder = QCheckBox("📁 Tạo thư mục theo Task"); self.chk_task_folder.setChecked(True)
        h_dir2.addWidget(self.chk_task_folder)
        h_dir2.addStretch()
        box_lay.addLayout(h_dir2)

        box_lay.addWidget(QLabel("Thư mục lưu:", objectName="lbl_group"))
        h_dir3 = QHBoxLayout()
        self.txt_out_dir = QLineEdit("outputs/glabs_images"); h_dir3.addWidget(self.txt_out_dir)
        self.btn_d3 = QPushButton("📂"); self.btn_d3.setStyleSheet("background: transparent; font-size: 16px; border: none;"); h_dir3.addWidget(self.btn_d3)
        box_lay.addLayout(h_dir3)

        h_queue = QHBoxLayout()
        btn_add = QPushButton("+ Thêm vào hàng chờ")
        btn_add.setStyleSheet("background: transparent; border: 1px solid #5A4FCC; color: #5A4FCC; border-radius: 6px; padding: 8px; font-weight: bold;")
        h_queue.addWidget(btn_add)
        btn_mgr = QPushButton("📋 Quản lý hàng chờ (0)")
        btn_mgr.setStyleSheet("background: transparent; border: 1px solid #282840; color: #A0A0C0; border-radius: 6px; padding: 8px;")
        h_queue.addWidget(btn_mgr)
        box_lay.addLayout(h_queue)

        left_lay.addWidget(box_config)

        h_bottom = QHBoxLayout()
        self.btn_run = QPushButton("🚀 CHẠY NGAY"); self.btn_run.setObjectName("btn_run")
        btn_pause = QPushButton("TẠM DỪNG"); btn_pause.setObjectName("btn_dark")
        btn_stop = QPushButton("DỪNG"); btn_stop.setObjectName("btn_dark")
        h_bottom.addWidget(self.btn_run, 2)
        h_bottom.addWidget(btn_pause, 1)
        h_bottom.addWidget(btn_stop, 1)
        left_lay.addLayout(h_bottom)
        
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setFixedWidth(292)
        left_scroll.setWidget(left_panel)
        main_lay.addWidget(left_scroll)

        # RIGHT PANEL
        right_panel = QVBoxLayout()
        right_panel.setSpacing(12)

        banner = QFrame()
        banner.setStyleSheet("background: #1A1A32; border: 1px solid #2A2A50; border-radius: 8px;")
        b_lay = QVBoxLayout(banner)
        lbl_btitle = QLabel("🍌 Nano Banana Pro")
        lbl_btitle.setStyleSheet("color: #FFB300; font-weight: bold; font-size: 14px;")
        b_lay.addWidget(lbl_btitle)
        b_lay.addWidget(QLabel("→ Kết hợp tối đa 10 ảnh tham chiếu để tạo ảnh độc đáo.\n💡 Chọn thư mục ảnh tham chiếu, gõ tên file vào prompt để tự động thêm ảnh.\n⭐ Phù hợp nhất để tạo ảnh có ảnh tham chiếu."))
        right_panel.addWidget(banner)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["", "STT", "Task", "Ảnh tham chiếu", "Prompt", "Ảnh output", "Tiến độ"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(1, 40)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(2, 140)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(3, 120) 
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) 
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(5, 280) 
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(6, 100)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        right_panel.addWidget(self.table)

        f_lay = QHBoxLayout()
        btns = ["+ Thêm dòng", "🖼️ Thêm ảnh", "🗑️ Xóa", "🧹 Xóa hết", "🔄 Chạy lại lỗi", "▶ Chạy mục chọn", "📂 Load Session", "✅ Hoàn thành"]
        for b in btns:
            btn = QPushButton(b)
            btn.setObjectName("btn_footer")
            if b == "✅ Hoàn thành":
                btn.setStyleSheet("background: #1E1E32; border: 1px solid #5A4FCC; color: #D0D0E0; border-radius: 6px; padding: 6px 16px; font-weight: bold;")
            f_lay.addWidget(btn)
        f_lay.addStretch()
        right_panel.addLayout(f_lay)

        main_lay.addLayout(right_panel)

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn file prompt", "", "Text Files (*.txt);;Excel Files (*.xlsx *.xls)")
        if path:
            if path.endswith('.txt'):
                with open(path, 'r', encoding='utf-8') as f:
                    self.txt_prompts.setPlainText(f.read())
            elif path.endswith(('.xlsx', '.xls')):
                try:
                    import pandas as pd
                    df = pd.read_excel(path)
                    prompts = "\n".join(df.iloc[:, 0].astype(str).tolist())
                    self.txt_prompts.setPlainText(prompts)
                except ImportError:
                    QMessageBox.warning(self, "Lỗi", "Vui lòng cài đặt thư viện 'pandas' để đọc file Excel.")

    def _choose_dir(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if dir_path: line_edit.setText(dir_path)

    def _start_engine(self):
        if not ENGINE_OK:
            QMessageBox.critical(self, "Lỗi", "Engine glabs_engine.py chưa được nạp!")
            return
            
        raw_prompts = self.txt_prompts.toPlainText().strip().split('\n')
        valid_prompts = [p.strip() for p in raw_prompts if p.strip()]
        
        if not valid_prompts:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập danh sách prompt.")
            return

        self.txt_prompts.clear()

        try:
            amt = int(self.cmb_amt.currentText().replace("x", ""))
        except ValueError:
            amt = 2

        task_name = os.path.basename(self.txt_out_dir.text())
        if not task_name or task_name == "glabs_images":
            import datetime
            task_name = datetime.datetime.now().strftime("Task_%m%d_%H%M")

        config = {
            "prompts": valid_prompts,
            "save_dir": self.txt_out_dir.text(),
            "expected_images": amt,
            "aspect_ratio": self.cmb_ratio.currentText(),
            "model": self.cmb_model.currentText(),
            "seed": self.txt_seed.text() if self.chk_seed.isChecked() else None,
            "task_name": task_name if self.chk_task_folder.isChecked() else None
        }
        
        start_row_idx = self._prepare_table_for_run(valid_prompts, config)
        
        self.btn_run.setEnabled(False)
        self.btn_run.setText("⏳ ĐANG CHẠY...")
        
        self.engine_thread = EngineThread(config, start_row_idx)
        self.engine_thread.progress_signal.connect(self._update_row_progress)
        self.engine_thread.status_signal.connect(self._update_row_status)
        self.engine_thread.image_signal.connect(self._add_image_to_row)
        self.engine_thread.finished_signal.connect(self._on_engine_finished)
        self.engine_thread.start()

    def _prepare_table_for_run(self, prompts, config):
        start_idx = self.table.rowCount()
        self.table.setRowCount(start_idx + len(prompts))
        
        for i, prompt_text in enumerate(prompts):
            row = start_idx + i
            
            expected = config['expected_images']
            if expected == 1:
                self.table.setRowHeight(row, 180)
            elif expected == 2:
                self.table.setRowHeight(row, 140)
            else:
                self.table.setRowHeight(row, 190)
            
            chk_widget = QWidget(); l_chk = QHBoxLayout(chk_widget); l_chk.setContentsMargins(0,0,0,0)
            l_chk.addWidget(QCheckBox(), alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 0, chk_widget)
            
            stt = QTableWidgetItem(str(row+1)); stt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stt.setForeground(QColor("#8A8AA0"))
            self.table.setItem(row, 1, stt)
            
            task_info = f"{config['task_name'] or 'Default'}\n{config['model']}\n{config['aspect_ratio']}"
            task = QTableWidgetItem(task_info)
            task.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            task.setForeground(QColor("#E8E8F0"))
            self.table.setItem(row, 2, task)
            
            # Khởi tạo Lưới ảnh tham chiếu sạch sẽ (chỉ có nút, không có chữ)
            self.table.setCellWidget(row, 3, RefImageGrid())
            
            prompt_item = QTableWidgetItem(prompt_text)
            prompt_item.setForeground(QColor("#E8E8F0"))
            self.table.setItem(row, 4, prompt_item)
            
            self.table.setCellWidget(row, 5, OutputImageContainer(config['expected_images']))
            
            lbl_prog = QLabel("0%")
            lbl_prog.setStyleSheet("color: #8A8AA0; font-weight: bold; font-size: 14px;")
            lbl_prog.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 6, lbl_prog)
            
        return start_idx

    def _update_row_status(self, row_idx, status):
        lbl = self.table.cellWidget(row_idx, 6)
        if lbl and "%" not in lbl.text(): 
            lbl.setText("⏳")
            lbl.setStyleSheet("color: #FFB300; font-weight: bold; font-size: 16px;")

    def _update_row_progress(self, row_idx, percent):
        lbl = self.table.cellWidget(row_idx, 6)
        if lbl:
            if percent == -1: # Nhận cờ lỗi -1 từ Engine
                lbl.setText("Bị chặn")
                lbl.setStyleSheet("color: #E84040; font-weight: bold; font-size: 14px;")
            elif percent >= 100:
                lbl.setText("Hoàn thành")
                lbl.setStyleSheet("color: #00E676; font-weight: bold; font-size: 12px;") 
            else:
                lbl.setText(f"{percent}%")
                lbl.setStyleSheet("color: #00E676; font-weight: bold; font-size: 14px;")

    def _add_image_to_row(self, row_idx, filepath):
        img_container = self.table.cellWidget(row_idx, 5)
        if isinstance(img_container, OutputImageContainer):
            img_container.add_loaded_image(filepath)

    def _on_engine_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("🚀 CHẠY NGAY")
        for i in range(self.table.rowCount()):
            lbl = self.table.cellWidget(i, 6)
            if lbl and ("%" in lbl.text() or "⏳" in lbl.text()):
                lbl.setText("Hoàn thành")
                lbl.setStyleSheet("color: #00E676; font-weight: bold; font-size: 12px;")

# =======================================================
# LUỒNG NỀN CHO ENGINE
# =======================================================
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
        self.config['on_gen_start'] = lambda idx, prmpt: self.status_signal.emit(self.start_row_idx + idx, "Đang khởi tạo...")
        self.config['on_gen_progress'] = lambda idx, pct: self.progress_signal.emit(self.start_row_idx + idx, pct)
        self.config['on_image_saved'] = lambda idx, fp: self.image_signal.emit(self.start_row_idx + idx, fp)
        
        run_auto(**self.config, log_fn=print)
        self.finished_signal.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GLabsAutomationTab()
    win.setWindowTitle("G-Labs Auto UI Clone")
    win.resize(1300, 800)
    win.show()
    sys.exit(app.exec())
