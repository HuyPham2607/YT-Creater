import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DEFAULT_VOICES = [
    {"name": "vi-VN-NamMinhNeural", "label": "Vietnamese - Nam Minh", "locale": "vi-VN", "gender": "Male"},
    {"name": "vi-VN-HoaiMyNeural", "label": "Vietnamese - Hoai My", "locale": "vi-VN", "gender": "Female"},
    {"name": "en-US-ChristopherNeural", "label": "English US - Christopher", "locale": "en-US", "gender": "Male"},
    {"name": "en-US-AndrewMultilingualNeural", "label": "English US - Andrew Multilingual", "locale": "en-US", "gender": "Male"},
    {"name": "en-US-BrianMultilingualNeural", "label": "English US - Brian Multilingual", "locale": "en-US", "gender": "Male"},
    {"name": "en-US-BrianNeural", "label": "English US - Brian", "locale": "en-US", "gender": "Male"},
    {"name": "en-US-EricNeural", "label": "English US - Eric", "locale": "en-US", "gender": "Male"},
    {"name": "en-US-SteffanNeural", "label": "English US - Steffan", "locale": "en-US", "gender": "Male"},
    {"name": "en-GB-RyanNeural", "label": "English UK - Ryan", "locale": "en-GB", "gender": "Male"},
    {"name": "en-GB-ThomasNeural", "label": "English UK - Thomas", "locale": "en-GB", "gender": "Male"},
    {"name": "en-US-AvaMultilingualNeural", "label": "English US - Ava Multilingual", "locale": "en-US", "gender": "Female"},
    {"name": "en-US-EmmaMultilingualNeural", "label": "English US - Emma Multilingual", "locale": "en-US", "gender": "Female"},
    {"name": "en-US-AriaNeural", "label": "English US - Aria", "locale": "en-US", "gender": "Female"},
    {"name": "en-US-JennyNeural", "label": "English US - Jenny", "locale": "en-US", "gender": "Female"},
]


LANGUAGE_NAMES = {
    "af": "Afrikaans", "am": "Amharic", "ar": "Arabic", "az": "Azerbaijani", "bg": "Bulgarian",
    "bn": "Bengali", "bs": "Bosnian", "ca": "Catalan", "cs": "Czech", "cy": "Welsh",
    "da": "Danish", "de": "German", "el": "Greek", "en": "English", "es": "Spanish",
    "et": "Estonian", "fa": "Persian", "fi": "Finnish", "fil": "Filipino", "fr": "French",
    "ga": "Irish", "gl": "Galician", "gu": "Gujarati", "he": "Hebrew", "hi": "Hindi",
    "hr": "Croatian", "hu": "Hungarian", "id": "Indonesian", "is": "Icelandic", "it": "Italian",
    "ja": "Japanese", "jv": "Javanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
    "kn": "Kannada", "ko": "Korean", "lo": "Lao", "lt": "Lithuanian", "lv": "Latvian",
    "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi", "ms": "Malay",
    "mt": "Maltese", "my": "Burmese", "nb": "Norwegian", "ne": "Nepali", "nl": "Dutch",
    "pl": "Polish", "ps": "Pashto", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali", "sq": "Albanian",
    "sr": "Serbian", "su": "Sundanese", "sv": "Swedish", "sw": "Swahili", "ta": "Tamil",
    "te": "Telugu", "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "uz": "Uzbek", "vi": "Vietnamese", "zh": "Chinese", "zu": "Zulu",
}

REGION_NAMES = {
    "AE": "United Arab Emirates", "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "BE": "Belgium", "BG": "Bulgaria", "BH": "Bahrain", "BO": "Bolivia", "BR": "Brazil",
    "CA": "Canada", "CH": "Switzerland", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "CR": "Costa Rica", "CU": "Cuba", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark",
    "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador", "EG": "Egypt", "ES": "Spain",
    "ET": "Ethiopia", "FI": "Finland", "FR": "France", "GB": "United Kingdom", "GR": "Greece",
    "GT": "Guatemala", "HK": "Hong Kong", "HN": "Honduras", "ID": "Indonesia", "IE": "Ireland",
    "IL": "Israel", "IN": "India", "IQ": "Iraq", "IT": "Italy", "JO": "Jordan", "JP": "Japan",
    "KE": "Kenya", "KR": "South Korea", "KW": "Kuwait", "LB": "Lebanon", "LY": "Libya",
    "MA": "Morocco", "MX": "Mexico", "MY": "Malaysia", "NG": "Nigeria", "NI": "Nicaragua",
    "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand", "OM": "Oman", "PA": "Panama",
    "PE": "Peru", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland", "PR": "Puerto Rico",
    "PT": "Portugal", "PY": "Paraguay", "QA": "Qatar", "RO": "Romania", "RU": "Russia",
    "SA": "Saudi Arabia", "SE": "Sweden", "SG": "Singapore", "SV": "El Salvador", "SY": "Syria",
    "TH": "Thailand", "TN": "Tunisia", "TR": "Turkey", "TW": "Taiwan", "TZ": "Tanzania",
    "UA": "Ukraine", "US": "United States", "UY": "Uruguay", "VE": "Venezuela", "VN": "Vietnam",
    "YE": "Yemen", "ZA": "South Africa",
}


