import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QGridLayout, QFrame, QScrollArea, 
                             QSizePolicy, QDialog, QLineEdit, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.components import DropZoneWidget

# Đường dẫn file lưu trữ database
DB_FILE = "profiles.json"

# =======================================================
# 1. CỬA SỔ POP-UP: DÙNG CHUNG CHO TẠO MỚI & CHỈNH SỬA
# =======================================================
class ProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tạo Profile mới")
        self.resize(750, 480) # Giảm chiều cao popup tối đa
        
        self.setStyleSheet("""
            QDialog { background-color: #0F0F18; border: 1px solid #252535; }
            QLabel { color: #E8E8F0; }
            QLineEdit, QTextEdit { background-color: #08080D; border: 1px solid #252535; border-radius: 8px; padding: 10px; color: #E8E8F0; font-size: 14px; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #E8742A; }
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(32, 32, 32, 20)

        # --- HEADER ---
        head_lay = QHBoxLayout()
        self.lbl_title = QLabel("Tạo Profile mới")
        self.lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #E8E8F0;")
        head_lay.addWidget(self.lbl_title)
        head_lay.addStretch()
        main_lay.addLayout(head_lay)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #252535; border: none; margin: 10px 0;")
        main_lay.addWidget(line)

        # --- NỘI DUNG FORM ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        widget = QWidget()
        form_lay = QVBoxLayout(widget)
        form_lay.setContentsMargins(0, 10, 16, 10)
        form_lay.setSpacing(20)

        # Khởi tạo các biến chứa dữ liệu
        self.txt_name = QLineEdit()
        self.txt_niche = QLineEdit("Roleplay & Makeover")
        self.txt_visual = QLineEdit("2D Cartoon")
        self.txt_lang = QLineEdit("Tiếng Việt, English")
        self.txt_pov = QLineEdit("Ngôi 2 (Bạn)")
        self.txt_char = QTextEdit()
        self.txt_bg = QTextEdit()
        
        self.txt_char.setMaximumHeight(80)
        self.txt_bg.setMaximumHeight(80)

        # 1. Tên kênh & Ngách
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        
        v_name = QVBoxLayout()
        v_name.addWidget(QLabel("TÊN KÊNH *", objectName="muted"))
        v_name.addWidget(self.txt_name)
        row1.addLayout(v_name)

        v_niche = QVBoxLayout()
        v_niche.addWidget(QLabel("NGÁCH", objectName="muted"))
        v_niche.addWidget(self.txt_niche)
        row1.addLayout(v_niche)
        form_lay.addLayout(row1)

        # 2. Cài đặt mặc định
        form_lay.addWidget(QLabel("DEFAULT SETTINGS", objectName="section_label"))
        grid_def = QGridLayout()
        grid_def.setSpacing(16)
        grid_def.addWidget(QLabel("VISUAL STYLE", objectName="muted"), 0, 0)
        grid_def.addWidget(QLabel("NGÔN NGỮ", objectName="muted"), 0, 1)
        grid_def.addWidget(QLabel("POV STYLE", objectName="muted"), 0, 2)
        grid_def.addWidget(self.txt_visual, 1, 0)
        grid_def.addWidget(self.txt_lang, 1, 1)
        grid_def.addWidget(self.txt_pov, 1, 2)
        form_lay.addLayout(grid_def)

        # 3. G-Labs Prompts
        form_lay.addWidget(QLabel("STYLE PROMPTS G-LABS", objectName="section_label"))
        form_lay.addWidget(QLabel("CHARACTER STYLE", objectName="muted"))
        form_lay.addWidget(self.txt_char)
        form_lay.addWidget(QLabel("BACKGROUND STYLE", objectName="muted"))
        form_lay.addWidget(self.txt_bg)

        # 4. Context Files
        form_lay.addWidget(QLabel("CONTEXT FILES", objectName="section_label"))
        ctx_lay = QHBoxLayout()
        ctx_lay.setSpacing(16)
        ctx_lay.addWidget(DropZoneWidget("📋", "STYLE GUIDE", "Upload .md"))
        ctx_lay.addWidget(DropZoneWidget("🧬", "DNA KÊNH", "Upload .md"))
        ctx_lay.addWidget(DropZoneWidget("📝", "CHỦ ĐỀ", "Upload .md"))
        form_lay.addLayout(ctx_lay)

        # NÚT AUTO EXTRACT (Đã được nâng cấp)
        self.btn_extract = QPushButton("⚡ Auto Extract", objectName="btn_sec")
        self.btn_extract.setFixedWidth(150)
        self.btn_extract.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_extract.clicked.connect(self.auto_extract_data) # Gắn sự kiện click
        form_lay.addWidget(self.btn_extract)

        form_lay.addStretch()
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        # --- ĐÁY POP-UP ---
        act_lay = QHBoxLayout()
        act_lay.setContentsMargins(0, 10, 0, 0)
        act_lay.addStretch()
        
        btn_cancel = QPushButton("Hủy", objectName="btn_sec")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Lưu Profile", objectName="btn_primary")
        btn_save.clicked.connect(self.validate_and_save)
        
        act_lay.addWidget(btn_cancel)
        act_lay.addWidget(btn_save)
        main_lay.addLayout(act_lay)

    # =======================================================
    # LOGIC: AUTO EXTRACT TỪ AI
    # =======================================================
    def auto_extract_data(self):
        # Đổi chữ trên nút để báo hiệu đang xử lý
        self.btn_extract.setText("⏳ Đang trích xuất...")
        self.btn_extract.setEnabled(False)
        
        # Hiển thị thông báo (Thực tế sau này đây sẽ là lúc gọi API Claude/Gemini)
        QMessageBox.information(self, "Auto Extract", "Hệ thống đang mô phỏng gọi AI API đọc nội dung từ file Context và Style Guide...")
        
        # GIẢ LẬP KẾT QUẢ AI TRẢ VỀ: Tự động đổ dữ liệu vào Form
        self.txt_name.setText("Kênh Trinh Thám Lịch Sử")
        self.txt_niche.setText("Lịch Sử, Bí Ẩn, Án Mạng")
        self.txt_visual.setText("Dark Academia, Noir, Sepia tone")
        self.txt_lang.setText("English, Tiếng Việt")
        self.txt_pov.setText("Ngôi 3 (Người kể chuyện bí ẩn)")
        self.txt_char.setText("Nhân vật mang phong cách thế kỷ 19, mặc áo măng tô, đội mũ phớt, bóng tối che nửa khuôn mặt, nét vẽ comic đen trắng có điểm xuyết màu đỏ đẫm máu.")
        self.txt_bg.setText("Thành phố sương mù London cổ kính, đèn đường leo lét, ngõ hẻm ẩm ướt đầy gạch vụn, phòng làm việc bừa bộn tài liệu phá án.")
        
        # Phục hồi lại trạng thái của nút
        self.btn_extract.setText("⚡ Auto Extract")
        self.btn_extract.setEnabled(True)
        QMessageBox.information(self, "Thành công", "Đã trích xuất và điền dữ liệu thành công!")


    def validate_and_save(self):
        if not self.txt_name.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Tên Kênh!")
            self.txt_name.setFocus()
            return
        self.accept()

    def get_profile_data(self):
        return {
            "name": self.txt_name.text().strip(),
            "niche": self.txt_niche.text().strip(),
            "visual": self.txt_visual.text().strip(),
            "lang": self.txt_lang.text().strip(),
            "pov": self.txt_pov.text().strip(),
            "char_style": self.txt_char.toPlainText().strip(),
            "bg_style": self.txt_bg.toPlainText().strip()
        }

    def load_data(self, data):
        self.lbl_title.setText("Chỉnh sửa Profile")
        self.setWindowTitle("Chỉnh sửa Profile")
        
        self.txt_name.setText(data.get("name", ""))
        self.txt_niche.setText(data.get("niche", ""))
        self.txt_visual.setText(data.get("visual", ""))
        self.txt_lang.setText(data.get("lang", ""))
        self.txt_pov.setText(data.get("pov", ""))
        self.txt_char.setText(data.get("char_style", ""))
        self.txt_bg.setText(data.get("bg_style", ""))


# =======================================================
# 2. COMPONENT: THẺ PROFILE (CÓ TÍN HIỆU EDIT & DELETE)
# =======================================================
class ProfileCard(QFrame):
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, data, index):
        super().__init__()
        self.index = index
        
        self.setObjectName("profile_card")
        self.setStyleSheet("""
            QFrame#profile_card { background: #0F0F18; border: 1px solid #252535; border-radius: 12px; }
            QFrame#profile_card:hover { border: 1px solid #E8742A; background: rgba(232,116,42,0.02); }
        """)
        self.setFixedWidth(290) # Thu nhỏ card thêm nữa để vừa 3 cột trên màn hình laptop

        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(12)

        lbl_title = QLabel(data.get("name", "Unknown Profile"))
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #E8E8F0;")
        lay.addWidget(lbl_title)

        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        info_grid.addWidget(QLabel("Ngách:", objectName="muted"), 0, 0)
        info_grid.addWidget(QLabel(data.get("niche", ""), styleSheet="color: #E8E8F0; font-weight: bold;"), 0, 1)
        info_grid.addWidget(QLabel("Ngôn ngữ:", objectName="muted"), 1, 0)
        info_grid.addWidget(QLabel(data.get("lang", ""), styleSheet="color: #E8E8F0;"), 1, 1)
        info_grid.addWidget(QLabel("Visual:", objectName="muted"), 2, 0)
        info_grid.addWidget(QLabel(data.get("visual", ""), styleSheet="color: #E8E8F0;"), 2, 1)
        info_grid.setColumnStretch(1, 1)
        lay.addLayout(info_grid)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #252535; border: none; margin: 5px 0;")
        lay.addWidget(line)

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(12)
        
        self.btn_edit = QPushButton("✏️ Chỉnh sửa", objectName="btn_sec")
        self.btn_edit.setStyleSheet("font-size: 12px; padding: 8px 12px;")
        
        self.btn_delete = QPushButton("🗑️ Xóa")
        self.btn_delete.setStyleSheet("""
            QPushButton { background: transparent; color: #E84040; border: 1px solid rgba(232,64,64,0.3); border-radius: 8px; padding: 8px 12px; font-size: 12px; font-weight: bold;}
            QPushButton:hover { background: rgba(232,64,64,0.1); border: 1px solid #E84040; }
        """)
        
        btn_lay.addWidget(self.btn_edit)
        btn_lay.addWidget(self.btn_delete)
        btn_lay.addStretch()
        lay.addLayout(btn_lay)

        self.btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.index))
        self.btn_delete.clicked.connect(lambda: self.delete_clicked.emit(self.index))


# =======================================================
# 3. TAB CHÍNH: PROFILE MANAGER
# =======================================================
class ProfileManagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.profiles = []
        
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(15, 15, 15, 15) # Giảm lề

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 15)
        
        vbox_h = QVBoxLayout()
        vbox_h.setSpacing(4)
        vbox_h.addWidget(QLabel("Profile Manager", objectName="page_title"))
        vbox_h.addWidget(QLabel("Quản lý DNA và Style cho từng kênh", objectName="page_desc"))
        header.addLayout(vbox_h)
        
        lbl_badge = QLabel("Tool Profile", objectName="page_badge")
        header.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignTop)
        header.addStretch()

        self.btn_new_profile = QPushButton("+ Tạo Profile mới", objectName="btn_primary")
        self.btn_new_profile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_profile.clicked.connect(self.open_new_profile_dialog)
        header.addWidget(self.btn_new_profile, alignment=Qt.AlignmentFlag.AlignTop)
        
        main_lay.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)

        self.grid_cards = QGridLayout()
        self.grid_cards.setSpacing(16) # Giảm khoảng cách giữa các card
        lay.addLayout(self.grid_cards)
        lay.addStretch()

        scroll.setWidget(widget)
        main_lay.addWidget(scroll)

        self.load_database()

    def load_database(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.profiles = json.load(f)
            except Exception as e:
                print("Lỗi đọc file:", e)
                self.profiles = []
        self.render_grid()

    def save_database(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.profiles, f, ensure_ascii=False, indent=4)

    def render_grid(self):
        for i in reversed(range(self.grid_cards.count())):
            widget_to_remove = self.grid_cards.itemAt(i).widget()
            if widget_to_remove is not None:
                widget_to_remove.setParent(None)
                widget_to_remove.deleteLater()

        columns = 3
        for index, profile_data in enumerate(self.profiles):
            row = index // columns
            col = index % columns
            
            card = ProfileCard(profile_data, index)
            card.edit_clicked.connect(self.edit_profile)
            card.delete_clicked.connect(self.delete_profile)
            
            self.grid_cards.addWidget(card, row, col)

        self.grid_cards.setColumnStretch(0, 1)
        self.grid_cards.setColumnStretch(1, 1)
        self.grid_cards.setColumnStretch(2, 1)

    def open_new_profile_dialog(self):
        dialog = ProfileDialog(self)
        if dialog.exec(): 
            new_data = dialog.get_profile_data()
            self.profiles.append(new_data) 
            self.save_database()           
            self.render_grid()             

    def edit_profile(self, index):
        dialog = ProfileDialog(self)
        dialog.load_data(self.profiles[index])
        
        if dialog.exec():
            updated_data = dialog.get_profile_data()
            self.profiles[index] = updated_data
            self.save_database()
            self.render_grid()

    def delete_profile(self, index):
        profile_name = self.profiles[index].get("name", "kênh này")
        
        reply = QMessageBox.question(self, 'Xác nhận xóa', 
                                     f'Bạn có chắc chắn muốn xóa profile "{profile_name}"?\n(Thao tác này không thể hoàn tác)',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.profiles.pop(index) 
            self.save_database()     
            self.render_grid()