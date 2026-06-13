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


METADATA_SYSTEM = """You are a senior YouTube SEO editor and metadata strategist.
You create upload-ready metadata from a finished script and user-provided SEO research notes.

Critical rules:
1. Do not invent search volume, keyword difficulty, ranking probability, or market scores.
2. Use ONLY the user's SEO research notes for market/keyword evidence.
3. If research notes are missing or thin, mark seo_confidence as "unverified".
4. Be truthful to the script. Do not promise outcomes, facts, or topics not supported by the script.
5. Follow channel DNA over generic SEO advice.
6. Do not keyword-stuff. Keywords must read naturally.
7. Return valid JSON only. No markdown outside JSON.
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


def build_metadata_prompt(config):
    return f"""Generate a YouTube metadata package.

Return exactly this JSON schema:
{{
  "analysis": {{
    "core_promise": "what the video honestly promises",
    "viewer_intent": ["intent 1", "intent 2", "intent 3"],
    "emotional_triggers": ["trigger 1", "trigger 2"],
    "primary_keywords_from_user_research": ["keyword 1", "keyword 2"],
    "secondary_keywords_from_user_research": ["keyword 1", "keyword 2"],
    "seo_confidence": "verified_by_user_notes | partial | unverified",
    "seo_confidence_reason": "explain based on whether research notes were provided",
    "metadata_risks": ["risk 1", "risk 2"]
  }},
  "title_options": [
    {{
      "title": "upload title",
      "angle": "title strategy",
      "keywords_used": ["keyword"],
      "channel_fit_reason": "why it fits channel DNA",
      "seo_note": "based only on user research notes, or say unverified"
    }}
  ],
  "description": {{
    "hook": "first 2-3 lines",
    "body": "main description body",
    "cta": "light CTA",
    "full_text": "complete ready-to-paste YouTube description"
  }},
  "tags": {{
    "broad": ["tag"],
    "specific": ["tag"],
    "long_tail": ["tag"],
    "all_comma_separated": "tag1, tag2, tag3"
  }},
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
  "chapters": [
    {{"time": "0:00", "title": "chapter title"}}
  ],
  "pinned_comment": "comment",
  "upload_notes": ["note 1", "note 2"]
}}

Requirements:
- Return 5 title options.
- Titles must obey the channel title rules if provided.
- If the metadata language is Vietnamese, write natural Vietnamese titles/descriptions/tags.
- Description must not sound like keyword spam.
- Chapters must use standard YouTube timestamps. Estimate timestamps from script structure if exact timings are unavailable.
- If user SEO research notes include selected keywords, prioritize them. If they do not, say seo_confidence is unverified.

=== VIDEO CONTEXT ===
Working title:
{config.get("title") or "Not provided"}

Video topic:
{config.get("topic") or "Not provided"}

Metadata language:
{config.get("language") or "Vietnamese"}

Channel name:
{config.get("channel_name") or "Not provided"}

Niche:
{config.get("niche") or "Not provided"}

Target audience:
{config.get("audience") or "Not provided"}

Thumbnail concept/text:
{config.get("thumbnail_context") or "Not provided"}

=== USER SEO RESEARCH NOTES ===
Use this as the ONLY source of market/keyword evidence:
{config.get("seo_notes") or "No user SEO research notes provided."}

=== CHANNEL DNA / STYLE GUIDE (WORKER FOCUS) ===
{config.get("worker_focus") or "Not provided"}

=== FINAL SCRIPT ===
{(config.get("script") or "Not provided").strip()}
"""


class MetadataWorker(QThread):
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
            self.config["worker_focus"] = build_worker_focus_block("metadata", profile)

            def build_metadata_request(model_name):
                cached_name = None
                try:
                    cached_name = get_or_create_shared_cache(
                        client,
                        model_name,
                        profile,
                        log_prefix="METADATA",
                    )
                except Exception as cache_error:
                    print(f"⚠️ [METADATA] Shared cache unavailable: {cache_error}")

                user_prompt = build_metadata_prompt(self.config)
                if cached_name:
                    user_prompt += channel_context_user_note()

                gen_kwargs = {
                    "system_instruction": METADATA_SYSTEM,
                    "temperature": 0.55,
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
                build_request=build_metadata_request,
                progress_callback=self.progress_signal.emit,
                log_prefix="METADATA",
            )
            self.result_signal.emit(_extract_json(response.text))
        except Exception as error:
            self.error_signal.emit(str(error))
