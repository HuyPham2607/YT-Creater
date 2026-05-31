from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QGridLayout, 
                             QComboBox, QScrollArea)
from PyQt6.QtCore import Qt

class CameraMovementTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(32, 32, 32, 32)
        
        # ==========================================
        # 1. HEADER
        # ==========================================
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 20)
        vbox_h = QVBoxLayout()
        
        lbl_title = QLabel("Camera Movement Prompts")
        lbl_title.setObjectName("page_title")
        vbox_h.addWidget(lbl_title)
        
        lbl_desc = QLabel("Tạo prompts chuyển động (Pan, Zoom, Tilt) cho AI Video (Runway Gen-3, Luma, Kling)")
        lbl_desc.setObjectName("page_desc")
        vbox_h.addWidget(lbl_desc)
        
        header.addLayout(vbox_h)
        header.addStretch()
        
        lbl_badge = QLabel("Tool 4")
        lbl_badge.setObjectName("page_badge")
        header.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignTop)
        
        main_lay.addLayout(header)

        # ==========================================
        # 2. SCROLL AREA & NỘI DUNG
        # ==========================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setSpacing(20)

        # --- WORKFLOW HINT ---
        hint_text = "💡 <b>Workflow Tool 4:</b> Dán danh sách các scenes đã sinh từ Tool 2 → Chọn Engine → Gen."
        hint = QLabel(hint_text)
        hint.setStyleSheet("background: rgba(232,116,42,0.06); border: 1px solid rgba(232,116,42,0.15); "
                           "border-radius: 8px; padding: 12px 16px; color: #E8742A; line-height: 1.5; font-size: 13px;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # --- 3. INPUT SCENES ---
        lay.addWidget(QLabel("DANH SÁCH SCENES / ẢNH (TỪ TOOL 2)", objectName="section_label"))
        
        self.txt_scenes = QTextEdit()
        self.txt_scenes.setPlaceholderText("Dán danh sách scenes (VD: [001] agent-young standing in dark-office...)")
        self.txt_scenes.setMinimumHeight(120)
        lay.addWidget(self.txt_scenes)

        # --- 4. CÀI ĐẶT MOTION GRID ---
        lay.addWidget(QLabel("CÀI ĐẶT MOTION", objectName="section_label"))
        
        grid = QGridLayout()
        grid.setSpacing(14)
        
        grid.addWidget(QLabel("AI ENGINE", objectName="muted"), 0, 0)
        grid.addWidget(QLabel("CAMERA MOTION", objectName="muted"), 0, 1)
        grid.addWidget(QLabel("CƯỜNG ĐỘ MOTION", objectName="muted"), 0, 2)
        
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["Runway Gen-3", "Luma Dream Machine", "Kling AI", "Haiper", "Minimax"])
        grid.addWidget(self.cmb_engine, 1, 0)
        
        self.cmb_motion = QComboBox()
        self.cmb_motion.addItems(["Auto (AI quyết định theo cảnh)", "Zoom In từ từ", "Zoom Out chậm", 
                                  "Pan Left (sang trái)", "Pan Right (sang phải)", "Tilt Up", 
                                  "Tilt Down", "Dolly In", "Tracking shot"])
        grid.addWidget(self.cmb_motion, 1, 1)
        
        self.cmb_intensity = QComboBox()
        self.cmb_intensity.addItems(["Nhẹ (Subtle)", "Vừa (Moderate)", "Mạnh (Dynamic)"])
        grid.addWidget(self.cmb_intensity, 1, 2)
        
        # Căn chỉnh độ rộng các cột cho đẹp mắt
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 1)
        lay.addLayout(grid)

        # --- 5. ACTION BUTTON ---
        act_lay = QHBoxLayout()
        btn_gen = QPushButton("🎬 Generate Motion Prompts", objectName="btn_primary")
        btn_gen.setMinimumWidth(250)
        act_lay.addWidget(btn_gen)
        act_lay.addStretch()
        lay.addLayout(act_lay)

        # --- 6. OUTPUT PROMPTS ---
        lay.addWidget(QLabel("KẾT QUẢ PROMPTS (COPY VÀO RUNWAY/LUMA/KLING)", objectName="section_label"))
        
        self.txt_result = QTextEdit()
        self.txt_result.setPlaceholderText("Motion prompts sẽ hiển thị ở đây...")
        self.txt_result.setMinimumHeight(150)
        lay.addWidget(self.txt_result)

        # Đẩy toàn bộ widget lên trên, tránh bị dãn rỗng ở giữa
        lay.addStretch()
        
        scroll.setWidget(widget)
        main_lay.addWidget(scroll)