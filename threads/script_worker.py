import os
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

load_dotenv()


# ============================================================
#  STRUCTURE PROMPT LIBRARY
#  Each function returns a (system_prompt, user_prompt) tuple.
#  All prompts are in English.
# ============================================================

def _build_metadata_block(topic, target_mins, target_words, parts, structure_label):
    """Shared metadata block injected into every user prompt."""
    return f"""=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration : {target_mins} minutes
- Total Words     : ~{target_words} words
- Number of Parts : {parts}
- Structure Used  : {structure_label}

---"""


def _word_count_rules(target_words):
    """Shared word-count enforcement instructions."""
    margin = max(int(target_words * 0.03), 25)
    low    = target_words - margin
    high   = target_words + margin
    return f"""
⚠️  WORD COUNT — MANDATORY ENFORCEMENT
- Count ONLY spoken dialogue and CTA text.
- Do NOT count metadata, section headers, dividers, timestamps, bracketed performance cues, or the final estimated-word-count line.
- Spoken dialogue + CTA MUST land between {low} and {high} words.
- After drafting, estimate the spoken-dialogue word count only.
- If under → expand with concrete lived examples, emotional specificity, or practical reflection.
- If over  → cut filler phrases, repeated ideas, and decorative lines.
- ALWAYS end the script with this line (replace XXX with your actual estimate):
  [Estimated word count: XXX / Target: {target_words}]
"""


def _shared_output_rules():
    return """
GLOBAL OUTPUT RULES (apply to ALL structures):
1. Write mostly spoken dialogue. Short performance cues are allowed ONLY when useful for pacing.
2. Every sentence on its own line — one line break between sentences, one blank line between paragraphs.
3. Section headers must use this exact syntax:  === SECTION NAME ===
4. Level / Chapter / Act dividers use:  --- LABEL ---
5. Key declarations or harsh truths: wrap in *asterisks*  e.g. *This is the first illusion.*
6. Optional call-to-action beats: >>> ACTION LAYER: [content]
7. The very last section is always  === OUTRO ===
8. Allowed bracketed cues: [PAUSE], [CHẬM], [TEXT OVERLAY: ...], [MUSIC DROP]. Use sparingly.
9. Do NOT add camera directions, B-roll lists, editing notes, or scene production notes.
10. NO intro greetings. NO closing remarks from you. Output the script ONLY.
"""


def _research_injection(research_notes: str) -> str:
    """
    Returns a formatted block to append to any user_prompt when
    research notes are available. Empty string if no notes.
    """
    if not research_notes or not research_notes.strip():
        return ""
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFIED RESEARCH NOTES (use these facts in the script — do NOT invent new statistics)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The research team has pre-gathered the following data for this script.
RULES for using this data:
- Prioritise facts from this block over your own training data when they conflict.
- Any fact marked ⚠️ is uncertain — either omit it or flag it with hedging language in the script.
- You do NOT need to use every fact — select only those that serve the script's structure and flow.
- Do NOT copy the research notes verbatim — weave the facts naturally into the dialogue.

{research_notes}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF RESEARCH NOTES — Now write the script below.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def _factuality_rules(research_notes: str) -> str:
    if research_notes and research_notes.strip():
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACTUALITY MODE — RESEARCH-BACKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- You may use specific statistics, studies, years, named institutions, or case examples ONLY when they are present in the research notes.
- If research notes are uncertain or marked ⚠️, hedge the claim naturally or omit it.
- Do not invent additional facts outside the research notes.
"""

    return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FACTUALITY MODE — SCRIPT-ONLY / NO RESEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Do NOT invent statistics, percentages, study results, named institutions, laws, reports, dates, or named case studies.
- Avoid phrases like "research shows", "studies prove", "data says", or exact percentages unless provided by research notes.
- You may use general human observations, emotional truths, everyday examples, and culturally familiar situations.
- If you need credibility, phrase it as lived experience or common pattern, not as verified data.
"""


def _list_to_lines(items, prefix="- "):
    if not isinstance(items, list):
        return str(items or "").strip()
    return "\n".join(f"{prefix}{str(item).strip()}" for item in items if str(item).strip())


