"""
glabs_engine.py — v7
Root cause fix:
- Flow đôi khi UPDATE row hiện tại thay vì tạo row mới
  → không thể dùng row index để lọc "new rows"
  → quay lại dùng before_urls để phân biệt ảnh mới (như code gốc)

- isBlocked: chỉ check row có chứa ảnh MỚI (src không có trong before_urls)
  hoặc row có progress > 0 sau khi submit
  → tránh false positive từ row cũ

- Progress: lấy max từ TẤT CẢ row có ảnh mới / đang busy
  (không lọc theo index)

- Điều kiện thoát: giữ relaxed check từ v6 nhưng áp dụng đúng
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
STABLE_WAIT   = 3
BETWEEN_DELAY = 2

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
        log_fn("✅ Chrome Debug đã sẵn sàng.")
        return True
    log_fn("🌐 Đang khởi động Chrome...")
    chrome_exe = find_chrome_path()
    if not chrome_exe:
        log_fn("❌ Không tìm thấy Chrome.")
        return False
    os.makedirs(PROFILE_DIR, exist_ok=True)
    cmd = [
        chrome_exe, "--remote-debugging-port=9222", "--remote-allow-origins=*",
        f"--user-data-dir={PROFILE_DIR}", "--no-first-run", "--no-default-browser-check", FLOW_URL
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        time.sleep(1)
        if is_port_open("127.0.0.1", 9222):
            log_fn("✅ Chrome đã khởi động.")
            time.sleep(2)
            return True
    log_fn("❌ Không thể kích hoạt cổng Debug sau 10 giây.")
    return False


# ──────────────────────────────────────────────────────
# SELECTORS
# ──────────────────────────────────────────────────────
NEW_PROJECT_SELECTORS = [
    'button:has-text("Dự án mới")', 'button:has-text("New project")',
    '[aria-label*="Dự án mới" i]',
]
PROMPT_SELECTORS = [
    'div[role="textbox"]', 'div[contenteditable="true"]',
    'textarea[placeholder*="tạo" i]', 'textarea[placeholder*="What do you" i]', 'textarea',
]
SUBMIT_SELECTORS = [
    'button:has(i:text-is("arrow_forward"))', 'button:has(i:text-is("send"))',
    'button:has-text("arrow_forwardTạo")', 'button[type="submit"]:has-text("Tạo")',
    'button[type="submit"]:has-text("Create")', '[data-testid*="send"]', '[data-testid*="submit"]',
]

# ──────────────────────────────────────────────────────
# IMAGE SCAN JS — v7
# Trả về rows với đầy đủ thông tin
# isBlocked KHÔNG tự quyết định — caller tự kiểm tra dựa vào context
# ──────────────────────────────────────────────────────
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

            // ĐẾM số lượng ảnh bị chặn trong container NÀY
            const warningIcons = Array.from(container.querySelectorAll('i.google-symbols'))
                .filter(i => i.innerText.trim() === 'warning');
            
            let blockedCount = 0;
            warningIcons.forEach(icon => {
                const pTxt = (icon.parentElement ? icon.parentElement.innerText : "").toLowerCase();
                if (pTxt.includes('vi phạm') || pTxt.includes('không thể tạo') || pTxt.includes('violate') || pTxt.includes('chính sách')) blockedCount++;
            });
            
            // Fallback nếu không bóc được text cạnh icon
            if (blockedCount === 0 && warningIcons.length > 0) {
                 const cTxt = (container.innerText || "").toLowerCase();
                 if (cTxt.includes('vi phạm') || cTxt.includes('không thể tạo') || cTxt.includes('violate') || cTxt.includes('chính sách')) blockedCount = warningIcons.length;
            }

            // TRÍCH XUẤT PROMPT TEXT CỦA DÒNG NÀY
            let promptText = "Unknown Prompt";
            const reuseBtn = container.querySelector('.reuse-prompt-button');
            if (reuseBtn) {
                const btnContainer = reuseBtn.parentElement;
                if (btnContainer && btnContainer.previousElementSibling) {
                    promptText = btnContainer.previousElementSibling.innerText.trim();
                }
            }
            // Fallback nếu không tìm thấy nút reuse
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

    // Fallback: không có role="article"
    // Chỉ dùng fallback nếu hoàn toàn không tìm thấy danh sách chứa ảnh
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


# ──────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────

def find_el(page: Page, selectors: list, timeout=5000):
    combined_sel = ", ".join(selectors)
    try:
        el = page.wait_for_selector(combined_sel, timeout=timeout, state="visible")
        if el: return el, "combined"
    except Exception:
        pass
    return None, None


def wait_for_project_page(page: Page, log_fn=print, timeout=20) -> bool:
    log_fn("   ⏳ Chờ trang dự án...")
    deadline = time.time() + timeout
    signals = ['text="Nhân vật"', 'text="Characters"', 'div[role="textbox"]', 'text="Cảnh"']
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
        log_fn(f"   📂 Tìm thấy {len(urls)} dự án.")
        if urls:
            log_fn(f"   🔗 Vào: {urls[0][:80]}")
            page.goto(urls[0], wait_until="domcontentloaded", timeout=20000)
            return wait_for_project_page(page, log_fn)
    except Exception as e:
        log_fn(f"   ⚠️  JS scan lỗi: {e}")
    log_fn("   ➕ Tạo dự án mới...")
    el, _ = find_el(page, NEW_PROJECT_SELECTORS, timeout=8000)
    if not el: return False
    el.click()
    return wait_for_project_page(page, log_fn, timeout=20)


def fill_prompt(page: Page, prompt: str, log_fn=print) -> bool:
    el, _ = find_el(page, PROMPT_SELECTORS, timeout=10000)
    if not el:
        log_fn("   ❌ Không tìm thấy ô nhập!")
        return False
    log_fn("   ✍️  Đã gõ Prompt")
    try:
        el.click(); time.sleep(0.3)
        page.keyboard.press("Control+a"); time.sleep(0.1)
        page.keyboard.press("Backspace"); time.sleep(0.2)
        el.type(prompt, delay=30); time.sleep(0.5)
        return True
    except Exception as e:
        log_fn(f"   ❌ fill error: {e}")
        return False


def click_submit(page: Page, log_fn=print) -> bool:
    el, _ = find_el(page, SUBMIT_SELECTORS, timeout=5000)
    if el:
        log_fn("   🖱️  Click Submit: Đã tìm thấy nút Tạo")
        el.click(force=True)
        return True
    log_fn("   🖱️  JS fallback submit...")
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
            log_fn(f"   🖱️  JS click: '{clicked[:30]}'"); return True
    except Exception as e:
        log_fn(f"   ⚠️  JS submit error: {e}")
    log_fn("   🖱️  Enter fallback")
    page.keyboard.press("Enter")
    return True


def setup_flow_options(page: Page, expected_images: int, aspect_ratio: str, model: str,
                       output_type: str, seed: str = None, log_fn=print):
    log_fn(f"   ⚙️ Thiết lập: {output_type} | {expected_images} ảnh | {aspect_ratio} | {model} | Seed: {seed or 'Auto'}")
    target_count = str(expected_images)
    ratio_map = {
        "16:9 Ngang": "16:9", "9:16 Dọc": "9:16", "1:1 Vuông": "1:1", "4:3": "4:3", "3:4": "3:4",
    }
    web_ratio = ratio_map.get(aspect_ratio, aspect_ratio)

    try:
        # Bước 1: Tìm và Click nút Settings bằng Playwright Native Click
        # Tìm nút có text chứa thông tin model/crop và gán cho nó 1 ID tạm thời để Playwright click chính xác
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
            # Thực hiện click thật (Native Click) - tin cậy hơn JS click
            page.click('[data-qa-settings-trigger="true"]', delay=100)
            log_fn(f"   🖱️ Đã click nút Settings: '{btn_info[:40]}...'")
            
            # Kiểm tra xem panel đã mở chưa (thường là div có role menu hoặc data-state open)
            panel_opened = False
            for _ in range(5):
                time.sleep(0.5)
                panel_opened = page.evaluate("""() => {
                    const panel = document.querySelector('div[role="menu"][data-state="open"], div[data-test-id="settings-panel"]');
                    if (panel) {
                        // Đảm bảo panel đang hiển thị
                        const style = window.getComputedStyle(panel);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }
                    return false;
                }""")
                if panel_opened: break
            
            if not panel_opened:
                log_fn("   ⚠️ Đã click nhưng Panel Settings vẫn chưa xuất hiện."); return
            else:
                log_fn("   ✅ Panel Settings đã hiển thị.")
        else:
            log_fn("   ⚠️ Không tìm thấy nút Settings nào trên giao diện."); return

        # Bước 2: Loại output
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
                log_fn(f"   ✅ Đã click chọn output: {output_type}"); time.sleep(0.4)
            elif output_status == 'already_selected':
                log_fn(f"   ⏩ Bỏ qua output (đang ở sẵn: {output_type})")
            else:
                log_fn(f"   ⚠️ Không tìm thấy nút output: {output_type}")

        # Bước 3: Tỷ lệ (Ratio) - Native Click
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
            log_fn(f"   ✅ Đã click chọn tỷ lệ: {web_ratio}"); time.sleep(0.4)
        elif ratio_status == 'already_selected':
            log_fn(f"   ⏩ Bỏ qua tỷ lệ (đang ở sẵn: {web_ratio})")
        else:
            log_fn(f"   ⚠️ Không tìm thấy nút tỷ lệ: {web_ratio}")

        # Bước 4: Số lượng (Quantity) - Native Click
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
            log_fn(f"   ✅ Đã click chọn số lượng: {target_count}"); time.sleep(0.4)
        elif count_status == 'already_selected':
            log_fn(f"   ⏩ Bỏ qua số lượng (đang ở sẵn: {target_count})")
        else:
            log_fn(f"   ⚠️ Không tìm thấy nút số lượng: {target_count}")

        # Bước 5: Model dropdown bên trong panel
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
                    // Nếu text của nút đã hiển thị đúng model đang chọn thì bỏ qua
                    if (dropBtn.textContent.includes(modelName)) return 'already_selected';
                    
                    dropBtn.setAttribute('data-qa-model-dropdown', 'true');
                    return 'needs_click';
                } 
                return 'not_found';
            }""", model)

            if model_status == 'already_selected':
                log_fn(f"   ⏩ Bỏ qua model (đang ở sẵn: {model})")
            elif model_status == 'needs_click':
                page.click('[data-qa-model-dropdown="true"]', delay=100)
                log_fn("   🖱️ Đã click mở dropdown Model.")
                time.sleep(1.0) # Đợi animation mở popup
                
                model_found = page.evaluate("""(modelName) => {
                    const panels = Array.from(document.querySelectorAll('[role="menu"][data-state="open"], [role="dialog"], [role="listbox"]'));
                    const lastPanel = panels.length > 0 ? panels[panels.length - 1] : document;
                    const opts = Array.from(lastPanel.querySelectorAll('[role="menuitem"], [role="option"]'))
                        .filter(b => b.offsetParent !== null && b.checkVisibility()); // Chỉ lấy phần tử đang hiển thị
                    
                    const target = opts.find(el => (el.innerText || el.textContent || '').trim().includes(modelName));
                    if (target) {
                        target.setAttribute('data-qa-model-trigger', 'true');
                        return true;
                    }
                    return false;
                }""", model)
                if model_found:
                    page.click('[data-qa-model-trigger="true"]', delay=100)
                    log_fn(f"   ✅ Đã click chọn model: {model}")
                else:
                    log_fn(f"   ⚠️ Không click được model: {model}")
                time.sleep(0.5)
            else:
                log_fn("   ⚠️ Không tìm thấy dropdown model bên trong panel.")

        page.keyboard.press("Escape"); time.sleep(0.5)

    except Exception as e:
        log_fn(f"   ⚠️ Lỗi setup_flow_options: {e}")
        try: page.keyboard.press("Escape")
        except: pass

    if seed and seed.strip():
        try:
            inp = page.locator('input[placeholder*="Seed"], input[aria-label*="Seed"]').first
            if inp.count() > 0:
                inp.fill(seed.strip())
                log_fn(f"   🔢 Đã khóa Seed: {seed}")
        except Exception as e:
            log_fn(f"   ⚠️ Lỗi Seed: {e}")


