"""
Launch a dedicated Chrome profile for one Google Labs account.

Usage:
    python launch_glabs_account.py acc1
    python launch_glabs_account.py acc2
    python launch_glabs_account.py acc3

Each account uses a separate Chrome user-data-dir and CDP port:
    acc1 -> 9222
    acc2 -> 9223
    acc3 -> 9224
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


FLOW_URL = "https://labs.google/fx/tools/flow"
RX_FLOW_HELPER_DIR = str(Path(__file__).resolve().parent / "extensions" / "rx-flow-helper")

ACCOUNTS = {
    "acc1": {"port": 9222, "profile": Path.home() / "ChromeGLabsProfile_acc1"},
    "acc2": {"port": 9223, "profile": Path.home() / "ChromeGLabsProfile_acc2"},
    "acc3": {"port": 9224, "profile": Path.home() / "ChromeGLabsProfile_acc3"},
}

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


def find_chrome() -> str | None:
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


def launch(account_name: str) -> None:
    account = ACCOUNTS[account_name]
    chrome = find_chrome()
    if not chrome:
        print("ERROR Chrome was not found. Paste the Chrome executable path manually.")
        chrome_manual = input("Chrome path: ").strip()
        if not chrome_manual or not os.path.exists(chrome_manual):
            print("ERROR Invalid Chrome path. Exit.")
            return
        chrome = chrome_manual

    profile_dir = str(account["profile"])
    port = int(account["port"])
    os.makedirs(profile_dir, exist_ok=True)

    cmd = [
        chrome,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if os.path.exists(RX_FLOW_HELPER_DIR):
        cmd.append(f"--load-extension={RX_FLOW_HELPER_DIR}")

    cmd.append(FLOW_URL)

    print(f"Account       : {account_name}")
    print(f"Chrome        : {chrome}")
    print(f"Profile dir   : {profile_dir}")
    print(f"Remote port   : {port}")
    print(f"URL           : {FLOW_URL}")
    if os.path.exists(RX_FLOW_HELPER_DIR):
        print(f"RX Flow Helper: {RX_FLOW_HELPER_DIR}")
    print()
    print("Login steps:")
    print("   1. Log in manually to the Google account for this profile.")
    print("   2. Complete any Google verification in the Chrome window.")
    print("   3. Open Google Labs Flow and confirm it loads.")
    print("   4. Keep this Chrome window open while running automation.")

    subprocess.Popen(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch one Google Labs account profile.")
    parser.add_argument("account", choices=sorted(ACCOUNTS), help="Account profile to launch.")
    args = parser.parse_args()
    launch(args.account)


if __name__ == "__main__":
    main()
