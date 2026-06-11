import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QUrl, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.api_voice import (
    generate_cached_preview_voice,
    generate_edge_tts,
    generate_preview_voice,
    list_default_voices,
    list_edge_voices,
    open_file,
)


FAVORITES_PATH = Path(__file__).resolve().parents[1] / "data" / "voice_favorites.json"


class VoiceWorker(QThread):
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            self.log_signal.emit("Generating Edge TTS audio...")
            result = generate_edge_tts(**self.config)
            self.done_signal.emit({
                "audio_path": result.audio_path,
                "subtitle_path": result.subtitle_path,
                "script_path": result.script_path,
                "manifest_path": result.manifest_path,
                "voice": result.voice,
                "chars": result.chars,
            })
        except Exception as exc:
            self.error_signal.emit(str(exc))


def edge_rate_from_speed(speed):
    pct = int(round((float(speed) - 1.0) * 100))
    return f"{pct:+d}%"


def edge_pitch_from_value(value):
    return f"{int(value):+d}Hz"


def edge_volume_from_value(value):
    return f"{int(value):+d}%"


def display_gender(value):
    return {"Male": "Nam", "Female": "Nữ"}.get(value or "", value or "Không rõ")


def display_categories(values):
    names = {
        "General": "Đọc thông dụng",
        "News": "Tin tức",
        "Novel": "Truyện / sách nói",
        "Cartoon": "Hoạt hình",
        "Conversation": "Hội thoại",
        "Copilot": "Trợ lý AI",
        "Dialect": "Giọng địa phương",
    }
    return ", ".join(names.get(v, v) for v in (values or [])) or "Thông dụng"


def display_personalities(values):
    names = {
        "Friendly": "thân thiện",
        "Positive": "tích cực",
        "Lively": "sinh động",
        "Warm": "ấm áp",
        "Reliable": "đáng tin",
        "Authority": "uy tín",
        "Professional": "chuyên nghiệp",
        "Pleasant": "dễ nghe",
        "Clear": "rõ ràng",
        "Confident": "tự tin",
        "Cute": "dễ thương",
        "Rational": "lý trí",
        "Passion": "cảm xúc",
        "Humorous": "hài hước",
        "Bright": "sáng",
        "Casual": "tự nhiên",
        "Sincere": "chân thành",
        "Conversational": "đối thoại",
    }
    return ", ".join(names.get(v, v.lower()) for v in (values or [])) or "thân thiện"


class PreviewWorker(QThread):
    done_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, voice, text, rate, pitch, volume):
        super().__init__()
        self.voice = voice
        self.text = text
        self.rate = rate
        self.pitch = pitch
        self.volume = volume

    def run(self):
        try:
            self.done_signal.emit(generate_preview_voice(self.voice, self.text, self.rate, self.pitch, self.volume))
        except Exception as exc:
            self.error_signal.emit(str(exc))


class VoiceListWorker(QThread):
    done_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def run(self):
        try:
            self.done_signal.emit(list_edge_voices())
        except Exception as exc:
            self.error_signal.emit(str(exc))


class CachedPreviewWorker(QThread):
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, voice_info, rate, pitch, volume, force=False):
        super().__init__()
        self.voice_info = voice_info
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.force = force

    def run(self):
        try:
            self.log_signal.emit(f"Preparing preview: {self.voice_info.get('name', '')}")
            self.done_signal.emit(generate_cached_preview_voice(self.voice_info, self.rate, self.pitch, self.volume, self.force))
        except Exception as exc:
            self.error_signal.emit(str(exc))


class BatchPreviewWorker(QThread):
    progress_signal = pyqtSignal(str)
    done_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, voices, rate, pitch, volume):
        super().__init__()
        self.voices = voices
        self.rate = rate
        self.pitch = pitch
        self.volume = volume

    def run(self):
        count = 0
        try:
            total = len(self.voices)
            for idx, voice in enumerate(self.voices, 1):
                generate_cached_preview_voice(voice, self.rate, self.pitch, self.volume, force=False)
                count += 1
                if idx == 1 or idx % 10 == 0 or idx == total:
                    self.progress_signal.emit(f"Cached previews: {idx}/{total}")
            self.done_signal.emit(count)
        except Exception as exc:
            self.error_signal.emit(str(exc))


