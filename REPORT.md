# REPORT — 3D Asset Organizer

---

## 1. Mô tả chức năng đã làm

### Tổng quan
Xây dựng web app **3D Asset Organizer** — công cụ giúp người dùng tổ chức, phân loại danh sách asset không gian 3D bằng Google Gemini AI.

### Các chức năng đã hoàn thành

#### Backend (FastAPI)
- **`POST /api/assets/organize`** — Nhận input thô, parse, gọi Gemini AI phân loại asset theo nhóm không gian, trả về kết quả đầy đủ
- **`GET /api/assets/health`** — Health check endpoint cho monitoring
- **Parser đa định dạng** — Chấp nhận input dạng dấu phẩy, xuống dòng, gạch đầu dòng, JSON array, hoặc kết hợp tất cả
- **Slugify tiếng Việt** — Tự động chuyển tên asset sang slug chuẩn hóa (bỏ dấu, thay khoảng trắng bằng gạch ngang)
- **Fail-fast validation** — Từ chối sớm input rỗng trước khi gọi AI
- **Timing middleware** — Đo thời gian xử lý mỗi request, thêm header `X-Process-Time-Ms`
- **CORS** — Cho phép frontend gọi API từ mọi origin
- **Static file serving** — Serve frontend HTML/CSS/JS ngay qua FastAPI tại `/`

#### AI Integration (Google Gemini)
- Xây dựng system prompt yêu cầu Gemini đóng vai chuyên gia 3D architecture
- Phân loại asset vào các nhóm không gian: Khu vực chung, Khu vực riêng tư, Khu vực kỹ thuật, Ngoại thất, Trang trí & Ánh sáng
- Yêu cầu Gemini trả về JSON thuần túy theo schema cố định
- Tự động thử lần lượt các model khả dụng (`gemini-2.5-flash`, `gemini-2.0-flash`...)
- Mock mode khi không có API key — toàn bộ luồng vẫn hoạt động

#### Frontend (Vanilla JS)
- Form nhập liệu với placeholder gợi ý và nút "Dùng dữ liệu mẫu"
- Loading state với spinner trong khi chờ AI
- Hiển thị 4 phần kết quả: asset phân nhóm, slug mappings, metadata, đề xuất cải thiện
- Xử lý lỗi: hiển thị banner đỏ với message từ server
- Reset UI về form ban đầu sau khi xem kết quả

#### Kiến trúc (4 tầng tách biệt)
```
Tầng HTTP     → app/api/routes/assets.py
Tầng nghiệp vụ → app/services/ (asset_service, gemini_service, parser_service)
Tầng dữ liệu  → app/schemas/asset.py (7 Pydantic models)
Entry point   → main.py
```

---

## 2. Cách dùng AI/LLM

### Công cụ sử dụng
**Antigravity** (Google DeepMind) — AI coding assistant tích hợp trong môi trường phát triển.

### Mục đích sử dụng

| Mục đích | Cụ thể |
|----------|--------|
| Scaffold cấu trúc | Tạo toàn bộ thư mục, file khung với comment trách nhiệm |
| Viết backend | FastAPI routes, Pydantic schemas, service layer, middleware |
| Viết frontend | HTML/CSS/JS, xử lý trạng thái loading/error/reset |
| Prompt engineering | Thiết kế system prompt cho Gemini trả JSON đúng schema |
| Debug lỗi | Phân tích HTTP error log, tìm nguyên nhân và đề xuất fix |
| Viết tài liệu | README, report |

### Prompt mẫu đã dùng

**Prompt 1 — Scaffold dự án:**
```
Tạo cấu trúc thư mục cho web app "3D Asset Organizer".
Tech stack: FastAPI backend, HTML/CSS/JS thuần frontend, Google Gemini AI engine.
Tách biệt rõ: tầng HTTP, tầng nghiệp vụ, tầng dữ liệu, file khởi động.
Tạo toàn bộ file với comment ngắn giải thích trách nhiệm từng file.
```

