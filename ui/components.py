import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal

class DropZoneWidget(QFrame):
    file_loaded = pyqtSignal(str, str)

    def __init__(self, icon, title, desc):
        super().__init__()
        self.setObjectName("upload_card")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(80) # Giảm chiều cao tối thiểu của khu vực kéo thả

        vbox = QVBoxLayout(self); vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(2)
        
        lbl_icon = QLabel(icon); lbl_icon.setStyleSheet("font-size: 18px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel(title); lbl_title.setStyleSheet("color: #E8742A; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_desc = QLabel(desc); self.lbl_desc.setStyleSheet("color: #606075; font-size: 11px;")
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        vbox.addWidget(lbl_icon); vbox.addWidget(lbl_title); vbox.addWidget(self.lbl_desc)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("border-color: #3AD68A; background-color: rgba(58,214,138,0.04);")

    def dragLeaveEvent(self, event): self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        for url in event.mimeData().urls():
            self.process_file(url.toLocalFile()); break

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            file_path, _ = QFileDialog.getOpenFileName(self, "Chọn File", "", "Text Files (*.txt *.md)")
            if file_path: self.process_file(file_path)

    def process_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            self.lbl_desc.setText(f"Đã tải: {os.path.basename(file_path)}")
            self.lbl_desc.setStyleSheet("color: #3AD68A; font-size: 13px;") # Màu xanh chuẩn Web
            self.file_loaded.emit(file_path, content)
        except Exception:
            self.lbl_desc.setText("Lỗi đọc file!"); self.lbl_desc.setStyleSheet("color: #E84040;")