class VoiceFilterDialog(QDialog):
    def __init__(self, parent, voices, filters):
        super().__init__(parent)
        self.setWindowTitle("Voice Filters")
        self.setMinimumWidth(560)
        self.voices = voices or []
        self.filters = dict(filters or {})
        self._setup_ui()

    def _values(self, key):
        if key in {"categories", "personalities"}:
            return sorted({item for voice in self.voices for item in voice.get(key, []) if item})
        if key == "locale":
            return sorted({
                (voice.get("locale", ""), voice.get("locale_display") or voice.get("locale", ""))
                for voice in self.voices
                if voice.get("locale", "")
            }, key=lambda item: item[1])
        return sorted({voice.get(key, "") for voice in self.voices if voice.get(key, "")})

    def _combo(self, values, current=""):
        combo = QComboBox()
        combo.addItem("Any")
        for value in values:
            if isinstance(value, tuple):
                combo.addItem(value[1], value[0])
            else:
                combo.addItem(value, value)
        if current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        return combo

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Voice Filters")
        title.setObjectName("page_title")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.cmb_locale = self._combo(self._values("locale"), self.filters.get("locale", ""))
        self.cmb_gender = self._combo(self._values("gender"), self.filters.get("gender", ""))
        self.cmb_category = self._combo(self._values("categories"), self.filters.get("category", ""))
        self.cmb_personality = self._combo(self._values("personalities"), self.filters.get("personality", ""))
        self.cmb_status = self._combo(self._values("status"), self.filters.get("status", ""))
        self.cmb_codec = self._combo(self._values("codec"), self.filters.get("codec", ""))

        fields = [
            ("Locale", self.cmb_locale),
            ("Gender", self.cmb_gender),
            ("Category", self.cmb_category),
            ("Personality", self.cmb_personality),
            ("Status", self.cmb_status),
            ("Codec", self.cmb_codec),
        ]
        for idx, (label, combo) in enumerate(fields):
            row = (idx // 2) * 2
            col = idx % 2
            grid.addWidget(QLabel(label), row, col)
            grid.addWidget(combo, row + 1, col)
        root.addLayout(grid)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_reset = QPushButton("Reset All")
        self.btn_apply = QPushButton("Apply Filters")
        self.btn_apply.setObjectName("btn_primary")
        actions.addWidget(self.btn_reset)
        actions.addWidget(self.btn_apply)
        root.addLayout(actions)

        self.btn_reset.clicked.connect(self._reset)
        self.btn_apply.clicked.connect(self.accept)

    def _clean(self, combo):
        value = combo.currentData()
        return "" if value == "Any" else value

    def _reset(self):
        for combo in [self.cmb_locale, self.cmb_gender, self.cmb_category, self.cmb_personality, self.cmb_status, self.cmb_codec]:
            combo.setCurrentIndex(0)

    def selected_filters(self):
        return {
            "locale": self._clean(self.cmb_locale),
            "gender": self._clean(self.cmb_gender),
            "category": self._clean(self.cmb_category),
            "personality": self._clean(self.cmb_personality),
            "status": self._clean(self.cmb_status),
            "codec": self._clean(self.cmb_codec),
        }


class VoiceGeneratorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.preview_worker = None
        self.voice_list_worker = None
        self.cached_preview_worker = None
        self.batch_preview_worker = None
        self.last_audio_path = ""
        self.last_subtitle_path = ""
        self.all_voice_items = []
        self.voice_filters = {}
        self.selected_voice_id = ""
        self.favorite_voices = self._load_favorites()
        self.show_favorites_only = False
        self.audio_output = QAudioOutput()
        self.audio_player = QMediaPlayer()
        self.audio_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)
        self._setup_ui()
        self._connect()
        self._refresh_voices()

    def _slider_row(self, title, left_text, right_text, minimum, maximum, value, formatter):
        box = QFrame()
        box.setObjectName("subpanel")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        top = QHBoxLayout()
        label = QLabel(title)
        value_label = QLabel(formatter(value))
        value_label.setObjectName("page_badge")
        top.addWidget(label)
        top.addStretch()
        top.addWidget(value_label)
        lay.addLayout(top)

        hint = QHBoxLayout()
        left = QLabel(left_text)
        left.setObjectName("page_desc")
        right = QLabel(right_text)
        right.setObjectName("page_desc")
        hint.addWidget(left)
        hint.addStretch()
        hint.addWidget(right)
        lay.addLayout(hint)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(lambda v: value_label.setText(formatter(v)))
        lay.addWidget(slider)
        return box, slider, value_label

    def _voice_row_widget(self, item):
        box = QFrame()
        box.setStyleSheet("""
            QFrame { background:#151515; border:1px solid #2A2A2A; border-radius:8px; }
            QLabel { background:transparent; border:none; }
            QLabel#voice_name { color:#FFFFFF; font-size:12px; font-weight:800; }
            QLabel#voice_meta { color:#D5D8E2; font-size:11px; }
            QLabel#voice_hint { color:#8F97A8; font-size:11px; }
        """)
        root = QHBoxLayout(box)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        lay = QVBoxLayout()
        lay.setSpacing(3)
        root.addLayout(lay, 1)

        title = QLabel(item.get("name", ""))
        title.setObjectName("voice_name")
        title.setWordWrap(False)
        lay.addWidget(title)

        language = item.get("locale_display") or item.get("locale", "")
        gender = display_gender(item.get("gender", ""))
        meta = QLabel(f"Ngôn ngữ: {language}    |    Giới tính: {gender}")
        meta.setObjectName("voice_meta")
        meta.setWordWrap(True)
        lay.addWidget(meta)

        category = display_categories(item.get("categories", []))
        personality = display_personalities(item.get("personalities", []))
        hint = QLabel(f"Phù hợp: {category}    |    Chất giọng: {personality}")
        hint.setObjectName("voice_hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        actions = QHBoxLayout()
        actions.setSpacing(5)
        btn_preview = QPushButton("Preview")
        btn_preview.setObjectName("btn_sec")
        btn_preview.setFixedWidth(72)
        btn_use = QPushButton("Use")
        btn_use.setObjectName("btn_primary")
        btn_use.setFixedWidth(54)
        btn_star = QPushButton("★" if item.get("name", "") in self.favorite_voices else "☆")
        btn_star.setCheckable(True)
        btn_star.setChecked(item.get("name", "") in self.favorite_voices)
        btn_star.setFixedWidth(34)
        voice_id = item.get("name", "")
        btn_preview.clicked.connect(lambda checked=False, v=item: self._preview_voice_item(v))
        btn_use.clicked.connect(lambda checked=False, vid=voice_id: self._use_voice_id(vid))
        btn_star.clicked.connect(lambda checked=False, vid=voice_id, b=btn_star: self._toggle_voice_favorite(vid, b))
        actions.addWidget(btn_preview)
        actions.addWidget(btn_use)
        actions.addWidget(btn_star)
        root.addLayout(actions)
        return box

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(540)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(left_scroll)

        left = QFrame()
        left.setObjectName("panel")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(14, 12, 14, 12)
        left_lay.setSpacing(8)
        left_scroll.setWidget(left)

        title = QLabel("Voice Generator")
        title.setObjectName("page_title")
        left_lay.addWidget(title)
        desc = QLabel("Edge TTS audio + SRT generator")
        desc.setObjectName("page_desc")
        left_lay.addWidget(desc)
        provider_note = QLabel("Edge TTS supports Voice, Speed, Pitch, and Volume. Other provider-specific voice-clone controls are hidden.")
        provider_note.setWordWrap(True)
        provider_note.setObjectName("page_desc")
        left_lay.addWidget(provider_note)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.btn_filter_voices = QPushButton("Filters")
        self.btn_filter_voices.setObjectName("btn_sec")
        self.btn_favorites_only = QPushButton("★ Starred")
        self.btn_favorites_only.setCheckable(True)
        self.btn_favorites_only.setObjectName("btn_sec")
        self.btn_cache_previews = QPushButton("Cache previews")
        self.btn_cache_previews.setObjectName("btn_sec")
        self.voice_items = []

        self.txt_project = QLineEdit("voice_project")
        self.txt_output = QLineEdit("outputs/voice")
        self.btn_output = QPushButton("Open")

        self.lbl_voice_title = QLabel("Voice Selection")
        grid.addWidget(self.lbl_voice_title, 0, 0, 1, 2)
        self.txt_voice_search = QLineEdit()
        self.txt_voice_search.setPlaceholderText("Search library voices")
        voice_tools = QHBoxLayout()
        voice_tools.addWidget(self.txt_voice_search, 1)
        voice_tools.addWidget(self.btn_filter_voices)
        voice_tools.addWidget(self.btn_favorites_only)
        grid.addLayout(voice_tools, 1, 0, 1, 2)

        self.voice_list = QListWidget()
        self.voice_list.setMinimumHeight(230)
        self.voice_list.setMaximumHeight(260)
        self.voice_list.setSpacing(4)
        grid.addWidget(self.voice_list, 2, 0, 1, 2)

        selected_row = QHBoxLayout()
        self.lbl_selected_voice = QLabel("Selected: none")
        self.lbl_selected_voice.setObjectName("page_desc")
        self.btn_use_voice = QPushButton("Use selected")
        self.btn_use_voice.setObjectName("btn_sec")
        selected_row.addWidget(self.lbl_selected_voice, 1)
        selected_row.addWidget(self.btn_use_voice)
        grid.addLayout(selected_row, 3, 0, 1, 2)
        self._populate_voices(list_default_voices())

        cache_row = QHBoxLayout()
        cache_hint = QLabel("Preview trong từng voice sẽ dùng file cache; chưa có thì tự tạo lần đầu.")
        cache_hint.setObjectName("page_desc")
        cache_hint.setWordWrap(True)
        cache_row.addWidget(cache_hint, 1)
        cache_row.addWidget(self.btn_cache_previews)
        grid.addLayout(cache_row, 4, 0, 1, 2)

        grid.addWidget(QLabel("Project"), 5, 0)
        grid.addWidget(QLabel("Output folder"), 5, 1)
        grid.addWidget(self.txt_project, 6, 0)
        out_row = QHBoxLayout()
        out_row.addWidget(self.txt_output, 1)
        out_row.addWidget(self.btn_output)
        grid.addLayout(out_row, 6, 1)
        left_lay.addLayout(grid)

        speed_box, self.sld_speed, self.lbl_speed_value = self._slider_row(
            "Speed", "Slower", "Faster", 70, 120, 100, lambda v: f"{v / 100:.2f}"
        )
        pitch_box, self.sld_pitch, self.lbl_pitch_value = self._slider_row(
            "Pitch", "Lower", "Higher", -50, 50, 0, lambda v: f"{v:+d}Hz"
        )
        volume_box, self.sld_volume, self.lbl_volume_value = self._slider_row(
            "Volume", "Quieter", "Louder", -50, 50, 0, lambda v: f"{v:+d}%"
        )
        left_lay.addWidget(speed_box)
        left_lay.addWidget(pitch_box)
        left_lay.addWidget(volume_box)

        self.txt_preview = QTextEdit()
        self.txt_preview.setMaximumHeight(88)
        self.txt_preview.setPlainText("Tôi từng ngồi đúng vị trí mà bạn đang ngồi lúc này. Hôm nay tôi muốn nói với bạn một điều thật.")
        left_lay.addWidget(QLabel("Preview text"))
        left_lay.addWidget(self.txt_preview)

        row = QHBoxLayout()
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setObjectName("btn_sec")
        self.btn_generate = QPushButton("Generate Audio")
        self.btn_generate.setObjectName("btn_primary")
        row.addWidget(self.btn_preview)
        row.addWidget(self.btn_generate)
        left_lay.addLayout(row)

        self.btn_open_audio = QPushButton("Open audio")
        self.btn_open_audio.setEnabled(False)
        self.btn_open_sub = QPushButton("Open SRT")
        self.btn_open_sub.setEnabled(False)
        open_row = QHBoxLayout()
        open_row.addWidget(self.btn_open_audio)
        open_row.addWidget(self.btn_open_sub)
        left_lay.addLayout(open_row)

        left_lay.addStretch()

        right = QVBoxLayout()
        root.addLayout(right, 1)
        self.txt_script = QTextEdit()
        self.txt_script.setPlaceholderText("Paste script here. Markers like [PAUSE], [CHẬM], [MUSIC DROP], [TEXT OVERLAY: \"...\"] will be removed from TTS text.")
        right.addWidget(QLabel("Script"))
        right.addWidget(self.txt_script, 1)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(130)
        right.addWidget(QLabel("Log"))
        right.addWidget(self.txt_log)

    def _connect(self):
        self.btn_output.clicked.connect(self._choose_output)
        self.btn_filter_voices.clicked.connect(self._open_filters)
        self.btn_favorites_only.toggled.connect(self._toggle_favorites_filter)
        self.btn_cache_previews.clicked.connect(self._cache_all_previews)
        self.txt_voice_search.textChanged.connect(self._apply_voice_filters)
        self.voice_list.itemDoubleClicked.connect(lambda item: self._use_current_voice())
        self.btn_use_voice.clicked.connect(self._use_current_voice)
        self.btn_preview.clicked.connect(self._preview)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_open_audio.clicked.connect(lambda: open_file(self.last_audio_path))
        self.btn_open_sub.clicked.connect(lambda: open_file(self.last_subtitle_path))

    def _log(self, msg):
        self.txt_log.append(msg)

    def _play_audio_in_app(self, path):
        if not path:
            return
        self.audio_player.stop()
        self.audio_player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        self.audio_player.play()

    def _load_favorites(self):
        try:
            if FAVORITES_PATH.exists():
                data = json.loads(FAVORITES_PATH.read_text(encoding="utf-8"))
                return set(data.get("voices", []))
        except Exception as exc:
            print(f"Could not load voice favorites: {exc}")
        return set()

    def _save_favorites(self):
        try:
            FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
            FAVORITES_PATH.write_text(
                json.dumps({"voices": sorted(self.favorite_voices)}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"Could not save voice favorites: {exc}")

    def _populate_voices(self, voices, update_source=True):
        current = self._voice()
        self.voice_list.clear()
        if update_source:
            self.all_voice_items = voices or list_default_voices()
        self.voice_items = voices or list_default_voices()
        for item in self.voice_items:
            friendly = item.get("friendly_name") or item.get("label", "")
            row = QListWidgetItem()
            row.setData(Qt.ItemDataRole.UserRole, item.get("name", ""))
            row.setToolTip(f"{friendly}\nStatus: {item.get('status', '')}\nCodec: {item.get('codec', '')}")
            row.setSizeHint(QSize(0, 98))
            self.voice_list.addItem(row)
            self.voice_list.setItemWidget(row, self._voice_row_widget(item))
        if current:
            for index in range(self.voice_list.count()):
                if self.voice_list.item(index).data(Qt.ItemDataRole.UserRole) == current:
                    self.voice_list.setCurrentRow(index)
                    break
        if self.voice_list.currentRow() < 0 and self.voice_list.count() > 0:
            self.voice_list.setCurrentRow(0)
        total = len(self.all_voice_items) if self.all_voice_items else len(self.voice_items)
        self.lbl_voice_title.setText(f"Voice Selection ({len(self.voice_items)} / {total})")
        if not self.selected_voice_id and self.voice_list.currentItem():
            self.selected_voice_id = self.voice_list.currentItem().data(Qt.ItemDataRole.UserRole)
            self.lbl_selected_voice.setText(f"Selected: {self.selected_voice_id}")

    def _apply_voice_filters(self):
        voices = self.all_voice_items or list_default_voices()
        query = self.txt_voice_search.text().strip().lower() if hasattr(self, "txt_voice_search") else ""
        locale = self.voice_filters.get("locale", "")
        gender = self.voice_filters.get("gender", "")
        category = self.voice_filters.get("category", "")
        personality = self.voice_filters.get("personality", "")
        status = self.voice_filters.get("status", "")
        codec = self.voice_filters.get("codec", "")

        filtered = []
        for voice in voices:
            haystack = " ".join([
                voice.get("name", ""),
                voice.get("friendly_name", ""),
                voice.get("locale", ""),
                voice.get("gender", ""),
                voice.get("status", ""),
                voice.get("codec", ""),
                " ".join(voice.get("categories", [])),
                " ".join(voice.get("personalities", [])),
            ]).lower()
            if query and query not in haystack:
                continue
            if locale and voice.get("locale") != locale:
                continue
            if gender and voice.get("gender") != gender:
                continue
            if status and voice.get("status") != status:
                continue
            if codec and voice.get("codec") != codec:
                continue
            if category and category not in voice.get("categories", []):
                continue
            if personality and personality not in voice.get("personalities", []):
                continue
            if self.show_favorites_only and voice.get("name", "") not in self.favorite_voices:
                continue
            filtered.append(voice)
        self._populate_voices(filtered, update_source=False)

    def _toggle_favorites_filter(self, checked):
        self.show_favorites_only = checked
        self.btn_favorites_only.setText("★ Starred" if checked else "☆ Starred")
        self._apply_voice_filters()

    def _open_filters(self):
        dialog = VoiceFilterDialog(self, self.all_voice_items or list_default_voices(), self.voice_filters)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.voice_filters = dialog.selected_filters()
            active = [value for value in self.voice_filters.values() if value]
            self.btn_filter_voices.setText(f"Filters ({len(active)})" if active else "Filters")
            self._apply_voice_filters()

    def _use_current_voice(self):
        item = self.voice_list.currentItem()
        if not item:
            return
        self._use_voice_id(item.data(Qt.ItemDataRole.UserRole) or item.text().splitlines()[0].strip())

    def _use_voice_id(self, voice_id):
        if not voice_id:
            return
        self.selected_voice_id = voice_id
        self.lbl_selected_voice.setText(f"Selected: {self.selected_voice_id}")
        self._log(f"Selected voice: {self.selected_voice_id}")

    def _toggle_voice_favorite(self, voice_id, button=None):
        if not voice_id:
            return
        if voice_id in self.favorite_voices:
            self.favorite_voices.remove(voice_id)
            if button:
                button.setText("☆")
                button.setChecked(False)
        else:
            self.favorite_voices.add(voice_id)
            if button:
                button.setText("★")
                button.setChecked(True)
        self._save_favorites()
        if self.show_favorites_only:
            self._apply_voice_filters()

    def _preview_voice_item(self, voice_info):
        if self.cached_preview_worker and self.cached_preview_worker.isRunning():
            return
        self.cached_preview_worker = CachedPreviewWorker(
            voice_info,
            edge_rate_from_speed(self._speed()),
            self._pitch(),
            self._volume(),
            force=False,
        )
        self.cached_preview_worker.log_signal.connect(self._log)
        self.cached_preview_worker.done_signal.connect(self._cached_preview_done)
        self.cached_preview_worker.error_signal.connect(self._cached_preview_error)
        self.cached_preview_worker.start()

    def _cached_preview_done(self, path):
        self._log(f"Preview ready: {path}")
        self._play_audio_in_app(path)

    def _cached_preview_error(self, message):
        self._log(f"Preview failed: {message}")
        QMessageBox.warning(self, "Preview failed", message)

    def _cache_all_previews(self):
        if self.batch_preview_worker and self.batch_preview_worker.isRunning():
            return
        voices = self.all_voice_items or list_default_voices()
        self.btn_cache_previews.setEnabled(False)
        self.batch_preview_worker = BatchPreviewWorker(
            voices,
            edge_rate_from_speed(self._speed()),
            self._pitch(),
            self._volume(),
        )
        self.batch_preview_worker.progress_signal.connect(self._log)
        self.batch_preview_worker.done_signal.connect(self._cache_all_done)
        self.batch_preview_worker.error_signal.connect(self._cache_all_error)
        self.batch_preview_worker.start()

    def _cache_all_done(self, count):
        self.btn_cache_previews.setEnabled(True)
        self._log(f"Cached {count} voice preview file(s).")

    def _cache_all_error(self, message):
        self.btn_cache_previews.setEnabled(True)
        self._log(f"Cache previews failed: {message}")
        QMessageBox.warning(self, "Cache previews failed", message)

    def _choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.txt_output.setText(path)

    def _refresh_voices(self):
        if self.voice_list_worker and self.voice_list_worker.isRunning():
            return
        self.btn_filter_voices.setEnabled(False)
        self._log("Loading full Edge TTS voice list...")
        self.voice_list_worker = VoiceListWorker()
        self.voice_list_worker.done_signal.connect(self._voices_loaded)
        self.voice_list_worker.error_signal.connect(self._voices_failed)
        self.voice_list_worker.start()

    def _voices_loaded(self, voices):
        self.btn_filter_voices.setEnabled(True)
        self._populate_voices(voices)
        self._log(f"Loaded {len(voices)} Edge TTS voice(s).")
        if not self.selected_voice_id and self.voice_list.count() > 0:
            self._use_current_voice()

    def _voices_failed(self, message):
        self.btn_filter_voices.setEnabled(True)
        self._log(f"Could not load voices: {message}")
        QMessageBox.warning(self, "Voice list failed", message)

    def _voice(self):
        if self.selected_voice_id:
            return self.selected_voice_id
        item = self.voice_list.currentItem() if hasattr(self, "voice_list") else None
        if item:
            return item.data(Qt.ItemDataRole.UserRole) or item.text().splitlines()[0].strip()
        if self.voice_items:
            return self.voice_items[0].get("name", "")
        return "vi-VN-NamMinhNeural"

    def _speed(self):
        return self.sld_speed.value() / 100

    def _pitch(self):
        return edge_pitch_from_value(self.sld_pitch.value())

    def _volume(self):
        return edge_volume_from_value(self.sld_volume.value())

    def _preview(self):
        if self.preview_worker and self.preview_worker.isRunning():
            return
        self.btn_preview.setEnabled(False)
        self._log("Rendering preview with current Speed, Pitch, and Volume.")
        self.preview_worker = PreviewWorker(
            self._voice(),
            self.txt_preview.toPlainText().strip(),
            edge_rate_from_speed(self._speed()),
            self._pitch(),
            self._volume(),
        )
        self.preview_worker.done_signal.connect(self._preview_done)
        self.preview_worker.error_signal.connect(self._preview_error)
        self.preview_worker.start()

    def _preview_done(self, path):
        self.btn_preview.setEnabled(True)
        self._log(f"Preview ready: {path}")
        self._play_audio_in_app(path)

    def _preview_error(self, message):
        self.btn_preview.setEnabled(True)
        self._log(f"Preview failed: {message}")
        QMessageBox.warning(self, "Preview failed", message)

    def _generate(self):
        script = self.txt_script.toPlainText().strip()
        if not script:
            QMessageBox.warning(self, "Missing script", "Paste a script first.")
            return
        if self.worker and self.worker.isRunning():
            return

        self.btn_generate.setEnabled(False)
        self.btn_open_audio.setEnabled(False)
        self.btn_open_sub.setEnabled(False)
        config = {
            "text": script,
            "output_dir": self.txt_output.text().strip() or "outputs/voice",
            "project_name": self.txt_project.text().strip() or "voice_project",
            "voice": self._voice(),
            "speed": self._speed(),
            "rate": edge_rate_from_speed(self._speed()),
            "pitch": self._pitch(),
            "volume": self._volume(),
        }
        self.worker = VoiceWorker(config)
        self.worker.log_signal.connect(self._log)
        self.worker.done_signal.connect(self._done)
        self.worker.error_signal.connect(self._error)
        self.worker.start()

    def _done(self, result):
        self.btn_generate.setEnabled(True)
        self.last_audio_path = result["audio_path"]
        self.last_subtitle_path = result["subtitle_path"]
        self.btn_open_audio.setEnabled(True)
        self.btn_open_sub.setEnabled(True)
        self._log(f"Done: {result['audio_path']}")
        self._log(f"SRT : {result['subtitle_path']}")

    def _error(self, message):
        self.btn_generate.setEnabled(True)
        self._log(f"Error: {message}")
        QMessageBox.warning(self, "Voice generation failed", message)

    def load_script_data(self, title="", script="", topic=""):
        if title or topic:
            self.txt_project.setText((topic or title).strip())
        if script:
            self.txt_script.setPlainText(script)
