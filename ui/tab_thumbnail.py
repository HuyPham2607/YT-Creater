from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QGridLayout, QComboBox, QScrollArea, QLineEdit)

class ThumbnailTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self); main_lay.setContentsMargins(15, 15, 15, 15) # Giảm lề
        
        header = QHBoxLayout(); header.setContentsMargins(0,0,0,15)
        vbox = QVBoxLayout(); vbox.addWidget(QLabel("Thumbnail Generator", objectName="page_title"))
        vbox.addWidget(QLabel("Dựa trên Title & DNA để tạo prompt Midjourney + Text Overlays", objectName="page_desc"))
        header.addLayout(vbox); header.addStretch(); header.addWidget(QLabel("Tool 5", objectName="page_badge"))
        main_lay.addLayout(header)

        scroll = QScrollArea(); widget = QWidget(); lay = QVBoxLayout(widget); lay.setSpacing(20)

        grid_top = QGridLayout()
        grid_top.addWidget(QLabel("VIDEO TITLE CHÍNH", objectName="section_label"), 0, 0)
        self.txt_title = QLineEdit(placeholderText="VD: Tại sao người giàu không gửi tiết kiệm?")
        grid_top.addWidget(self.txt_title, 1, 0)

        grid_top.addWidget(QLabel("THUMBNAIL STYLE (TỪ DNA)", objectName="section_label"), 0, 1)
        self.cmb_style = QComboBox(); self.cmb_style.addItems(["Tương phản cao (Đỏ/Đen)", "Bí ẩn (Xanh Navy/Vàng)", "Tối giản"])
        grid_top.addWidget(self.cmb_style, 1, 1)
        lay.addLayout(grid_top)

        h_lists = QHBoxLayout()
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("MÔ TẢ HÌNH ẢNH (VISUAL IDEA)", objectName="section_label"))
        v1.addWidget(QTextEdit(placeholderText="Nhập ý tưởng hoặc để AI tự nghĩ...", maximumHeight=80))
        
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("CHARACTER FOCUS", objectName="section_label"))
        v2.addWidget(QTextEdit(placeholderText="Nhân vật nào xuất hiện trên thumb? Biểu cảm ra sao?", maximumHeight=80))
        h_lists.addLayout(v1); h_lists.addLayout(v2); lay.addLayout(h_lists)

        act_lay = QHBoxLayout()
        act_lay.addWidget(QPushButton("🖼️ Generate Thumbnail Prompts & Text", objectName="btn_primary"))
        act_lay.addStretch()
        lay.addLayout(act_lay)

        split_res = QHBoxLayout()
        v_res1 = QVBoxLayout()
        v_res1.addWidget(QLabel("MIDJOURNEY PROMPTS", objectName="section_label"))
        v_res1.addWidget(QTextEdit())
        
        v_res2 = QVBoxLayout()
        v_res2.addWidget(QLabel("TEXT OVERLAY BOLD (CHỮ TRÊN ẢNH)", objectName="section_label"))
        v_res2.addWidget(QTextEdit())
        split_res.addLayout(v_res1); split_res.addLayout(v_res2); lay.addLayout(split_res)

        scroll.setWidget(widget); main_lay.addWidget(scroll)