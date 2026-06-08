"""
asset_prompt_worker.py
======================
Nhận enriched prescan data (characters + backgrounds với description)
→ gọi Anthropic API → trả về dict prompt cho từng asset.

Input thay đổi so với v1:
  KHÔNG CẦN:  video_title, script_excerpt, raw character/bg name lists
  CẦN:        prescan_data (dict từ SceneWorker prescan result)
              char_style, bg_style, scene_style
"""

import json
import re
import os
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv
from threads.gemini_retry import generate_content_with_retries

load_dotenv()

MODEL = "gemini-3.5-flash"


def _clip_context(text, limit=10000):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[TRUNCATED]..."

# ──────────────────────────────────────────────
# SYSTEM PROMPTS
# ──────────────────────────────────────────────

CHAR_SYSTEM = """You are an expert AI image prompt engineer.
Generate a single character reference sheet prompt.

RULES:
1. Start with the sceneStyle verbatim as the aesthetic anchor.
2. Apply the charStyle as the visual base (proportions, outline, shading, skin tone).
3. Adapt CLOTHING and ERA-SPECIFIC details from the asset description provided.
   - If charStyle says "dark hoodie" but the character is ancient Egyptian → replace with
     "white linen kalasiris robe, gold collar" while keeping all other charStyle rules.
4. Use CHANNEL VISUAL DNA and STYLE GUIDE only for visual identity, mood, palette, cultural setting, recurring props, and forbidden visuals.
   - If they define a protagonist identity, silhouette rule, face-visibility rule, recurring props, or anti-luxury/no-logo rule, preserve it.
   - Do not use writing/tone/title rules unless they imply a visible design constraint.
5. Keep every non-clothing attribute from charStyle unchanged
   (outline weight, shading technique, skin tone, proportions, eye style, etc.)
6. Never include readable text, logo, brand mark, celebrity likeness, or copyrighted character likeness.
7. End EXACTLY with:
   "Professional white background, TOP ROW 4 full-body views front 45-degree side back,
   BOTTOM ROW 6 expression close-ups."
8. Output ONLY the prompt string. No JSON, no explanation, no markdown."""

BG_SYSTEM = """You are an expert AI image prompt engineer.
Generate a single background reference sheet prompt.

RULES:
1. Start with the sceneStyle verbatim as the aesthetic anchor.
2. Apply the bgStyle as the visual base (art style, palette, lighting, mood).
3. Adapt LOCATION-SPECIFIC details from the asset description provided.
   - If bgStyle mentions "Vietnamese urban night" but the location is ancient Egypt →
     keep the lighting/shading technique but replace architecture with Egyptian setting
     (sandstone walls, torchlight instead of neon, hieroglyph reliefs on walls, etc.)
4. Use CHANNEL VISUAL DNA and STYLE GUIDE only for visual identity, mood, palette, cultural setting, recurring props, and forbidden visuals.
   - Preserve recurring channel locations, palette, lighting, anti-luxury rules, no-logo rules, and cultural fit when compatible with this asset.
   - Do not use writing/tone/title rules unless they imply a visible design constraint.
5. Keep atmosphere and lighting style from bgStyle (single directional source, shadow zones, etc.)
6. Never include readable text, logo, brand mark, celebrity likeness, or copyrighted character likeness.
7. End EXACTLY with:
   "NO characters NO people NO text NO words, 16:9."
8. Output ONLY the prompt string. No JSON, no explanation, no markdown."""


# ──────────────────────────────────────────────
# USER MESSAGE BUILDERS
# ──────────────────────────────────────────────

def build_channel_context(channel_desc="", topic="", channel_dna="", style_guide=""):
    return f"""=== CHANNEL / VIDEO CONTEXT ===
Channel description:
{channel_desc or "No channel description provided."}

Video topic:
{topic or "No video topic provided."}

CHANNEL DNA - use only visual/brand-identity rules relevant to image prompts:
{_clip_context(channel_dna)}

STYLE GUIDE - use only visual rules relevant to image prompts:
{_clip_context(style_guide)}
"""


def build_char_user_message(asset_name, asset_info, char_style, scene_style, channel_desc="", topic="", channel_dna="", style_guide=""):
    samples = "\n".join(f"- {s}" for s in asset_info.get("sample_scenes", []))
    return f"""=== SCENE STYLE (paste verbatim at start) ===
{scene_style}

=== CHARACTER STYLE (aesthetic base) ===
{char_style}

{build_channel_context(channel_desc, topic, channel_dna, style_guide)}

=== CHARACTER TO GENERATE ===
Name: {asset_name}
Display name: {asset_info.get("display_name", asset_name)}
Era/Context: {asset_info.get("era_context", "modern")}
Description from script:
{asset_info.get("description", "No description available.")}
Continuity traits:
{asset_info.get("continuity_traits", "No continuity traits available.")}
Scene state rules:
{asset_info.get("scene_state_rules", "No scene state rules available.")}
Do not show:
{asset_info.get("do_not_show", "No do-not-show rules available.")}

Sample scenes this character appears in:
{samples}

Generate the character reference sheet prompt now."""


