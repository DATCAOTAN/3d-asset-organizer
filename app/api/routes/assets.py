# app/api/routes/assets.py
# -----------------------------------------------------------------------
# Tầng HTTP — Router chính xử lý các endpoint của Asset
#
# Chịu trách nhiệm:
#   - Nhận HTTP request từ frontend
#   - Từ chối sớm (fail-fast) các input rỗng hoặc vô nghĩa
#     với thông báo lỗi rõ ràng, thân thiện
#   - Điều phối: validate → gọi asset_service → trả response
#   - KHÔNG bao giờ để lộ lỗi nội bộ hay stack trace ra client
#   - Ghi log các sự kiện quan trọng
#
# Dependency injection: AssetService được inject qua FastAPI Depends.
# Tầng này KHÔNG chứa business logic — chỉ điều phối HTTP I/O.
# -----------------------------------------------------------------------

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.asset import AssetOrganizeRequest, AssetOrganizeResponse
from app.services import asset_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency — có thể mock dễ dàng trong test
# ---------------------------------------------------------------------------

def get_asset_service():
    """Dependency provider cho asset_service module."""
    return asset_service


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/organize",
    response_model=AssetOrganizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Phân loại và tổ chức danh sách asset 3D bằng AI",
    description=(
        "Nhận tên dự án và danh sách asset 3D thô (text hoặc JSON), "
        "gửi lên Google Gemini để phân loại theo nhóm không gian, "
        "sinh slug tên file, tóm tắt metadata và đề xuất cải thiện."
    ),
    responses={
        200: {"description": "Phân tích thành công"},
        400: {"description": "Input không hợp lệ (rỗng hoặc không có asset)"},
        503: {"description": "AI service không khả dụng"},
    },
)
async def organize_assets(
    request: Request,
    payload: AssetOrganizeRequest,
    service=Depends(get_asset_service),
) -> AssetOrganizeResponse:
    """
    Endpoint chính: nhận input → điều phối service → trả kết quả AI.

    Luồng xử lý:
      1. FastAPI tự validate payload qua Pydantic (trả 422 nếu sai schema)
      2. Kiểm tra sớm nội dung có ý nghĩa (không chỉ là khoảng trắng)
      3. Gọi asset_service.organize_assets()
      4. Wrap mọi lỗi thành HTTPException phù hợp — không lộ internals
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "POST /organize — project='%s', client=%s",
        payload.project_name,
        client_ip,
    )

    # --- Fail-fast: kiểm tra raw_assets có nội dung thực sự không ---
    if not payload.raw_assets.strip():
        logger.warning("Request bị từ chối: raw_assets rỗng.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách asset không được để trống. Vui lòng nhập ít nhất 1 asset.",
        )

    if not payload.project_name.strip():
        logger.warning("Request bị từ chối: project_name rỗng.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên dự án không được để trống.",
        )

    start_time = time.perf_counter()

    try:
        result = await service.organize_assets(payload)

    except ValueError as exc:
        # Lỗi validate logic (ví dụ: parse xong không có asset nào)
        logger.warning("Lỗi validate input: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        # Lỗi từ AI service (network, API key, format sai...)
        logger.error("Lỗi AI service: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Lỗi không mong đợi — log đầy đủ nhưng KHÔNG lộ ra client
        logger.exception("Lỗi không xác định khi xử lý request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi máy chủ nội bộ. Vui lòng thử lại sau.",
        ) from exc

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "POST /organize hoàn tất — %d groups, %d assets, %.1fms",
        result.metadata.total_groups,
        result.metadata.total_assets,
        elapsed_ms,
    )
    return result


@router.get(
    "/health",
    summary="Kiểm tra trạng thái API",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict:
    """
    Health check endpoint — dùng cho Docker, load balancer, hoặc monitoring.
    Trả về trạng thái server và thông tin cơ bản.
    """
    import os
    has_api_key = bool(os.getenv("GEMINI_API_KEY", ""))
    return {
        "status": "ok",
        "service": "3D Asset Organizer API",
        "version": "1.0.0",
        "ai_engine": "Google Gemini",
        "ai_ready": has_api_key,
        "ai_mode": "live" if has_api_key else "mock",
    }
