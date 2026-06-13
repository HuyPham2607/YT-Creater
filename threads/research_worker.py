import json
import os
from pathlib import Path
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal
from threads.gemini_retry import generate_content_with_retries
from core.profile_context import (
    build_worker_focus_block,
    channel_context_user_note,
    get_or_create_shared_cache,
    worker_channel_fields,
)

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


# ============================================================
#  RESEARCH PROMPT BUILDER
#  Builds the research prompt based on topic + structure hint
# ============================================================

def _list_to_lines(items, prefix="- "):
    if not isinstance(items, list):
        return str(items or "").strip()
    return "\n".join(f"{prefix}{str(item).strip()}" for item in items if str(item).strip())


def _research_strategy_block(strategy: dict) -> str:
    if not isinstance(strategy, dict) or not strategy:
        return ""

    return f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC STRATEGY FROM TOPIC IDEATOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use this brief to decide what evidence to prioritise. Do not blindly validate the angle; actively check where it is strong, weak, or unsupported.

- Original topic: {strategy.get("title") or strategy.get("topic_name", "")}
- Selected title: {strategy.get("selected_title_text", "")}
- Target audience: {strategy.get("target_audience", "")}
- Viewer promise: {strategy.get("one_line_promise", "")}
- Viewer question: {strategy.get("viewer_question", "")}
- Unique angle: {strategy.get("unique_angle", "")}
- Better angle: {strategy.get("our_better_angle", "")}
- Local/Vietnam angle: {strategy.get("local_vietnam_angle", "")}
- Risk/watchout: {strategy.get("risk_or_watchout", "")}

Evidence requested by Topic Ideator:
{_list_to_lines(strategy.get("evidence_needed", []))}

Research keywords to prioritise:
{_list_to_lines(strategy.get("research_keywords", []))}

Retention hooks to fact-check or support:
{_list_to_lines(strategy.get("retention_hooks", []))}
"""


def build_research_prompt(config: dict) -> tuple[str, str]:
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    structure    = config.get("structure", "Auto")
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    extra        = config.get("extra_context", "")
    strategy     = config.get("topic_strategy", {})

    # Determine research depth hint based on structure
    structure_hint_map = {
        "Levels — Escalation (POV)": "Focus on layered facts — surface statistics first, then deeper systemic causes, then root mechanisms.",
        "Levels - Escalation":       "Focus on layered facts — surface statistics first, then deeper systemic causes, then root mechanisms.",
        "Acts — Story Arc (Narrative)": "Focus on real case studies, turning-point events, and narrative-worthy data points (stories of real people or situations).",
        "Acts - Story Arc":          "Focus on real case studies, turning-point events, and narrative-worthy data points.",
        "Timeline — Chronological":  "Focus on chronological milestones — specific years, key events, and cause-effect chains across time.",
        "Timeline":                  "Focus on chronological milestones — specific years, key events, and cause-effect chains across time.",
        "Chapters — Topic-based":    "Focus on distinct sub-topic facts — each cluster of facts should map to one standalone chapter.",
        "Chapters":                  "Focus on distinct sub-topic facts — each cluster of facts should map to one standalone chapter.",
        "Parts — Flexible":          "Focus on multi-angle facts — covering the problem, the mechanism, and the practical implications.",
        "Parts":                     "Focus on multi-angle facts — covering the problem, the mechanism, and the practical implications.",
        "Auto":                      "Cover all angles: statistics, root causes, real-world examples, expert consensus, and counterarguments.",
        "Custom":                    "Cover all angles: statistics, root causes, real-world examples, expert consensus, and counterarguments.",
    }
    structure_hint = structure_hint_map.get(structure, structure_hint_map["Auto"])

    extra_block = f"\nExtra context from creator: {extra}" if extra else ""
    strategy_block = _research_strategy_block(strategy)

    system_prompt = """You are a professional research analyst and fact-checker for a YouTube content team.
Gather verified factual data for a scriptwriter. Do NOT write script dialogue.

RULES:
1. Use specific data: percentages, years, named institutions/studies when possible.
2. Mark uncertain facts with ⚠️
3. Neutral tone. No editorialising.
4. Write research_notes in the creator's requested language.

Return ONLY JSON: {"research_notes": "<markdown>"}

Inside research_notes, use EXACTLY these 7 sections (markdown headings + bullets):

## RESEARCH NOTES — [TOPIC IN CAPS]
**Searches conducted:** [N] | **Confidence:** High/Medium/Low — [reason]

