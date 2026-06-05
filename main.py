# main.py
# -----------------------------------------------------------------------
# File khởi động ứng dụng (Application Entry Point)
#
# Chịu trách nhiệm:
#   - Tạo và cấu hình FastAPI app instance (factory pattern)
#   - Load biến môi trường từ file .env
#   - Đăng ký tất cả API router
#   - Cấu hình CORS để frontend (file HTML local) gọi được API
#   - Thêm middleware đo thời gian xử lý mỗi request (timing middleware)
#   - Log khi app khởi động (startup) và tắt (shutdown)
#   - Mount thư mục frontend để serve UI qua trình duyệt
#
# Chạy server:
#   uvicorn main:app --reload
#   hoặc: python main.py
# -----------------------------------------------------------------------

from __future__ import annotations

import logging
import os
import time

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Load .env trước khi import các service (service đọc env khi module load)
load_dotenv()

from app.api.routes import assets

# ---------------------------------------------------------------------------
# Cấu hình logging toàn cục
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("3d-asset-organizer")


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """
    Factory function tạo và cấu hình FastAPI instance.
    Tách riêng để dễ test (có thể tạo app với config khác nhau).
    """
    application = FastAPI(
        title="3D Asset Organizer",
        description=(
            "AI-powered tool sử dụng Google Gemini để tự động phân loại, "
            "đặt tên và tổ chức các asset không gian 3D."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # -----------------------------------------------------------------------
    # CORS Middleware
    # Cho phép frontend chạy dưới dạng file HTML local (file://) hoặc
    # dev server (localhost:xxxx) gọi được API.
    # -----------------------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # Mở rộng cho dev; thu hẹp lại khi production
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Timing Middleware — đo thời gian xử lý mỗi request
    # Thêm header X-Process-Time vào response để debug/monitoring
    # -----------------------------------------------------------------------
    @application.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        if request.url.path.startswith("/api/"):
            logger.debug(
                "%s %s → %d (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response

    # -----------------------------------------------------------------------
    # Đăng ký API Routers
    # -----------------------------------------------------------------------
    application.include_router(
        assets.router,
        prefix="/api/assets",
        tags=["Assets"],
    )

    # -----------------------------------------------------------------------
    # Lifecycle Events — Log khi khởi động và tắt
    # -----------------------------------------------------------------------
    @application.on_event("startup")
    async def on_startup():
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        mode = "LIVE (Google Gemini)" if gemini_key else "MOCK (không có API key)"
        logger.info("=" * 60)
        logger.info("🚀 3D Asset Organizer đã khởi động thành công!")
        logger.info("   AI Mode  : %s", mode)
        logger.info("   API Docs : http://localhost:8000/api/docs")
        logger.info("   Frontend : http://localhost:8000")
        logger.info("=" * 60)

    @application.on_event("shutdown")
    async def on_shutdown():
        logger.info("🛑 3D Asset Organizer đang tắt...")

    # -----------------------------------------------------------------------
    # Serve frontend (HTML/CSS/JS) tại root "/"
    # Phải đặt SAU khi đăng ký tất cả API route để không bị override
    # -----------------------------------------------------------------------
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    if os.path.isdir(frontend_dir):
        application.mount(
            "/",
            StaticFiles(directory=frontend_dir, html=True),
            name="frontend",
        )

    return application


# ---------------------------------------------------------------------------
# App instance (dùng cho `uvicorn main:app`)
# ---------------------------------------------------------------------------
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
