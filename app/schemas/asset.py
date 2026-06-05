# app/schemas/asset.py
# -----------------------------------------------------------------------
# Tầng định nghĩa dữ liệu — Data Contracts cho luồng Asset
#
# Chịu trách nhiệm định nghĩa toàn bộ shape của dữ liệu trong hệ thống:
#
#   1. AssetOrganizeRequest   → Dữ liệu người dùng gửi lên API
#   2. ClassifiedAsset        → Một asset đã được AI phân loại
#   3. AssetGroup             → Nhóm asset theo không gian (phòng ngủ, khu vực kỹ thuật...)
#   4. SlugMapping            → Mapping tên gốc → slug thân thiện với URL
#   5. ProjectMetadata        → Metadata tóm tắt toàn bộ dự án
#   6. AIAnalysisResult       → Dữ liệu AI được kỳ vọng trả về (parse từ Gemini)
#   7. AssetOrganizeResponse  → Response cuối cùng API trả về cho frontend
#
# Dùng Pydantic v2. Contract rõ ràng, tự giải thích được qua Field descriptions.
# -----------------------------------------------------------------------

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. REQUEST — Dữ liệu người dùng gửi lên
# ---------------------------------------------------------------------------

class AssetOrganizeRequest(BaseModel):
    """
    Payload mà người dùng POST lên /api/assets/organize.
    Chấp nhận tên dự án và danh sách asset thô ở nhiều định dạng:
      - Phân cách bằng dấu phẩy: "Sofa, Bàn trà, Đèn sàn"
      - Phân cách bằng xuống dòng
      - Gạch đầu dòng: "- Sofa\n- Bàn trà"
      - JSON array dạng string: '["Sofa", "Bàn trà"]'
    """
    project_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Tên dự án 3D (ví dụ: 'Căn hộ Vinhomes Central Park').",
        examples=["Căn hộ Vinhomes Central Park"],
    )
    raw_assets: str = Field(
        ...,
        min_length=1,
        description=(
            "Danh sách asset thô do người dùng nhập. Chấp nhận nhiều định dạng: "
            "phân cách bằng dấu phẩy, xuống dòng, gạch đầu dòng, hoặc JSON array."
        ),
        examples=["Sofa, Bàn cà phê, Đèn sàn\nGiường đôi, Tủ quần áo\n- Điều hòa"],
    )


# ---------------------------------------------------------------------------
# 2. AI ANALYSIS RESULT — Dữ liệu AI được kỳ vọng trả về
# ---------------------------------------------------------------------------

class ClassifiedAsset(BaseModel):
    """Một asset đã được AI gán vào nhóm không gian cụ thể."""
    name: str = Field(..., description="Tên gốc của asset.")
    group: str = Field(
        ...,
        description=(
            "Nhóm không gian AI phân loại, ví dụ: "
            "'Khu vực riêng tư', 'Khu vực chung', 'Khu vực kỹ thuật'."
        ),
    )
    reason: str = Field(..., description="Lý do ngắn gọn AI xếp asset này vào nhóm đó.")


class AssetGroup(BaseModel):
    """Nhóm asset theo loại không gian, chứa danh sách asset thuộc nhóm."""
    group_name: str = Field(..., description="Tên nhóm không gian (ví dụ: 'Phòng ngủ').")
    assets: list[ClassifiedAsset] = Field(
        default_factory=list,
        description="Danh sách các asset thuộc nhóm này.",
    )


class AIAnalysisResult(BaseModel):
    """
    Dữ liệu có cấu trúc mà GeminiService parse từ response của Gemini.
    Đây là contract nội bộ giữa GeminiService và AssetService.
    """
    groups: list[AssetGroup] = Field(
        description="Các asset đã được phân nhóm theo loại không gian."
    )
    improvements: list[str] = Field(
        description="2–3 đề xuất cải thiện cách tổ chức hoặc đặt tên asset.",
        min_length=1,
        max_length=5,
    )


# ---------------------------------------------------------------------------
# 3. RESPONSE — Dữ liệu API trả về cho frontend
# ---------------------------------------------------------------------------

class SlugMapping(BaseModel):
    """Mapping tên gốc của asset sang slug thân thiện với URL/hệ thống file."""
    original_name: str = Field(..., description="Tên gốc của asset.")
    slug: str = Field(
        ...,
        description=(
            "Slug được sinh ra: chữ thường, không dấu, dấu cách → gạch ngang. "
            "Ví dụ: 'Bàn cà phê' → 'ban-ca-phe'."
        ),
    )


class ProjectMetadata(BaseModel):
    """Metadata tóm tắt toàn bộ dự án, trả về kèm kết quả AI."""
    project_name: str = Field(..., description="Tên dự án.")
    total_assets: int = Field(..., description="Tổng số asset (sau khi lọc trùng).")
    total_groups: int = Field(..., description="Số nhóm không gian AI phân loại được.")
    asset_names: list[str] = Field(..., description="Danh sách tên asset đã được làm sạch.")


class AssetOrganizeResponse(BaseModel):
    """
    Response cuối cùng API trả về cho frontend sau khi xử lý xong.
    Gồm 4 phần theo yêu cầu:
      1. grouped_assets  — Asset đã phân nhóm theo không gian
      2. slug_mappings   — Slug tên file gợi ý cho từng asset
      3. metadata        — Metadata tóm tắt dự án
      4. improvements    — Đề xuất cải thiện
    """
    grouped_assets: list[AssetGroup] = Field(
        description="Asset đã được AI phân nhóm theo loại không gian."
    )
    slug_mappings: list[SlugMapping] = Field(
        description="Slug tên file gợi ý, tương ứng với từng asset."
    )
    metadata: ProjectMetadata = Field(
        description="Metadata tóm tắt toàn bộ dự án."
    )
    improvements: list[str] = Field(
        description="2–3 đề xuất của AI về cách tổ chức hoặc đặt tên asset."
    )
