(() => {
  const RX = {
    version: "0.1.1",
    lastError: null
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const norm = (text) => (text || "").trim().toLowerCase();

  function visible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
  }

  function allVisible(selector) {
    return Array.from(document.querySelectorAll(selector)).filter(visible);
  }

  function composerRoot() {
    const boxes = allVisible('textarea, [contenteditable="true"], [role="textbox"]');
    if (!boxes.length) return document.body;
    const input = boxes[boxes.length - 1];
    let node = input;
    for (let depth = 0; depth < 8 && node && node !== document.body; depth += 1) {
      const buttons = Array.from(node.querySelectorAll("button, [role='button']")).filter(visible);
      const hasPlus = buttons.some((button) => {
        const text = norm(button.innerText || button.textContent || button.getAttribute("aria-label"));
        return text === "+" || text.includes("add") || text.includes("them") || text.includes("thêm");
      });
      if (hasPlus) return node;
      node = node.parentElement;
    }
    return input.parentElement || document.body;
  }

  function countComposerMedia() {
    const root = composerRoot();
    return Array.from(root.querySelectorAll("img, video")).filter((el) => {
      const src = el.currentSrc || el.src || "";
      return visible(el) && src && !src.includes(".svg") && !src.startsWith("data:image/svg");
    }).length;
  }

  function findComposerPlus() {
    const boxes = allVisible('textarea, [contenteditable="true"], [role="textbox"]');
    const promptBox = boxes[boxes.length - 1];
    const promptRect = promptBox ? promptBox.getBoundingClientRect() : null;
    const buttons = allVisible("button, [role='button']");

    const candidates = buttons.filter((button) => {
      const rect = button.getBoundingClientRect();
      const text = norm(button.innerText || button.textContent || button.getAttribute("aria-label"));
      const isPlus = text === "+" || text.includes("add") || text.includes("them") || text.includes("thêm");
      if (!isPlus) return false;
      if (!promptRect) return rect.top > window.innerHeight * 0.55;
      const nearPromptY = rect.top >= promptRect.top - 80 && rect.bottom <= promptRect.bottom + 80;
      return nearPromptY;
    });
    if (candidates.length) {
      const scored = candidates.map((button) => {
        const rect = button.getBoundingClientRect();
        const insideMedia = !!button.closest("img, video, [data-rx-reference-result]");
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
      return scored[0].button;
    }

    return buttons.reverse().find((button) => {
      const rect = button.getBoundingClientRect();
      const text = norm(button.innerText || button.textContent || button.getAttribute("aria-label"));
      return rect.top > window.innerHeight * 0.65 &&
        (text === "+" || text.includes("add") || text.includes("them") || text.includes("thêm"));
    }) || null;
  }

  function findAssetSearchInput() {
    const inputs = allVisible('input[type="search"], [role="searchbox"], input')
      .filter((el) => !el.disabled && !el.readOnly);
    const pickerWords = [
      "tat ca", "tất cả", "hinh anh", "hình ảnh", "video",
      "giong noi", "giọng nói", "tep tai len", "tệp tải lên",
      "them vao cau lenh", "thêm vào câu lệnh", "add to prompt"
    ];

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
  }

  function setInputValue(input, value) {
    input.focus();
    input.value = value;
    input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function loadedImageIn(el) {
    return Array.from(el.querySelectorAll("img")).some((img) => {
      const src = img.currentSrc || img.src || "";
      const style = window.getComputedStyle(img);
      return src &&
        !src.includes(".svg") &&
        !src.startsWith("data:image/svg") &&
        (img.naturalWidth > 40 || img.width > 40) &&
        (img.naturalHeight > 40 || img.height > 40) &&
        parseFloat(style.opacity || "1") > 0.5 &&
        !style.filter.includes("blur");
    });
  }

  function resultCandidates(query) {
    const q = norm(query);
    const nodes = allVisible('[role="option"], [role="listitem"], button, div');
    return nodes.filter((el) => {
      const text = norm(el.innerText || el.textContent);
      if (!text.includes(q)) return false;
      const busy = /\b\d{1,3}%\b/.test(text) ||
        text.includes("uploading") ||
        text.includes("dang tai") ||
        text.includes("đang tải") ||
        text.includes("tai len") ||
        text.includes("tải lên");
      return !busy && loadedImageIn(el);
    });
  }

  function findAddToPromptButton() {
    const nodes = allVisible("button, [role='button'], div, span");
    return nodes.find((el) => {
      const text = norm(el.innerText || el.textContent);
      return text === "thêm vào câu lệnh" ||
        text.includes("thêm vào câu lệnh") ||
        text === "add to prompt" ||
        text.includes("add to prompt");
    }) || null;
  }

  async function openAssetPicker() {
    const plus = findComposerPlus();
    if (!plus) return { ok: false, error: "composer_plus_not_found" };
    plus.click();
    for (let i = 0; i < 20; i += 1) {
      await sleep(250);
      if (findAssetSearchInput()) return { ok: true };
    }
    return { ok: false, error: "picker_search_not_found" };
  }

  async function attachReference(filename, options = {}) {
    const timeoutMs = options.timeoutMs || 300000;
    const started = Date.now();
    const base = filename.replace(/\.[^.]+$/, "");
    const queries = [base, filename];
    const beforeMedia = countComposerMedia();
    let cycles = 0;

    while (Date.now() - started < timeoutMs) {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
      await sleep(250);

      const opened = await openAssetPicker();
      if (!opened.ok) {
        RX.lastError = opened.error;
        await sleep(1000);
        continue;
      }

      const input = findAssetSearchInput();
      if (!input) {
        RX.lastError = "asset_search_input_missing";
        await sleep(1000);
        continue;
      }

      for (const query of queries) {
        setInputValue(input, query);
        await sleep(900);

        const candidates = resultCandidates(query);
        if (!candidates.length) continue;

        candidates[0].click();
        await sleep(700);

        for (let i = 0; i < 40; i += 1) {
          const add = findAddToPromptButton();
          if (add) {
            add.click();
            for (let j = 0; j < 24; j += 1) {
              await sleep(250);
              if (countComposerMedia() > beforeMedia) {
                return { ok: true, filename, query, cycles };
              }
            }
            RX.lastError = "reference_count_did_not_increase";
            return { ok: false, filename, query, cycles, error: RX.lastError };
          }
          await sleep(250);
        }
        RX.lastError = "add_to_prompt_not_found";
      }

      cycles += 1;
      await sleep(1500);
    }

    return { ok: false, error: RX.lastError || "timeout", filename };
  }

  RX.openAssetPicker = openAssetPicker;
  RX.attachReference = attachReference;
  RX.countComposerMedia = countComposerMedia;

  window.rxFlowHelper = RX;
  window.postMessage({ source: "rx-flow-helper", type: "ready", version: RX.version }, "*");
})();