def _title_options_to_lines(titles):
    if not isinstance(titles, list):
        return ""
    lines = []
    for item in titles:
        if not isinstance(item, dict):
            continue
        text = item.get("text", "")
        formula = item.get("formula", "")
        score = item.get("score", "")
        parts = [text]
        meta = " / ".join(str(v) for v in [formula, f"score {score}" if score != "" else ""] if v)
        if meta:
            parts.append(f"({meta})")
        line = " ".join(str(part).strip() for part in parts if str(part).strip())
        if line:
            lines.append(f"- {line}")
    return "\n".join(lines)


def _topic_strategy_injection(strategy: dict) -> str:
    if not isinstance(strategy, dict) or not strategy:
        return ""

    selected_title = strategy.get("selected_title_text") or ""
    original_topic = strategy.get("title") or strategy.get("topic_name") or ""
    titles = _title_options_to_lines(strategy.get("titles", []))
    retention_hooks = _list_to_lines(strategy.get("retention_hooks", []))
    script_path = _list_to_lines(strategy.get("script_path", []))
    evidence_needed = _list_to_lines(strategy.get("evidence_needed", []))
    research_keywords = _list_to_lines(strategy.get("research_keywords", []))

    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCRIPT STRATEGY BRIEF FROM TOPIC IDEATOR — USE, BUT DO NOT PRINT AS A SEPARATE SECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This brief is the creative strategy behind the selected topic. Use it to shape the script's angle, emotional arc, examples, transitions, and retention design.

FORMAT PRESERVATION RULE:
- Keep the required script output format from the structure prompt exactly.
- Keep metadata, section headers, notes, outro, and word-count line exactly as requested.
- Do NOT add a JSON block.
- Do NOT print this strategy brief as its own section.

SELECTED TITLE:
{selected_title}

ORIGINAL TOPIC:
{original_topic}

TARGET AUDIENCE:
{strategy.get("target_audience", "")}

VIEWER PROMISE:
{strategy.get("one_line_promise", "")}

CORE VIEWER QUESTION:
{strategy.get("viewer_question", "")}

EMOTIONAL DRIVER:
{strategy.get("emotional_driver", "")}

UNIQUE ANGLE:
{strategy.get("unique_angle", "")}

COMPETITOR COMMON ANGLE:
{strategy.get("competitor_common_angle", "")}

OUR BETTER ANGLE:
{strategy.get("our_better_angle", "")}

TREND / LOCAL RELEVANCE:
{strategy.get("trend_connection", "")}
{strategy.get("local_vietnam_angle", "")}

TITLE OPTIONS:
{titles}

RETENTION OPEN LOOPS TO WEAVE INTO THE SCRIPT:
{retention_hooks}

RECOMMENDED SCRIPT PATH:
{script_path}

EVIDENCE NEEDED:
{evidence_needed}

RESEARCH KEYWORDS:
{research_keywords}

VISUAL POTENTIAL:
{strategy.get("visual_potential", "")}

RISK / WATCHOUT:
{strategy.get("risk_or_watchout", "")}

SCORING CONTEXT:
- CTR: {strategy.get("ctr_level", "")} / {strategy.get("ctr_score", "")}
- Evergreen: {strategy.get("evergreen_score", "")}
- Originality: {strategy.get("originality_score", "")}
- Production: {strategy.get("production_score", "")}
- Overall: {strategy.get("overall_score", "")}

WRITING INTERPRETATION:
- Start from the viewer's lived tension, not from an abstract lecture.
- Build the script around the better angle, not the generic competitor angle.
- Use the retention hooks as open loops across the script, then resolve them progressively.
- Use the recommended script path as the backbone unless the selected structure requires a cleaner order.
- Treat risk/watchout as a guardrail: avoid exaggeration, victim-blaming, fake certainty, or unsupported claims.
"""


def _creator_extra_context_injection(extra_context: str) -> str:
    if not extra_context or not extra_context.strip():
        return ""
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CREATOR EXTRA INSTRUCTIONS — APPLY WITHOUT BREAKING FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{extra_context.strip()}
"""


# ------------------------------------------------------------------
#  1. LEVELS — ESCALATION  (LV)
# ------------------------------------------------------------------
def prompt_levels(config):
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    pov          = config.get("pov", "Second person (You)")
    parts        = config.get("parts", 3)
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    dna          = config.get("dna_content", "")
    style        = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter specialising in ESCALATION-style scripts.
