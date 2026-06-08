import os
import time
import json
import re
import hashlib
from datetime import datetime, timezone
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
PROJECT_ROOT = Path(__file__).parent.parent
CACHE_INDEX_PATH = PROJECT_ROOT / 'data' / 'gemini_cache_index.json'
load_dotenv(dotenv_path=env_path)
GEMINI_CACHE_TTL_SECONDS = int(os.getenv('GEMINI_CACHE_TTL_SECONDS', '3600'))


def _clip_context(value, max_chars):
    value = (value or "").strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "\n...[TRUNCATED]"


def _load_cache_index():
    if not CACHE_INDEX_PATH.exists():
        return {}
    try:
        with open(CACHE_INDEX_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache_index(index):
    CACHE_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_INDEX_PATH, "w", encoding="utf-8") as file:
        json.dump(index, file, ensure_ascii=False, indent=2)


def _cache_key(model_name, context):
    payload = f"{model_name}\n{context}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_cache_metadata_usable(cache):
    expire_time = getattr(cache, "expire_time", None) or getattr(cache, "expireTime", None)
    if not expire_time:
        return True
    if isinstance(expire_time, str):
        try:
            expire_time = datetime.fromisoformat(expire_time.replace("Z", "+00:00"))
        except ValueError:
            return True
    if expire_time.tzinfo is None:
        expire_time = expire_time.replace(tzinfo=timezone.utc)
    return expire_time > datetime.now(timezone.utc)


def build_profile_cache_context(config):
    style_content = _clip_context(config.get("style_content"), 12000)
    dna_content = _clip_context(config.get("dna_content"), 12000)
    done_content = _clip_context(config.get("done_content"), 10000)
    context_blocks = []

    if style_content:
        context_blocks.append(f"""--- CHANNEL STYLE GUIDE ---
{style_content}

Apply this to topic framing, titles, hooks, and wording. Do not merely mention it.""")

    if dna_content:
        context_blocks.append(f"""--- CHANNEL DNA ---
{dna_content}

Use this to match structure, viewer promise, pacing, and angle selection.""")

    if done_content:
        context_blocks.append(f"""--- PREVIOUS TOPICS / DO NOT DUPLICATE ---
{done_content}

Avoid exact duplicates and near-duplicates. If an idea overlaps, change the lens, case, or tension substantially.""")

    if not context_blocks:
        return ""

    return "PROFILE CONTEXT FOR THIS CHANNEL\n\n" + "\n\n".join(context_blocks)


