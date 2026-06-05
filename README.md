# 3D Asset Organizer

Công cụ giúp người dùng tổ chức và phân loại danh sách asset không gian 3D bằng AI.
Người dùng nhập danh sách asset thô (text hoặc JSON), hệ thống tự động phân nhóm theo loại không gian,
gợi ý tên file chuẩn hóa (slug), tóm tắt metadata dự án, và đề xuất cách tổ chức tối ưu.

---

## Tech Stack

| Thành phần | Công nghệ |
|------------|-----------|
| Backend    | Python 3.11+ · FastAPI · Uvicorn |
| AI Engine  | Google Gemini API (`gemini-2.5-flash`) |
| Frontend   | HTML5 · CSS3 · Vanilla JavaScript (không framework) |
| Data Layer | Pydantic v2 |
| HTTP Client| google-genai SDK |
| Env Config | python-dotenv |

---

## Yêu cầu hệ thống

- **Python** 3.10 trở lên (khuyến nghị 3.11+)
- **pip** 23+
- Kết nối Internet (để gọi Gemini API)
- Trình duyệt hiện đại (Chrome, Firefox, Edge)

> **Không có Gemini API key?**  
> App vẫn chạy được ở chế độ **MOCK** — AI sẽ được giả lập bằng logic từ khóa đơn giản.  
> Toàn bộ luồng UI vẫn hoạt động đầy đủ.

---

## Hướng dẫn cài đặt

### Bước 1 — Tải source code

```bash
git clone <repository-url>
cd 3d-asset-organizer
```

Hoặc tải file ZIP → giải nén → mở terminal trong thư mục `3d-asset-organizer/`.

---

### Bước 2 — Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

---

### Bước 3 — Cấu hình biến môi trường

```bash
cp .env.example .env
```

Mở file `.env` và điền API key:

```env
GEMINI_API_KEY=
GEMINI_MODEL=
```

> **Lấy API key miễn phí tại:** https://aistudio.google.com/app/apikey  
> Để trống `GEMINI_MODEL` để app tự động chọn model tốt nhất khả dụng.  
> Nếu bỏ trống `GEMINI_API_KEY`, app tự chuyển sang chế độ MOCK.

---

### Bước 4 — Cài đặt dependencies

```bash
pip install -r requirements.txt
```

---

### Bước 5 — Chạy backend server

```bash
uvicorn main:app --reload
```

Kết quả khi khởi động thành công:

```
INFO  | 3d-asset-organizer — ============================================================
INFO  | 3d-asset-organizer — 🚀 3D Asset Organizer đã khởi động thành công!
INFO  | 3d-asset-organizer —    AI Mode  : LIVE (Google Gemini)
INFO  | 3d-asset-organizer —    API Docs : http://localhost:8000/api/docs
INFO  | 3d-asset-organizer —    Frontend : http://localhost:8000
INFO  | 3d-asset-organizer — ============================================================
```

---

### Bước 6 — Mở giao diện người dùng

Mở trình duyệt và truy cập:

```
http://localhost:8000
```

> - **API Docs (Swagger UI):** http://localhost:8000/api/docs  
> - **Health Check:** http://localhost:8000/api/assets/health

---

## Cách sử dụng

### Nhập dữ liệu

| Trường | Mô tả |
|--------|-------|
| **Tên dự án** | Tên dự án 3D (ví dụ: `Căn hộ Vinhomes Central Park`) |
| **Danh sách asset** | Danh sách asset thô — chấp nhận nhiều định dạng |

**Các định dạng input được chấp nhận:**

```
# Phân cách bằng dấu phẩy
Sofa 3 chỗ, Bàn cà phê, Đèn sàn, Tivi 65 inch

# Phân cách bằng xuống dòng
Giường đôi King size
Tủ quần áo 4 cánh

# Gạch đầu dòng
- Điều hòa 2HP
- Quạt trần
* Bóng đèn LED âm trần

# JSON array
["Bồn tắm", "Vòi sen", "Toilet thông minh"]

# Kết hợp tất cả định dạng ✓
Sofa, Bàn trà
Giường đôi
- Điều hòa
["Bồn tắm"]
```

---

### Ví dụ input mẫu

**Tên dự án:**
```
Căn hộ Vinhomes Central Park - Tầng 15
```

**Danh sách asset:**
```
Sofa 3 chỗ, Bàn cà phê tròn, Đèn sàn
Giường đôi King size
- Tủ quần áo 4 cánh
- Bàn trang điểm
Điều hòa 2HP, Quạt trần
Bồn tắm, Vòi sen, Toilet thông minh
Bàn ăn 6 người, Ghế ăn
Tủ bếp, Bếp từ, Máy hút mùi
Đèn chùm phòng khách, Đèn LED âm trần
```

