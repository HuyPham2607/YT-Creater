"""
launch_chrome.py — Mở Chrome với remote debugging port 9222
Chạy file này TRƯỚC khi mở glabs_ui.py
"""

import subprocess
import sys
import os
from pathlib import Path


# ──────────────────────────────────────────────
# Đường dẫn Chrome / Chromium phổ biến
# ──────────────────────────────────────────────
CHROME_PATHS_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

CHROME_PATHS_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

CHROME_PATHS_LINUX = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]

# Thư mục profile riêng (tách biệt với Chrome thường để không bị xung đột)
PROFILE_DIR = str(Path.home() / "ChromeGLabsProfile")


def find_chrome():
    if sys.platform == "win32":
        paths = CHROME_PATHS_WINDOWS
    elif sys.platform == "darwin":
        paths = CHROME_PATHS_MAC
    else:
        paths = CHROME_PATHS_LINUX

    for p in paths:
        if os.path.exists(p):
            return p

    return None


def launch():
    chrome = find_chrome()
    if not chrome:
        print("❌ Không tìm thấy Chrome. Hãy cung cấp đường dẫn thủ công.")
        chrome_manual = input("Nhập đường dẫn Chrome: ").strip()
        if not chrome_manual or not os.path.exists(chrome_manual):
            print("❌ Đường dẫn không hợp lệ. Thoát.")
            return

        chrome = chrome_manual

    os.makedirs(PROFILE_DIR, exist_ok=True)

    cmd = [
        chrome,
        f"--remote-debugging-port=9222",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://labs.google/fx/tools/flow",   # Mở thẳng trang Flow
    ]

    print(f"🚀 Mở Chrome tại: {chrome}")
    print(f"📁 Profile dir : {PROFILE_DIR}")
    print(f"🔌 Remote port : 9222")
    print(f"🌐 URL         : https://labs.google/fx/tools/flow")
    print()
    print("⚠️  QUAN TRỌNG:")
    print("   1. Đăng nhập Google account trong cửa sổ Chrome vừa mở.")
    print("   2. Sau khi đăng nhập xong, quay lại đây và nhấn Enter.")
    print("   3. Chạy: python glabs_ui.py")

    proc = subprocess.Popen(cmd)

    input("\nNhấn Enter khi đã đăng nhập xong trong Chrome...")
    print("✅ Sẵn sàng! Chạy: python glabs_ui.py")


if __name__ == "__main__":
    launch()