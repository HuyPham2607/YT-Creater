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

SUBMIT_SELECTORS = [
    # Nhắm chính xác vào icon mũi tên (arrow_forward) để tránh nhầm với nút add_2 (Thêm thành phần)
    'button:has(i:text-is("arrow_forward"))',
    'button:has(i:text-is("send"))',
    'button:has-text("arrow_forwardTạo")',
    'button[type="submit"]:has-text("Tạo")',
    'button[type="submit"]:has-text("Create")',
    '[data-testid*="send"]',
    '[data-testid*="submit"]',
]

# Selector ảnh — scan rất rộng, lọc bằng JS sau
IMAGE_SCAN_JS = """
() => {
    const rows = [];
    const turnContainers = document.querySelectorAll('div[role="article"]');

    // 1. Quét theo role="article" nếu có
    if (turnContainers.length > 0) {
        turnContainers.forEach((container, index) => {
            const imgs = Array.from(container.querySelectorAll('img, video')).filter(img => img.src && !img.src.startsWith('data:image/svg'));
            const isBusy = container.querySelector('.generating, .is-generating, [aria-busy="true"], [class*="spinner"], g-progress-circular');
            
            let progress = 0;
            const pctMatch = container.innerText.match(/(\d+)%/);
            if (pctMatch) progress = parseInt(pctMatch[1]);
            else if (isBusy) {
                const ariaVal = isBusy.getAttribute('aria-valuenow');
                if (ariaVal) progress = parseInt(ariaVal);
            }

            const readyImages = imgs.map(img => {
                const style = window.getComputedStyle(img);
                const w = img.naturalWidth || img.videoWidth || img.width || 0;
                const isReady = !isBusy && parseFloat(style.opacity) > 0.9 && !style.filter.includes('blur') && w > 100;
                return { src: img.src, isReady: isReady, tag: img.tagName.toLowerCase() };
            });

            if (imgs.length === 0 && progress === 0 && !isBusy) return;

            const textEl = container.querySelector('div[dir="auto"], span[jsname]');
            let prompt = textEl ? textEl.innerText.trim() : "Hàng #" + (index + 1);

            rows.push({
                rowIndex: rows.length + 1,
                prompt: prompt,
                count: imgs.length,
                images: readyImages,
                progress: progress
            });
        });
    }

    // 2. Fallback nếu UI thay đổi (không có role="article")
    if (rows.length === 0) {
        let globalProg = 0;
        // Tìm % tiến độ từ các element có khả năng chứa nó
        const progressEls = document.querySelectorAll('[aria-busy="true"], [class*="spinner"], [class*="progress"], [role="progressbar"], .generating, .is-generating, g-progress-circular');
        progressEls.forEach(el => {
            const txtMatch = el.innerText?.match(/(\d+)%/);
            if (txtMatch) {
                const val = parseInt(txtMatch[1]);
                if (val > globalProg && val <= 100) globalProg = val;
            } else {
                 const ariaVal = el.getAttribute('aria-valuenow');
                 if (ariaVal) {
                     const val = parseInt(ariaVal);
                     if (val > globalProg && val <= 100) globalProg = val;
                 }
            }
        });
        
        // Nếu không tìm thấy bằng class, quét mù (chỉ tìm text dính %)
        if (globalProg === 0) {
             const allTextMatch = document.body.innerText.match(/(\d+)%/g);
             if (allTextMatch) {
                 allTextMatch.forEach(m => {
                     const val = parseInt(m);
                     if (val > globalProg && val <= 100) globalProg = val;
                 });
             }
        }

        const allImgs = Array.from(document.querySelectorAll('img, video')).filter(i => (i.width > 50 || i.videoWidth > 50) && !i.src.startsWith('data:image/svg'));
        const groups = new Map();
        allImgs.forEach(i => {
            const p = i.closest('div[style*="grid"]') || i.parentElement.parentElement;
            if(!groups.has(p)) groups.set(p, []);
            const style = window.getComputedStyle(i);
            const w = i.naturalWidth || i.videoWidth || i.width || 0;
            const isReady = globalProg === 0 && parseFloat(style.opacity) > 0.9 && !style.filter.includes('blur') && w > 100;
            groups.get(p).push({src: i.src, isReady: isReady, tag: i.tagName.toLowerCase()});
        });

        groups.forEach((imgs, p) => {
            rows.push({ 
                rowIndex: rows.length+1, 
                prompt: "Dòng tự động", 
                count: imgs.length, 
                images: imgs,
                progress: globalProg
            });
        });
        
        // Nếu không có ảnh nào nhưng có progress, trả về 1 row giả
        if (rows.length === 0 && globalProg > 0) {
            rows.push({
                rowIndex: 1,
                prompt: "Đang tạo...",
                count: 0,
                images: [],
                progress: globalProg
            });
        }
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
    return Array.from(document.querySelectorAll('img, video'))
        .map(img => img.src)
        .filter(src => src && !src.startsWith('data:image/svg'));
}
"""