> Hoặc nhấn nút **"Dùng dữ liệu mẫu"** để điền tự động.

---

### Kết quả hiển thị

| # | Phần | Nội dung |
|---|------|----------|
| 1 | **Asset đã phân nhóm** | Từng asset được xếp vào nhóm không gian kèm lý do |
| 2 | **Slug tên file gợi ý** | `Bàn cà phê` → `ban-ca-phe` |
| 3 | **Metadata dự án** | Tên dự án · Tổng số asset · Số nhóm |
| 4 | **Đề xuất cải thiện** | 2–3 gợi ý của AI về cách đặt tên hoặc tổ chức |

---

## Cấu trúc thư mục

```
3d-asset-organizer/
│
├── main.py                      # Entry point: khởi tạo app, CORS, middleware, serve frontend
├── requirements.txt             # Dependencies với version cụ thể
├── .env.example                 # Template biến môi trường (copy thành .env)
├── README.md                    # File này
│
├── app/
│   ├── api/                     # ── Tầng HTTP (nhận/trả request, không chứa logic) ──
│   │   └── routes/
│   │       └── assets.py        # POST /api/assets/organize · GET /api/assets/health
│   │
│   ├── services/                # ── Tầng nghiệp vụ (business logic, độc lập với HTTP) ──
│   │   ├── parser_service.py    # Parse mọi định dạng input → asset sạch + slugify tiếng Việt
│   │   ├── gemini_service.py    # Gọi Gemini API, xây dựng prompt, parse JSON, xử lý lỗi
│   │   └── asset_service.py     # Orchestrator: điều phối parser → AI → build response
│   │
│   └── schemas/                 # ── Tầng dữ liệu (Pydantic v2 data contracts) ──
│       └── asset.py             # 7 model: Request · ClassifiedAsset · AssetGroup ·
│                                #          SlugMapping · ProjectMetadata ·
│                                #          AIAnalysisResult · Response
│
└── frontend/                    # ── Giao diện người dùng (HTML/CSS/JS thuần) ──
    ├── index.html               # Cấu trúc 2 view: form nhập liệu & trang kết quả
    ├── style.css                # Design tokens, layout, component styles, responsive
    └── app.js                   # Validate · gọi API · render kết quả · loading/error state
```

---

## API Reference

### `POST /api/assets/organize`

**Request body:**
```json
{
  "project_name": "Căn hộ Vinhomes Central Park",
  "raw_assets": "Sofa, Bàn trà\nGiường đôi\n- Điều hòa"
}
```

**Response `200 OK`:**
```json
{
  "grouped_assets": [
    {
      "group_name": "Khu vực chung",
      "assets": [
        { "name": "Sofa", "group": "Khu vực chung", "reason": "Đồ nội thất phòng khách" }
      ]
    }
  ],
  "slug_mappings": [
    { "original_name": "Sofa", "slug": "sofa" },
    { "original_name": "Bàn trà", "slug": "ban-tra" }
  ],
  "metadata": {
    "project_name": "Căn hộ Vinhomes Central Park",
    "total_assets": 3,
    "total_groups": 2,
    "asset_names": ["Sofa", "Bàn trà", "Giường đôi"]
  },
  "improvements": [
    "Dùng prefix nhóm khi đặt tên file: living_sofa_01.fbx",
    "Tách thư mục asset tĩnh và asset có animation riêng biệt"
  ]
}
```

**Error responses:**

| Status | Nguyên nhân |
|--------|-------------|
| `400`  | Input rỗng hoặc không có asset hợp lệ |
| `503`  | Gemini API không khả dụng |
| `500`  | Lỗi server nội bộ |

### `GET /api/assets/health`

```json
{
  "status": "ok",
  "service": "3D Asset Organizer API",
  "version": "1.0.0",
  "ai_engine": "Google Gemini",
  "ai_ready": true,
  "ai_mode": "live"
}
```

---

## Xử lý lỗi

| Tình huống | Phản hồi |
|------------|----------|
| Để trống tên dự án hoặc asset | Thông báo lỗi ngay dưới field, không gửi request |
| Gemini API key sai / hết quota | Banner lỗi đỏ với message từ server |
| Mất kết nối Internet | Banner lỗi: "Không thể kết nối đến server" |
| Không có `GEMINI_API_KEY` | Tự động chuyển sang chế độ MOCK |

---


