"""
glabs_engine.py — v4
Fix dựa trên debug log thực tế:
- Nút submit: text chứa "Tạo" + type=submit (arrow_forwardTạo)
- Nút download: text chứa "Tải xuống" + type=button
- Ảnh kết quả: cần scan rộng hơn vì Flow dùng nhiều kiểu render
"""

from playwright.sync_api import sync_playwright, Page
import time, os, re, base64, socket, subprocess, sys
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
FLOW_URL      = "https://labs.google/fx/tools/flow"
CDP_ENDPOINT  = "http://127.0.0.1:9222"
GEN_TIMEOUT   = 180
STABLE_WAIT   = 5
BETWEEN_DELAY = 2

# ──────────────────────────────────────────────────────
# AUTO LAUNCH CONFIG
# ──────────────────────────────────────────────────────
CHROME_PATHS_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
PROFILE_DIR = str(Path.home() / "ChromeGLabsProfile")

def is_port_open(host, port):
    """Kiểm tra xem cổng debug đã mở chưa."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0

def find_chrome_path():
    """Tìm đường dẫn thực thi của Chrome."""
    if sys.platform == "win32":
        for p in CHROME_PATHS_WINDOWS:
            if os.path.exists(p): return p
    return None

def ensure_chrome_running(log_fn):
    """Đảm bảo Chrome đang chạy với port 9222, nếu chưa thì tự mở."""
    if is_port_open("127.0.0.1", 9222):
        log_fn("✅ Chrome Debug đã sẵn sàng.")
        return True

    log_fn("🌐 Chrome chưa chạy ở chế độ Debug. Đang tự động khởi động...")
    chrome_exe = find_chrome_path()
    
    if not chrome_exe:
        log_fn("❌ Không tìm thấy Chrome. Vui lòng cài đặt Chrome hoặc chạy launch_chrome.py thủ công.")
        return False

    os.makedirs(PROFILE_DIR, exist_ok=True)
    
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        FLOW_URL
    ]
    
    # Khởi động Chrome mà không đợi nó đóng (non-blocking)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Chờ tối đa 10 giây để cổng 9222 mở
    for _ in range(10):
        time.sleep(1)
        if is_port_open("127.0.0.1", 9222):
            log_fn("✅ Chrome đã được khởi động thành công.")
            # Cho thêm 2 giây để trang web load sơ bộ
            time.sleep(2)
            log_fn("⚠️  Lưu ý: Nếu đây là lần đầu, hãy đảm bảo bạn đã đăng nhập Google trên cửa sổ vừa hiện ra.")
            return True
            
    log_fn("❌ Không thể kích hoạt cổng Debug của Chrome sau 10 giây.")
    return False


# ──────────────────────────────────────────────────────
# SELECTORS — cập nhật từ debug log thực tế
# ──────────────────────────────────────────────────────

NEW_PROJECT_SELECTORS = [
    'button:has-text("Dự án mới")',
    'button:has-text("New project")',
    '[aria-label*="Dự án mới" i]',
]

PROMPT_SELECTORS = [
    'div[role="textbox"]',                          # ✅ đã confirm trong log
    'div[contenteditable="true"]',
    'textarea[placeholder*="tạo" i]',
    'textarea[placeholder*="What do you" i]',
    'textarea',
]

# Từ log: text='arrow_forwardTạo' type=submit — nút cuối cùng có text "Tạo"
SUBMIT_SELECTORS = [
    # Chính xác nhất: button submit có text "Tạo" (kể cả khi có icon material trước)
    'button[type="submit"]:has-text("Tạo")',
    'button[type="submit"]:has-text("Create")',
    'button[type="submit"]:has-text("Send")',
    'button[type="submit"]:has-text("Gửi")',
    # Fallback rộng hơn
    'button:has-text("arrow_forwardTạo")',
    '[data-testid*="send"]',
    '[data-testid*="submit"]',
    'button[aria-label*="Tạo" i]',
    'button[aria-label*="Send" i]',
    'button[aria-label*="Generate" i]',
]

# Selector ảnh — scan rất rộng, lọc bằng JS sau
IMAGE_SCAN_JS = """
() => {
    const rows = [];
    // Nhắm thẳng vào các container chứa lượt chat
    const turnContainers = document.querySelectorAll('div[role="article"]');

    turnContainers.forEach((container, index) => {
        const imgs = Array.from(container.querySelectorAll('img')).filter(img => img.src && !img.src.startsWith('data:image/svg'));
        if (imgs.length === 0) return;

        // Kiểm tra nhanh xem container này có đang 'bận' không
        const isBusy = container.querySelector('.generating, .is-generating, [aria-busy="true"], [class*="spinner"]');

        const readyImages = imgs.map(img => {
            const style = window.getComputedStyle(img);
            // Ảnh sẵn sàng khi: Container không busy, opacity cao, không blur và có kích thước thật
            const isReady = !isBusy && parseFloat(style.opacity) > 0.9 && !style.filter.includes('blur') && img.naturalWidth > 100;
            return { src: img.src, isReady };
        });

        const textEl = container.querySelector('div[dir="auto"], span[jsname]');
        let prompt = textEl ? textEl.innerText.trim() : "Hàng #" + (index + 1);

        rows.push({
            rowIndex: rows.length + 1,
            prompt: prompt,
            count: imgs.length,
            images: readyImages
        });
    });

    if (rows.length === 0) {
         const allImgs = Array.from(document.querySelectorAll('img')).filter(i => i.width > 50);
         const groups = new Map();
         allImgs.forEach(i => {
             const p = i.closest('div[style*="grid"]') || i.parentElement.parentElement;
             if(!groups.has(p)) groups.set(p, []);
             groups.get(p).push({src: i.src, isReady: i.naturalWidth > 100});
         });
         groups.forEach((imgs, p) => {
             rows.push({ rowIndex: rows.length+1, prompt: "Dòng tự động", count: imgs.length, images: imgs });
         });
    }
    return rows;
}
"""

DOWNLOAD_BTN_JS = """
() => {
    // Tìm nút "Tải xuống" hoặc "Download" visible
    const btns = [];
    document.querySelectorAll('button').forEach(btn => {
        const txt = btn.textContent || '';
        if ((txt.includes('Tải xuống') || txt.includes('Download')) && btn.offsetParent) {
            btns.push(btn);
        }
    });
    return btns.length;
}
"""

GET_ALL_URLS_JS = """
() => {
    return Array.from(document.querySelectorAll('img'))
        .map(img => img.src)
        .filter(src => src && !src.startsWith('data:image/svg'));
}
"""


# ──────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────

def find_el(page: Page, selectors: list, timeout=5000):
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                return el, sel
        except Exception:
            continue
    return None, None


def wait_for_project_page(page: Page, log_fn=print, timeout=20) -> bool:
    log_fn("   ⏳ Chờ trang dự án...")
    deadline = time.time() + timeout
    signals  = ['text="Nhân vật"', 'text="Characters"', 'div[role="textbox"]',
                'text="Cảnh"', 'text="Công cụ"']
    while time.time() < deadline:
        for sig in signals:
            try:
                el = page.query_selector(sig)
                if el and el.is_visible():
                    log_fn(f"   ✅ Trong dự án ({sig})")
                    return True
            except Exception:
                pass
        time.sleep(0.8)
    return False


def enter_project(page: Page, log_fn=print) -> bool:
    log_fn("   🏠 Trang chủ — tìm dự án...")
    time.sleep(2)
    js = """
    () => {
        const res = [];
        document.querySelectorAll('a').forEach(a => {
            const h = a.href || '';
            if (h.includes('/project/') && h.length > 50)
                res.push(h);
        });
        return [...new Set(res)].slice(0, 5);
    }
    """
    try:
        urls = page.evaluate(js)
        log_fn(f"   📂 Tìm thấy {len(urls)} dự án.")
        if urls:
            log_fn(f"   🔗 Vào: {urls[0][:80]}")
            page.goto(urls[0], wait_until="domcontentloaded", timeout=20000)
            return wait_for_project_page(page, log_fn)
    except Exception as e:
        log_fn(f"   ⚠️  JS scan lỗi: {e}")

    # Tạo mới
    log_fn("   ➕ Tạo dự án mới...")
    el, sel = find_el(page, NEW_PROJECT_SELECTORS, timeout=8000)
    if not el:
        return False
    el.click()
    return wait_for_project_page(page, log_fn, timeout=20)


def fill_prompt(page: Page, prompt: str, log_fn=print) -> bool:
    el, sel = find_el(page, PROMPT_SELECTORS, timeout=10000)
    if not el:
        log_fn("   ❌ Không tìm thấy ô nhập!")
        return False
    log_fn(f"   ✍️  {sel}")
    try:
        el.click()
        time.sleep(0.3)
        page.keyboard.press("Control+a")
        time.sleep(0.1)
        page.keyboard.press("Backspace")
        time.sleep(0.2)
        el.type(prompt, delay=30)
        time.sleep(0.5)
        return True
    except Exception as e:
        log_fn(f"   ❌ fill error: {e}")
        return False


def click_submit(page: Page, log_fn=print) -> bool:
    """
    Ưu tiên click nút 'Tạo' (type=submit) — đã confirm từ debug log.
    Fallback: Enter.
    """
    # Thử SUBMIT_SELECTORS trước
    el, sel = find_el(page, SUBMIT_SELECTORS, timeout=5000)
    if el:
        log_fn(f"   🖱️  Click Submit: {sel}")
        el.click()
        return True

    # Fallback JS: tìm button submit cuối cùng visible
    log_fn("   🖱️  JS fallback: tìm button submit...")
    try:
        clicked = page.evaluate("""
            () => {
                const btns = [...document.querySelectorAll('button[type="submit"]')]
                    .filter(b => b.offsetParent !== null);
                if (btns.length > 0) {
                    btns[btns.length - 1].click();  // nút submit cuối = nút Tạo
                    return btns[btns.length - 1].textContent.trim();
                }
                return null;
            }
        """)
        if clicked:
            log_fn(f"   🖱️  JS click: '{clicked[:30]}'")
            return True
    except Exception as e:
        log_fn(f"   ⚠️  JS submit error: {e}")

    # Enter cuối cùng
    log_fn("   🖱️  Enter fallback")
    page.keyboard.press("Enter")
    return True


def get_all_images(page: Page, log_fn=None) -> list[dict]:
    """Lấy tất cả ảnh kết quả trên trang bằng JS."""
    try:
        items = page.evaluate(IMAGE_SCAN_JS)
        return items or []
    except Exception as e:
        if log_fn:
            log_fn(f"   ⚠️  scan images error: {e}")
        return []


def wait_for_new_images(page: Page, before_urls: set, log_fn=print) -> list[dict]:
    """Chờ ảnh có URL mới xuất hiện và ở trạng thái Ready."""
    log_fn(f"   ⏳ Chờ ảnh mới (đã biết: {len(before_urls)})...")
    deadline     = time.time() + GEN_TIMEOUT
    stable_since = None
    last_new_ready_count = 0

    while time.time() < deadline:
        current = get_all_images(page)
        
        # Lọc những ảnh có URL mới và đã Ready
        new_ready = [img for img in current if img['src'] not in before_urls and img['isReady']]
        now_count = len(new_ready)

        if now_count > 0:
            if now_count > last_new_ready_count:
                log_fn(f"   🖼️  Đã thấy {now_count} ảnh mới sẵn sàng...")
                last_new_ready_count = now_count
                stable_since = time.time()
            elif stable_since and (time.time() - stable_since) >= STABLE_WAIT:
                log_fn(f"   ✅ Ổn định: {now_count} ảnh mới.")
                time.sleep(2)
                return new_ready

        # Nếu sau một lúc vẫn chưa thấy gì mới, hoặc đang bận "generating"
        all_new = [img for img in current if img['src'] not in before_urls]
        if len(all_new) > now_count:
            # Có ảnh mới nhưng chưa Ready, reset timer ổn định
            stable_since = None

        time.sleep(1.5)

    log_fn("   ⏰ Timeout.")
    current = get_all_images(page)
    return [img for img in current if img['src'] not in before_urls and img['isReady']]


def save_one_image(src: str, page: Page, save_dir: str,
                   prompt: str, idx: int, log_fn=print) -> str | None:
    """Lưu 1 ảnh từ src (data / blob / https)."""
    try:
        os.makedirs(save_dir, exist_ok=True)
        safe  = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_{idx:02d}_{safe}.png"
        fpath = os.path.join(save_dir, fname)

        b64 = None
        if src.startswith("data:image"):
            _, b64 = src.split(",", 1)
        else:
            b64 = page.evaluate(f"""
                async () => {{
                    const r = await fetch({repr(src)});
                    const blob = await r.blob();
                    return new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    }});
                }}
            """)
        
        if b64:
            img_data = base64.b64decode(b64)
            if len(img_data) > 10000: # Chỉ lưu nếu ảnh > 10KB (tránh ảnh trắng/icon)
                Path(fpath).write_bytes(img_data)
                log_fn(f"   💾 Lưu: {fname} ({len(img_data)//1024}KB)")
                return fpath
            else:
                log_fn(f"   ⚠️ Bỏ qua ảnh lỗi (dung lượng thấp: {len(img_data)} bytes)")
    except Exception as e:
        log_fn(f"   ⚠️ Lỗi lưu ảnh {idx}: {e}")
    return None


# ──────────────────────────────────────────────────────
# ENGINE CHÍNH
# ──────────────────────────────────────────────────────

def run_auto(
    prompts: list[str],
    save_dir: str,
    tool: str = "flow",
    log_fn=print,
    stop_fn=None,
    on_image_saved=None,
    new_project_each_run: bool = False
) -> list[str]:
    saved = []

    log_fn("\n🚀 G-Labs Engine v4...")

    try:
        if not ensure_chrome_running(log_fn):
            return []

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)
            context = browser.contexts[0]
            page = context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            if not enter_project(page, log_fn):
                log_fn("❌ Không xác định được dự án.")
                return []
            
            log_fn(f"🔗 URL Dự án hiện tại: {page.url}")
            time.sleep(2)

            # Vòng lặp Generate thực tế
            valid_prompts = [p.strip() for p in prompts if p.strip()]
            total = len(valid_prompts)

            for done, prompt in enumerate(valid_prompts, 1):
                if stop_fn and stop_fn(): break

                log_fn(f"\n{'━'*50}")
                log_fn(f"▶  [{done}/{total}] {prompt[:70]}")

                # Lấy baseline ảnh cũ: quét tuyệt đối tất cả URL hiện có
                before_urls = set(page.evaluate(GET_ALL_URLS_JS))
                
                log_fn(f"   📊 Đã có {len(before_urls)} ảnh trong lịch sử.")

                # Gõ prompt và nhấn Tạo
                if not fill_prompt(page, prompt, log_fn): continue
                if not click_submit(page, log_fn): continue

                # Chờ ảnh mới
                log_fn("   ⏳ Đang đợi Google sinh ảnh...")
                new_images = []
                timeout_at = time.time() + GEN_TIMEOUT
                
                while time.time() < timeout_at:
                    current_rows = page.evaluate(IMAGE_SCAN_JS)
                    # Tìm các ảnh có URL không nằm trong before_urls và đã isReady
                    current_new = []
                    for r in current_rows:
                        for img in r['images']:
                            if img['src'] not in before_urls and img['isReady']:
                                current_new.append(img)
                    
                    if len(current_new) >= 2: # Theo user nói mỗi lượt ra 2 ảnh
                        log_fn(f"   ✅ Đã thấy {len(current_new)} ảnh mới hoàn thiện.")
                        new_images = current_new
                        break
                    time.sleep(1)

                if not new_images:
                    log_fn("   ⚠️ Không tìm thấy ảnh mới sau khi sinh. Thử quét lại lần cuối...")
                    # Fallback quét lại một lần nữa
                    final_rows = page.evaluate(IMAGE_SCAN_JS)
                    new_images = [i for r in final_rows for i in r['images'] if i['src'] not in before_urls]

                # Lưu ảnh
                for i, img in enumerate(new_images):
                    fp = save_one_image(img['src'], page, save_dir, prompt, i+1, log_fn)
                    if fp:
                        saved.append(fp)
                        if on_image_saved: on_image_saved(fp)

                if done < total: time.sleep(BETWEEN_DELAY)

            log_fn(f"\n🎉 HOÀN THÀNH! Đã lưu {len(saved)} ảnh mới.")
            page.close()

    except Exception as e:
        log_fn(f"\n❌ LỖI: {e}")
        log_fn("💡 Chrome cần --remote-debugging-port=9222")

    return saved