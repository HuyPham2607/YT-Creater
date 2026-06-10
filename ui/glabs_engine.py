"""
glabs_engine.py â€” v7
Root cause fix:
- Flow Ä‘Ã´i khi UPDATE row hiá»‡n táº¡i thay vÃ¬ táº¡o row má»›i
  â†’ khÃ´ng thá»ƒ dÃ¹ng row index Ä‘á»ƒ lá»c "new rows"
  â†’ quay láº¡i dÃ¹ng before_urls Ä‘á»ƒ phÃ¢n biá»‡t áº£nh má»›i (nhÆ° code gá»‘c)

- isBlocked: chá»‰ check row cÃ³ chá»©a áº£nh Má»šI (src khÃ´ng cÃ³ trong before_urls)
  hoáº·c row cÃ³ progress > 0 sau khi submit
  â†’ trÃ¡nh false positive tá»« row cÅ©

- Progress: láº¥y max tá»« Táº¤T Cáº¢ row cÃ³ áº£nh má»›i / Ä‘ang busy
  (khÃ´ng lá»c theo index)

- Äiá»u kiá»‡n thoÃ¡t: giá»¯ relaxed check tá»« v6 nhÆ°ng Ã¡p dá»¥ng Ä‘Ãºng
"""

from playwright.sync_api import sync_playwright, Page
import time, os, re, base64, socket, subprocess, sys, unicodedata, threading
from datetime import datetime
from pathlib import Path

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FLOW_URL      = "https://labs.google/fx/tools/flow"
CDP_ENDPOINT  = "http://127.0.0.1:9222"
GEN_TIMEOUT   = 180
STABLE_WAIT   = 3
BETWEEN_DELAY = 2
RX_FLOW_HELPER_DIR = str(Path(__file__).resolve().parents[1] / "extensions" / "rx-flow-helper")
PROJECT_CREATE_LOCK = threading.Lock()
CHROME_START_LOCK = threading.Lock()
CLAIMED_PROJECT_URLS = set()

CHROME_PATHS_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
PROFILE_DIR = str(Path.home() / "ChromeGLabsProfile")