Your job is to write a video script that pulls the viewer deeper with every single section.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés ("amazingly", "surprisingly", "you won't believe").
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "LEVELS — Escalation")

    user_prompt = f"""Write a LEVELS (Escalation) video script with the parameters below.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE DEFINITION — LEVELS (ESCALATION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core philosophy:
  Each part = one escalating level. Every level must be MORE intense, deeper,
  or more complex than the one before. The viewer is pulled progressively deeper.
  NEVER let two consecutive levels feel equal in weight or depth.

Level architecture for {parts} parts:
  - Level 1  → Surface / Entry point: something the viewer already half-knows.
  - Level 2…{parts-1} → Each raises stakes, introduces new friction or complexity.
  - Level {parts} → The core / peak insight: the hardest truth most people never reach.

Transition rule:
  Every level transition must contain a REFRAME — the viewer's understanding
  must visibly shift between levels. Use phrases that signal a gear-change.

Section naming:
  Do NOT use generic names like "Level 1, Level 2".
  Give each level a meaningful label that hints at its depth.
  Examples: [Bề mặt] → [Sự thật ẩn] → [Gốc rễ]
            [Triệu chứng] → [Nguyên nhân] → [Hệ thống]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic         : {topic}
- Language      : {lang}
- POV           : {pov}
- Parts (Levels): {parts}  ← this is the number of LEVELS, excluding Hook and Outro
- Target words  : {target_words}
- Target mins   : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Exact template to follow:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration : {target_mins} minutes
- Total Words     : ~{target_words} words
- Number of Levels: {parts}
- Applied Structure: LEVELS — Escalation

---

=== HOOK (0:00 – 0:xx) ===
[Sentence 1 of hook]

[Sentence 2 of hook]

[Closing hook line — do NOT resolve the tension yet]

--- LEVEL 1 — [MEANINGFUL LABEL] ---

[Opening sentence of level 1]

[Body of level 1 — one sentence per line, blank line between thoughts]

*[Key declaration if applicable]*

--- LEVEL 2 — [MEANINGFUL LABEL] ---

[Content...]

--- LEVEL {parts} — [MEANINGFUL LABEL] ---

[Peak insight — the deepest layer]

*[Final hard-truth statement]*

>>> ACTION LAYER: [Optional CTA beat]

---

=== OUTRO ===
[Closing thought / reflection prompt]

[Final line]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ------------------------------------------------------------------
#  2. ACTS — STORY ARC  (Narrative)
# ------------------------------------------------------------------
def prompt_acts(config):
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    pov          = config.get("pov", "First person (I)")
    parts        = config.get("parts", 3)
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    dna          = config.get("dna_content", "")
    style        = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter specialising in NARRATIVE storytelling scripts.
Your job is to write a story-driven script with a clear 3-act dramatic arc.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés.
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "ACTS — Story Arc")

    # Distribute parts across 3 acts
    act_note = ""
    if parts <= 3:
        act_note = "Use exactly 3 Acts. Each act = 1 part."
    else:
        act_note = f"You have {parts} parts to distribute across 3 Acts. Split them proportionally: Act 1 gets ~1 part, Act 2 gets ~{parts-2} parts (this is where conflict deepens), Act 3 gets ~1 part."

    user_prompt = f"""Write an ACTS (Story Arc / Narrative) video script with the parameters below.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE DEFINITION — ACTS (STORY ARC)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core philosophy:
  Classic 3-act narrative structure. There must be a protagonist (can be the
  narrator, viewer, or a character), a conflict, a turning point, and a resolution.
  The viewer emotionally follows a journey, not just receives information.

Act blueprint:
  - ACT 1 — Setup    : Introduce the world, character, and the central problem.
                        End with the inciting incident that breaks the status quo.
  - ACT 2 — Conflict : The struggle. Attempts, failures, deeper complications.
                        Must contain at least one major turning point / reversal.
  - ACT 3 — Resolution: The insight, transformation, or lesson earned from the journey.
                         NOT a happy ending — an honest one.

Part distribution note:
  {act_note}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic   : {topic}
- Language: {lang}
- POV     : {pov}
- Parts   : {parts}
- Target words: {target_words}
- Target mins : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Exact template to follow:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration  : {target_mins} minutes
- Total Words      : ~{target_words} words
- Number of Parts  : {parts}
- Applied Structure: ACTS — Story Arc

