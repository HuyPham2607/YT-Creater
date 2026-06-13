from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QHBoxLayout, QPushButton, QMessageBox,
)

from core.project_store import list_saved_projects, load_active_project, save_active_project, restore_project_to_main_window


class ProjectManagerDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._projects = []
        self.setWindowTitle("Project Manager")
        self.resize(520, 420)
        self.setStyleSheet("""
            QDialog { background: #0F0F18; }
            QLabel { color: #E8E8F0; }
            QListWidget { background: #18182B; border: 1px solid #282840; color: #E8E8F0; }
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Projects</b> — lưu/khôi phục tiến độ video giữa các lần mở app"))

        self.list_projects = QListWidget()
        self._reload_list()
        layout.addWidget(self.list_projects)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 Lưu project hiện tại")
        btn_save.clicked.connect(self._save_current)
        btn_load = QPushButton("📂 Mở project đã chọn")
        btn_load.clicked.connect(self._load_selected)
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_load)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _reload_list(self):
        self.list_projects.clear()
        self._projects = list_saved_projects()
        active = load_active_project()
        active_name = (active or {}).get("name")
        for project in self._projects:
            name = project.get("name", "untitled")
            state = project.get("state") or {}
            title = state.get("script_title") or state.get("topic_title") or "(chưa có title)"
            marker = "★ " if name == active_name else ""
            self.list_projects.addItem(f"{marker}{name} — {title}")

    def _save_current(self):
        project = save_active_project(self.main_window)
        restore_project_to_main_window(self.main_window, project)
        QMessageBox.information(self, "Đã lưu", f"Project đã lưu: {project.get('name')}")
        self._reload_list()

    def _load_selected(self):
        row = self.list_projects.currentRow()
        if row < 0 or row >= len(self._projects):
            QMessageBox.warning(self, "Chưa chọn", "Chọn một project trong danh sách.")
            return
        project = self._projects[row]
        restore_project_to_main_window(self.main_window, project)
        save_active_project(self.main_window)
        self.accept()
