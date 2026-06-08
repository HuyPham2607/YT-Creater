# CODEX HANDOFF - RX Tools / YT-Creater

Repo dang lam viec: `C:\newapp`

## Da Lam Trong Phien Nay

### Gemini retry/backoff
- Them `threads/gemini_retry.py`.
- Cac worker chinh da dung retry/fallback model khi gap `429`, `503`, timeout, `WinError 10054`, high demand.
- File lien quan: `threads/topic_worker.py`, `threads/research_worker.py`, `threads/script_worker.py`, `threads/scene_worker.py`, `threads/asset_prompt_worker.py`.

### Tool 2 - Scene Breakdown
- Bo field `SCENE STYLE PROMPT` khoi UI; scene style van lay ngam tu active profile.
- Pre-scan gio tao enriched continuity bible cho characters/backgrounds:
  - `description`, `continuity_traits`, `scene_state_rules`, `do_not_show`, `era_context`, `sample_scenes`.
- Prompt pre-scan da co rule:
  - narrator/voiceover khong phai character neu khong hien tren man hinh.
  - ngoi ke thu 2 / "ban" / implied viewer map ve `protagonist`.
  - background co the la visual space nhu `phone-screen`, `social-media-feed`, `success-feed`.
  - khong ep outfit/boi canh hien dai neu script la co dai, fantasy, hospital, school, etc.
- Assign Assets gio viet `image_prompt` rieng cho tung scene, dua tren:
  - prescan_data,
  - character/background list,
  - character style,
  - background style,
  - scene style.
- Them safe asset naming cho G-Labs:
  - brand/IP/dia danh/tieng rieng nhu `vietcombank`, `thu-do-ha-noi`, `doraemon` -> `Location01` / `Character01`.
- Them Run Pipeline: clean script -> split scenes -> pre-scan -> assign assets -> deduplicate.
- Them Deduplicate: gop scene lien ke trung character + background.
- Tool 2 truyen sang Tool 3 ca `prescan_data`, khong chi list ten.

### Tool 3 - Asset Reference Prompts
- Ket noi nut `Generate All Prompts` chay that.
- Input hien dung:
  - `prescan_data` tu Tool 2,
  - danh sach character/background,
  - topic,
  - channel description,
  - character style,
  - background style,
  - scene style,
  - channel DNA,
  - style guide.
- `threads/asset_prompt_worker.py` da duoc nang prompt:
  - tao character reference sheet prompt.
  - tao background reference sheet prompt.
  - dung DNA/Style Guide chi cho visual rules: palette, silhouette, protagonist identity, recurring props, cultural setting, no-logo/no-luxury.
- UI Tool 3 co output tabs:
  - `Characters`
  - `Backgrounds`
  - `All Prompts`
- Them `Copy Tab` va `Export Tab`.
- Luong dung dung: moi topic/video nen Generate All Prompts mot lan sau khi Tool 2 pre-scan/assign xong, vi character/background reference phu thuoc noi dung tung video.

## Kiem Tra Da Chay

```powershell
python -m py_compile threads/asset_prompt_worker.py ui/tab_asset_prompts.py ui/tab_scene_breakdown.py ui/main_window.py
```

## Luu Y Worktree

- Chua commit/stage.
- `__pycache__` la file tracked trong repo; neu compile/import lam doi `.pyc`, restore lai truoc khi commit.
- Cac file dang co thay doi lien quan phien nay:
  - `.gitignore`
  - `threads/gemini_retry.py`
  - `threads/topic_worker.py`
  - `threads/research_worker.py`
  - `threads/script_worker.py`
  - `threads/scene_worker.py`
  - `threads/asset_prompt_worker.py`
  - `ui/tab_scene_breakdown.py`
  - `ui/tab_asset_prompts.py`
  - `ui/main_window.py`