---

=== HOOK (0:00 – 0:xx) ===
[Opening scene or statement that drops the viewer into the story mid-motion]

[One or two lines establishing stakes]

--- ACT 1 — [MEANINGFUL LABEL: e.g. THE WORLD I THOUGHT I KNEW] ---

[Setup content — introduce context, character state, the illusion of normalcy]

*[Inciting incident — the moment everything changes]*

--- ACT 2 — [MEANINGFUL LABEL: e.g. THE CRACK IN THE FOUNDATION] ---

[Conflict and struggle — attempts, failures, deepening complications]

[Turning point]

*[The hardest moment — the lowest point or most brutal realisation]*

--- ACT 3 — [MEANINGFUL LABEL: e.g. WHAT THE WRECKAGE TAUGHT ME] ---

[Resolution — not a fix, but a truth earned through the journey]

*[Final statement — honest, not inspirational-poster]*

>>> ACTION LAYER: [Optional CTA beat]

---

=== OUTRO ===
[Reflection or question left with the viewer]

[Final line]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ------------------------------------------------------------------
#  3. TIMELINE — CHRONOLOGICAL  (Educational)
# ------------------------------------------------------------------
def prompt_timeline(config):
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    pov          = config.get("pov", "Third person (Narrator)")
    parts        = config.get("parts", 4)
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    dna          = config.get("dna_content", "")
    style        = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter specialising in CHRONOLOGICAL educational scripts.