**Prompt 2 — Thiết kế system prompt Gemini:**
```
Viết system prompt cho Gemini để phân loại asset 3D.
Yêu cầu: đóng vai chuyên gia 3D architecture, phân loại theo nhóm không gian,
đề xuất 2-3 cải thiện, chỉ trả về JSON thuần theo schema cố định,
xử lý trường hợp Gemini bọc JSON trong markdown code block.
```

### Cách kiểm tra output của AI

1. **Đọc lại toàn bộ file được sinh ra** — Đảm bảo đúng phân tách layer, không có logic nhầm tầng
2. **Chạy thực tế và đọc log** — Gửi request thật, theo dõi từng bước qua log (parse → AI → response)
3. **Test API độc lập** — Viết `test_api.py` gọi thẳng REST API bằng `urllib` để xác nhận key và model trước khi tích hợp
4. **Xác minh JSON response** — Log raw response của Gemini để phát hiện AI bọc JSON trong markdown
5. **Đọc kỹ HTTP error body** — Đọc toàn bộ error message (status + reason + details) thay vì chỉ nhìn status code

---

## 3. Khó khăn gặp phải

### Vấn đề 1 — Prompt engineering để Gemini luôn trả về JSON đúng schema

**Tình huống:** Gemini đôi khi trả về text giải thích kèm JSON, bọc JSON trong markdown code block (` ```json ... ``` `), hoặc thêm field không có trong schema. Pydantic validation thất bại ngay sau đó.

**Nguyên nhân:** LLM không đảm bảo output format tuyệt đối ổn định dù đã có system prompt. Với input đa dạng (tiếng Việt, tên asset dài, nhiều ký tự đặc biệt), model có xu hướng thêm commentary trước/sau JSON.

**Cách xử lý:** Viết hàm `_extract_json()` để tách JSON ra khỏi bất kỳ dạng wrapper nào (markdown block, text trước/sau). Đồng thời củng cố system prompt với chỉ thị rõ ràng: *"CHỈ trả về JSON thuần túy, không có markdown, không có text giải thích"* và cung cấp schema mẫu cụ thể ngay trong prompt.

---

### Vấn đề 2 — Chạy Gemini SDK (sync) trong FastAPI (async) mà không block event loop

**Tình huống:** Gemini SDK (`_client.models.generate_content()`) là hàm đồng bộ (blocking). Gọi trực tiếp trong async endpoint của FastAPI sẽ block toàn bộ event loop, khiến server không thể xử lý request khác trong lúc chờ AI phản hồi (trung bình 5–15 giây).

**Nguyên nhân:** FastAPI chạy trên asyncio event loop đơn luồng. Hàm blocking nếu không được offload sẽ chiếm toàn bộ thread và đóng băng server.

**Cách xử lý:** Dùng `asyncio.get_event_loop().run_in_executor(None, lambda: sdk_call())` để chạy SDK call trong thread pool riêng biệt, giải phóng event loop trong khi chờ AI. Pattern này đảm bảo server vẫn responsive với các request khác dù đang xử lý AI.

---

### Vấn đề 3 — Thiết kế parser xử lý input đa định dạng hỗn hợp

**Tình huống:** Người dùng có thể nhập asset theo nhiều cách khác nhau — dấu phẩy, xuống dòng, gạch đầu dòng (`-`, `*`, `•`), JSON array — hoặc kết hợp tất cả trong cùng một lần nhập. Parser cần xử lý đúng tất cả trường hợp mà không yêu cầu người dùng theo một chuẩn cụ thể.

**Nguyên nhân:** Không có thư viện sẵn cho bài toán này vì format hoàn toàn tự do. Phải tự thiết kế logic parse theo thứ tự ưu tiên, tránh parse nhầm (ví dụ: tên asset có dấu phẩy, tên asset bắt đầu bằng dấu `-`).

**Cách xử lý:** Xây dựng pipeline parse trong `parser_service.py`: (1) Thử parse JSON array trước, (2) Tách theo dòng, (3) Tách theo dấu phẩy nếu dòng không có bullet, (4) Strip ký tự bullet ở đầu dòng, (5) Lọc bỏ dòng rỗng và trùng lặp. Thứ tự ưu tiên rõ ràng giúp tránh false positive.

