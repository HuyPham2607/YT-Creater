from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QScrollArea)

class VideoMetadataTab(QWidget):
    def __init__(self):
        super().__init__()
        main_lay = QVBoxLayout(self); main_lay.setContentsMargins(32, 32, 32, 32)
        
        header = QHBoxLayout(); header.setContentsMargins(0,0,0,20)
        vbox = QVBoxLayout(); vbox.addWidget(QLabel("Video Metadata (SEO)", objectName="page_title"))
        vbox.addWidget(QLabel("Phân tích kịch bản hoàn chỉnh để xuất Tiêu đề, Description, Timestamps & Tags", objectName="page_desc"))
        header.addLayout(vbox); header.addStretch(); header.addWidget(QLabel("Tool 6", objectName="page_badge"))
        main_lay.addLayout(header)

        scroll = QScrollArea(); widget = QWidget(); lay = QVBoxLayout(widget); lay.setSpacing(20)

        lay.addWidget(QLabel("KỊCH BẢN HOÀN CHỈNH (FINAL SCRIPT)", objectName="section_label"))
        self.txt_script = QTextEdit(placeholderText="Paste toàn bộ kịch bản cuối cùng vào đây để AI đọc hiểu ngữ cảnh...")
        self.txt_script.setFixedHeight(120)
        lay.addWidget(self.txt_script)

        act_lay = QHBoxLayout()
        act_lay.addWidget(QPushButton("🚀 Generate SEO Metadata", objectName="btn_primary"))
        act_lay.addStretch()
        lay.addLayout(act_lay)

        # Kết quả trả về chia làm 3 box
        lay.addWidget(QLabel("5 PHƯƠNG ÁN TITLE (CLICKBAIT + SEO)", objectName="section_label"))
        lay.addWidget(QTextEdit(maximumHeight=100))

        lay.addWidget(QLabel("DESCRIPTION & TIMESTAMPS (CHƯƠNG)", objectName="section_label"))
        lay.addWidget(QTextEdit(maximumHeight=120))

        lay.addWidget(QLabel("TAGS & HASHTAGS (COMMA SEPARATED)", objectName="section_label"))
        lay.addWidget(QTextEdit(maximumHeight=60))

        scroll.setWidget(widget); main_lay.addWidget(scroll)