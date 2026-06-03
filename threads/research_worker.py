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

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


# ============================================================
#  RESEARCH PROMPT BUILDER
#  Builds the research prompt based on topic + structure hint
# ============================================================

def build_research_prompt(config: dict) -> tuple[str, str]:
    topic        = config.get("topic", "")
    lang         = config.get("lang", "Vietnamese")
    structure    = config.get("structure", "Auto")
    target_mins  = config.get("target_mins", 10)
    target_words = config.get("target_words", 1550)
    extra        = config.get("extra_context", "")

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

    system_prompt = """You are a professional research analyst and fact-checker for a YouTube content team.
Your job is to gather, organise, and present verified factual data that a scriptwriter will use to write an accurate, credible video script.

RESEARCH RULES:
1. Prioritise SPECIFIC data: exact percentages, years, named institutions, named studies.
2. Flag any data point you are not fully certain about with ⚠️
3. Do NOT write any script content — only structured research notes.
4. Separate facts into clear labelled clusters.
5. Keep language neutral and factual — no editorialising.
6. Output must be in the language specified by the creator."""

    user_prompt = f"""Conduct research for a YouTube video script on the following topic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESEARCH REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Topic          : {topic}
- Output language: {lang}
- Script length  : ~{target_words} words / {target_mins} minutes
- Script structure: {structure}
- Structure focus: {structure_hint}{extra_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESEARCH SCOPE — COVER ALL OF THESE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. CORE STATISTICS & DATA
   - Quantitative facts directly relevant to the topic
   - Source type (government report / academic study / industry survey)
   - Year of data

2. ROOT CAUSES & MECHANISMS
   - WHY this phenomenon exists — the underlying systems or behaviours
   - Any expert consensus or widely-cited explanations

3. REAL-WORLD EXAMPLES & CASE STUDIES
   - Specific named examples (people, companies, countries, events)
   - What happened and what it illustrates about the topic

4. COMMON MISCONCEPTIONS
   - What most people believe that is partially or fully wrong
   - What the data actually shows

5. COUNTERARGUMENTS & NUANCE
   - The strongest objection to the main thesis
   - Data that complicates the simple narrative

6. NAMED ENTITIES (for fact accuracy)
   - Key organisations, laws, reports, or studies the script might reference
   - Correct names and basic descriptions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RESEARCH NOTES — [TOPIC IN CAPS]
{topic.upper()}

---

**Searches conducted:** [N searches]
**Confidence level:** [High / Medium / Low — one line explanation]

---

### 📊 1. CORE STATISTICS & DATA

- **[Fact label]:** [Specific data point]. *(Source type, Year)*
- **[Fact label]:** [Specific data point]. *(Source type, Year)*
⚠️ **[Uncertain fact label]:** [Data point — flagged because source unclear or old]

---

### 🔍 2. ROOT CAUSES & MECHANISMS

- **[Mechanism name]:** [Explanation in 1-2 sentences]
- **[Mechanism name]:** [Explanation in 1-2 sentences]

---

### 🧪 3. REAL-WORLD EXAMPLES & CASE STUDIES

- **[Name/Event]:** [What happened + what it illustrates — 2-3 sentences]
- **[Name/Event]:** [What happened + what it illustrates — 2-3 sentences]

---

### ❌ 4. COMMON MISCONCEPTIONS

- **Myth:** [What people believe]
  **Reality:** [What data shows]

---

### ⚖️ 5. COUNTERARGUMENTS & NUANCE

- [Strongest objection + supporting data in 2 sentences]
- [Complicating nuance in 2 sentences]

---

### 🏷️ 6. NAMED ENTITIES

- **[Entity name]:** [One-line description — what it is and why relevant]

---

⚠️ **Research notes là preliminary** — AI đã cross-check nhiều nguồn nhưng vẫn có thể sai. Fact có ⚠️ marker cần kiểm chứng lại trước khi viết.
💡 **Tip:** Kiểm tra research trước khi bấm Viết Script. Sau khi viết xong, vẫn nên sửa research rồi viết lại nếu cần.

---
[Research completed. Ready for script generation.]"""

    return system_prompt, user_prompt


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

        client     = genai.Client(api_key=api_key)
        model_name = "gemini-3.5-flash"

        try:
            self.progress_signal.emit("🔍 Đang research thông tin...")

            system_prompt, user_prompt = build_research_prompt(self.config)

            gen_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3   # Lower temp for factual research
            )

            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=gen_config
            )

            self.research_signal.emit(response.text)
            self.progress_signal.emit("✅ Research xong — kiểm tra rồi bấm Viết Script")

        except Exception as e:
            self.error_signal.emit(f"❌ Lỗi Research: {str(e)}")
        finally:
            self.finished_signal.emit()