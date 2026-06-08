# CODEX HANDOFF — RX Tools / YT-Creater

Tài liệu này ghi lại các thay đổi đã làm trong phiên làm việc gần đây để có thể tiếp tục ở máy khác hoặc push lên GitHub.

## Project

- Repo local: `F:\RxTools\YT-Creater`
- App: `RX MEDIA - Production Suite`
- Stack chính: `PyQt6`, `google-genai`, `python-dotenv`, `python-docx`, `playwright`
- API chính đang dùng: `Gemini API`
- Model đang dùng trong các worker chính: `gemini-3.5-flash`

## Cách Làm Việc Của Chủ Project

- Ưu tiên làm tool thực dụng, chạy được trước, sau đó nâng cấp prompt và UX.
- Muốn AI hiểu rõ “ý đồ chiến lược”, không chỉ nhận title/topic rời rạc.
- Ưu tiên prompt chuyên nghiệp, có cấu trúc rõ, nhưng vẫn giữ format output hiện tại nếu đã dùng được.
- Khi có thay đổi UI, cần phù hợp nhiều màn hình: laptop 15 inch, màn 24 inch công ty, màn 27 inch ở nhà.
- Muốn tránh lãng phí token bằng cache cho context cố định như `DNA`, `Style Guide`, `Topics đã làm`.
- Khi test API, ưu tiên free/cheap tier trước; Gemini free tier là hướng chính hiện tại.
- Thích giải thích rõ nguyên nhân trước khi sửa code nếu gặp lỗi API/network.

## Tool 0 — Topic Ideator

### Mục Tiêu Sau Nâng Cấp

Tool 0 không còn chỉ tạo topic/title. Nó đã được nâng thành module `Topic Strategy / Topic Ideator`, tạo topic có thể dùng tiếp cho Script Writer.

### Thay Đổi Chính

- File chính:
  - `ui/tab_topic.py`
  - `threads/topic_worker.py`

### UI

- Thêm ô `YÊU CẦU BỔ SUNG (OPTIONAL)`.
- Mở rộng focus:
  - `CTR cao nhất`
  - `Evergreen nhất`
  - `Góc độ độc đáo`
  - `Dễ làm nhất`
  - `Cân bằng`
- Thêm sort buttons:
  - `Sort: Overall`
  - `Sort: Production`
  - `Sort: Evergreen`
- Sort logic đã hoạt động dựa trên:
  - `overall_score`
  - `production_score`
  - `evergreen_score`
- Sửa trạng thái `TOPICS ĐÃ LÀM`:
  - Profile lưu key là `topic_content`
  - Topic Ideator giờ map `topic_content` sang `done_content`
  - DropZone `TOPICS ĐÃ LÀM` sáng xanh khi profile đã có dữ liệu.

### Prompt / Schema

Prompt Topic Ideator đã được thay bằng prompt có quality bar, ideation method, title rules, scoring rules và JSON schema rõ.

Mỗi topic AI trả về hiện có thêm:

- `target_audience`
- `one_line_promise`
- `viewer_question`
- `emotional_driver`
- `trend_connection`
- `local_vietnam_angle`
- `competitor_common_angle`
- `our_better_angle`
- `titles`
- `unique_angle`
- `hook_sentence`
- `retention_hooks`
- `script_path`
- `evidence_needed`
- `research_keywords`
- `visual_potential`
- `ctr_level`
- `ctr_score`
- `evergreen_score`
- `originality_score`
- `production_score`
- `overall_score`
- `difficulty_level`
- `why_it_can_work`
- `risk_or_watchout`
- `tags`

### Validation

`threads/topic_worker.py` đã có validation để bắt:

- Sai số lượng topic.
- Thiếu field bắt buộc.
- Không đủ 3 title.
- Không đủ 3 retention hooks.
- Không đủ 5 script beats.
- Không đủ 3 evidence items.
- Không đủ 5 research keywords.
- Score không phải integer `1-100`.
- Trùng topic/title.

### Gemini Cache Cho Tool 0

Đã thêm explicit cache cho phần context profile:

- `style_content`
- `dna_content`
- `done_content/topic_content`

Cache index local:

- `data/gemini_cache_index.json`

File này đã được thêm vào `.gitignore`.

Mặc định TTL:

- `GEMINI_CACHE_TTL_SECONDS=3600`

Có thể chỉnh trong `.env`.

Nếu cache lỗi, code fallback về full prompt để app vẫn chạy.

## Tool 1 — Script Writer

### Mục Tiêu Sau Nâng Cấp

Tool 1 không chỉ viết script từ title. Nó giờ nhận cả strategy object từ Tool 0 để viết script theo đúng audience, angle, retention path, evidence direction và risk guardrail.

### File Chính

- `ui/tab_script_writer.py`
- `threads/script_worker.py`
- `threads/research_worker.py`