def build_bg_user_message(asset_name, asset_info, bg_style, scene_style, channel_desc="", topic="", channel_dna="", style_guide=""):
    samples = "\n".join(f"- {s}" for s in asset_info.get("sample_scenes", []))
    return f"""=== SCENE STYLE (paste verbatim at start) ===
{scene_style}

=== BACKGROUND STYLE (aesthetic base) ===
{bg_style}

{build_channel_context(channel_desc, topic, channel_dna, style_guide)}

=== BACKGROUND TO GENERATE ===
Name: {asset_name}
Display name: {asset_info.get("display_name", asset_name)}
Era/Context: {asset_info.get("era_context", "modern")}
Description from script:
{asset_info.get("description", "No description available.")}
Continuity traits:
{asset_info.get("continuity_traits", "No continuity traits available.")}
Scene state rules:
{asset_info.get("scene_state_rules", "No scene state rules available.")}
Do not show:
{asset_info.get("do_not_show", "No do-not-show rules available.")}

Sample scenes set in this location:
{samples}

Generate the background reference sheet prompt now."""


# ──────────────────────────────────────────────
# API CALL
# ──────────────────────────────────────────────

def call_api(system_prompt, user_message, progress_callback=None, log_prefix="ASSET_PROMPT"):
    if genai is None:
        raise ImportError("Thư viện 'google-genai' chưa được cài đặt.")
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Không tìm thấy GEMINI_API_KEY trong file .env!")
        
    client = genai.Client(api_key=api_key)
    gen_config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.7
    )
    
    response, _ = generate_content_with_retries(
        client=client,
        build_request=lambda model_name: {
            "contents": user_message,
            "config": gen_config,
        },
        progress_callback=progress_callback,
        log_prefix=log_prefix,
    )
    return response.text.strip()


# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────

def generate_all_prompts(
    prescan_data,
    char_style,
    bg_style,
    scene_style,
    channel_desc="",
    topic="",
    channel_dna="",
    style_guide="",
    on_progress=None,
    on_success=None,
    on_error=None,
):
    """
    Entry point — gọi từ nút "Generate All Prompts".

    Args:
        prescan_data:  dict từ SceneWorker prescan result (schema mới)
                       {
                         "characters": {"name": {description, era_context, sample_scenes}},
                         "backgrounds": {"name": {description, era_context, sample_scenes}}
                       }
        char_style, bg_style, scene_style: từ txt fields trong UI
        on_progress(str), on_success(dict), on_error(str): callbacks

    Returns:
        {"characters": {"name": "prompt..."}, "backgrounds": {"name": "prompt..."}}
    """
    try:
        errors = []
        if not char_style.strip():   errors.append("charStyle trống.")
        if not bg_style.strip():     errors.append("bgStyle trống.")
        if not scene_style.strip():  errors.append("sceneStyle trống.")
        if not prescan_data:         errors.append("Chưa có prescan data — hãy chạy Pre-scan trước.")
        if errors:
            raise ValueError("\n".join(errors))

        characters = prescan_data.get("characters", {})
        backgrounds = prescan_data.get("backgrounds", {})

        if not characters and not backgrounds:
            raise ValueError("prescan_data không có characters lẫn backgrounds.")

        result = {"characters": {}, "backgrounds": {}}
        total = len(characters) + len(backgrounds)
        done = 0

        for name, info in characters.items():
            if on_progress:
                on_progress(f"[{done+1}/{total}] Character: {name}...")
            msg = build_char_user_message(
                name, info, char_style, scene_style,
                channel_desc=channel_desc,
                topic=topic,
                channel_dna=channel_dna,
                style_guide=style_guide,
            )
            result["characters"][name] = call_api(CHAR_SYSTEM, msg, on_progress, "ASSET_CHAR")
            done += 1

        for name, info in backgrounds.items():
            if on_progress:
                on_progress(f"[{done+1}/{total}] Background: {name}...")
            msg = build_bg_user_message(
                name, info, bg_style, scene_style,
                channel_desc=channel_desc,
                topic=topic,
                channel_dna=channel_dna,
                style_guide=style_guide,
            )
            result["backgrounds"][name] = call_api(BG_SYSTEM, msg, on_progress, "ASSET_BG")
            done += 1

        if on_success:
            on_success(result)
        return result

    except Exception as e:
        if on_error:
            on_error(str(e))
        else:
            raise
        return None


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def prescan_to_display_lists(prescan_data):
    """prescan_data → (chars_str, bgs_str) để hiển thị lên txt_prescan_chars/bgs."""
    chars = "\n".join(prescan_data.get("characters", {}).keys())
    bgs   = "\n".join(prescan_data.get("backgrounds", {}).keys())
    return chars, bgs


# ──────────────────────────────────────────────
# HOW TO WIRE VÀO UI
# ──────────────────────────────────────────────
#
# 1. Trong scene_breakdown_tab._handle_worker_result, task_type == "prescan":
#
#    self._prescan_data = data   # lưu toàn bộ dict
#    from asset_prompt_worker import prescan_to_display_lists
#    chars_str, bgs_str = prescan_to_display_lists(data)
#    self.txt_prescan_chars.setPlainText(chars_str)
#    self.txt_prescan_bgs.setPlainText(bgs_str)
#
# 2. Khi transfer_to_tool3, thêm prescan_data vào signal hoặc lưu vào shared state.
#
# 3. Trong AssetPromptsTab._on_generate_all:
#
#    from asset_prompt_worker import generate_all_prompts
#    generate_all_prompts(
#        prescan_data = self._prescan_data,
#        char_style   = self.txt_char_style.toPlainText(),
#        bg_style     = self.txt_bg_style.toPlainText(),
#        scene_style  = self.txt_scene_style.toPlainText(),
#        on_progress  = lambda msg: self.btn_gen_all.setText(msg),
#        on_success   = self._on_gen_success,
#        on_error     = self._on_gen_error,
#    )
