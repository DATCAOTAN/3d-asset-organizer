# app/services/asset_service.py
# -----------------------------------------------------------------------
# Tầng xử lý nghiệp vụ — Asset Orchestration Service
#
# Chịu trách nhiệm điều phối toàn bộ luồng xử lý chính:
#   1. Nhận input thô từ tầng HTTP
#   2. Gọi parser_service để làm sạch và parse danh sách asset
#   3. Gọi gemini_service để phân tích AI
#   4. Lắp ráp AssetOrganizeResponse hoàn chỉnh (gồm slug mappings,
#      metadata dự án, grouped assets, và đề xuất cải thiện)
#   5. Trả về response đã đóng gói cho tầng HTTP
#
# Đây là "orchestrator" — không tự xử lý logic chi tiết,
# chỉ điều phối các service con và ghép kết quả lại.
# -----------------------------------------------------------------------

from __future__ import annotations

import logging

from app.schemas.asset import (
    AssetOrganizeRequest,
    AssetOrganizeResponse,
    ProjectMetadata,
    SlugMapping,
)
from app.services import gemini_service
from app.services.parser_service import parse_raw_assets, slugify

logger = logging.getLogger(__name__)


async def organize_assets(request: AssetOrganizeRequest) -> AssetOrganizeResponse:
    """
    Orchestrate toàn bộ luồng phân tích và tổ chức asset 3D.

    Args:
        request: AssetOrganizeRequest từ tầng HTTP (đã qua Pydantic validation).

    Returns:
        AssetOrganizeResponse đầy đủ, sẵn sàng để trả về cho frontend.

    Raises:
        ValueError:   Khi input không có asset hợp lệ sau khi parse.
        RuntimeError: Khi AI service gặp lỗi (propagate từ gemini_service).
    """
    logger.info(
        "Bắt đầu xử lý dự án '%s'.", request.project_name
    )

    # -----------------------------------------------------------------------
    # Bước 1: Parse input thô → danh sách asset sạch
    # -----------------------------------------------------------------------
    asset_names = parse_raw_assets(request.raw_assets)
    logger.info("Đã parse được %d asset từ input thô.", len(asset_names))

    if not asset_names:
        raise ValueError(
            "Không tìm thấy asset hợp lệ trong dữ liệu nhập. "
            "Vui lòng kiểm tra lại định dạng."
        )

    # -----------------------------------------------------------------------
    # Bước 2: Gọi Gemini AI để phân loại
    # -----------------------------------------------------------------------
    ai_result = await gemini_service.analyze_assets(
        project_name=request.project_name,
        asset_names=asset_names,
    )

    # -----------------------------------------------------------------------
    # Bước 3: Sinh slug mappings cho từng asset
    # -----------------------------------------------------------------------
    slug_mappings = [
        SlugMapping(original_name=name, slug=slugify(name))
        for name in asset_names
    ]
    logger.debug("Đã sinh %d slug mappings.", len(slug_mappings))

    # -----------------------------------------------------------------------
    # Bước 4: Build metadata tóm tắt dự án
    # -----------------------------------------------------------------------
    metadata = ProjectMetadata(
        project_name=request.project_name,
        total_assets=len(asset_names),
        total_groups=len(ai_result.groups),
        asset_names=asset_names,
    )

    # -----------------------------------------------------------------------
    # Bước 5: Ghép toàn bộ thành response cuối cùng
    # -----------------------------------------------------------------------
    response = AssetOrganizeResponse(
        grouped_assets=ai_result.groups,
        slug_mappings=slug_mappings,
        metadata=metadata,
        improvements=ai_result.improvements,
    )

    logger.info(
        "Hoàn tất xử lý dự án '%s': %d nhóm, %d assets.",
        request.project_name,
        metadata.total_groups,
        metadata.total_assets,
    )
    return response