### Truyền Strategy Từ Tool 0 Sang Tool 1

Khi `Load Topic`, Tool 1 giờ lưu cả topic object:

- `topic_strategy`
- `selected_title`
- `selected_title_text`

Không còn chỉ lấy `selected_subtitle` đưa vào ô title.

Nếu user gõ tay title khác với `selected_title_text`, code không dùng nhầm strategy cũ.

### Prompt Viết Script

Đã thêm block:

- `SCRIPT STRATEGY BRIEF FROM TOPIC IDEATOR`

Block này chứa:

- selected title
- original topic
- target audience
- viewer promise
- viewer question
- emotional driver
- unique angle
- competitor common angle
- our better angle
- trend/local relevance
- title options
- retention open loops
- recommended script path
- evidence needed
- research keywords
- visual potential
- risk/watchout
- scoring context

Quan trọng: prompt yêu cầu AI dùng brief này để viết, nhưng không in brief thành section riêng.

### Giữ Format Output Hiện Tại

Đã thêm rule:

- Giữ nguyên metadata.
- Giữ section headers.
- Giữ outro.
- Giữ word-count line.
- Không thêm JSON.
- Không cắt format cũ.

Format vẫn có dạng:

```text
=== VIDEO TITLE ===
...

=== METADATA ===
...

=== HOOK ===
...

--- LEVEL / ACT / CHAPTER ---
...

=== OUTRO ===
...

[Estimated word count: XXX / Target: YYY]
```

### Word Count

Đã sửa prompt word-count:

- Chỉ đếm spoken dialogue + CTA text.
- Không đếm metadata, section headers, dividers, timestamps, bracketed cues, estimated line.
- Margin giảm xuống khoảng `±3%`, tối thiểu `25 từ`.

Lý do: user thường lọc metadata/note ra rồi mới đếm từ thực tế.

### Research / No Research Mode

Đã thêm factuality mode:

#### Không Research

AI bị cấm bịa:

- số liệu cụ thể
- phần trăm
- nghiên cứu
- tổ chức
- năm
- case study có tên
- câu kiểu `nghiên cứu chỉ ra...`

AI chỉ được dùng:

- quan sát đời sống
- ví dụ thường gặp
- trải nghiệm cảm xúc
- mẫu hình xã hội chung

#### Có Research

AI chỉ được dùng fact có trong `research_notes`.

Nếu fact được đánh dấu không chắc, phải hedge hoặc bỏ qua.

### Cues / Production Notes

Trước đó prompt mâu thuẫn: nói `pure dialogue`, nhưng output lại có `[PAUSE]`, `[TEXT OVERLAY]`.

Đã sửa:

- Cho phép cue ngắn:
  - `[PAUSE]`
  - `[CHẬM]`
  - `[TEXT OVERLAY: ...]`
  - `[MUSIC DROP]`
- Dùng sparingly.
- Cấm camera direction, B-roll list, editing note dài.

### Structure / Parts

Đã sửa lỗi:

```text
unsupported operand type(s) for -: 'str' and 'int'
```

Nguyên nhân:

- UI gửi `parts = "Auto"`
- Prompt cụ thể như `Levels`, `Acts`, `Timeline` lại tính `parts - 1`, `parts - 2`

Đã thêm normalize:

- Nếu structure cụ thể mà số phần là `Auto`, code tự chọn số phần hợp lý theo structure và target minutes.

### Structure Hint UI

Đã thêm dòng giải thích dưới dropdown cấu trúc:

- `Auto`: dùng khi chưa chắc, Gemini tự chọn.
- `Levels`: hợp mindset, tâm lý, sự thật ẩn, đào sâu từng tầng.
- `Acts`: hợp story/case/tiểu sử/hành trình.
- `Timeline`: hợp lịch sử, tiến trình, nguyên nhân theo thời gian.
- `Chapters`: hợp breakdown nhiều góc ngang hàng.
- `Parts`: chia linh hoạt khi không fit cấu trúc khác.
- `Custom`: dùng khi nhập structure riêng rõ trong Extra Context.

### Model UI

Đã sửa dropdown model ở Tool 1 chỉ còn:

- `Gemini 3.5 Flash`

Lý do:

- Worker hiện đang hard-code `gemini-3.5-flash`.
- Không hiển thị Claude/Sonnet để tránh hiểu nhầm.

## Tool 1 — Research Worker

### Nâng Cấp Prompt Research

`threads/research_worker.py` giờ nhận `topic_strategy`.

Research prompt dùng thêm:

- selected title
- target audience
- viewer promise
- viewer question
- unique angle
- better angle
- local/Vietnam angle
- risk/watchout
- evidence needed
- research keywords
- retention hooks

Đã thêm section output:

- `STRATEGY VALIDATION NOTES`

Mục đích:

- Cho biết angle nào được support.
- Claim nào cần hedge.
- Claim nào nên tránh.
- Evidence nào tốt nhất cho hook.

