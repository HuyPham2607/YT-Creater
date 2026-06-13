import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QFormLayout, QSpinBox, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

from core.ai_settings import load_ai_settings, save_ai_settings, mask_api_key

try:
    from google import genai
except ImportError:
    genai = None


class AISettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings — AI Config")
        self.resize(560, 420)
        self.setStyleSheet("""
            QDialog { background: #0F0F18; }
            QLabel { color: #E8E8F0; }
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background: #18182B; border: 1px solid #282840; border-radius: 6px;
                padding: 8px; color: #E8E8F0;
            }
        """)

        settings = load_ai_settings()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>AI Configuration</b>"))
        layout.addWidget(QLabel(
            "Cấu hình API key và model chain. Lưu vào <code>.env</code> và <code>data/ai_settings.json</code>.",
            wordWrap=True,
        ))

        form = QFormLayout()
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText(mask_api_key(settings.get("api_key", "")) or "Nhập GEMINI_API_KEY mới")
        self.txt_model_chain = QLineEdit(settings.get("model_chain", ""))
        self.spin_cache_ttl = QSpinBox()
        self.spin_cache_ttl.setRange(300, 86400)
        self.spin_cache_ttl.setValue(int(settings.get("cache_ttl_seconds", 3600)))
        self.spin_topic_temp = QDoubleSpinBox()
        self.spin_topic_temp.setRange(0.0, 1.5)
        self.spin_topic_temp.setSingleStep(0.05)
        self.spin_topic_temp.setValue(float(settings.get("topic_temperature", 0.75)))
        self.spin_research_temp = QDoubleSpinBox()
        self.spin_research_temp.setRange(0.0, 1.5)
        self.spin_research_temp.setSingleStep(0.05)
        self.spin_research_temp.setValue(float(settings.get("research_temperature", 0.3)))

        form.addRow("Gemini API Key", self.txt_api_key)
        form.addRow("Model chain (comma)", self.txt_model_chain)
        form.addRow("Cache TTL (seconds)", self.spin_cache_ttl)
        form.addRow("Topic temperature", self.spin_topic_temp)
        form.addRow("Research temperature", self.spin_research_temp)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_test = QPushButton("Test API")
        btn_test.clicked.connect(self._test_api)
        btn_save = QPushButton("Lưu")
        btn_save.setStyleSheet("background:#E8742A;color:#000;font-weight:bold;padding:8px 16px;border-radius:6px;")
        btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Đóng")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_test)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self._existing_key = settings.get("api_key", "")

    def _collect(self) -> dict:
        api_key = self.txt_api_key.text().strip() or self._existing_key
        return {
            "api_key": api_key,
            "model_chain": self.txt_model_chain.text().strip(),
            "cache_ttl_seconds": self.spin_cache_ttl.value(),
            "topic_temperature": self.spin_topic_temp.value(),
            "research_temperature": self.spin_research_temp.value(),
        }

    def _save(self):
        try:
            save_ai_settings(self._collect())
            QMessageBox.information(self, "Đã lưu", "Cấu hình AI đã được lưu.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

    def _test_api(self):
        if genai is None:
            QMessageBox.warning(self, "Thiếu thư viện", "google-genai chưa được cài đặt.")
            return
        api_key = self.txt_api_key.text().strip() or self._existing_key
        if not api_key:
            QMessageBox.warning(self, "Thiếu key", "Nhập GEMINI_API_KEY trước.")
            return
        try:
            client = genai.Client(api_key=api_key)
            models = list(client.models.list())
            count = len(models)
            QMessageBox.information(self, "OK", f"Kết nối API thành công.\nModels visible: {count}")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi API", str(exc))
