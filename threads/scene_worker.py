import os
import json
import re
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal
from threads.gemini_retry import generate_content_with_retries

load_dotenv()


ALLOWED_CAMERA_ANGLES = {
    "Close-up",
    "Wide shot",
    "Extreme Close-up",
    "Establishing shot",
    "Over-the-shoulder",
    "POV",
    "Medium shot",
}


def _normalise_asset_lines(value):
    if isinstance(value, dict):
        return set(value.keys())
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return {
        line.strip()
        for line in str(value or "").splitlines()
        if line.strip()
    }


def validate_prescan_response(data):
    if not isinstance(data, dict):
        raise ValueError("Pre-scan response must be a JSON object.")

    characters = data.get("characters")
    backgrounds = data.get("backgrounds")
    if not isinstance(characters, dict):
        raise ValueError("Pre-scan JSON must contain a 'characters' object.")
    if not isinstance(backgrounds, dict):
        raise ValueError("Pre-scan JSON must contain a 'backgrounds' object.")

    for group_name, group in [("characters", characters), ("backgrounds", backgrounds)]:
        for key, item in group.items():
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
                raise ValueError(f"{group_name} key must be kebab-case: {key}")
            if not isinstance(item, dict):
                raise ValueError(f"{group_name}.{key} must be an object.")
            for field in ["display_name", "description", "continuity_traits", "scene_state_rules", "do_not_show", "era_context", "sample_scenes"]:
                if field not in item:
                    raise ValueError(f"{group_name}.{key} missing field: {field}")
            if not isinstance(item["sample_scenes"], list):
                raise ValueError(f"{group_name}.{key}.sample_scenes must be an array.")

    return data


def validate_assign_response(data, expected_scene_count, characters, backgrounds):
    if not isinstance(data, dict):
        raise ValueError("Assign response must be a JSON object.")

    scenes = data.get("scenes")
    if not isinstance(scenes, list):
        raise ValueError("Assign JSON must contain a 'scenes' array.")
    if len(scenes) != expected_scene_count:
        raise ValueError(f"Expected {expected_scene_count} assigned scenes, got {len(scenes)}.")

    allowed_characters = _normalise_asset_lines(characters)
    allowed_backgrounds = _normalise_asset_lines(backgrounds)
    seen_ids = set()

    for item in scenes:
        if not isinstance(item, dict):
            raise ValueError("Every assigned scene must be an object.")
        scene_id = item.get("id")
        if not isinstance(scene_id, int) or not 1 <= scene_id <= expected_scene_count:
            raise ValueError(f"Invalid scene id: {scene_id}")
        if scene_id in seen_ids:
            raise ValueError(f"Duplicate scene id: {scene_id}")
        seen_ids.add(scene_id)

        character = item.get("character")
        background = item.get("background")
        camera = item.get("camera")
        image_prompt = item.get("image_prompt")
        if character != "none" and character not in allowed_characters:
            raise ValueError(f"Scene {scene_id} uses unknown character: {character}")
        if background not in allowed_backgrounds:
            raise ValueError(f"Scene {scene_id} uses unknown background: {background}")
        if camera not in ALLOWED_CAMERA_ANGLES:
            raise ValueError(f"Scene {scene_id} uses invalid camera angle: {camera}")
        if not isinstance(image_prompt, str) or not image_prompt.strip():
            raise ValueError(f"Scene {scene_id} missing image_prompt.")
        if "NO TEXT NO WORDS on image" not in image_prompt:
            raise ValueError(f"Scene {scene_id} image_prompt must end with NO TEXT NO WORDS on image.")

    return data