Lưu ý: Research hiện vẫn là Gemini tự research từ knowledge/model, chưa có web search thật. Nếu cần verified research nghiêm túc, cần thêm web/search API hoặc browser workflow sau.

## Layout / Responsive UI

### Main Window

Đã sửa app không mở cứng `1920x1080`.

Giờ window tự scale theo màn hình:

- khoảng `88%` width
- khoảng `86%` height
- max `1600x920`
- min hợp lý cho laptop
- tự căn giữa màn hình

File:

- `ui/main_window.py`

### Các Tab Đã Giảm Chiều Cao Tối Thiểu

Script Writer:

- giảm `output_splitter` từ `800` xuống `520`
- giảm `txt_output` từ `500` xuống `320`
- giảm research box xuống `120`

Scene Breakdown:

- giảm `table_scenes` xuống `300`
- giảm `stack` xuống `360`

G-Labs:

- thêm scroll cho panel trái để các nút dưới không bị mất trên màn hình thấp.

## API / Model Notes

### Gemini

Model chính:

- `gemini-3.5-flash`

Đã kiểm tra các model free-tier khả dụng nên cân nhắc fallback sau này:

- `gemini-3.5-flash`
- `gemini-3.1-flash-lite`
- `gemini-3-flash-preview`
- `gemini-2.5-flash-lite`

Chưa patch fallback chain cho Tool 1 vì user đang tạm dừng hướng này.

### Lỗi API Đã Gặp

#### 503 UNAVAILABLE

Ý nghĩa:

- Gemini đang high demand.
- Không phải lỗi prompt.
- Nên thêm retry/backoff sau.

#### WinError 10054

Ý nghĩa:

- Kết nối tới remote host bị đóng đột ngột.
- Có thể do server reset, mạng công ty, VPN, firewall, request dài, hoặc free tier quá tải.

Nên thêm retry/backoff cho:

- `ScriptWorker`
- `ResearchWorker`
- `TopicWorker`

## Token / Cache Notes

### Tool 0

Đã có explicit Gemini cache cho context profile.

### Tool 1

Chưa có explicit cache riêng cho `style_content + dna_content`.

Ước tính hiện tại với topic:

```text
Bạn Sẽ Mãi Mệt Mỏi Nếu Vẫn Cố Thành Công Chỉ Để Người Khác Nhìn Vào.
```

Nếu không cache:

- khoảng `13k input tokens`

Nếu cache được `style_content + dna_content`:

- còn khoảng `2.8k input tokens`

Output script 10 phút:

- khoảng `1.8k–3k output tokens`

Research prompt cho cùng topic:

- khoảng `2k input tokens`
- output tùy độ dài research, thường `1k–2.5k tokens`

## Việc Nên Làm Tiếp

Ưu tiên kỹ thuật:

1. Thêm retry/backoff cho Gemini errors:
   - `503`
   - `429`
   - `WinError 10054`
   - timeout/deadline
2. Thêm fallback model chain cho Tool 0/Tool 1/Research.
3. Thêm explicit cache cho Tool 1:
   - `style_content`
   - `dna_content`
4. Nếu muốn research thật:
   - thêm web/search workflow
   - hoặc tích hợp search API
5. Thêm nút `Regenerate this topic`.
6. Thêm nút `Make more like this`.
7. Nối output Script Writer sang Scene Breakdown bằng full script + strategy + research.

## Git Notes

Các file đã được chỉnh trong phiên gần đây gồm:

- `.gitignore`
- `ui/main_window.py`
- `ui/tab_topic.py`
- `ui/tab_script_writer.py`
- `ui/tab_scene_breakdown.py`
- `ui/tab_glabs.py`
- `threads/topic_worker.py`
- `threads/script_worker.py`
- `threads/research_worker.py`

Các file data/profile có thể bị app tự ghi:

- `active_profile.json`
- `profiles.json`

Cần kiểm tra trước khi commit để tránh push dữ liệu cá nhân hoặc profile nhạy cảm.

## Lưu Ý Bảo Mật

Không push:

- `.env`
- API key
- file cache credentials
- dữ liệu profile riêng nếu không muốn public

`.gitignore` hiện đã ignore:

- `.env`
- `profiles.json`
- `crash_log.txt`
- `data/gemini_cache_index.json`

## Cách Tiếp Tục Trên Máy Khác

1. Pull/paste repo code.
2. Copy `.env` riêng trên máy mới.
3. Cài dependencies:

```powershell
pip install -r requirements.txt
```

4. Chạy app:

```powershell
python main.py
```

5. Nếu muốn giữ history Codex:
   - copy thư mục `C:\Users\<USER>\.codex` từ máy cũ sang máy mới.
   - tắt Codex trước khi copy.
   - không chia sẻ thư mục này cho người khác vì có auth/session data.
