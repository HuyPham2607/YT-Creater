"""
glabs_engine.py — v4
Fix dựa trên debug log thực tế:
- Nút submit: text chứa "Tạo" + type=submit (arrow_forwardTạo)
- Nút download: text chứa "Tải xuống" + type=button
- Ảnh kết quả: cần scan rộng hơn vì Flow dùng nhiều kiểu render
"""

from playwright.sync_api import sync_playwright, Page
import time, os, re, base64
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
FLOW_URL      = "https://labs.google/fx/tools/flow"
CDP_ENDPOINT  = "http://localhost:9222"
GEN_TIMEOUT   = 180
STABLE_WAIT   = 5
BETWEEN_DELAY = 3


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
    const results = [];
    
    // 1. Tất cả <img> có src thật
    document.querySelectorAll('img').forEach(img => {
        const src = img.src || '';
        if (!src || src.startsWith('data:image/svg') ) return;
        if (src.includes('spinner') || src.includes('loading')) return;
        if (!img.offsetParent) return;  // không visible
        const r = img.getBoundingClientRect();
        if (r.width < 50 || r.height < 50) return;  // quá nhỏ, không phải ảnh kết quả
        results.push({ type: 'img', src, w: r.width, h: r.height });
    });
    
    // 2. Div có background-image (Flow đôi khi dùng kiểu này)
    document.querySelectorAll('div, figure, section').forEach(el => {
        const bg = window.getComputedStyle(el).backgroundImage || '';
        if (!bg || bg === 'none') return;
        const m = bg.match(/url\(["']?([^"')]+)["']?\)/);
        if (!m) return;
        const src = m[1];
        if (src.startsWith('data:image/svg')) return;
        if (!el.offsetParent) return;
        const r = el.getBoundingClientRect();
        if (r.width < 100 || r.height < 100) return;
        results.push({ type: 'bg', src, w: r.width, h: r.height });
    });
    
    return results;
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


def wait_for_new_images(page: Page, before_count: int, log_fn=print) -> list[dict]:
    """Chờ số ảnh tăng lên, trả về list dict {type, src, w, h}."""
    log_fn(f"   ⏳ Chờ ảnh mới (hiện có: {before_count})...")
    deadline     = time.time() + GEN_TIMEOUT
    last_total   = before_count
    stable_since = None

    while time.time() < deadline:
        current = get_all_images(page)
        now     = len(current)

        if now > last_total:
            log_fn(f"   🖼️  {now} ảnh tổng (+{now - before_count} mới)")
            last_total   = now
            stable_since = time.time()

        if stable_since and (time.time() - stable_since) >= STABLE_WAIT:
            new_items = current[before_count:]
            log_fn(f"   ✅ Ổn định: {len(new_items)} ảnh mới.")
            return new_items

        time.sleep(2)

    log_fn("   ⏰ Timeout.")
    all_imgs = get_all_images(page)
    return all_imgs[before_count:]


def save_one_image(src: str, page: Page, save_dir: str,
                   prompt: str, idx: int, log_fn=print) -> str | None:
    """Lưu 1 ảnh từ src (data / blob / https)."""
    os.makedirs(save_dir, exist_ok=True)
    safe  = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{idx:02d}_{safe}.png"
    fpath = os.path.join(save_dir, fname)

    # data:image
    if src.startswith("data:image"):
        try:
            _, b64 = src.split(",", 1)
            Path(fpath).write_bytes(base64.b64decode(b64))
            log_fn(f"   💾 (data) {fname}")
            return fpath
        except Exception as e:
            log_fn(f"   ⚠️  data err: {e}")

    # blob / https → fetch qua JS
    if src.startswith("blob:") or src.startswith("http"):
        try:
            b64 = page.evaluate(f"""
                async () => {{
                    const r   = await fetch({repr(src)});
                    const buf = await r.arrayBuffer();
                    const arr = new Uint8Array(buf);
                    let s = ''; arr.forEach(b => s += String.fromCharCode(b));
                    return btoa(s);
                }}
            """)
            if b64:
                Path(fpath).write_bytes(base64.b64decode(b64))
                log_fn(f"   💾 (fetch) {fname}")
                return fpath
        except Exception as e:
            log_fn(f"   ⚠️  fetch err: {e}")

    return None