@dataclass
class TTSResult:
    audio_path: str
    subtitle_path: str
    script_path: str
    manifest_path: str
    voice: str
    chars: int


def safe_slug(text: str, fallback: str = "voice_project") -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r'[\\/*?:"<>|]+', "", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    return text or fallback


def extract_voice_id(label: str) -> str:
    match = re.search(r"([a-z]{2}-[A-Z]{2}-[A-Za-z0-9]+(?:Multilingual|Expressive)?Neural)", label or "")
    return match.group(1) if match else (label or "").strip()


def clean_script_for_tts(text: str) -> str:
    text = text or ""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\[TEXT OVERLAY:[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(MUSIC DROP|MUSIC SWELL|BLACK FLASH|SILENCE COMPLETE)[^\]]*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[(PAUSE|CHẬM|CHAM|SLOW)[^\]]*\]", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def list_default_voices():
    return list(DEFAULT_VOICES)


def locale_display(locale: str) -> str:
    parts = (locale or "").split("-")
    if not parts:
        return locale or ""
    lang = LANGUAGE_NAMES.get(parts[0], parts[0])
    region = REGION_NAMES.get(parts[-1], parts[-1]) if len(parts) > 1 else ""
    return f"{lang} ({region})" if region else lang


PREVIEW_TEXT_BY_LANGUAGE = {
    "vi": "Bạn đang tìm kiếm một giải pháp đột phá cho công việc? Đừng chần chừ nữa. Hãy trải nghiệm ngay công nghệ hoàn toàn mới của chúng tôi.",
    "en": "Are you looking for a breakthrough solution for your work? Do not wait. Experience our new technology today.",
    "ar": "هل تبحث عن حل جديد يساعدك في عملك؟ لا تنتظر أكثر. جرّب تقنيتنا الجديدة اليوم واكتشف الفرق بنفسك.",
    "de": "Suchen Sie nach einer neuen Lösung für Ihre Arbeit? Warten Sie nicht länger. Probieren Sie unsere neue Technologie noch heute aus.",
    "fr": "Vous cherchez une solution nouvelle pour votre travail ? N'attendez plus. Essayez notre nouvelle technologie dès aujourd'hui.",
    "es": "¿Buscas una solución innovadora para tu trabajo? No esperes más. Prueba nuestra nueva tecnología hoy mismo.",
    "pt": "Você procura uma solução inovadora para o seu trabalho? Não espere mais. Experimente nossa nova tecnologia hoje.",
    "it": "Cerchi una soluzione innovativa per il tuo lavoro? Non aspettare. Prova oggi la nostra nuova tecnologia.",
    "ru": "Вы ищете новое решение для своей работы? Не откладывайте. Попробуйте нашу новую технологию уже сегодня.",
    "tr": "İşiniz için yeni bir çözüm mü arıyorsunuz? Daha fazla beklemeyin. Yeni teknolojimizi bugün deneyin.",
    "id": "Apakah Anda mencari solusi baru untuk pekerjaan Anda? Jangan menunggu lagi. Coba teknologi baru kami hari ini.",
    "ms": "Adakah anda mencari penyelesaian baharu untuk kerja anda? Jangan tunggu lagi. Cuba teknologi baharu kami hari ini.",
    "th": "คุณกำลังมองหาทางออกใหม่สำหรับงานของคุณอยู่หรือไม่ อย่ารอช้า ลองสัมผัสเทคโนโลยีใหม่ของเราวันนี้",
    "ja": "仕事のための新しい解決策を探していますか。もう迷わないでください。私たちの新しい技術を今すぐ体験してください。",
    "ko": "업무를 위한 새로운 해결책을 찾고 계신가요? 더 이상 망설이지 마세요. 지금 바로 새로운 기술을 경험해 보세요.",
    "zh": "你正在寻找一种突破性的工作解决方案吗？不要再犹豫了。现在就体验我们的全新技术。",
    "hi": "क्या आप अपने काम के लिए एक नया समाधान खोज रहे हैं? अब और इंतज़ार न करें। आज ही हमारी नई तकनीक का अनुभव करें।",
    "bn": "আপনি কি আপনার কাজের জন্য নতুন সমাধান খুঁজছেন? আর অপেক্ষা করবেন না। আজই আমাদের নতুন প্রযুক্তি ব্যবহার করে দেখুন।",
}


def preview_text_for_locale(locale: str) -> str:
    lang = (locale or "").split("-")[0].lower()
    return PREVIEW_TEXT_BY_LANGUAGE.get(lang, PREVIEW_TEXT_BY_LANGUAGE["en"])


