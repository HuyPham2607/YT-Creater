"""
Launch Chrome with remote debugging on port 9222 for Tool 8.
Run this before using the G-Labs automation when Chrome is not already open.
"""

import os
import subprocess
import sys
from pathlib import Path


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

FLOW_URL = "https://labs.google/fx/tools/flow"
PROFILE_DIR = str(Path.home() / "ChromeGLabsProfile")
RX_FLOW_HELPER_DIR = str(Path(__file__).resolve().parent / "extensions" / "rx-flow-helper")


def find_chrome():
    if sys.platform == "win32":
        paths = CHROME_PATHS_WINDOWS
    elif sys.platform == "darwin":
        paths = CHROME_PATHS_MAC
    else:
        paths = CHROME_PATHS_LINUX

    for path in paths:
        if os.path.exists(path):
            return path
    return None


def launch():
    chrome = find_chrome()
    if not chrome:
        print("ERROR Chrome was not found. Paste the Chrome executable path manually.")
        chrome_manual = input("Chrome path: ").strip()
        if not chrome_manual or not os.path.exists(chrome_manual):
            print("ERROR Invalid Chrome path. Exit.")
            return
        chrome = chrome_manual

    os.makedirs(PROFILE_DIR, exist_ok=True)

    cmd = [
        chrome,
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if os.path.exists(RX_FLOW_HELPER_DIR):
        cmd.append(f"--load-extension={RX_FLOW_HELPER_DIR}")

    cmd.append(FLOW_URL)

    print(f"Chrome        : {chrome}")
    print(f"Profile dir   : {PROFILE_DIR}")
    print("Remote port   : 9222")
    print(f"URL           : {FLOW_URL}")
    if os.path.exists(RX_FLOW_HELPER_DIR):
        print(f"RX Flow Helper: {RX_FLOW_HELPER_DIR}")
    print()
    print("IMPORTANT:")
    print("   1. Log in to your Google account in this Chrome window.")
    print("   2. Keep this terminal open while using Tool 8.")
    print("   3. After login, return to the app and run Tool 8.")

    subprocess.Popen(cmd)

    input("\nPress Enter after login is ready...")
    print("Ready. You can now use Tool 8.")


if __name__ == "__main__":
    launch()