def click_download_buttons(page: Page, save_dir: str, prompt: str,
                            start_idx: int, log_fn=print) -> list[str]:
    """
    Fallback: click từng nút 'Tải xuống' → nhận file download.
    Dùng khi fetch trực tiếp thất bại.
    """
    saved = []
    os.makedirs(save_dir, exist_ok=True)

    try:
        # Tìm tất cả nút Tải xuống visible
        btns = page.query_selector_all('button')
        dl_btns = []
        for btn in btns:
            try:
                txt = btn.text_content() or ""
                if ("Tải xuống" in txt or "Download" in txt) and btn.is_visible():
                    dl_btns.append(btn)
            except Exception:
                continue

        log_fn(f"   📥 Tìm thấy {len(dl_btns)} nút Tải xuống")

        for i, btn in enumerate(dl_btns):
            try:
                safe  = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
                ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"{ts}_{start_idx + i:02d}_{safe}.png"
                fpath = os.path.join(save_dir, fname)

                with page.expect_download(timeout=30000) as dl_info:
                    btn.click()
                dl_info.value.save_as(fpath)
                log_fn(f"   💾 (dl-btn) {fname}")
                saved.append(fpath)
                time.sleep(0.5)
            except Exception as e:
                log_fn(f"   ⚠️  dl-btn #{i}: {e}")

    except Exception as e:
        log_fn(f"   ⚠️  click_download_buttons: {e}")

    return saved


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
        with sync_playwright() as p:
            log_fn(f"🔗 Kết nối Chrome ({CDP_ENDPOINT})...")
            browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)
            context = browser.contexts[0]

            log_fn("📄 Mở tab mới...")
            page = context.new_page()

            log_fn(f"🌐 {FLOW_URL}")
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)

            # Vào dự án nếu cần
            has_input = False
            try:
                el = page.query_selector('div[role="textbox"]')
                has_input = el is not None and el.is_visible()
            except Exception:
                pass

            if not has_input or new_project_each_run:
                if not enter_project(page, log_fn):
                    log_fn("❌ Không vào được dự án.")
                    page.close(); return []
            else:
                log_fn("📌 Đang trong dự án.")

            time.sleep(2)

            # Vòng lặp
            valid_prompts = [p.strip() for p in prompts if p.strip()]
            total = len(valid_prompts)

            for done, prompt in enumerate(valid_prompts, 1):
                if stop_fn and stop_fn():
                    log_fn("🛑 Dừng."); break

                log_fn(f"\n{'━'*50}")
                log_fn(f"▶  [{done}/{total}] {prompt[:70]}")

                # Đếm ảnh hiện tại
                before_imgs = get_all_images(page)
                before_count = len(before_imgs)
                log_fn(f"   📊 Ảnh hiện tại trước generate: {before_count}")

                # Điền prompt
                if not fill_prompt(page, prompt, log_fn):
                    log_fn("   ⏭️  Bỏ qua.")
                    continue

                # Chờ nút Tạo active (đôi khi cần vài giây sau khi gõ)
                log_fn("   ⏳ Chờ nút Tạo active...")
                time.sleep(1.5)

                # Submit
                if not click_submit(page, log_fn):
                    log_fn("   ⏭️  Bỏ qua.")
                    continue

                # Chờ ảnh mới
                new_items = wait_for_new_images(page, before_count, log_fn)

                if not new_items:
                    log_fn("   ⚠️  Không detect ảnh qua JS scan. Thử click nút Tải xuống...")
                    dl_paths = click_download_buttons(page, save_dir, prompt, 1, log_fn)
                    for fp in dl_paths:
                        saved.append(fp)
                        if on_image_saved: on_image_saved(fp)
                    continue

                # Lưu từng ảnh
                n_saved = 0
                for i, item in enumerate(new_items):
                    fp = save_one_image(item['src'], page, save_dir, prompt, i+1, log_fn)
                    if fp:
                        saved.append(fp)
                        n_saved += 1
                        if on_image_saved: on_image_saved(fp)
                    else:
                        # fetch thất bại → fallback nút tải xuống
                        log_fn(f"   ↩️  fetch thất bại cho ảnh #{i+1}, thử nút Tải xuống...")

                if n_saved == 0:
                    log_fn("   ↩️  Fallback: click nút Tải xuống trên trang...")
                    dl_paths = click_download_buttons(page, save_dir, prompt, 1, log_fn)
                    for fp in dl_paths:
                        saved.append(fp)
                        if on_image_saved: on_image_saved(fp)
                else:
                    log_fn(f"   ✨ Đã lưu {n_saved} ảnh.")

                if done < total:
                    time.sleep(BETWEEN_DELAY)

            page.close()
            log_fn(f"\n{'═'*50}")
            log_fn(f"🎉 XONG! {len(saved)} ảnh → {save_dir}")

    except Exception as e:
        log_fn(f"\n❌ LỖI: {e}")
        log_fn("💡 Chrome cần --remote-debugging-port=9222")

    return saved