Your job is to guide the viewer through a clear, logical timeline that builds understanding step by step.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés.
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "TIMELINE — Chronological")

    user_prompt = f"""Write a TIMELINE (Chronological) educational video script with the parameters below.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE DEFINITION — TIMELINE (CHRONOLOGICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core philosophy:
  Present information along a LINEAR time axis. Each part = one time period or
  milestone. Order is FIXED — past to present (or present to projected future).
  The viewer's understanding compounds as the timeline progresses.

Timeline architecture for {parts} parts:
  - Part 1 → The beginning / origin point
  - Part 2…{parts-1} → Key milestones in chronological order
  - Part {parts} → Present day or future projection / lesson from the full arc

Writing rules:
  - Each milestone must include a SPECIFIC time marker (year, decade, period).
  - Connect each milestone to the next with a cause-effect bridge sentence.
  - The final milestone must answer: "So what does all of this mean TODAY?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic   : {topic}
- Language: {lang}
- POV     : {pov}
- Parts (Milestones): {parts}
- Target words: {target_words}
- Target mins : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Exact template to follow:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration  : {target_mins} minutes
- Total Words      : ~{target_words} words
- Number of Parts  : {parts}
- Applied Structure: TIMELINE — Chronological

---

=== HOOK (0:00 – 0:xx) ===
[Open with the END of the story — the most dramatic outcome — then rewind to the beginning]

[Bridge sentence: "To understand how we got here, we need to go back to..."]

--- MILESTONE 1 — [TIME MARKER: e.g. 1971 / Early 2000s / The Beginning] ---

[Content for this period]

*[Key shift or revelation from this era]*

--- MILESTONE 2 — [TIME MARKER] ---

[Content...]

[Cause-effect bridge to next milestone]

--- MILESTONE {parts} — [TIME MARKER: e.g. TODAY / 2024 / The Present] ---

[What the full arc means now]

*[Final insight — what history is actually telling us]*

>>> ACTION LAYER: [Optional CTA beat]

---

=== OUTRO ===
[Forward-looking question or reflection]

[Final line]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ------------------------------------------------------------------
#  4. CHAPTERS — TOPIC-BASED  (Educational)
# ------------------------------------------------------------------
def prompt_chapters(config):
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    pov          = config.get("pov", "Second person (You)")
    parts        = config.get("parts", 5)
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    dna          = config.get("dna_content", "")
    style        = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter specialising in TOPIC-BASED educational scripts.
Your job is to write a structured script where each chapter covers one distinct sub-topic completely.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés.
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "CHAPTERS — Topic-based")

    words_per_chapter = int(target_words / (parts + 1))  # +1 for hook/outro

    user_prompt = f"""Write a CHAPTERS (Topic-based) educational video script with the parameters below.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE DEFINITION — CHAPTERS (TOPIC-BASED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core philosophy:
  Each chapter = one self-contained sub-topic. Chapters are INDEPENDENT —
  the viewer could jump into any chapter and still fully understand it.
  This is the "textbook" or "listicle" structure: clear, complete, scannable.

Chapter architecture for {parts} chapters:
  - Hook introduces the full list or the central question.
  - Each chapter opens with a clear CHAPTER PREMISE (one sentence stating what this chapter is about).
  - Each chapter closes with a MICRO-CONCLUSION (one sentence summarising the takeaway).
  - Chapters do NOT need to connect causally — but thematically they serve the main topic.

Word distribution guide:
  - Hook: ~{int(target_words * 0.08)} words
  - Each chapter: ~{words_per_chapter} words
  - Outro: ~{int(target_words * 0.07)} words
  - Total target: {target_words} words

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic   : {topic}
- Language: {lang}
- POV     : {pov}
- Chapters: {parts}
- Target words: {target_words}
- Target mins : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Exact template to follow:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration  : {target_mins} minutes
- Total Words      : ~{target_words} words
- Number of Chapters: {parts}
- Applied Structure: CHAPTERS — Topic-based

---

=== HOOK (0:00 – 0:xx) ===
[Frame the full list — tease what all {parts} chapters will cover]

[Why this topic matters — create urgency to watch all chapters]

--- CHAPTER 1 — [TOPIC TITLE] ---

[Chapter premise: one sentence stating exactly what this chapter covers]

[Full dialogue for chapter 1]

*[Micro-conclusion: one-sentence takeaway]*

--- CHAPTER 2 — [TOPIC TITLE] ---

[Chapter premise]

[Content...]

*[Micro-conclusion]*

--- CHAPTER {parts} — [TOPIC TITLE] ---

[Content...]

*[Micro-conclusion]*

>>> ACTION LAYER: [Optional CTA beat]

---

=== OUTRO ===
[Synthesise the {parts} chapters into one overarching insight]

[Final line / reflection]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ------------------------------------------------------------------
#  5. PARTS — FLEXIBLE  (Educational)
# ------------------------------------------------------------------
def prompt_parts(config):
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    pov          = config.get("pov", "Second person (You)")
    parts        = config.get("parts", 4)
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    dna          = config.get("dna_content", "")
    style        = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter specialising in FLEXIBLE educational scripts.
Your job is to choose the most logical internal organisation for the given topic and execute it fully.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés.
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "PARTS — Flexible")

    user_prompt = f"""Write a PARTS (Flexible) video script with the parameters below.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE DEFINITION — PARTS (FLEXIBLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Core philosophy:
  The most open structure. YOU decide the best internal logic for this topic.
  Parts do not need to escalate, follow a timeline, or be independent chapters.
  Choose whatever organisation makes the content clearest and most compelling.

Possible internal logics you can choose from:
  - Problem → Mechanism → Solution
  - Myth → Reality → Implication
  - Before → During → After
  - Why → What → How
  - Surface → Root → Fix
  - Or any other logic that serves this specific topic best

Rules:
  - State your chosen logic INSIDE the metadata block as "Part Logic".
  - Each part must have a clear PURPOSE that is distinct from other parts.
  - Parts must flow — add a transition or bridge sentence between parts.

Total parts required: {parts}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic   : {topic}
- Language: {lang}
- POV     : {pov}
- Parts   : {parts}
- Target words: {target_words}
- Target mins : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Exact template to follow:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration  : {target_mins} minutes
- Total Words      : ~{target_words} words
- Number of Parts  : {parts}
- Applied Structure: PARTS — Flexible
- Part Logic Used  : [AI fills this in — e.g. Problem → Mechanism → Solution]

---

=== HOOK (0:00 – 0:xx) ===
[Hook content]

--- PART 1 — [MEANINGFUL LABEL] ---

[Content]

*[Key declaration if applicable]*

--- PART 2 — [MEANINGFUL LABEL] ---

[Content]

[Bridge to next part]

--- PART {parts} — [MEANINGFUL LABEL] ---

[Content]

*[Final insight]*

>>> ACTION LAYER: [Optional CTA beat]

---

=== OUTRO ===
[Closing thought]

[Final line]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ------------------------------------------------------------------
#  6. AUTO — Claude / AI decides (Smart)
# ------------------------------------------------------------------
def prompt_auto(config):
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    pov          = config.get("pov", "Second person (You)")
    parts        = config.get("parts", "Auto")
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    dna          = config.get("dna_content", "")
    style        = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter and content strategist.
Your first job is to ANALYSE the topic and CHOOSE the most effective script structure from the five available options.
Your second job is to execute that structure flawlessly.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés.
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "AUTO — AI decides")

    user_prompt = f"""Write a video script using the AUTO structure selection mode.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — STRUCTURE SELECTION (do this silently, then state your choice in metadata)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Analyse the topic: "{topic}"