def get_all_images(page: Page, log_fn=None) -> list[dict]:
    try:
        return page.evaluate(IMAGE_SCAN_JS) or []
    except Exception as e:
        if log_fn: log_fn(f"   ⚠️  scan images error: {e}")
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
                log_fn(f"   💾 Lưu: {os.path.basename(fpath)} ({len(data)//1024}KB)")
                return fpath
            else:
                log_fn(f"   ⚠️ Bỏ qua ảnh lỗi ({len(data)} bytes)")
    except Exception as e:
        log_fn(f"   ⚠️ Lỗi lưu ảnh {idx}: {e}")
    return None


# ──────────────────────────────────────────────────────
# ENGINE CHÍNH — v7
# Dùng before_urls để phân biệt ảnh mới (không dùng row index)
# isBlocked chỉ xét trên row CÓ CHỨA ảnh mới
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
    output_type: str = "Hình ảnh",
    task_name: str = None,
    seed: str = None
) -> list[str]:
    saved = []
    log_fn("\n🚀 G-Labs Engine v7...")

    try:
        if not ensure_chrome_running(log_fn): return []

        final_save_dir = os.path.join(save_dir, task_name) if task_name else save_dir
        os.makedirs(final_save_dir, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)
            context = browser.contexts[0]

            page = None
            for ep in context.pages:
                if "labs.google" in ep.url and "flow" in ep.url:
                    page = ep
                    try: page.bring_to_front()
                    except: pass
                    log_fn("   🔄 Sử dụng lại tab Google Labs đã mở.")
                    break

            if not page:
                page = context.new_page()
                page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                time.sleep(2)

            if new_project_each_run or "/project/" not in page.url:
                if new_project_each_run:
                    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(2)
                if not enter_project(page, log_fn):
                    log_fn("❌ Không xác định được dự án."); return []
            else:
                log_fn("   ✅ Tab đang ở sẵn trong dự án.")

            log_fn(f"🔗 URL Dự án: {page.url}")
            time.sleep(2)

            setup_flow_options(page, expected_images, aspect_ratio, model, output_type, seed, log_fn)

            # Quét toàn bộ lịch sử ảnh (từ đầu tới chân)
            log_fn("   🔍 Đang cuộn ngược để quét TOÀN BỘ ảnh cũ trong dự án...")
            all_existing_urls = set()
            unchanged_count = 0
            
            for _ in range(50):  # Cuộn tối đa 50 lần
                current_urls = set(page.evaluate(GET_ALL_URLS_JS))
                prev_total = len(all_existing_urls)
                all_existing_urls.update(current_urls)
                
                if len(all_existing_urls) > prev_total:
                    unchanged_count = 0
                    log_fn(f"      ...đã quét được {len(all_existing_urls)} ảnh/video")
                else:
                    unchanged_count += 1
                    if unchanged_count >= 3:  # Dừng nếu 3 lần cuộn không có ảnh mới
                        break
                        
                # Lệnh JS để tìm phần tử cuộn và đẩy lên trên
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
            log_fn(f"   📊 [DEBUG] Quét hoàn tất! Tổng số ảnh/video cũ trong dự án là: {len(existing_urls)}.")
            
            # Trả lại vị trí cuộn xuống dưới cùng để chuẩn bị gõ prompt
            page.evaluate("""() => {
                const articles = document.querySelectorAll('div[role="article"], div[data-testid="virtuoso-item-list"] > div[data-index]');
                if (articles.length > 0) articles[articles.length - 1].scrollIntoView();
            }""")
            time.sleep(1.0)
            
            # Debug kiểm tra cấu trúc Row theo Element mới
            log_fn("   🔍 Đang phân tích cấu trúc các lượt tạo ảnh (Rows)...")
            current_rows = page.evaluate(IMAGE_SCAN_JS)
            log_fn(f"   📝 [DEBUG] Tìm thấy {len(current_rows)} lượt tạo ảnh (Rows):")
            for r in current_rows:
                blocked = r.get('blockedCount', 0)
                blocked_str = f" | 🚫 Bị chặn (Policy): {blocked}" if blocked > 0 else ""
                log_fn(f"      - Row {r.get('rowIndex')} [Prompt: '{r.get('promptText')}']: chứa {r.get('count')} ảnh{blocked_str} | Đang load: {r.get('isBusy')}")

            # Quét và log ô nhập Prompt
            log_fn("   🔍 Đang quét ô nhập Prompt...")
            prompt_elements = page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], [role="textbox"]'));
                return els.map(e => `${e.tagName.toLowerCase()} (placeholder: "${e.getAttribute('placeholder') || ''}", role: "${e.getAttribute('role') || ''}")`);
            }""")
            log_fn(f"   📝 [DEBUG] Tìm thấy {len(prompt_elements)} ô nhập liệu tiềm năng:")
            for el in prompt_elements:
                log_fn(f"      - {el}")

            valid_prompts = [p.strip() for p in prompts if p.strip()]
            total = len(valid_prompts)

            for done, prompt in enumerate(valid_prompts, 1):
                if stop_fn and stop_fn(): break

                log_fn(f"\n{'━'*50}")
                log_fn(f"▶  [{done}/{total}] {prompt[:70]}")
                if on_gen_start: on_gen_start(done - 1, prompt)

                # Snapshot trước khi submit
                before_urls = set(page.evaluate(GET_ALL_URLS_JS))

                if not fill_prompt(page, prompt, log_fn): continue
                if not click_submit(page, log_fn): continue

                log_fn("   ⏳ Đang đợi Google sinh ảnh...")

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
                        row_imgs = r.get('images', [])
                        # Row này có chứa ảnh mới không?
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
                        log_fn(f"   ⏳ Đang render... {max_prog}%")
                        last_logged_prog = max_prog
                        last_change_time = time.time()

                    if on_gen_progress: on_gen_progress(done - 1, max_prog)

                    # Thoát khi đủ ảnh hoặc đạt 100%
                    total_resolved = len(strict_ready) + total_blocked
                    if total_resolved >= expected_images:
                        new_images = strict_ready; break
                    if (max_prog >= 100) and not any_busy and (len(relaxed_ready) + total_blocked > 0):
                        new_images = strict_ready if strict_ready else relaxed_ready; break
                    
                    # Kẹt lâu quá thì lấy ảnh hiện có
                    if (time.time() - last_change_time) > STABLE_WAIT and (len(relaxed_ready) + total_blocked > 0):
                        new_images = relaxed_ready; break

                    time.sleep(1)

                # Fallback lần cuối
                if not new_images:
                    final_rows = page.evaluate(IMAGE_SCAN_JS)
                    new_images = [
                        img for r in final_rows for img in r.get('images', [])
                        if img['src'] not in before_urls and img.get('isReadyRelaxed')
                    ]

                # Lưu ảnh
                for i, img in enumerate(new_images):
                    fp = save_one_media(img, page, final_save_dir, prompt, i + 1, log_fn)
                    if fp:
                        saved.append(fp)
                        if on_image_saved: on_image_saved(done - 1, fp)

                if done < total: time.sleep(BETWEEN_DELAY)

            log_fn(f"\n🎉 HOÀN THÀNH! Đã lưu {len(saved)} ảnh mới.")

    except Exception as e:
        log_fn(f"\n❌ LỖI: {e}")
        log_fn("💡 Chrome cần --remote-debugging-port=9222")

    return saved