### 1. CORE STATISTICS & DATA
- **[Label]:** [data]. *(Source type, Year)* | ⚠️ if uncertain

### 2. ROOT CAUSES & MECHANISMS
- **[Mechanism]:** [1-2 sentences]

### 3. REAL-WORLD EXAMPLES & CASE STUDIES
- **[Name/Event]:** [what happened + what it illustrates, 2-3 sentences]

### 4. COMMON MISCONCEPTIONS
- **Myth:** ... **Reality:** ...

### 5. COUNTERARGUMENTS & NUANCE
- [strongest objection + data] | [complicating nuance]

### 6. NAMED ENTITIES
- **[Entity]:** [one-line relevance]

### 7. STRATEGY VALIDATION NOTES
- **Supported angle:** | **Needs hedging:** | **Avoid saying:** | **Best evidence for hook:**

End with: Research notes are preliminary — verify ⚠️ facts before scripting."""

    user_prompt = f"""Research this YouTube video topic.

REQUEST
- Topic: {topic}
- Language: {lang}
- Script: ~{target_words} words / {target_mins} min
- Structure: {structure}
- Focus: {structure_hint}{extra_block}{strategy_block}

MUST RESEARCH ALL 7 AREAS (do not skip any):
1. Statistics — numbers, source type, year
2. Root causes — why it happens, expert consensus
3. Case studies — named examples + what they prove
4. Misconceptions — myth vs reality
5. Counterarguments — strongest objection + nuance
6. Named entities — orgs, laws, reports, studies (correct names)
7. Strategy validation — what angle is supported, what to hedge, what to avoid, best hook evidence"""

    return system_prompt, user_prompt


def _profile_from_config(config: dict) -> dict:
    profile = dict(config.get("profile_data") or {})
    for key in ("dna_content", "style_content", "name", "niche", "lang"):
        if config.get(key):
            profile[key] = config.get(key)
    return profile


def _parse_research_response(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("AI response is empty.")
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("research_notes", "notes", "research", "content"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    except json.JSONDecodeError:
        pass
    return raw


# ============================================================
#  RESEARCH WORKER — QThread
# ============================================================

class ResearchWorker(QThread):
    progress_signal  = pyqtSignal(str)   # status bar messages
    research_signal  = pyqtSignal(str)   # emits research notes text
    finished_signal  = pyqtSignal()      # always emitted at end
    error_signal     = pyqtSignal(str)   # emits on failure

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def run(self):
        if genai is None:
            self.error_signal.emit("❌ LỖI: Thư viện 'google-genai' chưa được cài đặt.")
            self.finished_signal.emit()
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.error_signal.emit("❌ LỖI: Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client = genai.Client(api_key=api_key)

        try:
            self.progress_signal.emit("🔍 Đang research thông tin...")

            profile = _profile_from_config(self.config)
            channel_fields = worker_channel_fields("research", profile)
            if channel_fields.get("dna_content") and not self.config.get("dna_content"):
                self.config["dna_content"] = channel_fields["dna_content"]
            worker_focus = build_worker_focus_block("research", profile)

            system_prompt, user_prompt = build_research_prompt(self.config)

            def build_request(model_name):
                cached_name = None
                try:
                    cached_name = get_or_create_shared_cache(
                        client, model_name, profile, log_prefix="RESEARCH_WORKER",
                    )
                except Exception as cache_error:
                    print(f"⚠️ [RESEARCH_WORKER] Shared cache unavailable: {cache_error}")
                prompt = user_prompt
                if worker_focus and not cached_name:
                    prompt = f"{worker_focus}\n\n{prompt}"
                if cached_name:
                    prompt += channel_context_user_note()
                gen_kwargs = {
                    "system_instruction": system_prompt,
                    "temperature": float(self.config.get("temperature", 0.3)),
                    "response_mime_type": "application/json",
                }
                if cached_name:
                    gen_kwargs["cachedContent"] = cached_name
                return {
                    "contents": prompt,
                    "config": types.GenerateContentConfig(**gen_kwargs),
                }

            response, model_used = generate_content_with_retries(
                client=client,
                build_request=build_request,
                progress_callback=self.progress_signal.emit,
                log_prefix="RESEARCH_WORKER",
            )

            notes = _parse_research_response(response.text)
            self.research_signal.emit(notes)
            self.progress_signal.emit(f"✅ Research xong bằng {model_used} — kiểm tra rồi bấm Viết Script")

        except Exception as e:
            self.error_signal.emit(f"❌ Lỗi Research: {str(e)}")
        finally:
            self.finished_signal.emit()
