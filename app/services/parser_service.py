# app/services/parser_service.py
# -----------------------------------------------------------------------
# Tầng xử lý nghiệp vụ — Input Parser Service
#
# Chịu trách nhiệm:
#   - Nhận bất kỳ định dạng thô nào từ người dùng:
#       * Phân cách bằng dấu phẩy: "Sofa, Bàn trà, Đèn"
#       * Phân cách bằng xuống dòng: "Sofa\nBàn trà"
#       * Gạch đầu dòng: "- Sofa\n- Bàn trà"
#       * JSON array dạng string: '["Sofa", "Bàn trà"]'
#   - Trả về danh sách tên asset sạch, không trùng lặp, không rỗng
#   - Chuyển đổi tên asset thành slug thân thiện với URL
#     (xử lý được ký tự tiếng Việt → ASCII, dấu cách → gạch ngang)
#
# Không dùng thư viện ngoài nào. Hoạt động ổn định với input lộn xộn.
# -----------------------------------------------------------------------

from __future__ import annotations

import json
import re
import unicodedata


# ---------------------------------------------------------------------------
# Bảng map ký tự có dấu tiếng Việt → không dấu
# Dùng thủ công để không phụ thuộc vào thư viện ngoài (unidecode, v.v.)
# ---------------------------------------------------------------------------
_VIETNAMESE_MAP: dict[str, str] = {
    "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
    "ă": "a", "ắ": "a", "ặ": "a", "ằ": "a", "ẳ": "a", "ẵ": "a",
    "â": "a", "ấ": "a", "ầ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
    "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
    "ê": "e", "ế": "e", "ề": "e", "ể": "e", "ễ": "e", "ệ": "e",
    "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
    "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
    "ô": "o", "ố": "o", "ồ": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
    "ơ": "o", "ớ": "o", "ờ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
    "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
    "ư": "u", "ứ": "u", "ừ": "u", "ử": "u", "ữ": "u", "ự": "u",
    "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    "đ": "d",
    # Chữ hoa
    "À": "a", "Á": "a", "Ả": "a", "Ã": "a", "Ạ": "a",
    "Ă": "a", "Ắ": "a", "Ặ": "a", "Ằ": "a", "Ẳ": "a", "Ẵ": "a",
    "Â": "a", "Ấ": "a", "Ầ": "a", "Ẩ": "a", "Ẫ": "a", "Ậ": "a",
    "È": "e", "É": "e", "Ẻ": "e", "Ẽ": "e", "Ẹ": "e",
    "Ê": "e", "Ế": "e", "Ề": "e", "Ể": "e", "Ễ": "e", "Ệ": "e",
    "Ì": "i", "Í": "i", "Ỉ": "i", "Ĩ": "i", "Ị": "i",
    "Ò": "o", "Ó": "o", "Ỏ": "o", "Õ": "o", "Ọ": "o",
    "Ô": "o", "Ố": "o", "Ồ": "o", "Ổ": "o", "Ỗ": "o", "Ộ": "o",
    "Ơ": "o", "Ớ": "o", "Ờ": "o", "Ở": "o", "Ỡ": "o", "Ợ": "o",
    "Ù": "u", "Ú": "u", "Ủ": "u", "Ũ": "u", "Ụ": "u",
    "Ư": "u", "Ứ": "u", "Ừ": "u", "Ử": "u", "Ữ": "u", "Ự": "u",
    "Ỳ": "y", "Ý": "y", "Ỷ": "y", "Ỹ": "y", "Ỵ": "y",
    "Đ": "d",
}


def _remove_vietnamese(text: str) -> str:
    """Chuyển ký tự tiếng Việt có dấu thành ASCII tương đương."""
    result = []
    for char in text:
        result.append(_VIETNAMESE_MAP.get(char, char))
    return "".join(result)


def slugify(text: str) -> str:
    """
    Chuyển một chuỗi tên asset thành slug thân thiện với URL và hệ thống file.

    Quy trình:
      1. Map ký tự tiếng Việt → ASCII
      2. Normalize unicode (NFKD) rồi bỏ combining characters
      3. Chuyển về chữ thường
      4. Thay ký tự không phải alphanumeric → gạch ngang
      5. Loại bỏ gạch ngang đầu/cuối và gạch ngang liên tiếp

    Ví dụ:
      "Bàn cà phê"   → "ban-ca-phe"
      "Điều hòa 2HP" → "dieu-hoa-2hp"
      "  Sofa đôi!!" → "sofa-doi"
    """
    text = _remove_vietnamese(text)
    # Normalize và bỏ dấu còn sót (combining characters)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    # Thay mọi ký tự không phải chữ/số bằng gạch ngang
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Bỏ gạch ngang đầu/cuối
    text = text.strip("-")
    return text


def parse_raw_assets(raw_input: str) -> list[str]:
    """
    Nhận chuỗi asset thô ở bất kỳ định dạng nào và trả về
    danh sách tên asset đã được làm sạch, không trùng lặp, không rỗng.

    Hỗ trợ các định dạng:
      - JSON array:    '["Sofa", "Bàn trà"]'
      - Dấu phẩy:     "Sofa, Bàn trà, Đèn sàn"
      - Xuống dòng:   "Sofa\nBàn trà\nĐèn sàn"
      - Gạch đầu dòng: "- Sofa\n- Bàn trà\n* Đèn sàn"
      - Hỗn hợp:      "Sofa, Bàn trà\n- Đèn sàn"

    Returns:
        Danh sách tên asset duy nhất, thứ tự giữ nguyên (insertion-ordered set).
    """
    raw_input = raw_input.strip()

    # --- Thử parse JSON array trước ---
    if raw_input.startswith("["):
        try:
            items: list = json.loads(raw_input)
            if isinstance(items, list):
                return _clean_list([str(i) for i in items])
        except json.JSONDecodeError:
            pass  # Không phải JSON hợp lệ → tiếp tục xử lý như text thô

    # --- Tách theo dấu phẩy VÀ/HOẶC xuống dòng ---
    # Ưu tiên tách theo dấu phẩy và newline đồng thời
    tokens = re.split(r"[,\n]+", raw_input)

    return _clean_list(tokens)


def _clean_list(tokens: list[str]) -> list[str]:
    """
    Làm sạch danh sách token:
      - Strip khoảng trắng
      - Bỏ prefix gạch đầu dòng (-, *, •)
      - Loại bỏ chuỗi rỗng
      - Loại bỏ trùng lặp (giữ thứ tự xuất hiện đầu tiên, case-insensitive)
    """
    seen: set[str] = set()
    result: list[str] = []

    for token in tokens:
        # Bỏ khoảng trắng thừa
        cleaned = token.strip()
        # Bỏ ký tự đầu dòng kiểu bullet: -, *, •, +
        cleaned = re.sub(r"^[\-\*\•\+]\s*", "", cleaned).strip()

        if not cleaned:
            continue

        # Dedup — so sánh lowercase nhưng giữ case gốc
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            result.append(cleaned)

    return result