# ──────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────

def find_el(page: Page, selectors: list, timeout=5000):
    # Nối tất cả selector bằng dấu phẩy. Playwright sẽ tìm song song toàn bộ!
    # Nhờ vậy không bị dính vòng lặp chờ 5s mỗi khi 1 thẻ không tồn tại.
    combined_sel = ", ".join(selectors)
    try:
        el = page.wait_for_selector(combined_sel, timeout=timeout, state="visible")
        if el:
            return el, "combined_selector"
    except Exception:
        pass
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
    log_fn("   ✍️  Đã gõ Prompt")
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
    """
    # Thử SUBMIT_SELECTORS trước
    el, sel = find_el(page, SUBMIT_SELECTORS, timeout=5000)
    if el:
        log_fn("   🖱️  Click Submit: Đã tìm thấy nút Tạo")
        # Sử dụng force=True phòng trường hợp thẻ span bị aria-disabled ảo khi vừa gõ xong
        el.click(force=True)
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


def setup_flow_options(page: Page, expected_images: int, aspect_ratio: str, model: str, output_type: str, log_fn=print):
    """
    Tự động mở Menu cài đặt trên Web Flow và setup toàn diện.
    """
    log_fn(f"   ⚙️ Đang thiết lập Web: {output_type} | {expected_images} output | {aspect_ratio} | {model}...")
    count_map = {1: "1x", 2: "x2", 3: "x3", 4: "x4"}
    target_count = count_map.get(expected_images, "x2")

    try:
        # MỞ MENU TỶ LỆ & SỐ LƯỢNG
        trigger_loc = page.locator('button[aria-haspopup="menu"]').filter(has_text=re.compile(r"(1x|x2|x3|x4|16:9|1:1)"))
        
        if trigger_loc.count() > 0:
            trigger_loc.first.click()
            time.sleep(0.8) # Chờ animation của Radix UI mở ra

            # Chọn loại (Hình ảnh / Video)
            if output_type:
                type_loc = page.locator('div[role="menu"][data-state="open"] button[role="tab"]').filter(has_text=output_type)
                if type_loc.count() > 0:
                    type_loc.first.click(force=True)
                    time.sleep(0.4)

            # Chọn tỷ lệ
            if aspect_ratio:
                aspect_loc = page.locator('div[role="menu"][data-state="open"] button[role="tab"]').filter(has_text=aspect_ratio)
                if aspect_loc.count() > 0:
                    aspect_loc.first.click(force=True)
                    time.sleep(0.4)

            # Chọn số lượng ảnh
            tab_loc = page.locator('div[role="menu"][data-state="open"] button[role="tab"]').filter(has_text=target_count)
            if tab_loc.count() > 0:
                tab_loc.first.click(force=True)
            
            # Đóng menu bằng phím ESC (chuẩn accessibility của Radix)
            page.keyboard.press("Escape")
            time.sleep(0.5)
        else:
            log_fn("   ⚠️ Không tìm thấy nút Cài đặt trên web (Google có thể đã đổi giao diện).")
    except Exception as e:
        log_fn(f"   ⚠️ Lỗi Setup Số lượng/Tỷ lệ: {e}")

    try:
        # MỞ MENU MODEL 
        if model:
            # --- DEBUG: Quét tất cả các nút Menu hiện có ---
            menu_btns = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button[aria-haspopup="menu"]')).map(b => b.textContent);
            }""")
            log_fn(f"   🔎 [DEBUG] Các nút Menu trên web: {menu_btns}")

            # Tìm và click nút Model bằng JS (bỏ qua locator lằng nhằng của Playwright)
            # Nút có dạng: <button aria-haspopup="menu">🍌 Nano Banana 2<i>arrow_drop_down</i></button>
            opened = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button[aria-haspopup="menu"]'));
                
                // Ưu tiên tìm nút có chứa tên model đã biết
                const knownModels = ["Nano Banana", "Imagen"];
                let targetBtn = btns.find(b => knownModels.some(m => b.textContent.includes(m)));
                
                // Fallback: Tìm nút có 'arrow_drop_down' và KHÔNG chứa các chỉ số tỉ lệ/số lượng (1x, 16:9...)
                if (!targetBtn) {
                    targetBtn = btns.find(b => b.textContent.includes('arrow_drop_down') && !b.textContent.match(/(1x|x2|x3|x4|16:9|1:1|4:3|3:4|9:16)/));
                }
                
                if (!targetBtn && btns.length > 0) targetBtn = btns[btns.length - 1]; // Fallback cuối cùng
                
                if (targetBtn) {
                    targetBtn.click();
                    return true;
                }
                return false;
            }""")
            
            if opened:
                time.sleep(1.0)

                # --- DEBUG: ĐỌC VÀ LOG CÁC MODEL BÊN TRONG MENU ---
                available_models = page.evaluate("""() => {
                    const menu = document.querySelector('div[role="menu"][data-state="open"]');
                    if (!menu) return [];
                    const items = Array.from(menu.querySelectorAll('[role="menuitem"]'));
                    if (items.length > 0) {
                        return items.map(i => i.innerText.trim().replace(/\\n/g, ' '));
                    }
                    return Array.from(menu.querySelectorAll('span')).map(s => s.innerText.trim()).filter(t => t.length > 0);
                }""")
                log_fn(f"   🔎 [DEBUG] Tìm thấy các Model sau trong Dropdown: {available_models}")

                # Dùng JS để ép click thẳng vào DOM của React/Radix (xuyên qua mọi lớp overlay ảo)
                clicked = page.evaluate("""(modelName) => {
                    const menu = document.querySelector('div[role="menu"][data-state="open"]');
                    if (!menu) return false;
                    
                    // Tìm item khớp với tên Model trong tất cả thẻ văn bản
                    const elements = Array.from(menu.querySelectorAll('[role="menuitem"], span, div'));
                    const targetEl = elements.find(el => el.innerText && el.innerText.trim().includes(modelName));
                    
                    if (targetEl) {
                        const btn = targetEl.closest('button') || targetEl.closest('[role="menuitem"]');
                        if (btn) btn.click(); 
                        else targetEl.click();
                        return true;
                    }
                    return false;
                }""", model)
                
                if not clicked:
                    log_fn(f"   ⚠️ [DEBUG] Không thể click chọn model: {model}")
                    page.keyboard.press("Escape")
                else:
                    log_fn(f"   ✅ [DEBUG] Đã thử click chọn model: {model}")
                time.sleep(0.5)
            else:
                log_fn("   ⚠️ [DEBUG] Không tìm thấy nút Menu Model.")
    except Exception as e:
         log_fn(f"   ⚠️ Lỗi Setup Model: {e}")


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


def save_one_media(img_info: dict, page: Page, save_dir: str,
                   prompt: str, idx: int, log_fn=print) -> str | None:
    """Lưu 1 ảnh hoặc video từ src (data / blob / https)."""
    try:
        os.makedirs(save_dir, exist_ok=True)
        safe  = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        src = img_info.get('src', '')
        tag = img_info.get('tag', 'img')
        ext = "mp4" if tag == "video" else "png"
        fname = f"{ts}_{idx:02d}_{safe}.{ext}"
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
    on_gen_start=None,
    on_gen_progress=None,
    new_project_each_run: bool = False,
    expected_images: int = 2,
    aspect_ratio: str = "16:9",
    model: str = "Nano Banana 2",
    output_type: str = "Hình ảnh"
) -> list[str]:
    saved = []

    log_fn("\n🚀 G-Labs Engine v4...")

    try:
        if not ensure_chrome_running(log_fn):
            return []

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)
            context = browser.contexts[0]
            
            # --- TÌM TAB ĐÃ MỞ SẴN ĐỂ TÁI SỬ DỤNG ---
            page = None
            for existing_page in context.pages:
                if "labs.google" in existing_page.url and "flow" in existing_page.url:
                    page = existing_page
                    try:
                        page.bring_to_front() # Kéo tab đó lên màn hình cho dễ nhìn
                    except:
                        pass
                    log_fn("   🔄 Sử dụng lại tab Google Labs đã mở.")
                    break
            
            if not page:
                page = context.new_page()
                page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)

            # --- KIỂM TRA & VÀO DỰ ÁN ---
            if new_project_each_run or "/project/" not in page.url:
                if new_project_each_run:
                    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                
                if not enter_project(page, log_fn):
                    log_fn("❌ Không xác định được dự án.")
                    return []
            else:
                log_fn("   ✅ Tab đang ở sẵn trong dự án.")
            
            log_fn(f"🔗 URL Dự án hiện tại: {page.url}")
            time.sleep(2)

            # --- TỰ ĐỘNG SETUP SỐ LƯỢNG ẢNH TRÊN WEB ---
            setup_flow_options(page, expected_images, aspect_ratio, model, output_type, log_fn)

            # Vòng lặp Generate thực tế
            valid_prompts = [p.strip() for p in prompts if p.strip()]
            total = len(valid_prompts)

            for done, prompt in enumerate(valid_prompts, 1):
                if stop_fn and stop_fn(): break

                log_fn(f"\n{'━'*50}")
                log_fn(f"▶  [{done}/{total}] {prompt[:70]}")

                if on_gen_start: on_gen_start(prompt)

                # Lấy baseline ảnh cũ: quét tuyệt đối tất cả URL hiện có
                before_urls = set(page.evaluate(GET_ALL_URLS_JS))
                
                # Đếm số row hiện tại để xác định row mới phát sinh
                before_rows_count = len(page.evaluate(IMAGE_SCAN_JS))
                
                log_fn(f"   📊 Đã có {len(before_urls)} ảnh trong lịch sử.")

                # Gõ prompt và nhấn Tạo
                if not fill_prompt(page, prompt, log_fn): continue
                if not click_submit(page, log_fn): continue

                # Chờ ảnh mới
                log_fn("   ⏳ Đang đợi Google sinh ảnh...")
                new_images = []
                timeout_at = time.time() + GEN_TIMEOUT
                last_logged_prog = 0
                
                while time.time() < timeout_at:
                    current_rows = page.evaluate(IMAGE_SCAN_JS)
                    current_new = []
                    max_prog = 0

                    for i, r in enumerate(current_rows):
                        prog = r.get('progress', 0)
                        # Row mới là row có index >= số row cũ, hoặc có chứa ảnh mới, hoặc có tiến độ > 0
                        is_new_row = (i >= before_rows_count) or any(img['src'] not in before_urls for img in r['images']) or (prog > 0)
                        
                        if is_new_row:
                            max_prog = max(max_prog, prog)
                        
                        for img in r['images']:
                            if img['src'] not in before_urls and img['isReady']:
                                current_new.append(img)
                    
                    if on_gen_progress: on_gen_progress(max_prog)

                    if max_prog > last_logged_prog:
                        log_fn(f"   ⏳ Đang render... {max_prog}%")
                        last_logged_prog = max_prog

                    if len(current_new) >= expected_images:
                        log_fn(f"   ✅ Đã thấy {len(current_new)}/{expected_images} kết quả mới hoàn thiện.")
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
                    fp = save_one_media(img, page, save_dir, prompt, i+1, log_fn)
                    if fp:
                        saved.append(fp)
                        if on_image_saved: on_image_saved(fp)

                if done < total: time.sleep(BETWEEN_DELAY)

            log_fn(f"\n🎉 HOÀN THÀNH! Đã lưu {len(saved)} ảnh mới.")
            # Không đóng tab để giữ nguyên hiện trạng cho lượt gen tiếp theo

    except Exception as e:
        log_fn(f"\n❌ LỖI: {e}")
        log_fn("💡 Chrome cần --remote-debugging-port=9222")

    return saved