---

## 4. Ba lỗi/điểm chưa hợp lý đã quan sát

### Lỗi 1 — Không auto-detect model khả dụng khi khởi động

**Vấn đề:** Model được hardcode là `gemini-1.5-flash` trong codebase. Khi model không tồn tại trong account, app trả lỗi 503 mà không tự thử model khác.

**Hệ quả:** Developer phải biết trước tên model đúng và điền vào `.env`. Nếu model bị deprecated sau này, app sẽ ngừng hoạt động mà không có cảnh báo sớm.

**Hướng fix:** Gọi `list_models()` một lần khi startup, cache danh sách, tự chọn model tốt nhất. Hiện tại đã fix bằng cách thử lần lượt `_MODEL_CANDIDATES`.

---

### Lỗi 2 — Gemini response chưa được validate đủ chặt

**Vấn đề:** Nếu Gemini trả về JSON đúng format nhưng số lượng `groups` là 0 (AI không phân loại được), app vẫn trả `200 OK` với `grouped_assets: []` mà không báo lỗi cho user.

**Hệ quả:** Frontend hiển thị kết quả trống, người dùng không biết đã xảy ra vấn đề gì.

**Hướng fix:** Thêm validation sau khi parse response: nếu `groups` rỗng hoặc số asset trong response không khớp với input, raise lỗi hoặc retry.

---

### Lỗi 3 — Slug tiếng Việt chưa xử lý hết ký tự đặc biệt

**Vấn đề:** Hàm `slugify()` trong `parser_service.py` xử lý bỏ dấu tiếng Việt bằng bảng mapping thủ công. Một số ký tự hoặc tổ hợp dấu ít gặp có thể bị bỏ sót, tạo ra slug chứa ký tự lạ.

**Hệ quả:** Slug không hoàn toàn clean, có thể gây lỗi khi dùng làm tên file hoặc URL path trong các hệ thống khác.

**Hướng fix:** Dùng thư viện `unidecode` hoặc `python-slugify` thay vì mapping thủ công để xử lý đầy đủ Unicode.

---

## 5. Hướng cải thiện nếu có thêm thời gian

### Cải thiện kỹ thuật

| Hạng mục | Mô tả |
|----------|-------|
| **Unit tests** | Viết test cho `parser_service.py` (parse đa định dạng, slugify), `gemini_service.py` (mock response, lỗi JSON), `asset_service.py` (orchestration) |
| **Retry logic** | Tự động retry khi Gemini trả lỗi 429 (quota) hoặc 5xx với exponential backoff |
| **Response caching** | Cache kết quả theo hash của `(project_name + asset_names)` để tránh gọi AI lại với cùng input |
| **Streaming response** | Dùng Gemini streaming API để hiển thị kết quả dần dần thay vì chờ toàn bộ |
| **Rate limiting** | Thêm rate limit per-IP trên endpoint `/organize` để tránh abuse |

### Cải thiện UX

| Hạng mục | Mô tả |
|----------|-------|
| **Export kết quả** | Cho phép tải kết quả dưới dạng JSON hoặc CSV |
| **Lịch sử** | Lưu các lần phân tích trước vào localStorage, cho phép xem lại |
| **Drag & drop** | Upload file `.txt` hoặc `.json` chứa danh sách asset thay vì phải paste thủ công |
| **Dark mode** | Thêm toggle dark/light mode |
| **Multi-language** | Hỗ trợ thêm tiếng Anh cho tên nhóm và gợi ý |

### Cải thiện production

| Hạng mục | Mô tả |
|----------|-------|
| **Docker** | Đóng gói thành Docker image để deploy dễ dàng hơn |
| **CI/CD** | GitHub Actions tự động chạy test và deploy khi push lên main |
| **Monitoring** | Tích hợp Sentry để track lỗi production |
| **API versioning** | Thêm prefix `/api/v1/` để dễ nâng cấp sau này mà không breaking change |