def get_or_create_profile_cache(client, model_name, context):
    if not context.strip() or types is None:
        return None

    key = _cache_key(model_name, context)
    index = _load_cache_index()
    cached = index.get(key)

    if cached and cached.get("name"):
        try:
            cache = client.caches.get(name=cached["name"])
            if _is_cache_metadata_usable(cache):
                client.caches.update(
                    name=cached["name"],
                    config=types.UpdateCachedContentConfig(ttl=f"{GEMINI_CACHE_TTL_SECONDS}s")
                )
                print(f"✅ [TOPIC_WORKER] Gemini cache HIT: {cached['name']}")
                return cached["name"]
        except Exception as error:
            print(f"⚠️ [TOPIC_WORKER] Cached content invalid, recreating: {error}")

    cache = client.caches.create(
        model=model_name,
        config=types.CreateCachedContentConfig(
            displayName=f"yt-creater-topic-{key[:12]}",
            contents=context,
            ttl=f"{GEMINI_CACHE_TTL_SECONDS}s"
        )
    )
    cache_name = cache.name
    index[key] = {
        "name": cache_name,
        "model": model_name,
        "display_name": f"yt-creater-topic-{key[:12]}",
        "context_hash": key,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    _save_cache_index(index)
    print(f"✅ [TOPIC_WORKER] Gemini cache CREATED: {cache_name}")
    return cache_name


def validate_topic_response(data, expected_count):
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object.")

    topics = data.get("topics")
    if not isinstance(topics, list):
        raise ValueError("JSON must contain a 'topics' array.")

    try:
        expected_count = int(expected_count)
    except (TypeError, ValueError):
        expected_count = len(topics)

    if len(topics) != expected_count:
        raise ValueError(f"Expected {expected_count} topics, got {len(topics)}.")

    required_fields = [
        "topic_name", "target_audience", "one_line_promise", "viewer_question",
        "emotional_driver", "trend_connection", "local_vietnam_angle",
        "competitor_common_angle", "our_better_angle", "titles", "unique_angle",
        "hook_sentence", "retention_hooks", "script_path", "evidence_needed",
        "research_keywords", "visual_potential", "ctr_level", "ctr_score",
        "evergreen_score", "originality_score", "production_score", "overall_score",
        "difficulty_level", "why_it_can_work", "risk_or_watchout", "tags"
    ]
    allowed_ctr_levels = {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"}
    allowed_difficulty = {"EASY", "MEDIUM", "HARD"}

    seen_names = set()
    seen_titles = set()
    for index, topic in enumerate(topics, 1):
        if not isinstance(topic, dict):
            raise ValueError(f"Topic #{index} must be an object.")

        missing = [field for field in required_fields if field not in topic]
        if missing:
            raise ValueError(f"Topic #{index} missing fields: {', '.join(missing)}.")

        topic_name = str(topic.get("topic_name", "")).strip().lower()
        if not topic_name:
            raise ValueError(f"Topic #{index} has empty topic_name.")
        if topic_name in seen_names:
            raise ValueError(f"Duplicate topic_name: {topic.get('topic_name')}.")
        seen_names.add(topic_name)

        titles = topic.get("titles")
        if not isinstance(titles, list) or len(titles) != 3:
            raise ValueError(f"Topic #{index} must contain exactly 3 titles.")
        for title_index, title in enumerate(titles, 1):
            if not isinstance(title, dict) or not title.get("text") or not title.get("formula"):
                raise ValueError(f"Topic #{index} title #{title_index} must include text and formula.")
            title_text = str(title.get("text", "")).strip().lower()
            if title_text in seen_titles:
                raise ValueError(f"Duplicate title text: {title.get('text')}.")
            seen_titles.add(title_text)
            if not isinstance(title.get("score"), int):
                raise ValueError(f"Topic #{index} title #{title_index} score must be an integer.")

        if not isinstance(topic.get("retention_hooks"), list) or len(topic["retention_hooks"]) != 3:
            raise ValueError(f"Topic #{index} retention_hooks must contain exactly 3 items.")
        if not isinstance(topic.get("script_path"), list) or len(topic["script_path"]) != 5:
            raise ValueError(f"Topic #{index} script_path must contain exactly 5 beats.")
        if not isinstance(topic.get("evidence_needed"), list) or len(topic["evidence_needed"]) != 3:
            raise ValueError(f"Topic #{index} evidence_needed must contain exactly 3 items.")
        if not isinstance(topic.get("research_keywords"), list) or len(topic["research_keywords"]) != 5:
            raise ValueError(f"Topic #{index} research_keywords must contain exactly 5 items.")
        if topic.get("ctr_level") not in allowed_ctr_levels:
            raise ValueError(f"Topic #{index} ctr_level must be one of {sorted(allowed_ctr_levels)}.")
        if topic.get("difficulty_level") not in allowed_difficulty:
            raise ValueError(f"Topic #{index} difficulty_level must be one of {sorted(allowed_difficulty)}.")
        for score_field in ["ctr_score", "evergreen_score", "originality_score", "production_score", "overall_score"]:
            score = topic.get(score_field)
            if not isinstance(score, int) or not 1 <= score <= 100:
                raise ValueError(f"Topic #{index} {score_field} must be an integer from 1 to 100.")

    return data


def build_topic_prompt(config, include_profile_context=True):
    num_topics = config.get('num_topics', '10')
    lang = config.get('lang', 'Ti?ng Vi?t')
    niche = config.get('niche', 'Unspecified')
    focus = config.get('focus', 'C?n b?ng')
    ref_channel = config.get('ref_channel', '').strip() or 'None'
    extra = config.get('extra', '').strip() or 'None'

    schema = """
{
  "topics": [
    {
      "topic_name": "Specific conceptual name of the video",
      "target_audience": "Specific viewer persona, pain point, and context",
      "one_line_promise": "What the viewer gets by watching",
      "viewer_question": "The central curiosity question",
      "emotional_driver": "Primary emotion or motivation",
      "trend_connection": "Why this can feel timely or culturally relevant now",
      "local_vietnam_angle": "How to make this relatable to Vietnamese viewers, or 'N/A' if not applicable",
      "competitor_common_angle": "How generic competitor videos usually cover this idea",
      "our_better_angle": "The sharper or more useful angle this channel should take",
      "titles": [
        {"text": "Title option 1", "formula": "Curiosity Gap", "score": 1},
        {"text": "Title option 2", "formula": "Contrarian Reframe", "score": 1},
        {"text": "Title option 3", "formula": "Stakes/Consequence", "score": 1}
      ],
      "unique_angle": "Detailed angle that separates this from generic competitor videos",
      "hook_sentence": "Exact first spoken sentence of the video",
      "retention_hooks": ["Open loop 1", "Open loop 2", "Open loop 3"],
      "script_path": ["Beat 1", "Beat 2", "Beat 3", "Beat 4", "Beat 5"],
      "evidence_needed": ["Evidence/case/data point 1", "Evidence/case/data point 2", "Evidence/case/data point 3"],
      "research_keywords": ["Keyword 1", "Keyword 2", "Keyword 3", "Keyword 4", "Keyword 5"],
      "visual_potential": "What kind of visuals/B-roll/AI images can support this topic",
      "ctr_level": "HIGH",
      "ctr_score": 80,
      "evergreen_score": 80,
      "originality_score": 80,
      "production_score": 80,
      "overall_score": 80,
      "difficulty_level": "MEDIUM",
      "why_it_can_work": "Concrete performance rationale",
      "risk_or_watchout": "Concrete caveat",
      "tags": ["tag1", "tag2", "tag3"]
    }
  ]
}
""".strip()

    core_prompt = f"""You are a senior YouTube strategist for faceless long-form channels.
Your job is NOT to list generic ideas. Your job is to design publishable video opportunities that can become strong scripts.

TASK
Generate exactly {num_topics} video topic candidates for the channel.

TARGET LANGUAGE
All human-facing content values must be written in: {lang}
JSON keys must stay in English.

CHANNEL BRIEF
- Niche: {niche}
- Optimization focus: {focus}
- Reference channel/style inspiration: {ref_channel}
- Extra requests: {extra}

QUALITY BAR
A valid topic must pass all checks:
1. Specificity: not a broad category; it must contain a concrete tension, question, paradox, character, event, system, or transformation.
2. Click intent: the viewer should immediately understand why this matters or why it feels unresolved.
3. Scriptability: enough depth for an 8-15 minute video, with room for escalation and examples.
4. Original angle: not a recycled YouTube title; explain what makes the angle different from common competitor coverage.
5. Audience fit: match the channel DNA, tone, pacing, and format when provided.
6. Non-duplication: avoid exact and semantic duplicates of previous topics when provided.

IDEATION METHOD
Before finalizing each topic, internally evaluate:
- Core viewer curiosity: what question keeps them watching?
- Emotional driver: fear, ambition, injustice, mystery, identity, money, status, survival, betrayal, or awe.
- Contrarian layer: what does the audience usually misunderstand?
- Evidence path: what facts, examples, cases, or story beats could support the script?
- Production feasibility: how hard it is to research, visualize, and write.
- Local relevance: how the topic can feel close to the target audience's real life, especially Vietnamese viewers when the output language is Vietnamese.
- Competitive separation: how this channel can avoid the obvious competitor angle and create a sharper framing.
- Retention path: what open loops can keep the viewer watching after the first click.

TITLE RULES
For every topic, create 3 distinct title options:
1. Curiosity Gap title: opens a loop without being vague.
2. Contrarian/Reframe title: challenges a common belief.
3. Stakes/Consequence title: makes the cost or impact clear.
Avoid empty clickbait, all-caps, fake urgency, and promises the video cannot deliver.

SCORING RULES
- ctr_level: use one of LOW, MEDIUM, HIGH, VERY_HIGH.
- difficulty_level: use one of EASY, MEDIUM, HARD.
- ctr_score: integer 1-100 based on title clickability, emotional pull, specificity, and freshness.
- evergreen_score: integer 1-100 based on long-term relevance.
- originality_score: integer 1-100 based on how non-generic the angle is.
- production_score: integer 1-100 based on research effort, visual feasibility, and script clarity.
- overall_score: integer 1-100 weighted by focus, CTR, evergreen value, originality, and production feasibility.
- why_it_can_work: concrete reason this topic can perform for this niche.
- risk_or_watchout: one honest weakness, risk, or research caveat.

OUTPUT CONTRACT
Return ONLY one valid JSON object. No markdown fences. No commentary. No trailing text.
The JSON must match this schema exactly:
{schema}

VALIDATION BEFORE OUTPUT
- Generate exactly {num_topics} items.
- Every topic must have exactly 3 titles.
- Every retention_hooks must have exactly 3 items.
- Every script_path must have exactly 5 beats.
- Every evidence_needed must have exactly 3 items.
- Every research_keywords must have exactly 5 items.
- Scores must be numbers, not strings.
- Sort topics by overall_score descending before returning.
- Do not repeat topic_name, title text, or unique_angle.
"""

    blocks = [core_prompt]

    if include_profile_context:
        profile_context = build_profile_cache_context(config)
        if profile_context:
            blocks.append(profile_context)

    return "\n\n".join(blocks)


class TopicWorker(QThread):
    result_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        if genai is None:
            self.result_signal.emit("❌ LỖI: Thư viện 'google-genai' chưa được cài đặt. Vui lòng chạy lệnh 'pip install google-genai' trong terminal.")
            self.finished_signal.emit()
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.result_signal.emit("❌ LỖI: Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client = genai.Client(api_key=api_key)

        try:
            profile_context = build_profile_cache_context(self.config)

            # Danh sách các model theo thứ tự ưu tiên (Fallback Chain)
            model_priority = [
                "gemini-3.5-flash"
            ]

            last_error = ""
            for model_name in model_priority:
                retries = 2  # Tăng lên 2 lần thử lại cho bản Pro
                while retries >= 0:
                    try:
                        print(f"🚀 [TOPIC_WORKER] ACTIVE MODEL: {model_name}")
                        print(f"📡 [TOPIC_WORKER] Sending request to {model_name}... (Please wait)")

                        cached_content_name = None
                        prompt = build_topic_prompt(self.config, include_profile_context=True)
                        if profile_context:
                            try:
                                cached_content_name = get_or_create_profile_cache(client, model_name, profile_context)
                                if cached_content_name:
                                    prompt = build_topic_prompt(self.config, include_profile_context=False)
                            except Exception as cache_error:
                                print(f"⚠️ [TOPIC_WORKER] Gemini cache unavailable, using full prompt: {cache_error}")

                        print("\n" + "="*50)
                        if cached_content_name:
                            print(f"📤 [TOPIC_WORKER] PROMPT SENT TO AI WITH CACHE: {cached_content_name}")
                        else:
                            print("📤 [TOPIC_WORKER] FULL PROMPT SENT TO AI:")
                        print(prompt)
                        print("="*50 + "\n")
                        
                        request_config = None
                        if cached_content_name and types is not None:
                            request_config = types.GenerateContentConfig(cachedContent=cached_content_name)

                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=request_config
                        )

                        
                        # Kiểm tra xem có phản hồi hợp lệ không (tránh lỗi Safety filters)
                        if not response.candidates or not response.candidates[0].content.parts:
                            print(f"🛡️ [TOPIC_WORKER] {model_name} BLOCKED by Safety Filters.")
                            raise ValueError(f"Bị chặn bởi bộ lọc an toàn của {model_name}.")

                        raw_text = response.text
                        print("\n" + "-"*30)
                        print(f"📥 [TOPIC_WORKER] RAW RESPONSE FROM {model_name}:")
                        print(raw_text)
                        print("-"*30 + "\n")
                        
                        # Regex to extract JSON securely
                        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                        if json_match:
                            clean_json = json_match.group(0)
                            data = json.loads(clean_json)
                            data = validate_topic_response(data, self.config.get("num_topics", "10"))
                            # Nhét thêm tên model vào JSON để UI hiển thị
                            data["model_used"] = model_name.split("/")[-1]
                            
                            print(f"✅ [TOPIC_WORKER] SUCCESS: Valid JSON result from {model_name}")
                            self.result_signal.emit(json.dumps(data, ensure_ascii=False))
                            return # Thành công, thoát hàm run
                        else:
                            print(f"❌ [TOPIC_WORKER] JSON Pattern not found in {model_name} response.")
                            raise ValueError(f"Model {model_name} không trả về đúng cấu trúc JSON.")

                    except Exception as e:
                        err_msg = str(e)
                        print(f"⚠️ [TOPIC_WORKER] {model_name} FAILED: {err_msg}")
                        last_error = f"[{model_name.split('/')[-1]}] {str(e)}"
                        
                        # Nếu lỗi API Key bị lộ (403), dừng ngay lập tức vì thử model khác cũng vô ích
                        if "leaked" in err_msg.lower() or "403" in err_msg.lower():
                            self.result_signal.emit("❌ LỖI: API Key của bạn đã bị lộ hoặc không có quyền (403). Hãy kiểm tra file .env!")
                            self.finished_signal.emit()
                            return

                        # Nếu gặp lỗi hạn mức hoặc lỗi hệ thống, thử retry trước khi fallback
                        if any(x in err_msg.lower() for x in ["429", "quota", "limit", "503", "overloaded", "not found", "deadline"]):
                            if retries > 0:
                                wait_time = 5
                                print(f"⏳ [TOPIC_WORKER] {model_name} hit quota/limit. Retrying ({retries} left) in {wait_time}s...")
                                time.sleep(wait_time)
                                retries -= 1
                                continue
                            else:
                                print(f"🔄 [TOPIC_WORKER] {model_name} exhausted retries. Falling back...")
                                break # Dừng vòng lặp while để for loop chuyển sang model tiếp theo
                        else:
                            print(f"⚠️ [TOPIC_WORKER] Unexpected error with {model_name}. Attempting fallback...")
                            break 

            print(f"🛑 [TOPIC_WORKER] All models failed. Last error: {last_error}")
            raise Exception(f"Tất cả các model đều thất bại. Lỗi cuối cùng: {last_error}")

        except Exception as e:
            self.result_signal.emit(f"❌ Lỗi AI API: {str(e)}")
        finally:
            self.finished_signal.emit()