class SceneWorker(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, str)  # task_type, json_result
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, task_type: str, config: dict):
        super().__init__()
        self.task_type = task_type  # 'prescan' | 'assign'
        self.config = config

    def run(self):
        if genai is None:
            self.error_signal.emit("❌ Thư viện 'google-genai' chưa được cài đặt.")
            self.finished_signal.emit()
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.error_signal.emit("❌ Không tìm thấy GEMINI_API_KEY trong file .env!")
            self.finished_signal.emit()
            return

        client = genai.Client(api_key=api_key)

        try:
            scenes = self.config.get("scenes", [])
            if not scenes:
                raise ValueError("Không có danh sách scenes để xử lý.")

            if self.task_type == "prescan":
                self._run_prescan(client, scenes)
            elif self.task_type == "assign":
                self._run_assign(
                    client,
                    scenes,
                    self.config.get("characters", ""),
                    self.config.get("backgrounds", ""),
                    self.config.get("char_style", ""),
                    self.config.get("bg_style", ""),
                    self.config.get("scene_style", ""),
                    self.config.get("prescan_data", {})
                )

        except Exception as e:
            self.error_signal.emit(f"❌ Lỗi: {str(e)}")
        finally:
            self.finished_signal.emit()

    # ──────────────────────────────────────────────────────────────────────
    # PRESCAN — Quét nhân vật + bối cảnh + MÔ TẢ chi tiết từng asset
    # ──────────────────────────────────────────────────────────────────────
    def _run_prescan(self, client, scenes):
        self.progress_signal.emit("🔍 AI đang đọc toàn bộ kịch bản để trích xuất và mô tả tài nguyên...")

        # Gửi toàn bộ scenes — cần đọc hết để hiểu từng nhân vật xuất hiện ở đâu
        script_text = "\n".join(
            f"Scene {i+1}: {text}" for i, text in enumerate(scenes)
        )

        system_prompt = """You are an AI Script Analyzer and Visual Continuity Director for video production.

Your task: read ALL scenes of a script, then build a continuity bible for image generation.
For EACH unique character and background / visual space:
1. Extract a unique kebab-case identifier.
2. Write a concise but specific visual description based ONLY on context clues in the script.
3. Lock the recurring visual traits that must stay consistent across scenes.
4. Capture scene-specific state changes when context changes across the script.
5. List up to 3 representative scene snippets where this asset appears.

IMPORTANT RULES:
- Base descriptions STRICTLY on what the script implies: era, location, social role, age, clothing, props, emotional state, and visible transformation.
- Do not force a default modern outfit, room, or prop if the scene context implies a different time period, culture, profession, climate, or story world.
- Infer the visible state of a character from context. If a character moves into a historical, fantasy, workplace, hospital, school, rural, futuristic, or symbolic setting, adapt wardrobe/props/environment to that setting while preserving the character's stable identity.
- Separate stable identity from scene-dependent state:
  stable_identity = face/silhouette/body type/recurring visual identity.
  scene_state = outfit, props, posture, emotion, era, location, lighting, and action that can change by scene.
- Do NOT invent details not supported by the script
- Normalize synonyms: "người chủ", "ông chủ", "boss" → pick one kebab name
- For characters with no visual clues → description = "role only, appearance undefined in script"
- kebab-case: lowercase, no accents, spaces → hyphens
- If a name is a brand, real institution, celebrity, copyrighted character, or sensitive proper noun, still keep a neutral kebab key, but describe it generically. Example: "vietcombank" means "a modern Vietnamese bank branch", not the real brand logo.
- Never require visible logos, real brand marks, copyrighted character likeness, or readable text.

VOICEOVER / NARRATOR RULES:
- The narrator/voiceover is NOT a visible character by default.
- Do NOT create assets named narrator, nguoi-ke-chuyen, voiceover, speaker, or toi unless the script explicitly shows that person on screen.
- In second-person motivational scripts, "you", "bạn", "chúng ta", and the implied viewer should map to one recurring main visual subject: protagonist.
- If the narrator says "Tôi từng..." only as empathy or lived-experience narration, keep using protagonist unless the script clearly cuts to a separate visible narrator.

BACKGROUND / VISUAL SPACE RULES:
- Backgrounds are not only physical locations. Extract recurring visual spaces and important visual surfaces too.
- A phone screen, social media feed, banking app, job post, memory montage, or abstract success feed can be a background/visual space if it is the main image surface.
- Use generic keys for digital spaces, for example social-media-feed, phone-screen, success-feed, small-rented-room.
- Do not create a real app/platform/bank background name. Use generic descriptions with no logos and no readable text.

Output ONLY valid raw JSON, no markdown fences, no explanation.

Schema:
{
  "characters_count": number,
  "backgrounds_count": number,
  "characters": {
    "kebab-name": {
      "display_name": "Tên hiển thị",
      "description": "Visual description inferred from script context...",
      "continuity_traits": "Stable age, silhouette, clothing, palette, facial design, and props that should remain consistent.",
      "scene_state_rules": "How outfit, props, posture, emotion, era, and setting should adapt when scenes change.",
      "do_not_show": "Visual details to avoid, including unsupported clothing, wrong era props, logos, readable text, or mismatched setting.",
      "era_context": "modern / ancient-egypt / feudal-china / futuristic / etc.",
      "sample_scenes": ["Scene text 1", "Scene text 2"]
    }
  },
  "backgrounds": {
    "kebab-name": {
      "display_name": "Tên hiển thị",
      "description": "Visual description of the location inferred from script...",
      "continuity_traits": "Stable architecture, lighting, palette, props, atmosphere, and layout that should remain consistent.",
      "scene_state_rules": "How this background should adapt to different moments, camera angles, time, mood, or symbolic use.",
      "do_not_show": "Visual details to avoid, including real logos, readable text, wrong era objects, or unsupported props.",
      "era_context": "modern / ancient-egypt / feudal-china / futuristic / etc.",
      "sample_scenes": ["Scene text 1", "Scene text 2"]
    }
  }
}"""

        user_prompt = (
            f"Analyze ALL scenes below and output the enriched JSON:\n\n{script_text}"
        )

        gen_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1
        )

        response, model_used = generate_content_with_retries(
            client=client,
            build_request=lambda model_name: {
                "contents": user_prompt,
                "config": gen_config,
            },
            progress_callback=self.progress_signal.emit,
            log_prefix="SCENE_PRESCAN",
        )

        json_str = self._extract_json(response.text)
        data = validate_prescan_response(json.loads(json_str))
        data["model_used"] = model_used
        json_str = json.dumps(data, ensure_ascii=False)
        self.result_signal.emit("prescan", json_str)

    # ──────────────────────────────────────────────────────────────────────
    # ASSIGN — Gán asset + viết image prompt riêng cho từng scene
    # ──────────────────────────────────────────────────────────────────────
    def _run_assign(self, client, scenes, characters, backgrounds, char_style, bg_style, scene_style, prescan_data):
        self.progress_signal.emit("⚡ AI đang gán asset và viết prompt hình cho từng scene...")

        input_data = [{"id": i + 1, "VO": text} for i, text in enumerate(scenes)]
        prescan_json = json.dumps(prescan_data or {}, ensure_ascii=False, indent=2)

        system_prompt = f"""You are an elite AI Image Prompt Director for a faceless YouTube production pipeline.
Your job is NOT only to assign assets. Your job is to write one production-ready G-Labs image prompt for EACH scene.

You will receive:
- A list of VO scenes.
- A character list and background list from pre-scan.
- Visual descriptions from pre-scan.
- Three style anchors: character style, background style, and scene style.

CRITICAL RULES:
1. CHARACTER — pick EXACTLY from this list (use kebab-case key):
{characters}
If no character is visible, use "none".
For second-person motivational narration, prefer protagonist for the implied viewer/main subject when the scene shows hands, phone POV, body language, emotional reaction, or a symbolic view from their perspective.
Do NOT use narrator/nguoi-ke-chuyen/voiceover as character unless that exact asset is in the list AND the scene explicitly shows that person on screen.

2. BACKGROUND — pick EXACTLY from this list (use kebab-case key):
{backgrounds}
If the VO is abstract, choose the most useful visual space from the background list, such as phone-screen/social-media-feed/success-feed/small-rented-room, rather than forcing "none" character or a random cafe.

3. CAMERA ANGLE — assign exactly one filmmaking tag based on dramatic weight:
   Close-up | Wide shot | Extreme Close-up | Establishing shot | Over-the-shoulder | POV | Medium shot

4. COVERAGE — return exactly {len(scenes)} scene objects, one per input id.
   Do not skip, duplicate, merge, renumber, or add scenes.

5. IMAGE PROMPT — write a unique image prompt for each scene.
   - The prompt must describe what is visually happening in that specific VO scene.
   - Keep the SAME art direction, character design language, palette, lighting, and scene style across ALL image_prompt values.
   - Repeat the core visual style language in every image_prompt so each prompt can stand alone when pasted into G-Labs.
   - Use the selected character and background as bracketed asset placeholders, for example [protagonist] and [phong-tro].
   - If no visible character, use [none] only in the character field, but the image_prompt should describe the background/POV/prop clearly.
   - Do not copy one generic prompt for every scene. Only the shared style anchor should repeat; the action, framing, facial expression, props, and composition must change with the story.
   - Include facial expression/body language when a character is visible.
   - Include concrete background details when a location is selected.
   - For abstract narration, create a concrete visual metaphor anchored to the protagonist's POV, phone screen, room, or recurring environment.
   - If the scene is a phone/social-media idea, the character can still be protagonist through visible hands, shoulder silhouette, reflection, or POV framing.
   - Use prescan scene_state_rules to adapt outfit, props, era, and environment per scene. Do not blindly reuse modern clothing or default locations when the current scene implies another context.
   - Preserve stable identity while adapting scene-dependent details. Example principle: same protagonist identity, but clothing/props/location change when the story world changes.
   - Translate abstract VO into visible action. Do not illustrate words literally if a stronger visual metaphor fits.
   - Never include readable text, logos, UI text, subtitles, brand marks, bank names, app names, copyrighted character likenesses, or real celebrity likenesses.
   - Replace brand/proper-name/IP visuals with generic equivalents inside the image_prompt. Example: a named bank becomes "a generic modern bank facade with no logo".
   - End every image_prompt exactly with: NO TEXT NO WORDS on image.

6. PROMPT STRUCTURE — each image_prompt must follow this order:
   [shared scene style anchor]. [camera/framing]. [character placeholder + locked character traits + expression/body language]. [background placeholder + locked location traits]. [scene-specific action, props, composition, mood]. NO TEXT NO WORDS on image.

Output ONLY raw JSON:
{{
  "scenes": [
    {{
      "id": 1,
      "character": "...",
      "background": "...",
      "camera": "...",
      "action_desc": "short visible action for this scene, not a summary of the VO",
      "image_prompt": "complete G-Labs image prompt for this exact scene"
    }}
  ]
}}"""

        user_prompt = (
            f"CHARACTER STYLE ANCHOR:\n{char_style or 'No separate character style provided.'}\n\n"
            f"BACKGROUND STYLE ANCHOR:\n{bg_style or 'No separate background style provided.'}\n\n"
            f"SCENE STYLE ANCHOR - repeat this visual language inside every image_prompt:\n"
            f"{scene_style or 'No separate scene style provided.'}\n\n"
            f"PRESCAN ASSET DESCRIPTIONS:\n{prescan_json}\n\n"
            f"SCENES TO PROCESS:\n"
            f"{json.dumps(input_data, ensure_ascii=False, indent=2)}\n\n"
            f"Generate the JSON output. Each image_prompt must be specific to its VO scene, safe for image generation, and visually consistent with the style anchors."
        )

        gen_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1
        )

        response, model_used = generate_content_with_retries(
            client=client,
            build_request=lambda model_name: {
                "contents": user_prompt,
                "config": gen_config,
            },
            progress_callback=self.progress_signal.emit,
            log_prefix="SCENE_ASSIGN",
        )

        json_str = self._extract_json(response.text)
        data = validate_assign_response(json.loads(json_str), len(scenes), characters, backgrounds)
        data["model_used"] = model_used
        json_str = json.dumps(data, ensure_ascii=False)
        self.result_signal.emit("assign", json_str)

    # ──────────────────────────────────────────────────────────────────────
    # HELPER
    # ──────────────────────────────────────────────────────────────────────
    def _extract_json(self, text: str) -> str:
        """Strip markdown fences nếu AI không tuân thủ, trả về JSON thuần."""
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text