def preview_cache_path(voice: str, rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%") -> str:
    voice = extract_voice_id(voice)
    preview_dir = Path("data") / "voice_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preset_key = safe_slug(f"{voice}_{rate}_{pitch}_{volume}")
    return str(preview_dir / f"{preset_key}.mp3")


async def _list_edge_voices_async():
    import edge_tts

    return await edge_tts.list_voices()


def list_edge_voices():
    voices = asyncio.run(_list_edge_voices_async())
    result = []
    for voice in voices:
        short_name = voice.get("ShortName") or voice.get("Name") or ""
        if not short_name:
            continue
        voice_tag = voice.get("VoiceTag") or {}
        categories = voice_tag.get("ContentCategories") or []
        personalities = voice_tag.get("VoicePersonalities") or []
        result.append({
            "name": short_name,
            "label": f"{locale_display(voice.get('Locale', ''))} - {voice.get('Gender', '')}".strip(" -"),
            "friendly_name": voice.get("FriendlyName", ""),
            "locale": voice.get("Locale", ""),
            "locale_display": locale_display(voice.get("Locale", "")),
            "gender": voice.get("Gender", ""),
            "status": voice.get("Status", ""),
            "codec": voice.get("SuggestedCodec", ""),
            "categories": categories,
            "personalities": personalities,
        })
    result.sort(key=lambda item: (item["locale"], item["gender"], item["name"]))
    return result


async def _edge_save_async(text: str, voice: str, audio_path: str, subtitle_path: str,
                           rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%"):
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=rate or "+0%",
        pitch=pitch or "+0Hz",
        volume=volume or "+0%",
    )
    submaker = edge_tts.SubMaker()
    with open(audio_path, "wb") as audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
    with open(subtitle_path, "w", encoding="utf-8") as sub:
        sub.write(submaker.get_srt())


def _run_edge_cli(text_path: str, voice: str, audio_path: str, subtitle_path: str,
                  rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%"):
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--rate", rate or "+0%",
        "--pitch", pitch or "+0Hz",
        "--volume", volume or "+0%",
        "-f", text_path,
        "--write-media", audio_path,
        "--write-subtitles", subtitle_path,
    ]
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(cmd, check=True, startupinfo=startupinfo)


def generate_edge_tts(text: str, output_dir: str, project_name: str,
                      voice: str = "vi-VN-NamMinhNeural",
                      rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%",
                      speed: float = 1.0,
                      use_python_api: bool = True) -> TTSResult:
    clean_text = clean_script_for_tts(text)
    if not clean_text:
        raise ValueError("Script is empty after cleaning TTS markers.")

    voice = extract_voice_id(voice)
    project_slug = safe_slug(project_name)
    out_dir = Path(output_dir or "outputs/voice") / project_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    index = 1
    while (out_dir / f"audio_{index}.mp3").exists():
        index += 1

    script_path = out_dir / f"script_{index}.txt"
    audio_path = out_dir / f"audio_{index}.mp3"
    subtitle_path = out_dir / f"sub_{index}.srt"
    manifest_path = out_dir / f"voice_{index}.json"

    script_path.write_text(clean_text, encoding="utf-8")

    try:
        if use_python_api:
            asyncio.run(_edge_save_async(clean_text, voice, str(audio_path), str(subtitle_path), rate, pitch, volume))
        else:
            _run_edge_cli(str(script_path), voice, str(audio_path), str(subtitle_path), rate, pitch, volume)
    except ImportError:
        _run_edge_cli(str(script_path), voice, str(audio_path), str(subtitle_path), rate, pitch, volume)

    manifest = {
        "provider": "edge-tts",
        "voice": voice,
        "speed": speed,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "notes": "Edge TTS applies voice, speed/rate, pitch, and volume.",
        "chars": len(clean_text),
        "script_path": str(script_path),
        "audio_path": str(audio_path),
        "subtitle_path": str(subtitle_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return TTSResult(
        audio_path=str(audio_path),
        subtitle_path=str(subtitle_path),
        script_path=str(script_path),
        manifest_path=str(manifest_path),
        voice=voice,
        chars=len(clean_text),
    )


def generate_preview_voice(voice: str, text: str, rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%") -> str:
    voice = extract_voice_id(voice)
    preview_dir = Path(tempfile.gettempdir()) / "rx_voice_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preset_key = safe_slug(f"{voice}_{rate}_{pitch}_{volume}")
    path = preview_dir / f"preview_{preset_key}.mp3"
    dummy_sub = preview_dir / f"preview_{preset_key}.srt"
    asyncio.run(_edge_save_async(text, voice, str(path), str(dummy_sub), rate, pitch, volume))
    return str(path)


def generate_cached_preview_voice(voice_info: dict, rate: str = "+0%", pitch: str = "+0Hz", volume: str = "+0%", force: bool = False) -> str:
    voice = extract_voice_id(voice_info.get("name", ""))
    path = preview_cache_path(voice, rate, pitch, volume)
    if os.path.exists(path) and not force:
        return path
    text = preview_text_for_locale(voice_info.get("locale", ""))
    dummy_sub = str(Path(path).with_suffix(".srt"))
    asyncio.run(_edge_save_async(text, voice, path, dummy_sub, rate, pitch, volume))
    return path


def open_file(path: str):
    if not path:
        return
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