Select the BEST structure from:
  A) LEVELS — Escalation  : Best for "most people don't know the full depth" topics
  B) ACTS   — Story Arc   : Best for personal journey, case studies, turning-point stories
  C) TIMELINE — Chron.   : Best for history, evolution, "how we got here" topics
  D) CHAPTERS — Topic     : Best for listicles, multi-angle breakdowns, "N things about X"
  E) PARTS — Flexible     : Best for topics that don't fit cleanly into the above

State your chosen structure AND your reasoning in the metadata block.
Then apply ALL rules of that chosen structure exactly as if it had been selected manually.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic   : {topic}
- Language: {lang}
- POV     : {pov}
- Parts   : {parts if parts != 'Auto' else 'You decide — choose the number that best fits your selected structure and the target word count'}
- Target words: {target_words}
- Target mins : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Output template:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration     : {target_mins} minutes
- Total Words         : ~{target_words} words
- Number of Parts     : [AI fills in]
- Chosen Structure    : [AI fills in — e.g. LEVELS — Escalation]
- Selection Reasoning : [AI fills in — one sentence why this structure fits this topic]

---

[Full script in the format of the chosen structure — follow that structure's exact template]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ------------------------------------------------------------------
#  7. CUSTOM — User-defined structure (Smart)
# ------------------------------------------------------------------
def prompt_custom(config):
    topic          = config.get("topic", "")
    lang           = config.get("lang", "Vietnamese")
    pov            = config.get("pov", "Second person (You)")
    parts          = config.get("parts", 3)
    target_mins    = config.get("target_mins", 10)
    target_words   = config.get("target_words", 1550)
    custom_schema  = config.get("custom_schema", "")
    dna            = config.get("dna_content", "")
    style          = config.get("style_content", "")

    system_prompt = f"""You are an A-list YouTube scriptwriter.
Your job is to execute a CUSTOM script structure defined entirely by the user.
You must follow the user's structure schema as the primary blueprint.

<channel_dna>
{dna}
</channel_dna>

<style_guide>
{style}
</style_guide>

MANDATORY WRITING RULES:
1. Follow the style guide 100% — pronouns, sentence length, forbidden words.
2. No empty exclamations or clichés.
3. Write full dialogue. Never summarise or outline.
4. All script content must be in the requested TARGET LANGUAGE.
5. Keep structural tags and syntax markers in English exactly as specified."""

    metadata = _build_metadata_block(topic, target_mins, target_words, parts, "CUSTOM — User-defined")

    user_prompt = f"""Write a video script using the CUSTOM structure defined below.

{metadata}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CUSTOM STRUCTURE SCHEMA (user-defined — follow exactly)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{custom_schema if custom_schema else "[No custom schema provided — infer the best structure from topic and parts count]"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT PARAMETERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic   : {topic}
- Language: {lang}
- POV     : {pov}
- Parts   : {parts}
- Target words: {target_words}
- Target mins : {target_mins}

{_word_count_rules(target_words)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_shared_output_rules()}

Output template:

=== VIDEO TITLE ===
{topic}

=== METADATA ===
- Target Duration  : {target_mins} minutes
- Total Words      : ~{target_words} words
- Number of Parts  : {parts}
- Applied Structure: CUSTOM — User-defined

---

=== HOOK (0:00 – 0:xx) ===
[Hook content]

[Follow the custom schema sections below]

---

=== OUTRO ===
[Closing thought]

[Final line]

---
[Estimated word count: XXX / Target: {target_words}]"""

    return system_prompt, user_prompt


# ============================================================
#  STRUCTURE ROUTER
#  Maps structure key → prompt builder function
# ============================================================

STRUCTURE_MAP = {
    # Keys match what your UI sends in config["structure"]
    "LV"       : prompt_levels,
    "Levels"   : prompt_levels,
    "Levels — Escalation (POV)": prompt_levels,

    "Acts"     : prompt_acts,
    "Acts — Story Arc (Narrative)": prompt_acts,

    "Timeline" : prompt_timeline,
    "Timeline — Chronological": prompt_timeline,

    "Chapters" : prompt_chapters,
    "Chapters — Topic-based": prompt_chapters,

    "Parts"    : prompt_parts,
    "Parts — Flexible": prompt_parts,

    "Auto"     : prompt_auto,
    "Auto — Claude tự quyết (recommended)": prompt_auto,

    "Custom"   : prompt_custom,
    "Custom — Tự nhập structure": prompt_custom,
}


def _default_parts_for_structure(structure_key: str, target_mins: int) -> int | str:
    if structure_key in ("Auto", "Auto — Claude tự quyết (recommended)"):
        return "Auto"

    if structure_key in ("Acts", "Acts — Story Arc (Narrative)"):
        return 5 if target_mins >= 12 else 4
    if structure_key in ("Levels", "Levels — Escalation (POV)", "LV"):
        return 4 if target_mins >= 12 else 3
    if structure_key in ("Timeline", "Timeline — Chronological"):
        return 5 if target_mins >= 12 else 4
    if structure_key in ("Chapters", "Chapters — Topic-based"):
        return 5 if target_mins >= 12 else 4
    if structure_key in ("Parts", "Parts — Flexible"):
        return 5 if target_mins >= 12 else 4
    if structure_key in ("Custom", "Custom — Tự nhập structure"):
        return 4

    return 4


def normalize_script_config(config: dict) -> dict:
    normalised = dict(config)
    structure_key = normalised.get("structure", "Auto")
    target_mins = int(normalised.get("target_mins", 10) or 10)
    parts = normalised.get("parts", "Auto")

    if parts == "Auto":
        normalised["parts"] = _default_parts_for_structure(structure_key, target_mins)
        return normalised

    try:
        normalised["parts"] = max(1, int(parts))
    except (TypeError, ValueError):
        normalised["parts"] = _default_parts_for_structure(structure_key, target_mins)

    return normalised


def build_prompts(config: dict) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for the given config.
    Falls back to AUTO if structure is not recognised.
    Research notes in config["research_notes"] are automatically injected.
    """
    config = normalize_script_config(config)
    structure_key = config.get("structure", "Auto")
    builder = STRUCTURE_MAP.get(structure_key, prompt_auto)
    system_prompt, user_prompt = builder(config)
    research_notes = config.get("research_notes", "")

    user_prompt += _factuality_rules(research_notes)

    topic_strategy = config.get("topic_strategy", {})
    if topic_strategy:
        user_prompt += _topic_strategy_injection(topic_strategy)

    extra_context = config.get("extra_context", "")
    if extra_context:
        user_prompt += _creator_extra_context_injection(extra_context)

    # Inject pre-gathered research notes if available
    if research_notes:
        user_prompt += _research_injection(research_notes)

    return system_prompt, user_prompt


# ============================================================
#  QThread WORKER  — Script only (research already done separately)
# ============================================================

class ScriptWorker(QThread):
    progress_signal = pyqtSignal(str)
    result_signal   = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def run(self):
        if genai is None:
            self.result_signal.emit("❌ LỖI: Thư viện 'google-genai' chưa được cài đặt.")
            self.finished_signal.emit()
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.result_signal.emit("❌ LỖI NGHIÊM TRỌNG: Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client     = genai.Client(api_key=api_key)
        model_name = "gemini-3.5-flash"

        try:
            structure    = self.config.get("structure", "Auto")
            has_research = bool(self.config.get("research_notes", "").strip())

            self.progress_signal.emit(
                f"✍️ Đang viết kịch bản — cấu trúc: {structure}"
                + (" (có research)" if has_research else "") + "..."
            )

            system_prompt, user_prompt = build_prompts(self.config)

            self.progress_signal.emit("🤖 Gemini đang viết kịch bản chi tiết...")

            gen_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )

            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=gen_config
            )

            self.result_signal.emit(response.text)

        except Exception as e:
            self.result_signal.emit(f"❌ Lỗi AI: {str(e)}")
        finally:
            self.finished_signal.emit()