def is_port_open(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def find_chrome_path():
    if sys.platform == "win32":
        for p in CHROME_PATHS_WINDOWS:
            if os.path.exists(p): return p
    return None

def ensure_chrome_running(log_fn):
    if is_port_open("127.0.0.1", 9222):
        log_fn("Chrome debug is ready.")
        return True
    log_fn("Starting Chrome debug profile...")
    chrome_exe = find_chrome_path()
    if not chrome_exe:
        log_fn("ERROR Chrome executable not found.")
        return False
    os.makedirs(PROFILE_DIR, exist_ok=True)
    cmd = [
        chrome_exe, "--remote-debugging-port=9222", "--remote-allow-origins=*",
        f"--user-data-dir={PROFILE_DIR}", "--no-first-run", "--no-default-browser-check",
    ]
    if os.path.exists(RX_FLOW_HELPER_DIR):
        cmd.append(f"--load-extension={RX_FLOW_HELPER_DIR}")
        log_fn(f"Loading RX Flow Helper extension: {RX_FLOW_HELPER_DIR}")
    cmd.append(FLOW_URL)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        time.sleep(1)
        if is_port_open("127.0.0.1", 9222):
            log_fn("Chrome started.")
            time.sleep(2)
            return True
    log_fn("ERROR Chrome debug port did not open after 10 seconds.")
    return False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SELECTORS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NEW_PROJECT_SELECTORS = [
    'button:has-text("Dá»± Ã¡n má»›i")', 'button:has-text("New project")',
    '[aria-label*="Dá»± Ã¡n má»›i" i]',
]
PROMPT_SELECTORS = [
    'div[role="textbox"]', 'div[contenteditable="true"]',
    'textarea[placeholder*="táº¡o" i]', 'textarea[placeholder*="What do you" i]', 'textarea',
]
SUBMIT_SELECTORS = [
    'button:has(i:text-is("arrow_forward"))', 'button:has(i:text-is("send"))',
    'button:has-text("arrow_forwardTáº¡o")', 'button[type="submit"]:has-text("Táº¡o")',
    'button[type="submit"]:has-text("Create")', '[data-testid*="send"]', '[data-testid*="submit"]',
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# IMAGE SCAN JS â€” v7
# Tráº£ vá» rows vá»›i Ä‘áº§y Ä‘á»§ thÃ´ng tin
# isBlocked KHÃ”NG tá»± quyáº¿t Ä‘á»‹nh â€” caller tá»± kiá»ƒm tra dá»±a vÃ o context
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
IMAGE_SCAN_JS = r"""
() => {
    const rows = [];
    const turnContainers = document.querySelectorAll('div[role="article"], div[data-testid="virtuoso-item-list"] > div[data-index]');

    if (turnContainers.length > 0) {
        turnContainers.forEach((container, index) => {
            const imgs = Array.from(container.querySelectorAll('img, video'))
                .filter(img => img.src && !img.src.startsWith('data:image/svg') && !img.src.includes('.svg') && !img.src.includes('googleusercontent.com'));
            const busyEl = container.querySelector(
                '.generating, .is-generating, [aria-busy="true"], [class*="spinner"], g-progress-circular'
            );

            // Äáº¾M sá»‘ lÆ°á»£ng áº£nh bá»‹ cháº·n trong container NÃ€Y
            const warningIcons = Array.from(container.querySelectorAll('i.google-symbols'))
                .filter(i => i.innerText.trim() === 'warning');
            
            let blockedCount = 0;
            warningIcons.forEach(icon => {
                const pTxt = (icon.parentElement ? icon.parentElement.innerText : "").toLowerCase();
                if (pTxt.includes('vi pháº¡m') || pTxt.includes('khÃ´ng thá»ƒ táº¡o') || pTxt.includes('violate') || pTxt.includes('chÃ­nh sÃ¡ch')) blockedCount++;
            });
            
            // Fallback náº¿u khÃ´ng bÃ³c Ä‘Æ°á»£c text cáº¡nh icon
            if (blockedCount === 0 && warningIcons.length > 0) {
                 const cTxt = (container.innerText || "").toLowerCase();
                 if (cTxt.includes('vi pháº¡m') || cTxt.includes('khÃ´ng thá»ƒ táº¡o') || cTxt.includes('violate') || cTxt.includes('chÃ­nh sÃ¡ch')) blockedCount = warningIcons.length;
            }

            // TRÃCH XUáº¤T PROMPT TEXT Cá»¦A DÃ’NG NÃ€Y
            let promptText = "Unknown Prompt";
            const reuseBtn = container.querySelector('.reuse-prompt-button');
            if (reuseBtn) {
                const btnContainer = reuseBtn.parentElement;
                if (btnContainer && btnContainer.previousElementSibling) {
                    promptText = btnContainer.previousElementSibling.innerText.trim();
                }
            }
            // Fallback náº¿u khÃ´ng tÃ¬m tháº¥y nÃºt reuse
            if (promptText === "Unknown Prompt") {
                const selectable = container.querySelector('[data-allow-text-selection="true"]');
                if (selectable) {
                    const firstDiv = selectable.querySelector('div > div');
                    if (firstDiv) promptText = firstDiv.innerText.trim();
                    else promptText = selectable.innerText.trim().split('\n')[0];
                }
            }

            // Progress
            let progress = 0;
            const pctMatch = container.innerText.match(/(\d+)%/);
            if (pctMatch) progress = parseInt(pctMatch[1]);
            else if (busyEl) {
                const av = busyEl.getAttribute('aria-valuenow');
                if (av) progress = parseInt(av);
            }

            const imageData = imgs.map(img => {
                const style = window.getComputedStyle(img);
                const w = img.naturalWidth || img.videoWidth || 0;
                const h = img.naturalHeight || img.videoHeight || 0;
                const opacity = parseFloat(style.opacity);
                const hasBlur = style.filter.includes('blur');
                const isReady = !busyEl && opacity > 0.9 && !hasBlur && w > 100 && h > 100;
                const isReadyRelaxed = (w > 50 || img.width > 50) && !hasBlur;
                return { src: img.src, isReady, isReadyRelaxed, tag: img.tagName.toLowerCase() };
            });

            rows.push({
                rowIndex: index,
                count: imgs.length,
                images: imageData,
                progress,
                blockedCount,
                isBusy: !!busyEl,
                promptText: promptText
            });
        });
    }

    // Fallback: khÃ´ng cÃ³ role="article"
    // Chá»‰ dÃ¹ng fallback náº¿u hoÃ n toÃ n khÃ´ng tÃ¬m tháº¥y danh sÃ¡ch chá»©a áº£nh
    if (rows.length === 0 && document.querySelectorAll('div[data-testid="virtuoso-item-list"]').length === 0) {
        let globalProg = 0;
        const progressEls = document.querySelectorAll(
            '[aria-busy="true"], [class*="spinner"], [role="progressbar"], .generating, g-progress-circular'
        );
        const isBusyGlobal = progressEls.length > 0;
        const allText = document.body.innerText.match(/(\d+)%/g);
        if (allText) allText.forEach(m => { const v = parseInt(m); if (v > globalProg && v <= 100) globalProg = v; });

        const allImgs = Array.from(document.querySelectorAll('img, video'))
            .filter(i => (i.width > 50 || i.videoWidth > 50) && !i.src.startsWith('data:image/svg') && !i.src.includes('.svg') && !i.src.includes('googleusercontent.com'));

        if (allImgs.length > 0 || globalProg > 0) {
            rows.push({
                rowIndex: 0,
                count: allImgs.length,
                images: allImgs.map(img => {
                    const w = img.naturalWidth || img.videoWidth || 0;
                    const style = window.getComputedStyle(img);
                    const hasBlur = style.filter.includes('blur');
                    return {
                        src: img.src,
                        isReady: !isBusyGlobal && w > 100 && !hasBlur,
                        isReadyRelaxed: (w > 50 || img.width > 50) && !hasBlur,
                        tag: img.tagName.toLowerCase()
                    };
                }),
                progress: globalProg,
                isBusy: isBusyGlobal,
                blockedCount: 0,
                promptText: "Unknown Prompt"
            });
        }
    }
    return rows;
}
"""

GET_ALL_URLS_JS = """
() => Array.from(document.querySelectorAll('img, video'))
    .map(i => i.src)
    .filter(s => s && !s.startsWith('data:image/svg') && !s.includes('.svg') && !s.includes('googleusercontent.com'))
"""


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HELPERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def find_el(page: Page, selectors: list, timeout=5000):
    combined_sel = ", ".join(selectors)
    try:
        el = page.wait_for_selector(combined_sel, timeout=timeout, state="visible")
        if el: return el, "combined"
    except Exception:
        pass
    return None, None


def wait_for_project_page(page: Page, log_fn=print, timeout=20) -> bool:
    log_fn("   Waiting for project page...")
    deadline = time.time() + timeout
    signals = ['text="NhÃ¢n váº­t"', 'text="Characters"', 'div[role="textbox"]', 'text="Cáº£nh"']
    while time.time() < deadline:
        if "/project/" not in page.url:
            time.sleep(0.8)
            continue
        log_fn(f"   Project URL detected: {page.url}")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        for sig in signals:
            try:
                el = page.query_selector(sig)
                if el and el.is_visible():
                    log_fn(f"   Project page ready ({sig})")
                    return True
            except Exception:
                pass
        log_fn("   Project page ready (URL confirmed)")
        return True
        time.sleep(0.8)
    log_fn(f"   ERROR project page not detected. Current URL: {page.url}")
    return False


def find_project_page(context, exclude_urls: set[str] | None = None):
    exclude_urls = exclude_urls or set()
    for candidate in reversed(context.pages):
        try:
            if "/project/" in candidate.url and candidate.url not in exclude_urls:
                return candidate
        except Exception:
            pass
    return None


def scan_project_urls(page: Page) -> list[str]:
    try:
        return page.evaluate(r"""() => {
            const urls = [];
            document.querySelectorAll('a[href*="/project/"]').forEach(a => {
                if (a.href) urls.push(a.href);
            });
            document.querySelectorAll('[data-href*="/project/"], [href*="/project/"]').forEach(el => {
                const href = el.getAttribute('href') || el.getAttribute('data-href');
                if (href) urls.push(new URL(href, location.href).href);
            });
            return [...new Set(urls)];
        }""") or []
    except Exception:
        return []


def click_new_project_button(page: Page, log_fn=print, timeout: int = 15) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            clicked = page.evaluate(r"""() => {
                const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                };
                const candidates = Array.from(document.querySelectorAll('button, a, div[role="button"]'))
                    .filter(visible)
                    .map(el => ({
                        el,
                        text: (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim(),
                        aria: el.getAttribute('aria-label') || '',
                    }));
                const target = candidates.find(({ text, aria }) => {
                    const hay = `${text} ${aria}`.toLowerCase();
                    return hay.includes('dự án mới') ||
                           hay.includes('du an moi') ||
                           hay.includes('new project') ||
                           hay.includes('+ dự án') ||
                           hay.includes('+ du an');
                }) || candidates.find(({ text, aria }) => {
                    const hay = `${text} ${aria}`.toLowerCase();
                    return hay.includes('project') && (hay.includes('new') || hay.includes('+'));
                });
                if (!target) return null;
                target.el.setAttribute('data-rx-new-project', 'true');
                return target.text || target.aria || 'new project button';
            }""")
            if clicked:
                page.click('[data-rx-new-project="true"]', force=True, timeout=5000)
                log_fn(f"   New project clicked: '{clicked[:60]}'")
                return True
        except Exception as e:
            log_fn(f"   WARN new project click attempt failed: {e}")
        time.sleep(1.0)
    log_fn("   ERROR new project button not found.")
    return False


def create_and_claim_project_from_landing(page: Page, log_fn=print, worker_id: int = 1):
    log_fn("   Creating new Flow project from landing...")
    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    before_urls = set(scan_project_urls(page))
    log_fn(f"   Existing project link(s) before create: {len(before_urls)}")

    if not click_new_project_button(page, log_fn):
        return None

    time.sleep(4)
    try:
        if "/project/" in page.url:
            log_fn("   Create click navigated directly into a project; returning to landing to claim URL.")
    except Exception:
        pass

    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    deadline = time.time() + 30
    while time.time() < deadline:
        urls = scan_project_urls(page)
        new_urls = [u for u in urls if u not in before_urls]
        unclaimed_new = [u for u in new_urls if u not in CLAIMED_PROJECT_URLS]
        unclaimed_any = [u for u in urls if u not in CLAIMED_PROJECT_URLS]
        chosen = unclaimed_new[0] if unclaimed_new else (unclaimed_any[0] if unclaimed_any else None)
        log_fn(
            f"   Project links after create: total={len(urls)} new={len(new_urls)} "
            f"claimed={len(CLAIMED_PROJECT_URLS)}"
        )
        if chosen:
            CLAIMED_PROJECT_URLS.add(chosen)
            log_fn(f"   Worker {worker_id} claimed project: {chosen}")
            page.goto(chosen, wait_until="domcontentloaded", timeout=30000)
            wait_for_project_page(page, log_fn, timeout=10)
            return page
        time.sleep(2)
        try:
            page.reload(wait_until="domcontentloaded", timeout=20000)
        except Exception:
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
    log_fn("   ERROR could not claim a unique project URL after create.")
    return None


def click_new_project(page: Page, log_fn=print, timeout: int = 20):
    log_fn("   Creating new Flow project...")
    before_project_urls = {
        p.url for p in page.context.pages
        if "/project/" in p.url
    }
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            clicked = page.evaluate(r"""() => {
                const visible = (el) => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                };
                const candidates = Array.from(document.querySelectorAll('button, a, div[role="button"]'))
                    .filter(visible)
                    .map(el => ({
                        el,
                        text: (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim(),
                        aria: el.getAttribute('aria-label') || '',
                    }));
                const target = candidates.find(({ text, aria }) => {
                    const hay = `${text} ${aria}`.toLowerCase();
                    return hay.includes('dự án mới') ||
                           hay.includes('du an moi') ||
                           hay.includes('new project') ||
                           hay.includes('+ dự án') ||
                           hay.includes('+ du an');
                }) || candidates.find(({ text, aria }) => {
                    const hay = `${text} ${aria}`.toLowerCase();
                    return hay.includes('project') && (hay.includes('new') || hay.includes('+'));
                });
                if (!target) return null;
                target.el.setAttribute('data-rx-new-project', 'true');
                return target.text || target.aria || 'new project button';
            }""")
            if clicked:
                page.click('[data-rx-new-project="true"]', force=True, timeout=5000)
                log_fn(f"   New project clicked: '{clicked[:60]}'")
                inner_deadline = time.time() + 30
                while time.time() < inner_deadline:
                    if "/project/" in page.url:
                        wait_for_project_page(page, log_fn, timeout=5)
                        return page
                    project_page = find_project_page(page.context, before_project_urls)
                    if project_page:
                        try:
                            project_page.bring_to_front()
                        except Exception:
                            pass
                        log_fn(f"   Project opened in tab: {project_page.url}")
                        wait_for_project_page(project_page, log_fn, timeout=5)
                        return project_page
                    project_urls = [u for u in scan_project_urls(page) if u not in before_project_urls]
                    if project_urls:
                        project_url = project_urls[0]
                        log_fn(f"   Project link appeared after create: {project_url}")
                        page.goto(project_url, wait_until="domcontentloaded", timeout=30000)
                        wait_for_project_page(page, log_fn, timeout=10)
                        return page
                    time.sleep(0.8)
                log_fn(f"   WARN new project click did not expose a project URL yet. Current URL: {page.url}")
        except Exception as e:
            log_fn(f"   WARN new project click attempt failed: {e}")
        time.sleep(1.0)
    log_fn("   ERROR new project button not found.")
    return None


def enter_project(page: Page, log_fn=print, force_new: bool = False, worker_id: int = 1):
    log_fn("   Finding Flow project...")
    time.sleep(2)
    if force_new:
        log_fn("   Waiting for project creation slot...")
        with PROJECT_CREATE_LOCK:
            log_fn("   Project creation slot acquired.")
            try:
                return create_and_claim_project_from_landing(page, log_fn, worker_id=worker_id)
            except Exception as e:
                log_fn(f"   ERROR create/claim project failed: {e}")
                return None

    js = """() => {
        const res = [];
        document.querySelectorAll('a').forEach(a => {
            const h = a.href || '';
            if (h.includes('/project/') && h.length > 50) res.push(h);
        });
        return [...new Set(res)].slice(0, 5);
    }"""
    try:
        urls = page.evaluate(js)
        log_fn(f"   Found {len(urls)} project URL(s).")
        if urls:
            log_fn(f"   Opening project: {urls[0][:80]}")
            page.goto(urls[0], wait_until="domcontentloaded", timeout=20000)
            return page if wait_for_project_page(page, log_fn) else None
    except Exception as e:
        log_fn(f"   WARN project scan failed: {e}")
    return click_new_project(page, log_fn)


def fill_prompt(page: Page, prompt: str, log_fn=print) -> bool:
    el, _ = find_el(page, PROMPT_SELECTORS, timeout=10000)
    if not el:
        log_fn("   ERROR prompt input not found.")
        return False
    log_fn("   Prompt filled.")
    try:
        el.click(); time.sleep(0.3)
        page.keyboard.press("Control+a"); time.sleep(0.1)
        page.keyboard.press("Backspace"); time.sleep(0.2)
        el.type(prompt, delay=30); time.sleep(0.5)
        return True
    except Exception as e:
        log_fn(f"   ERROR fill prompt failed: {e}")
        return False


def click_submit(page: Page, log_fn=print) -> bool:
    try:
        page.keyboard.press("Escape")
        time.sleep(0.3)
    except Exception:
        pass

    el, _ = find_el(page, SUBMIT_SELECTORS, timeout=5000)
    if el:
        log_fn("   Submit clicked.")
        el.click(force=True)
        return True
    log_fn("   Submit fallback via JS...")
    try:
        clicked = page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button[type="submit"]')]
                .filter(b => b.offsetParent !== null);
            if (btns.length > 0) {
                btns[btns.length - 1].click();
                return btns[btns.length - 1].textContent.trim();
            }
            return null;
        }""")
        if clicked:
            log_fn(f"   JS submit clicked: '{clicked[:30]}'"); return True
    except Exception as e:
        log_fn(f"   WARN JS submit error: {e}")
    try:
        clicked = page.evaluate(r"""() => {
            const visible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            };
            const boxes = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], [role="textbox"]')).filter(visible);
            const promptBox = boxes[boxes.length - 1];
            const promptRect = promptBox ? promptBox.getBoundingClientRect() : null;
            const buttons = Array.from(document.querySelectorAll('button, [role="button"]')).filter(visible);
            const candidates = buttons.map((button) => {
                const rect = button.getBoundingClientRect();
                const txt = (button.innerText || button.textContent || button.getAttribute('aria-label') || '').toLowerCase();
                const icon = txt.includes('arrow') || txt.includes('send') || txt.includes('tạo') || txt.includes('generate') || txt.includes('play_arrow');
                const nearComposer = !promptRect || (
                    rect.top >= promptRect.top - 80 &&
                    rect.bottom <= promptRect.bottom + 90 &&
                    rect.left >= promptRect.right - 160
                );
                const circular = Math.abs(rect.width - rect.height) < 18 && rect.width >= 32 && rect.width <= 72;
                let score = 0;
                if (nearComposer) score += 50;
                if (circular) score += 20;
                if (icon) score += 15;
                score += rect.left / 10000;
                return { button, score, txt };
            }).filter(item => item.score >= 50);
            candidates.sort((a, b) => b.score - a.score);
            const target = candidates[0]?.button;
            if (!target) return null;
            target.click();
            return candidates[0].txt || 'composer arrow';
        }""")
        if clicked:
            log_fn(f"   Submit clicked via composer arrow: '{str(clicked)[:30]}'")
            return True
    except Exception as e:
        log_fn(f"   WARN composer arrow submit error: {e}")
    log_fn("   Submit fallback via Enter.")
    page.keyboard.press("Enter")
    return True


def normalize_ref_key(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def list_reference_images(reference_dir: str) -> list[Path]:
    if not reference_dir:
        return []
    root = Path(reference_dir)
    if not root.exists() or not root.is_dir():
        return []
    return [
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]


def resolve_reference_images(prompt: str, reference_dir: str, reference_mode: str, max_files: int = 10) -> list[str]:
    images = list_reference_images(reference_dir)
    if not images or reference_mode == "None":
        return []

    if reference_mode == "Use all images in folder":
        return [str(path) for path in images[:max_files]]

    prompt_key = normalize_ref_key(prompt)
    prompt_compact = prompt_key.replace("-", "")
    matched = []
    for path in images:
        stem_key = normalize_ref_key(path.stem)
        stem_compact = stem_key.replace("-", "")
        if stem_key and (
            stem_key in prompt_key
            or prompt_key in stem_key
            or stem_compact in prompt_compact
            or prompt_compact in stem_compact
        ):
            matched.append(str(path))

    return matched[:max_files]


def ref_cache_key(path: str) -> str:
    try:
        return str(Path(path).resolve()).lower()
    except Exception:
        return str(path).lower()


def upload_reference_images(page: Page, image_paths: list[str], log_fn=print) -> bool:
    valid_paths = [p for p in image_paths if p and os.path.exists(p)]
    if not valid_paths:
        return True

    log_fn(f"   Upload reference: {len(valid_paths)} image(s)")

    try:
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0:
            file_input.set_input_files(valid_paths)
            time.sleep(2)
            log_fn("   Reference uploaded via existing file input.")
            return True
    except Exception as e:
            log_fn(f"   WARN existing file input upload failed: {e}")

    upload_button_selectors = [
        'button:has-text("Add image")',
        'button:has-text("Upload")',
        'button:has-text("Reference")',
        'button:has-text("ThÃªm áº£nh")',
        'button:has-text("Táº£i lÃªn")',
        'button[aria-label*="image" i]',
        'button[aria-label*="upload" i]',
        'button[aria-label*="reference" i]',
        'button:has(i:text-is("add_photo_alternate"))',
        'button:has(i:text-is("image"))',
        'button:has(i:text-is("attach_file"))',
    ]

    for selector in upload_button_selectors:
        try:
            button = page.locator(selector).first
            if button.count() == 0:
                continue
            with page.expect_file_chooser(timeout=5000) as chooser_info:
                button.click(force=True)
            chooser_info.value.set_files(valid_paths)
            time.sleep(2)
            log_fn(f"   Reference uploaded via selector: {selector}")
            return True
        except Exception:
            continue

    try:
        page.evaluate(
            """() => {
                const candidates = Array.from(document.querySelectorAll('button'))
                  .filter(b => b.offsetParent !== null)
                  .filter(b => {
                    const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').toLowerCase();
                    return txt.includes('image') || txt.includes('upload') || txt.includes('reference') ||
                           txt.includes('áº£nh') || txt.includes('táº£i lÃªn');
                  });
                if (candidates[0]) {
                  candidates[0].setAttribute('data-rx-upload-reference', 'true');
                  return true;
                }
                return false;
            }"""
        )
        with page.expect_file_chooser(timeout=5000) as chooser_info:
            page.click('[data-rx-upload-reference="true"]', force=True)
        chooser_info.value.set_files(valid_paths)
        time.sleep(2)
        log_fn("   Reference uploaded via fallback button.")
        return True
    except Exception as e:
        log_fn(f"   WARN could not upload reference image(s): {e}")
        return False


def wait_for_upload_idle(page: Page, log_fn=print, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    last_state = None
    while time.time() < deadline:
        try:
            state = page.evaluate(
                """() => {
                    const text = (document.body.innerText || '').toLowerCase();
                    const pct = text.match(/\\b\\d{1,3}%\\b/);
                    const busyWords = ['uploading', 'Ä‘ang táº£i', 'táº£i lÃªn', 'processing', 'Ä‘ang xá»­ lÃ½'];
                    const busy = !!pct || busyWords.some(w => text.includes(w));
                    return { busy, pct: pct ? pct[0] : '' };
                }"""
            )
            current = state.get("pct") or ("busy" if state.get("busy") else "idle")
            if current != last_state and state.get("busy"):
                log_fn(f"   â³ Reference upload still processing: {current}")
                last_state = current
            if not state.get("busy"):
                return True
        except Exception:
            return True
        time.sleep(1.0)

    log_fn("   âš ï¸ Reference upload wait timed out; trying to attach anyway.")
    return False


def open_reference_picker(page: Page, log_fn=print) -> bool:
    try:
        opened = page.evaluate(
            """() => {
                const visible = (el) => {
                    if (!el) return false;
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const textOf = (el) => (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().toLowerCase();
                const boxes = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], [role="textbox"]')).filter(visible);
                const promptBox = boxes[boxes.length - 1];
                const promptRect = promptBox ? promptBox.getBoundingClientRect() : null;
                const buttons = Array.from(document.querySelectorAll('button, [role="button"]')).filter(visible);
                const candidates = buttons.filter((button) => {
                    const rect = button.getBoundingClientRect();
                    const text = textOf(button);
                    const isPlus = text === '+' || text.includes('add') || text.includes('them') || text.includes('thêm');
                    if (!isPlus) return false;
                    if (!promptRect) return rect.top > window.innerHeight * 0.55;
                    const nearPromptY = rect.top >= promptRect.top - 80 && rect.bottom <= promptRect.bottom + 80;
                    return nearPromptY;
                });
                let target = null;
                if (candidates.length) {
                    const scored = candidates.map((button) => {
                        const rect = button.getBoundingClientRect();
                        const insideMedia = !!button.closest('img, video, [data-rx-reference-result]');
                        const overlapsPromptInput = promptRect && rect.left >= promptRect.left && rect.right <= promptRect.right;
                        const leftComposerAdd = promptRect && rect.right <= promptRect.left + 90;
                        let score = 0;
                        if (leftComposerAdd) score += 100;
                        if (!insideMedia) score += 20;
                        if (!overlapsPromptInput) score += 10;
                        score -= Math.abs(rect.top - (promptRect ? promptRect.top : rect.top)) / 100;
                        return { button, score, left: rect.left };
                    });
                    scored.sort((a, b) => b.score - a.score || a.left - b.left);
                    target = scored[0].button;
                }
                target = target || buttons.reverse().find((button) => {
                    const rect = button.getBoundingClientRect();
                    const text = textOf(button);
                    return rect.top > window.innerHeight * 0.65 && (text === '+' || text.includes('add') || text.includes('them') || text.includes('thêm'));
                });
                if (!target) return false;
                target.setAttribute('data-rx-open-reference-picker', 'true');
                return true;
            }"""
        )
        if opened:
            page.click('[data-rx-open-reference-picker="true"]', force=True)
            time.sleep(0.8)
            if get_reference_search_input(page) is not None:
                return True
    except Exception as e:
        log_fn(f"   WARN could not open reference picker near prompt: {e}")

    plus_selectors = [
        'button:has-text("+")',
        'button[aria-label*="add" i]',
        'button[aria-label*="thÃªm" i]',
        'button:has(i:text-is("add"))',
        'button:has(i:text-is("add_circle"))',
    ]

    for selector in plus_selectors:
        try:
            candidates = page.locator(selector)
            count = candidates.count()
            for idx in range(min(count, 8)):
                button = candidates.nth(count - 1 - idx)
                if not button.is_visible():
                    continue
                button.click(force=True)
                time.sleep(0.8)
                if get_reference_search_input(page) is not None:
                    return True
        except Exception:
            continue

    try:
        opened = page.evaluate(
            """() => {
                const buttons = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null);
                const target = buttons.reverse().find(b => {
                    const txt = (b.innerText || b.textContent || b.getAttribute('aria-label') || '').trim().toLowerCase();
                    return txt === '+' || txt.includes('add') || txt.includes('thÃªm');
                });
                if (!target) return false;
                target.setAttribute('data-rx-open-reference-picker', 'true');
                return true;
            }"""
        )
        if opened:
            page.click('[data-rx-open-reference-picker="true"]', force=True)
            time.sleep(0.8)
            return True
    except Exception as e:
        log_fn(f"   WARN could not open reference picker: {e}")

    log_fn("   WARN could not open reference picker with plus button.")
    return False


def get_reference_search_input(page: Page):
    try:
        handle = page.evaluate_handle(
            """() => {
                const visible = (el) => {
                    if (!el) return false;
                    const r = el.getBoundingClientRect();
                    const s = window.getComputedStyle(el);
                    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden';
                };
                const norm = (text) => (text || '').trim().toLowerCase();
                const inputs = Array.from(document.querySelectorAll('input[type="search"], [role="searchbox"], input')).filter((el) => {
                    return visible(el) && !el.disabled && !el.readOnly;
                });
                const pickerWords = ['tất cả', 'tat ca', 'hình ảnh', 'hinh anh', 'video', 'giọng nói', 'giong noi', 'tệp tải lên', 'tep tai len', 'thêm vào câu lệnh', 'them vao cau lenh', 'add to prompt'];
                const scored = inputs.map((input, index) => {
                    let node = input;
                    let best = 0;
                    for (let depth = 0; depth < 8 && node && node !== document.body; depth += 1) {
                        const rect = node.getBoundingClientRect();
                        const text = norm(node.innerText || node.textContent);
                        const wordScore = pickerWords.reduce((sum, word) => sum + (text.includes(word) ? 1 : 0), 0);
                        const modalLike = rect.width > 380 && rect.height > 260 && rect.top > 80 && rect.bottom < window.innerHeight - 20;
                        const overlayLike = rect.width > 380 && rect.height > 260 && rect.left > 40 && rect.right < window.innerWidth - 40;
                        const score = wordScore * 10 + (modalLike ? 3 : 0) + (overlayLike ? 2 : 0) + rect.top / 10000;
                        if (score > best) best = score;
                        node = node.parentElement;
                    }
                    return { input, index, best };
                }).filter((item) => item.best >= 10);
                scored.sort((a, b) => b.best - a.best || b.index - a.index);
                return scored.length ? scored[0].input : null;
            }"""
        )
        element = handle.as_element()
        if element:
            return element
    except Exception:
        pass

    selectors = [
        'input[type="search"]',
        '[role="searchbox"]',
        'input[placeholder*="search" i]',
        'input[placeholder*="tìm" i]',
        'input[placeholder*="tim" i]',
        'input',
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = locator.count()
            for idx in range(min(count, 8)):
                candidate = locator.nth(idx)
                if candidate.is_visible() and candidate.is_enabled():
                    return candidate
        except Exception:
            continue
    return None


def click_add_reference_to_prompt(page: Page, log_fn=print, timeout: int = 45) -> bool:
    deadline = time.time() + timeout
    selectors = [
        'button:has-text("Thêm vào câu lệnh")',
        '[role="button"]:has-text("Thêm vào câu lệnh")',
        'button:has-text("Add to prompt")',
        '[role="button"]:has-text("Add to prompt")',
    ]

    while time.time() < deadline:
        for selector in selectors:
            try:
                button = page.locator(selector).first
                if button.count() > 0 and button.is_visible() and button.is_enabled():
                    button.click(force=True)
                    time.sleep(0.8)
                    return True
            except Exception:
                continue

        try:
            clicked = page.evaluate(
                """() => {
                    const nodes = Array.from(document.querySelectorAll('button, [role="button"], div, span'))
                      .filter(el => el.offsetParent !== null);
                    const target = nodes.find(el => {
                        const txt = (el.innerText || el.textContent || '').trim().toLowerCase();
                        if (!txt) return false;
                        return txt === 'thêm vào câu lệnh' ||
                               txt.includes('thêm vào câu lệnh') ||
                               txt === 'add to prompt' ||
                               txt.includes('add to prompt');
                    });
                    if (!target) return false;
                    target.setAttribute('data-rx-add-reference-to-prompt', 'true');
                    return true;
                }"""
            )
            if clicked:
                page.click('[data-rx-add-reference-to-prompt="true"]', force=True)
                time.sleep(0.8)
                return True
        except Exception:
            pass

        time.sleep(0.8)

    log_fn("   WARN add-to-prompt button not found after selecting reference.")
    return False


def count_composer_reference_thumbs(page: Page) -> int:
    try:
        return int(page.evaluate(r"""() => {
            const visible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            };
            const boxes = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], [role="textbox"]')).filter(visible);
            const promptBox = boxes[boxes.length - 1];
            const promptRect = promptBox ? promptBox.getBoundingClientRect() : null;
            const imgs = Array.from(document.querySelectorAll('img')).filter(img => {
                if (!visible(img)) return false;
                const rect = img.getBoundingClientRect();
                const src = img.currentSrc || img.src || '';
                if (!src || src.startsWith('data:image/svg') || src.includes('.svg')) return false;
                if (img.naturalWidth < 20 && img.width < 20) return false;
                if (img.naturalHeight < 20 && img.height < 20) return false;
                if (!promptRect) return rect.top > window.innerHeight * 0.55;
                const nearComposer =
                    rect.bottom >= promptRect.top - 140 &&
                    rect.top <= promptRect.bottom + 80 &&
                    rect.left >= promptRect.left - 40 &&
                    rect.right <= promptRect.right + 80;
                return nearComposer;
            });
            return imgs.length;
        }""") or 0)
    except Exception:
        return 0


def attach_reference_with_extension(page: Page, image_path: str, log_fn=print, timeout_ms: int = 300000) -> bool | None:
    basename = os.path.basename(image_path)
    try:
        helper_ready = page.evaluate("() => !!window.rxFlowHelper && typeof window.rxFlowHelper.attachReference === 'function'")
    except Exception:
        helper_ready = False

    if not helper_ready:
        log_fn("   RX Flow Helper extension is not available; using Playwright fallback.")
        log_fn("   TIP Close the Chrome debug window and rerun Tool 8 once to load the extension.")
        return None

    log_fn(f"   RX Flow Helper attaching reference: {basename}")
    try:
        result = page.evaluate(
            """async ({ filename, timeoutMs }) => {
                return await window.rxFlowHelper.attachReference(filename, { timeoutMs });
            }""",
            {"filename": basename, "timeoutMs": timeout_ms},
        )
    except Exception as exc:
        log_fn(f"   WARN RX Flow Helper attach failed: {exc}")
        return False

    if result and result.get("ok"):
        log_fn(f"   OK RX Flow Helper attached reference: {basename}")
        return True

    log_fn(f"   WARN RX Flow Helper could not attach reference: {result}")
    return False


def attach_reference_image_to_prompt(page: Page, image_path: str, log_fn=print, timeout: int = 300) -> bool:
    extension_result = attach_reference_with_extension(page, image_path, log_fn, timeout * 1000)
    if extension_result is not None:
        return extension_result

    basename = os.path.basename(image_path)
    stem = os.path.splitext(basename)[0]
    selected = False
    deadline = time.time() + timeout
    attempt = 0
    queries = (stem, basename)
    search_input = None
    before_thumb_count = count_composer_reference_thumbs(page)
    log_fn(f"   Composer reference count before attach: {before_thumb_count}")

    while time.time() < deadline and not selected:
        if attempt == 0 or attempt % 12 == 0:
            try:
                page.keyboard.press("Escape")
                time.sleep(0.5)
            except Exception:
                pass
            if not open_reference_picker(page, log_fn):
                time.sleep(2.0)
                attempt += 1
                continue
            search_input = get_reference_search_input(page)
            if search_input is None:
                log_fn("   WARN Reference picker opened but search input was not found.")
                time.sleep(2.0)
                attempt += 1
                continue

        query = queries[attempt % len(queries)]
        attempt += 1
        try:
            search_input.click()
            page.keyboard.press("Control+a")
            page.keyboard.press("Backspace")
            search_input.fill(query)
            time.sleep(2.0)

            found = page.evaluate(
                """(q) => {
                    const ql = q.toLowerCase();
                    const nodes = Array.from(document.querySelectorAll('[role="option"], [role="listitem"], button, div'))
                      .filter(el => el.offsetParent !== null);
                    const target = nodes.find(el => {
                        const txt = (el.innerText || el.textContent || '').toLowerCase();
                        const stillUploading =
                            /\\b\\d{1,3}%\\b/.test(txt) ||
                            txt.includes('uploading') ||
                            txt.includes('dang tai') ||
                            txt.includes('đang tải') ||
                            txt.includes('tai len') ||
                            txt.includes('tải lên');
                        if (stillUploading) return false;
                        const textMatches = txt.includes(ql) && (
                            txt.includes('hinh') || txt.includes('hình') || txt.includes('image') ||
                            txt.includes('.png') || txt.includes('.jpg') ||
                            txt.includes('.jpeg') || txt.includes('.webp')
                        );
                        if (!textMatches) return false;
                        const imgs = Array.from(el.querySelectorAll('img'));
                        const hasLoadedThumb = imgs.some(img => {
                            const style = window.getComputedStyle(img);
                            const src = img.currentSrc || img.src || '';
                            return src &&
                                !src.startsWith('data:image/svg') &&
                                !src.includes('.svg') &&
                                (img.naturalWidth > 40 || img.width > 40) &&
                                (img.naturalHeight > 40 || img.height > 40) &&
                                parseFloat(style.opacity || '1') > 0.5 &&
                                !style.filter.includes('blur');
                        });
                        return hasLoadedThumb;
                    });
                    if (!target) return false;
                    target.setAttribute('data-rx-reference-result', 'true');
                    return true;
                }""",
                query,
            )
            if found:
                page.click('[data-rx-reference-result="true"]', force=True)
                time.sleep(1.2)
                after_select_count = count_composer_reference_thumbs(page)
                if after_select_count > before_thumb_count:
                    log_fn(
                        f"   OK Reference attached after selection: {basename} "
                        f"({before_thumb_count}->{after_select_count})"
                    )
                    try:
                        page.keyboard.press("Escape")
                    except Exception:
                        pass
                    return True
                selected = True
                break
            if attempt == 1 or attempt % 20 == 0:
                log_fn(f"   WAIT reference asset not ready yet: {basename}")
        except Exception:
            time.sleep(1.0)

    if not selected:
        log_fn(f"   WARN Reference asset not found in picker: {basename}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False

    for add_attempt in range(2):
        if click_add_reference_to_prompt(page, log_fn, timeout=45):
            log_fn(f"   OK Attached reference to prompt: {basename}")
            return True
        after_thumb_count = count_composer_reference_thumbs(page)
        if after_thumb_count > before_thumb_count:
            log_fn(
                f"   OK Reference appears attached without add button: {basename} "
                f"({before_thumb_count}->{after_thumb_count})"
            )
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return True
        log_fn(f"   WAIT add-to-prompt retry {add_attempt + 1}/2 for reference: {basename}")
        time.sleep(2.0)

    log_fn(f"   WARN Add-to-prompt failed for reference: {basename}")
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return False

def setup_flow_options(page: Page, expected_images: int, aspect_ratio: str, model: str,
                       output_type: str, seed: str = None, log_fn=print):
    log_fn(f"   Settings: {output_type} | {expected_images} images | {aspect_ratio} | {model} | Seed: {seed or 'Auto'}")
    target_count = str(expected_images)
    ratio_map = {
        "16:9 Ngang": "16:9", "9:16 Dá»c": "9:16", "1:1 VuÃ´ng": "1:1", "4:3": "4:3", "3:4": "3:4",
    }
    web_ratio = ratio_map.get(aspect_ratio, aspect_ratio)

    try:
        # BÆ°á»›c 1: TÃ¬m vÃ  Click nÃºt Settings báº±ng Playwright Native Click
        # TÃ¬m nÃºt cÃ³ text chá»©a thÃ´ng tin model/crop vÃ  gÃ¡n cho nÃ³ 1 ID táº¡m thá»i Ä‘á»ƒ Playwright click chÃ­nh xÃ¡c
        btn_info = page.evaluate(r"""() => {
            const btns = Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null);
            let target = btns.find(b => {
                const txt = b.textContent || '';
                return (txt.includes('Banana') || txt.includes('Imagen')) && (txt.includes('crop_') || txt.includes('x'));
            });
            if (!target) {
                target = btns.find(b => b.querySelector('i.google-symbols') && (b.innerText.includes('16:9') || b.innerText.includes('Banana')));
            }
            
            if (target) {
                target.setAttribute('data-qa-settings-trigger', 'true');
                return target.textContent.trim();
            }
            return null;
        }""")

        if btn_info:
            # Thá»±c hiá»‡n click tháº­t (Native Click) - tin cáº­y hÆ¡n JS click
            page.click('[data-qa-settings-trigger="true"]', delay=100)
            log_fn(f"   Opened settings: '{btn_info[:40]}...'")
            
            # Kiá»ƒm tra xem panel Ä‘Ã£ má»Ÿ chÆ°a (thÆ°á»ng lÃ  div cÃ³ role menu hoáº·c data-state open)
            panel_opened = False
            for _ in range(5):
                time.sleep(0.5)
                panel_opened = page.evaluate("""() => {
                    const panel = document.querySelector('div[role="menu"][data-state="open"], div[data-test-id="settings-panel"]');
                    if (panel) {
                        // Äáº£m báº£o panel Ä‘ang hiá»ƒn thá»‹
                        const style = window.getComputedStyle(panel);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }
                    return false;
                }""")
                if panel_opened: break
            
            if not panel_opened:
                log_fn("   WARN settings panel did not open."); return
            else:
                log_fn("   Settings panel is visible.")
        else:
            log_fn("   WARN settings button not found."); return

        # BÆ°á»›c 2: Loáº¡i output
        if output_type:
            output_status = page.evaluate("""(t) => {
                const panel = document.querySelector('div[role="menu"][data-state="open"]');
                if (!panel) return 'not_found';
                const tab = Array.from(panel.querySelectorAll('button[role="tab"]')).find(b => (b.innerText || b.textContent).trim().includes(t));
                if (tab) {
                    if (tab.getAttribute('aria-selected') === 'true' || tab.getAttribute('data-state') === 'active') return 'already_selected';
                    tab.setAttribute('data-qa-output-trigger', 'true');
                    return 'needs_click';
                }
                return 'not_found';
            }""", output_type);
            
            if output_status == 'needs_click':
                page.click('[data-qa-output-trigger="true"]', delay=100)
                log_fn(f"   Output selected: {output_type}"); time.sleep(0.4)
            elif output_status == 'already_selected':
                log_fn(f"   Output already selected: {output_type}")
            else:
                log_fn(f"   WARN output option not found: {output_type}")

        # BÆ°á»›c 3: Tá»· lá»‡ (Ratio) - Native Click
        ratio_status = page.evaluate("""(ratio) => {
            const panel = document.querySelector('div[role="menu"][data-state="open"]');
            if (!panel) return 'not_found';
            const tab = Array.from(panel.querySelectorAll('button[role="tab"]')).find(b => (b.innerText || b.textContent).trim().includes(ratio));
            if (tab) {
                if (tab.getAttribute('aria-selected') === 'true' || tab.getAttribute('data-state') === 'active') return 'already_selected';
                tab.setAttribute('data-qa-ratio-trigger', 'true');
                return 'needs_click';
            } return 'not_found';
        }""", web_ratio)
        
        if ratio_status == 'needs_click':
            page.click('[data-qa-ratio-trigger="true"]', delay=100)
            log_fn(f"   Aspect ratio selected: {web_ratio}"); time.sleep(0.4)
        elif ratio_status == 'already_selected':
            log_fn(f"   Aspect ratio already selected: {web_ratio}")
        else:
            log_fn(f"   WARN aspect ratio option not found: {web_ratio}")

        # BÆ°á»›c 4: Sá»‘ lÆ°á»£ng (Quantity) - Native Click
        count_status = page.evaluate("""(cnt) => {
            const panel = document.querySelector('div[role="menu"][data-state="open"]');
            if (!panel) return 'not_found';
            const btns = Array.from(panel.querySelectorAll('button[role="tab"]'));
            
            let tab = btns.find(b => {
                const txt = (b.innerText || b.textContent).trim().toLowerCase();
                return txt === cnt || txt === 'x' + cnt || txt === cnt + 'x';
            });
            if (tab) {
                if (tab.getAttribute('aria-selected') === 'true' || tab.getAttribute('data-state') === 'active') return 'already_selected';
                tab.setAttribute('data-qa-qty-trigger', 'true');
                return 'needs_click';
            } return 'not_found';
        }""", target_count)
        
        if count_status == 'needs_click':
            page.click('[data-qa-qty-trigger="true"]', delay=100)
            log_fn(f"   Image count selected: {target_count}"); time.sleep(0.4)
        elif count_status == 'already_selected':
            log_fn(f"   Image count already selected: {target_count}")
        else:
            log_fn(f"   WARN image count option not found: {target_count}")

        # BÆ°á»›c 5: Model dropdown bÃªn trong panel
        if model:
            model_status = page.evaluate("""(modelName) => {
                const panel = document.querySelector('div[role="menu"][data-state="open"]');
                if (!panel) return 'not_found';
                const btns = Array.from(panel.querySelectorAll('button'));
                const dropBtn = btns.find(b => 
                    b.getAttribute('aria-haspopup') === 'menu' ||
                    b.innerText.includes('arrow_drop_down') ||
                    (b.textContent && (b.textContent.includes('Banana') || b.textContent.includes('Imagen')))
                );
                if (dropBtn) {
                    // Náº¿u text cá»§a nÃºt Ä‘Ã£ hiá»ƒn thá»‹ Ä‘Ãºng model Ä‘ang chá»n thÃ¬ bá» qua
                    if (dropBtn.textContent.includes(modelName)) return 'already_selected';
                    
                    dropBtn.setAttribute('data-qa-model-dropdown', 'true');
                    return 'needs_click';
                } 
                return 'not_found';
            }""", model)

            if model_status == 'already_selected':
                log_fn(f"   Model already selected: {model}")
            elif model_status == 'needs_click':
                page.click('[data-qa-model-dropdown="true"]', delay=100)
                log_fn("   ðŸ–±ï¸ ÄÃ£ click má»Ÿ dropdown Model.")
                time.sleep(1.0) # Äá»£i animation má»Ÿ popup
                
                model_found = page.evaluate("""(modelName) => {
                    const panels = Array.from(document.querySelectorAll('[role="menu"][data-state="open"], [role="dialog"], [role="listbox"]'));
                    const lastPanel = panels.length > 0 ? panels[panels.length - 1] : document;
                    const opts = Array.from(lastPanel.querySelectorAll('[role="menuitem"], [role="option"]'))
                        .filter(b => b.offsetParent !== null && b.checkVisibility()); // Chá»‰ láº¥y pháº§n tá»­ Ä‘ang hiá»ƒn thá»‹
                    
                    const target = opts.find(el => (el.innerText || el.textContent || '').trim().includes(modelName));
                    if (target) {
                        target.setAttribute('data-qa-model-trigger', 'true');
                        return true;
                    }
                    return false;
                }""", model)
                if model_found:
                    page.click('[data-qa-model-trigger="true"]', delay=100)
                    log_fn(f"   Model selected: {model}")
                else:
                    log_fn(f"   WARN model option not clickable: {model}")
                time.sleep(0.5)
            else:
                log_fn("   WARN model dropdown not found.")

        if seed and seed.strip():
            seed_value = seed.strip()
            try:
                seed_result = page.evaluate(r"""(seedValue) => {
                    const panel = document.querySelector('div[role="menu"][data-state="open"], div[data-test-id="settings-panel"]');
                    const root = panel || document;
                    const inputs = Array.from(root.querySelectorAll('input, textarea')).filter(el => {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
                    });
                    const describe = (el) => {
                        const label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.name || el.id || '';
                        const wrapText = (el.closest('label, div, section, form')?.innerText || '').slice(0, 180);
                        return { label, type: el.type || el.tagName, text: wrapText };
                    };
                    const candidates = inputs.map(describe);
                    let target = inputs.find(el => {
                        const label = `${el.getAttribute('aria-label') || ''} ${el.getAttribute('placeholder') || ''} ${el.name || ''} ${el.id || ''}`.toLowerCase();
                        const text = (el.closest('label, div, section, form')?.innerText || '').toLowerCase();
                        return label.includes('seed') || text.includes('seed');
                    });
                    if (!target && inputs.length === 1) target = inputs[0];
                    if (!target) return { ok: false, reason: 'seed_input_not_found', candidates };
                    target.focus();
                    target.value = seedValue;
                    target.dispatchEvent(new Event('input', { bubbles: true }));
                    target.dispatchEvent(new Event('change', { bubbles: true }));
                    return { ok: true, reason: 'filled', target: describe(target), candidates };
                }""", seed_value)
                candidates = seed_result.get("candidates", []) if isinstance(seed_result, dict) else []
                log_fn(f"   Seed requested: {seed_value}")
                log_fn(f"   Seed input scan: {len(candidates)} visible input(s) in settings scope")
                for idx, cand in enumerate(candidates[:5], 1):
                    label = str(cand.get("label", "")).strip()
                    text = " ".join(str(cand.get("text", "")).split())[:90]
                    log_fn(f"      Seed candidate {idx}: label='{label}' text='{text}'")
                if isinstance(seed_result, dict) and seed_result.get("ok"):
                    target = seed_result.get("target", {})
                    log_fn(f"   Seed filled: {seed_value} | target='{target.get('label', '')}'")
                else:
                    reason = seed_result.get("reason", "unknown") if isinstance(seed_result, dict) else "unknown"
                    log_fn(f"   WARN seed not applied: {reason}")
            except Exception as e:
                log_fn(f"   WARN seed diagnostic failed: {e}")

        page.keyboard.press("Escape"); time.sleep(0.5)

    except Exception as e:
        log_fn(f"   âš ï¸ Lá»—i setup_flow_options: {e}")
        try: page.keyboard.press("Escape")
        except: pass

def get_all_images(page: Page, log_fn=None) -> list[dict]:
    try:
        return page.evaluate(IMAGE_SCAN_JS) or []
    except Exception as e:
        if log_fn: log_fn(f"   âš ï¸  scan images error: {e}")
        return []


def save_one_media(img_info: dict, page: Page, save_dir: str,
                   prompt: str, idx: int, log_fn=print) -> str | None:
    try:
        os.makedirs(save_dir, exist_ok=True)
        safe  = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        src   = img_info.get('src', '')
        tag   = img_info.get('tag', 'img')
        ext   = "mp4" if tag == "video" else "png"
        fpath = os.path.join(save_dir, f"{ts}_{idx:02d}_{safe}.{ext}")

        b64 = None
        if src.startswith("data:image"):
            _, b64 = src.split(",", 1)
        else:
            b64 = page.evaluate(f"""
                async () => {{
                    const r = await fetch({repr(src)});
                    const blob = await r.blob();
                    return new Promise(resolve => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    }});
                }}
            """)
        if b64:
            data = base64.b64decode(b64)
            if len(data) > 10000:
                Path(fpath).write_bytes(data)
                log_fn(f"   ðŸ’¾ LÆ°u: {os.path.basename(fpath)} ({len(data)//1024}KB)")
                return fpath
            else:
                log_fn(f"   âš ï¸ Bá» qua áº£nh lá»—i ({len(data)} bytes)")
    except Exception as e:
        log_fn(f"   âš ï¸ Lá»—i lÆ°u áº£nh {idx}: {e}")
    return None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ENGINE CHÃNH â€” v7
# DÃ¹ng before_urls Ä‘á»ƒ phÃ¢n biá»‡t áº£nh má»›i (khÃ´ng dÃ¹ng row index)
# isBlocked chá»‰ xÃ©t trÃªn row CÃ“ CHá»¨A áº£nh má»›i
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_auto(
    prompts: list[str],
    save_dir: str,
    tool: str = "flow",
    log_fn=print,
    stop_fn=None,
    on_image_saved=None,
    on_gen_start=None,
    on_gen_progress=None,
    new_project_each_run: bool = False,
    expected_images: int = 2,
    aspect_ratio: str = "16:9",
    model: str = "Nano Banana 2",
    output_type: str = "HÃ¬nh áº£nh",
    task_name: str = None,
    seed: str = None,
    reference_mode: str = "None",
    reference_dir: str = None,
    manual_reference_paths: list[list[str]] = None,
    worker_id: int = 1,
) -> list[str]:
    saved = []
    uploaded_reference_keys = set()
    log_fn("\nG-Labs Engine v7")

    try:
        with CHROME_START_LOCK:
            if not ensure_chrome_running(log_fn): return []

        final_save_dir = os.path.join(save_dir, task_name) if task_name else save_dir
        os.makedirs(final_save_dir, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)
            context = browser.contexts[0]

            page = None
            if not new_project_each_run:
                for ep in context.pages:
                    if "labs.google" in ep.url and "flow" in ep.url:
                        page = ep
                        try: page.bring_to_front()
                        except: pass
                        log_fn("   Reusing existing Google Labs tab.")
                        break

            if not page:
                page = context.new_page()
                page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)
                log_fn(f"   Worker {worker_id}: opened a new Google Labs tab.")

            if new_project_each_run or "/project/" not in page.url:
                if new_project_each_run:
                    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                project_page = enter_project(page, log_fn, force_new=new_project_each_run, worker_id=worker_id)
                if not project_page:
                    log_fn("ERROR could not enter a Flow project."); return []
                page = project_page
            else:
                log_fn("   Existing tab is already in a project.")

            log_fn(f"Worker {worker_id} project URL: {page.url}")
            time.sleep(2)

            setup_flow_options(page, expected_images, aspect_ratio, model, output_type, seed, log_fn)

            # QuÃ©t toÃ n bá»™ lá»‹ch sá»­ áº£nh (tá»« Ä‘áº§u tá»›i chÃ¢n)
            log_fn("   Scanning existing project media...")
            all_existing_urls = set()
            unchanged_count = 0
            
            for _ in range(50):  # Cuá»™n tá»‘i Ä‘a 50 láº§n
                current_urls = set(page.evaluate(GET_ALL_URLS_JS))
                prev_total = len(all_existing_urls)
                all_existing_urls.update(current_urls)
                
                if len(all_existing_urls) > prev_total:
                    unchanged_count = 0
                    log_fn(f"      scanned {len(all_existing_urls)} existing media URL(s)")
                else:
                    unchanged_count += 1
                    if unchanged_count >= 3:  # Dá»«ng náº¿u 3 láº§n cuá»™n khÃ´ng cÃ³ áº£nh má»›i
                        break
                        
                # Lá»‡nh JS Ä‘á»ƒ tÃ¬m pháº§n tá»­ cuá»™n vÃ  Ä‘áº©y lÃªn trÃªn
                page.evaluate("""() => {
                    const articles = document.querySelectorAll('div[role="article"], div[data-testid="virtuoso-item-list"] > div[data-index]');
                    if (articles.length > 0) {
                        articles[0].scrollIntoView();
                    } else {
                        window.scrollTo(0, 0);
                    }
                }""")
                time.sleep(1.0)
                
            existing_urls = all_existing_urls
            log_fn(f"   Scan complete. Existing media URL(s): {len(existing_urls)}")
            
            # Tráº£ láº¡i vá»‹ trÃ­ cuá»™n xuá»‘ng dÆ°á»›i cÃ¹ng Ä‘á»ƒ chuáº©n bá»‹ gÃµ prompt
            page.evaluate("""() => {
                const articles = document.querySelectorAll('div[role="article"], div[data-testid="virtuoso-item-list"] > div[data-index]');
                if (articles.length > 0) articles[articles.length - 1].scrollIntoView();
            }""")
            time.sleep(1.0)
            
            # Debug kiá»ƒm tra cáº¥u trÃºc Row theo Element má»›i
            log_fn("   Reading existing generation rows...")
            current_rows = page.evaluate(IMAGE_SCAN_JS)
            log_fn(f"   Existing generation row(s): {len(current_rows)}")
            for r in current_rows:
                blocked = r.get('blockedCount', 0)
                blocked_str = f" | blocked: {blocked}" if blocked > 0 else ""
                log_fn(f"      - Row {r.get('rowIndex')} [Prompt: '{r.get('promptText')}']: media={r.get('count')}{blocked_str} | busy={r.get('isBusy')}")

            # QuÃ©t vÃ  log Ã´ nháº­p Prompt
            log_fn("   Scanning prompt input fields...")
            prompt_elements = page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], [role="textbox"]'));
                return els.map(e => `${e.tagName.toLowerCase()} (placeholder: "${e.getAttribute('placeholder') || ''}", role: "${e.getAttribute('role') || ''}")`);
            }""")
            log_fn(f"   Prompt input candidate(s): {len(prompt_elements)}")
            for el in prompt_elements:
                log_fn(f"      - {el}")

            valid_prompts = [p.strip() for p in prompts if p.strip()]
            total = len(valid_prompts)

            for done, prompt in enumerate(valid_prompts, 1):
                if stop_fn and stop_fn(): break

                log_fn(f"\n{'-'*50}")
                log_fn(f"> [{done}/{total}] {prompt[:70]}")
                if on_gen_start: on_gen_start(done - 1, prompt)

                # Snapshot trÆ°á»›c khi submit
                manual_refs = manual_reference_paths[done - 1] if manual_reference_paths and done - 1 < len(manual_reference_paths) else []
                ref_paths = manual_refs or resolve_reference_images(prompt, reference_dir, reference_mode)
                if ref_paths:
                    log_fn("   Matched reference: " + ", ".join(os.path.basename(p) for p in ref_paths))
                    upload_needed = [p for p in ref_paths if ref_cache_key(p) not in uploaded_reference_keys]
                    if upload_needed:
                        for upload_path in upload_needed:
                            if upload_reference_images(page, [upload_path], log_fn):
                                wait_for_upload_idle(page, log_fn, timeout=120)
                                uploaded_reference_keys.add(ref_cache_key(upload_path))
                            else:
                                log_fn(f"   WARN Reference upload failed: {os.path.basename(upload_path)}")
                    else:
                        log_fn("   Reference already uploaded in this batch; reusing library asset.")
                elif reference_mode != "None" and reference_dir:
                    log_fn("   No matching reference image for this prompt.")

                if not fill_prompt(page, prompt, log_fn): continue
                attach_ok = True
                for ref_idx, ref_path in enumerate(ref_paths, 1):
                    log_fn(f"   Attach reference {ref_idx}/{len(ref_paths)}: {os.path.basename(ref_path)}")
                    if not attach_reference_image_to_prompt(page, ref_path, log_fn):
                        attach_ok = False
                        break
                if ref_paths and not attach_ok:
                    log_fn("   WARN Reference attach failed; skipping prompt to avoid generating without reference.")
                    if on_gen_progress: on_gen_progress(done - 1, -1)
                    continue

                before_urls = set(page.evaluate(GET_ALL_URLS_JS))

                if not click_submit(page, log_fn): continue

                log_fn("   Waiting for Google to generate images...")

                new_images         = []
                timeout_at         = time.time() + GEN_TIMEOUT
                last_logged_prog   = -1
                last_change_time   = time.time()

                while time.time() < timeout_at:
                    all_rows = page.evaluate(IMAGE_SCAN_JS)
                    
                    strict_ready   = []
                    relaxed_ready  = []
                    max_prog       = 0
                    any_busy       = False
                    total_blocked  = 0

                    for r in all_rows:
                        row_prompt = r.get('promptText', 'Unknown Prompt')
                        
                        # [FIX] Lá»c chÃ©o: Bá» qua cÃ¡c row cá»§a prompt cÅ© Ä‘ang render ngáº§m (vÃ­ dá»¥ "gojo")
                        if row_prompt != "Unknown Prompt":
                            rp_clean = re.sub(r'\s+', ' ', row_prompt.strip().lower())
                            curr_clean = re.sub(r'\s+', ' ', prompt.strip().lower())
                            # Náº¿u text khÃ´ng khá»›p, bá» qua row nÃ y hoÃ n toÃ n
                            if rp_clean != curr_clean and not rp_clean.startswith(curr_clean) and not curr_clean.startswith(rp_clean):
                                continue

                        row_imgs = r.get('images', [])
                        # Row nÃ y cÃ³ chá»©a áº£nh má»›i khÃ´ng?
                        row_has_new = any(img['src'] not in before_urls for img in row_imgs)
                        row_in_progress = r.get('isBusy') or r.get('progress', 0) > 0

                        if not row_has_new and not row_in_progress: continue

                        if r.get('isBusy'): any_busy = True
                        prog = r.get('progress', 0)
                        if prog > max_prog: max_prog = prog
                        total_blocked += r.get('blockedCount', 0)

                        for img in row_imgs:
                            if img['src'] in before_urls: continue
                            if img.get('isReady'): strict_ready.append(img)
                            if img.get('isReadyRelaxed'): relaxed_ready.append(img)

                    if max_prog != last_logged_prog:
                        log_fn(f"   Rendering... {max_prog}%")
                        last_logged_prog = max_prog
                        last_change_time = time.time()

                    if on_gen_progress: on_gen_progress(done - 1, max_prog)

                    # ThoÃ¡t khi Ä‘á»§ áº£nh hoáº·c Ä‘áº¡t 100%
                    total_resolved = len(strict_ready) + total_blocked
                    if total_resolved >= expected_images:
                        new_images = strict_ready; break
                    if (max_prog >= 100) and not any_busy and (len(relaxed_ready) + total_blocked > 0):
                        new_images = strict_ready if strict_ready else relaxed_ready; break
                    
                    # Káº¹t lÃ¢u quÃ¡ thÃ¬ láº¥y áº£nh hiá»‡n cÃ³
                    if (time.time() - last_change_time) > STABLE_WAIT and (len(relaxed_ready) + total_blocked > 0):
                        new_images = relaxed_ready; break

                    time.sleep(1)

                # Fallback láº§n cuá»‘i
                if not new_images:
                    final_rows = page.evaluate(IMAGE_SCAN_JS)
                    for r in final_rows:
                        row_prompt = r.get('promptText', 'Unknown Prompt')
                        if row_prompt != "Unknown Prompt":
                            rp_clean = re.sub(r'\s+', ' ', row_prompt.strip().lower())
                            curr_clean = re.sub(r'\s+', ' ', prompt.strip().lower())
                            if rp_clean != curr_clean and not rp_clean.startswith(curr_clean) and not curr_clean.startswith(rp_clean):
                                continue
                        new_images.extend([
                            img for img in r.get('images', [])
                            if img['src'] not in before_urls and img.get('isReadyRelaxed')
                        ])

                # LÆ°u áº£nh
                for i, img in enumerate(new_images):
                    fp = save_one_media(img, page, final_save_dir, prompt, i + 1, log_fn)
                    if fp:
                        saved.append(fp)
                        if on_image_saved: on_image_saved(done - 1, fp)

                if done < total: time.sleep(BETWEEN_DELAY)

            log_fn(f"\nDONE. Saved {len(saved)} new image(s).")

    except Exception as e:
        log_fn(f"\nERROR: {e}")
        log_fn("Chrome must be running with --remote-debugging-port=9222")

    return saved


