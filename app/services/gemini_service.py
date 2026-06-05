# app/services/gemini_service.py
# -----------------------------------------------------------------------
# Tầng xử lý nghiệp vụ — Google Gemini AI Service
#
# SDK: google-genai >= 1.0.0
#
# Chịu trách nhiệm:
#   - Xây dựng prompt phân loại asset 3D theo nhóm không gian
#   - Yêu cầu Gemini đề xuất 2–3 cải thiện
#   - Parse JSON response thành AIAnalysisResult
#   - Xử lý lỗi: key sai, quota hết, sai format, timeout
#   - Mock mode khi không có API key
# -----------------------------------------------------------------------

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from google import genai
from google.genai import types

from app.schemas.asset import AIAnalysisResult, AssetGroup, ClassifiedAsset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_API_KEY = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

# Danh sách model theo thứ tự ưu tiên (đúng với account hiện tại)
_ENV_MODEL = os.getenv("GEMINI_MODEL", "").strip()
_MODEL_CANDIDATES: list[str] = [m for m in [
    _ENV_MODEL,
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
] if m]
_MODEL_CANDIDATES = list(dict.fromkeys(_MODEL_CANDIDATES))

_client: genai.Client | None = None

if _API_KEY:
    _client = genai.Client(api_key=_API_KEY)
    logger.info("Gemini client khởi tạo — %s... (%d ký tự)", _API_KEY[:8], len(_API_KEY))
else:
    logger.warning("GEMINI_API_KEY chưa cấu hình — sẽ dùng mock data.")


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Bạn là chuyên gia tư vấn tổ chức dự án 3D architecture với 10+ năm kinh nghiệm.
Phân tích danh sách asset 3D và phân loại chuyên nghiệp.

QUAN TRỌNG: Chỉ trả về JSON thuần túy, không markdown, không text giải thích.
Schema bắt buộc:
{
  "groups": [
    {
      "group_name": "Tên nhóm không gian",
      "assets": [
        {"name": "Tên asset gốc", "group": "Tên nhóm", "reason": "Lý do ngắn"}
      ]
    }
  ],
  "improvements": ["Đề xuất 1", "Đề xuất 2", "Đề xuất 3"]
}

Nhóm điển hình: Khu vực riêng tư, Khu vực chung, Khu vực kỹ thuật, Ngoại thất, Trang trí & Ánh sáng."""


def _build_prompt(project_name: str, asset_names: list[str]) -> str:
    asset_list = "\n".join(f"- {name}" for name in asset_names)
    return (
        f"Tên dự án: {project_name}\n\n"
        f"Danh sách asset ({len(asset_names)} asset):\n{asset_list}\n\n"
        "Phân loại tất cả asset và đề xuất 2-3 cải thiện. Trả về JSON thuần túy."
    )


# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------

def _build_mock_result(asset_names: list[str]) -> AIAnalysisResult:
    logger.info("[MOCK] Trả về mock result.")
    private_kw = {"giường", "tủ", "gương", "bồn", "vòi", "toilet", "gối"}
    common_kw  = {"sofa", "bàn", "ghế", "đèn", "tivi", "kệ", "thảm"}
    tech_kw    = {"điều hòa", "quạt", "ổ điện", "đường ống", "máy lạnh"}

    groups_dict: dict[str, list[ClassifiedAsset]] = {
        "Khu vực chung": [], "Khu vực riêng tư": [],
        "Khu vực kỹ thuật": [], "Khác": [],
    }
    for name in asset_names:
        lower = name.lower()
        if any(kw in lower for kw in private_kw):  grp = "Khu vực riêng tư"
        elif any(kw in lower for kw in tech_kw):   grp = "Khu vực kỹ thuật"
        elif any(kw in lower for kw in common_kw): grp = "Khu vực chung"
        else:                                       grp = "Khác"
        groups_dict[grp].append(
            ClassifiedAsset(name=name, group=grp, reason="Phân loại tự động (mock mode)")
        )
    return AIAnalysisResult(
        groups=[AssetGroup(group_name=g, assets=a) for g, a in groups_dict.items() if a],
        improvements=[
            "[MOCK] Dùng prefix nhóm: living_sofa_01.fbx",
            "[MOCK] Tách thư mục asset tĩnh và animation.",
            "[MOCK] Chuẩn tên: [khu_vuc]_[loai]_[stt]",
        ],
    )


# ---------------------------------------------------------------------------
# JSON Parsing
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start:end + 1]
    return text


def _parse_response(raw_text: str) -> AIAnalysisResult:
    json_str = _extract_json(raw_text)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.error("Gemini không trả về JSON hợp lệ: %s", raw_text[:400])
        raise ValueError(f"AI trả về dữ liệu không đúng JSON: {exc}") from exc
    try:
        return AIAnalysisResult.model_validate(data)
    except Exception as exc:
        raise ValueError(f"Cấu trúc AI không đúng schema: {exc}") from exc


# ---------------------------------------------------------------------------
# Gọi SDK — thử từng model theo thứ tự ưu tiên
# ---------------------------------------------------------------------------

def _call_sdk(model: str, prompt: str) -> str:
    """Gọi Gemini SDK đồng bộ — chạy trong executor để không block event loop."""
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        temperature=0.3,
        max_output_tokens=4096,
    )
    response = _client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    return response.text


async def _call_with_fallback(prompt: str) -> str:
    """Thử từng model, dừng khi thành công."""
    loop = asyncio.get_event_loop()
    last_err: Exception = RuntimeError("Không có model nào khả dụng.")

    for model in _MODEL_CANDIDATES:
        logger.info("Thử model: %s", model)
        try:
            text = await loop.run_in_executor(None, lambda m=model: _call_sdk(m, prompt))
            logger.info("✓ Model '%s' hoạt động.", model)
            return text
        except Exception as exc:
            err = str(exc)
            if "not found" in err.lower() or "404" in err:
                logger.warning("Model '%s' không khả dụng, thử tiếp...", model)
                last_err = exc
                continue
            # Lỗi khác (401, quota...) → raise ngay
            raise RuntimeError(_friendly_error(err)) from exc

    raise last_err


def _friendly_error(msg: str) -> str:
    if "401" in msg or "403" in msg or "unauthenticated" in msg.lower():
        return "API key không hợp lệ. Kiểm tra GEMINI_API_KEY trong .env."
    if "429" in msg or "quota" in msg.lower():
        return "Hết quota Gemini API. Vui lòng thử lại sau."
    return f"Lỗi Gemini: {msg[:200]}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_assets(project_name: str, asset_names: list[str]) -> AIAnalysisResult:
    """Phân tích và phân loại danh sách asset 3D bằng Google Gemini."""
    if not _client:
        return _build_mock_result(asset_names)

    prompt = _build_prompt(project_name, asset_names)
    logger.info("Gọi Gemini — dự án='%s', %d assets.", project_name, len(asset_names))

    try:
        raw_text = await _call_with_fallback(prompt)
        logger.debug("Gemini raw (300 đầu): %s", raw_text[:300])
        result = _parse_response(raw_text)
        logger.info("Gemini thành công — %d nhóm, %d đề xuất.", len(result.groups), len(result.improvements))
        return result
    except (ValueError, LookupError) as exc:
        raise RuntimeError(str(exc)) from exc
