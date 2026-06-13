import json
import os
import re

from PyQt6.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from threads.gemini_retry import generate_content_with_retries
from core.profile_context import (
    build_worker_focus_block,
    channel_context_user_note,
    get_or_create_shared_cache,
)

load_dotenv()


THUMBNAIL_SYSTEM = """You are a senior YouTube thumbnail strategist and AI image prompt director.
Your job is to create clickable but brand-safe thumbnail concepts and G-Labs image prompts.

Rules:
1. Optimize for mobile readability: thumbnail text must be 1 to 4 short words.
2. The generated image prompt must NOT ask the image model to render readable text. Text is added later in Canva.
3. Avoid logos, brand marks, copyrighted characters, celebrity likenesses, readable UI text, and luxury-flex visuals unless the channel rules explicitly allow them.
4. Respect the channel thumbnail rules, visual DNA, palette, character identity, and forbidden visuals.
5. Return ONLY valid JSON. No markdown, no explanation outside JSON.
"""


def _extract_json(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def build_thumbnail_prompt(config):
    return f"""Create thumbnail concepts for this video.

Return exactly this JSON schema:
{{
  "recommendation": {{
    "format": "short format name",
    "thumbnail_text": "1-4 words, uppercase if Vietnamese/English fits",
    "reason": "why this should earn clicks without misleading"
  }},
  "title_suggestions": ["short thumbnail text option 1", "option 2", "option 3", "option 4", "option 5"],
  "concepts": [
    {{
      "name": "concept name",
      "hook_visual": "what the viewer sees",
      "emotion": "dominant emotion",
      "thumbnail_text": "1-4 words",
      "layout_notes": "subject/text placement and contrast notes",
      "why_it_clicks": "CTR reasoning"
    }}
  ],
  "variations": [
    {{
      "name": "variation name",
      "text_line_1": "main thumbnail text",
      "text_line_2": "optional second line or empty string",
      "glabs_prompt": "image generation prompt, 16:9, no text rendered in image",
      "layout_notes": "how to place generated image and text"
    }}
  ],
  "canva_guide": ["step 1", "step 2", "step 3", "step 4"],
  "mobile_qc": ["check 1", "check 2", "check 3"]
}}

Hard requirements:
- Return 3 concepts.
- Return 3 G-Labs variations.
- Every glabs_prompt must say: no text, no words, no logos.
- Thumbnail text must be intended for overlay later, not inside generated image.

=== VIDEO CONTEXT ===
Video topic:
{config.get("topic") or "Not provided"}

Candidate title:
{config.get("title") or "Not provided"}

Short script summary / hook:
{config.get("summary") or "Not provided"}

Target audience:
{config.get("audience") or "Not provided"}

=== CHANNEL / PROFILE ===
Channel name:
{config.get("channel_name") or "Not provided"}

Niche:
{config.get("niche") or "Not provided"}

Visual style:
{config.get("visual") or "Not provided"}

Worker focus (thumbnail rules):
{config.get("worker_focus") or build_worker_focus_block("thumbnail", config)}

=== USER CONTROLS ===
Thumbnail format:
{config.get("format") or "AI choose"}

Background / setting:
{config.get("background") or "AI choose from channel rules"}

Character / key prop:
{config.get("character") or "AI choose from channel rules"}

Text line 1:
{config.get("text_line_1") or "AI choose"}

Text line 2:
{config.get("text_line_2") or ""}

Palette:
{config.get("palette") or "AI choose from channel rules"}

Reference thumbnail analysis:
{config.get("reference_analysis") or "No reference analysis provided."}
"""


class ThumbnailWorker(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            if genai is None:
                raise ImportError("google-genai is not installed.")
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in .env.")

            client = genai.Client(api_key=api_key)
            profile = {
                "dna_content": self.config.get("dna_content", ""),
                "style_content": self.config.get("style_guide") or self.config.get("style_content", ""),
            }
            self.config["worker_focus"] = build_worker_focus_block("thumbnail", profile)

            def build_thumbnail_request(model_name):
                cached_name = None
                try:
                    cached_name = get_or_create_shared_cache(
                        client,
                        model_name,
                        profile,
                        log_prefix="THUMBNAIL",
                    )
                except Exception as cache_error:
                    print(f"⚠️ [THUMBNAIL] Shared cache unavailable: {cache_error}")

                user_prompt = build_thumbnail_prompt(self.config)
                if cached_name:
                    user_prompt += channel_context_user_note()

                gen_kwargs = {
                    "system_instruction": THUMBNAIL_SYSTEM,
                    "temperature": 0.75,
                    "response_mime_type": "application/json",
                }
                if cached_name:
                    gen_kwargs["cachedContent"] = cached_name
                return {
                    "contents": user_prompt,
                    "config": types.GenerateContentConfig(**gen_kwargs),
                }

            response, _ = generate_content_with_retries(
                client=client,
                build_request=build_thumbnail_request,
                progress_callback=self.progress_signal.emit,
                log_prefix="THUMBNAIL",
            )
            self.result_signal.emit(_extract_json(response.text))
        except Exception as error:
            self.error_signal.emit(str(error))
