from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QStackedWidget, QFrame, QButtonGroup, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

# Import Äáº¦Y Äá»¦ cÃ¡c mÃ n hÃ¬nh
from ui.tab_topic import TopicIdeatorTab
from ui.tab_script_writer import ScriptWriterTab
from ui.tab_scene_breakdown import SceneBreakdownTab
from ui.tab_asset_prompts import AssetPromptsTab
from ui.tab_camera import CameraMovementTab
from ui.tab_thumbnail import ThumbnailTab
from ui.tab_metadata import VideoMetadataTab
from ui.tab_qc import UploadQCTab
from ui.tab_profile import ProfileManagerTab
from ui.tab_glabs import GLabsAutomationTab # <--- IMPORT TAB G-LABS

# =======================================================
# HÃ€M TRá»¢ GIÃšP: Táº¡o ra má»™t Frame cÃ³ kháº£ nÄƒng nháº­n Click
# =======================================================
class ClickableFrame(QFrame):
    clicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RX MEDIA - Production Suite")
        self._apply_adaptive_window_size()

        main_widget = QWidget()
        main_widget.setObjectName("main_content")
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------------- SIDEBAR ----------------
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(170) # Thu háº¹p sidebar tá»‘i Ä‘a
        self.sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(8, 10, 8, 10) # NÃ©n lá» sidebar

        logo_layout = QHBoxLayout()
        lbl_logo = QLabel("RX")
        lbl_logo.setStyleSheet("background: #E8742A; color: #000; font-weight: bold; border-radius: 7px; padding: 6px; font-size: 14px;")
        lbl_text = QLabel("RX Media<br><b>Production Suite</b>")
        lbl_text.setStyleSheet("color: #606075; font-size: 12px;")
        logo_layout.addWidget(lbl_logo)
        logo_layout.addWidget(lbl_text)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        sidebar_layout.addSpacing(4) # NÃ©n spacing logo
        sidebar_layout.addWidget(QLabel("PROJECT", styleSheet="font-size: 10px; color: #606075; font-weight: bold; letter-spacing: 1px;"))
        btn_proj = QPushButton("â€” No project â€”")
        btn_proj.setStyleSheet("background: #171724; border: 1px solid #252535; color: #E8742A; padding: 8px; border-radius: 8px; text-align: left; padding-left: 12px;")
        sidebar_layout.addWidget(btn_proj)

        # ACTIVE PROFILE BOX
        sidebar_layout.addSpacing(16)
        
        self.prof_box = ClickableFrame()
        self.prof_box.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prof_box.setStyleSheet("""
            QFrame { background: rgba(232,116,42,0.08); border: 1px solid rgba(232,116,42,0.2); border-radius: 8px; }
            QFrame:hover { background: rgba(232,116,42,0.15); border: 1px solid #E8742A; }
        """)
        prof_lay = QVBoxLayout(self.prof_box)
        prof_lay.addWidget(QLabel("ACTIVE PROFILE", styleSheet="font-size: 10px; color: #E8742A; font-weight: bold; border: none; background: transparent;"))
        prof_lay.addWidget(QLabel("No profile â€” click to manage", styleSheet="font-size: 12px; color: #E8E8F0; border: none; background: transparent;"))
        
        self.prof_box.clicked.connect(self.open_profile_manager)
        sidebar_layout.addWidget(self.prof_box)

        # Navigation Menu
        sidebar_layout.addSpacing(16)
        self.nav_group = QButtonGroup(self)
        self.content_area = QStackedWidget()
        
        # --- ÄÃƒ THÃŠM TOOL 8 G-LABS VÃ€O MENU ---
        menus = [
            "0 Topic Ideator", "1 Script Writer", "2 Scene Breakdown", 
            "3 Asset Prompts", "4 Camera Movement", "5 Thumbnail", 
            "6 Video Metadata", "7 Upload QC", "8 G-Labs Auto"
        ]
        
        for idx, title in enumerate(menus):
            btn = QPushButton(title)
            btn.setObjectName("nav_item")
            btn.setCheckable(True)
            self.nav_group.addButton(btn, idx)
            btn.clicked.connect(lambda checked, i=idx: self.content_area.setCurrentIndex(i))
            sidebar_layout.addWidget(btn)
            if idx == 0: 
                btn.setChecked(True)

        sidebar_layout.addStretch()
        
        btn_export = QPushButton("â†“ Export Pipeline")
        btn_export.setStyleSheet("background: rgba(58,214,138,0.1); border: 1px solid rgba(58,214,138,0.25); color: #3AD68A; padding: 12px; border-radius: 8px; text-align: left; font-weight: bold;")
        sidebar_layout.addWidget(btn_export)
        
        credit_lay = QHBoxLayout()
        credit_lay.addWidget(QLabel("Credit", styleSheet="font-size: 12px; color: #606075; font-weight: bold;"))
        credit_lay.addStretch()
        credit_lay.addWidget(QLabel("0", styleSheet="color: #E8742A; font-weight: bold; font-size: 14px;"))
        sidebar_layout.addLayout(credit_lay)
        
        btn_settings = QPushButton("âš™ Settings â€” AI Config")
        btn_settings.setStyleSheet("background: rgba(232,116,42,0.08); border: 1px solid rgba(232,116,42,0.25); color: #E8742A; padding: 10px; border-radius: 8px; font-weight: bold;")
        sidebar_layout.addWidget(btn_settings)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)

        # ---------------- Náº P CÃC TRANG VÃ€O Há»† THá»NG ----------------
        self.tab_topic = TopicIdeatorTab()
        self.tab_script = ScriptWriterTab()
        self.tab_scene = SceneBreakdownTab()
        self.tab_asset = AssetPromptsTab()
        self.tab_camera = CameraMovementTab()
        self.tab_thumb = ThumbnailTab()
        self.tab_meta = VideoMetadataTab()
        self.tab_qc = UploadQCTab()

        self.content_area.addWidget(self.tab_topic)        # Index 0
        self.content_area.addWidget(self.tab_script)       # Index 1
        self.content_area.addWidget(self.tab_scene)        # Index 2
        self.content_area.addWidget(self.tab_asset)        # Index 3
        self.content_area.addWidget(self.tab_camera)       # Index 4
        self.content_area.addWidget(self.tab_thumb)        # Index 5
        self.content_area.addWidget(self.tab_meta)         # Index 6
        self.content_area.addWidget(self.tab_qc)              # Index 7
        
        # --- Náº P TAB G-LABS VÃ€O ÄÃšNG INDEX 8 ---
        self.tab_glabs = GLabsAutomationTab()
        self.content_area.addWidget(self.tab_glabs)           # Index 8
        
        # Náº¡p trang Profile Manager (Sáº½ á»Ÿ Index 9, khÃ´ng náº±m trong Menu chÃ­nh)
        self.page_profile = ProfileManagerTab()
        self.content_area.addWidget(self.page_profile)        # Index 9

        # Káº¾T Ná»I Sá»° KIá»†N ÃP Dá»¤NG PROFILE
        self.page_profile.profile_applied.connect(self.on_profile_applied)
        
        # Káº¿t ná»‘i luá»“ng Data giá»¯a Tool 2 vÃ  Tool 3
        self.tab_scene.transfer_to_tool3.connect(self.on_transfer_to_tool3)
        self.tab_asset.request_load_tool2.connect(self.on_request_load_tool2)
        self.tab_camera.request_load_tool2.connect(self.on_request_load_tool2_camera)
        self.tab_meta.request_load_script.connect(self.on_request_load_script_metadata)

        # Tá»± Ä‘á»™ng náº¡p profile khi khá»Ÿi Ä‘á»™ng náº¿u Ä‘Ã£ cÃ³ file
        self.load_active_profile()

    def _apply_adaptive_window_size(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(1366, 768)
            return

        available = screen.availableGeometry()
        width = min(max(int(available.width() * 0.88), 1100), 1600)
        height = min(max(int(available.height() * 0.86), 680), 920)
        width = min(width, available.width() - 40)
        height = min(height, available.height() - 40)

        self.resize(width, height)
        self.setMinimumSize(min(1024, width), min(640, height))

        x = available.x() + (available.width() - width) // 2
        y = available.y() + (available.height() - height) // 2
        self.move(x, y)

    def load_active_profile(self):
        import os, json
        if os.path.exists("active_profile.json"):
            try:
                with open("active_profile.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.on_profile_applied(data)
            except Exception:
                pass

    def on_profile_applied(self, data):
        # Cáº­p nháº­t tÃªn Profile lÃªn Sidebar
        name = data.get("name", "Active Profile")
        self.prof_box.findChildren(QLabel)[1].setText(name.upper())
        
        # Truyá»n data cho cÃ¡c Tool
        for idx in range(self.content_area.count()):
            tool = self.content_area.widget(idx)
            if hasattr(tool, 'apply_profile'):
                tool.apply_profile(data)

    def open_profile_manager(self):
        if self.nav_group.checkedButton():
            self.nav_group.setExclusive(False)
            self.nav_group.checkedButton().setChecked(False)
            self.nav_group.setExclusive(True)
        self.content_area.setCurrentWidget(self.page_profile)

    def on_transfer_to_tool3(self, chars, bgs, prescan_data=None):
        self.tab_asset.load_assets_data(chars, bgs, prescan_data)
        self.content_area.setCurrentIndex(3)
        self.nav_group.button(3).setChecked(True)

    def on_request_load_tool2_camera(self):
        scene_data = getattr(self.tab_scene, "_assigned_data", [])
        if not scene_data:
            QMessageBox.warning(self, "Missing scenes", "Run Tool 2 Assign Assets or Run Pipeline first.")
            return
        self.tab_camera.load_data(scene_data)
        QMessageBox.information(self, "Loaded", f"Loaded {len(scene_data)} scenes from Tool 2.")

    def on_request_load_script_metadata(self):
        script = self.tab_script.txt_output.toPlainText().strip()
        title = self.tab_script.txt_topic.text().strip()
        topic = getattr(self.tab_script, "current_topic_title", "") or title
        if not script:
            QMessageBox.warning(self, "Missing script", "Generate or paste a script in Tool 1 first.")
            return
        self.tab_meta.load_script_data(title=title, script=script, topic=topic)
        QMessageBox.information(self, "Loaded", "Loaded script from Tool 1.")

    def on_request_load_tool2(self):
        chars = self.tab_scene.txt_prescan_chars.toPlainText().strip()
        bgs = self.tab_scene.txt_prescan_bgs.toPlainText().strip()
        if not chars and not bgs:
            QMessageBox.warning(self, "Trá»‘ng", "BÃªn Tool 2 hiá»‡n chÆ°a cÃ³ dá»¯ liá»‡u Characters/Backgrounds (Pre-scan)!")
            return
        self.tab_asset.load_assets_data(chars, bgs, self.tab_scene._prescan_data)
        QMessageBox.information(self, "ThÃ nh cÃ´ng", "ÄÃ£ náº¡p danh sÃ¡ch Characters vÃ  Backgrounds tá»« Tool 2!")

