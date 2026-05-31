import sys
import traceback
from PyQt6.QtWidgets import QApplication

# NHÚNG TRỰC TIẾP CSS VÀO ĐÂY ĐỂ TRÁNH LỖI ĐƯỜNG DẪN
QSS_STYLE = """
/* Nền chính và font chữ */
QMainWindow, QWidget#main_content { background-color: #08080D; color: #E8E8F0; font-family: "Segoe UI", sans-serif; }
QFrame#sidebar { background-color: #0F0F18; border-right: 1px solid #252535; }

/* Text & Typography */
QLabel { color: #E8E8F0; }
QLabel#muted { color: #606075; font-size: 12px; font-weight: normal; margin-bottom: 4px; }
QLabel#page_title { font-size: 26px; font-weight: bold; letter-spacing: 0.5px; }
QLabel#page_desc { font-size: 14px; color: #606075; margin-top: 4px; }
QLabel#page_badge { color: #E8742A; background-color: rgba(232,116,42,0.1); border: 1px solid rgba(232,116,42,0.2); padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }
QLabel#section_label { font-size: 12px; color: #606075; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; padding-left: 10px; border-left: 3px solid #E8742A; margin-top: 15px; margin-bottom: 5px;}

/* Buttons */
QPushButton#btn_primary { background-color: #E8742A; color: #000; border: none; border-radius: 8px; padding: 12px 24px; font-weight: bold; font-size: 14px; }
QPushButton#btn_primary:hover { background-color: #FF9A50; }
QPushButton#btn_sec { background-color: transparent; color: #E8E8F0; border: 1px solid #252535; padding: 12px 24px; border-radius: 8px; font-size: 14px; font-weight: bold; }
QPushButton#btn_sec:hover { border-color: #E8742A; color: #E8742A; }

/* Inputs & Dropdowns */
QLineEdit, QTextEdit, QComboBox { background-color: #0F0F18; border: 1px solid #252535; color: #E8E8F0; border-radius: 8px; padding: 12px 14px; font-size: 14px; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #E8742A; background-color: #11111A; }
QComboBox::drop-down { border: none; }

/* Sidebar Navigation */
QPushButton#nav_item { text-align: left; padding: 12px 16px; border-radius: 8px; color: #606075; font-size: 14px; border: 1px solid transparent; background-color: transparent; margin-bottom: 2px;}
QPushButton#nav_item:hover { background-color: #171724; color: #E8E8F0; }
QPushButton#nav_item:checked { background-color: rgba(232,116,42,0.12); border: 1px solid rgba(232,116,42,0.25); color: #E8742A; font-weight: bold; border-left: 4px solid #E8742A;}

/* Custom Components */
QFrame#upload_card { background-color: #0F0F18; border: 1px dashed #252535; border-radius: 10px; }
QFrame#upload_card:hover { border: 1px dashed #E8742A; background-color: rgba(232,116,42,0.04); }
QPushButton#tag_btn { background-color: #0F0F18; border: 1px solid #252535; color: #606075; border-radius: 16px; padding: 6px 16px; font-size: 13px; }
QPushButton#tag_btn:hover { border-color: #E8742A; color: #E8742A; }
QPushButton#tag_btn:checked { background-color: rgba(232,116,42,0.12); border: 1px solid #E8742A; color: #E8742A; font-weight: bold;}

/* Scrollbars & Splitters */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #08080D; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #252535; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #E8742A; }
QSplitter::handle { background: transparent; }
"""

def main():
    app = QApplication(sys.argv)
    
    # ÉP ÁP DỤNG CSS TRỰC TIẾP
    app.setStyleSheet(QSS_STYLE)

    try:
        from ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        with open("crash_log.txt", "w", encoding="utf-8") as f:
            f.write("=== LỖI HỆ THỐNG ===\n")
            traceback.print_exc(file=f)
        print("❌ App gặp lỗi nặng! Xem 'crash_log.txt' để biết chi tiết.")

if __name__ == "__main__":
    main()