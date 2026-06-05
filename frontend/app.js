/**
 * frontend/app.js
 * -----------------------------------------------------------------------
 * Logic frontend của 3D Asset Organizer — Vanilla JS thuần, không framework.
 *
 * Chịu trách nhiệm:
 *   - Validate input phía client trước khi gửi (input rỗng, tên dự án rỗng)
 *   - Gọi backend API tại http://localhost:8000/api/assets/organize
 *   - Quản lý trạng thái UI: loading, error, result, reset
 *   - Render 4 phần kết quả từ API response:
 *       1. Grouped assets (asset đã phân nhóm)
 *       2. Slug mappings (tên file gợi ý)
 *       3. Project metadata (tóm tắt dự án)
 *       4. Improvements (đề xuất cải thiện)
 *   - Nút "Dùng dữ liệu mẫu" để thử nhanh
 *   - Nút "Reset" quay về form nhập liệu
 *
 * Cấu trúc module — mỗi chức năng trong hàm riêng biệt:
 *   - DOM helpers
 *   - Validation
 *   - API call
 *   - Render functions (1 per result section)
 *   - UI state management (showLoading, showError, showResult, resetView)
 *   - Event listeners (form submit, reset, sample data)
 * -----------------------------------------------------------------------
 */

"use strict";

/* =========================================================
   CONSTANTS
   ========================================================= */

/** Địa chỉ backend API */
const API_BASE_URL = "http://localhost:8000";
const API_ORGANIZE_URL = `${API_BASE_URL}/api/assets/organize`;

/** Dữ liệu mẫu để test nhanh */
const SAMPLE_PROJECT_NAME = "Căn hộ Vinhomes Central Park - Tầng 15";
const SAMPLE_ASSETS = `Sofa 3 chỗ, Bàn cà phê tròn, Đèn sàn
Giường đôi King size
- Tủ quần áo 4 cánh
- Bàn trang điểm
Điều hòa 2HP, Quạt trần
Bồn tắm, Vòi sen, Toilet thông minh
Bàn ăn 6 người, Ghế ăn
Tủ bếp, Bếp từ, Máy hút mùi
Đèn chùm phòng khách, Đèn LED âm trần
Thảm trang trí, Rèm cửa`;


/* =========================================================
   DOM HELPERS
   ========================================================= */

/**
 * Lấy element theo ID — throw nếu không tìm thấy.
 * @param {string} id
 * @returns {HTMLElement}
 */
function getEl(id) {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Element #${id} không tồn tại trong DOM`);
  return el;
}

/**
 * Tạo một DOM element với attributes và children tùy chọn.
 * @param {string} tag
 * @param {Object} [attrs={}]
 * @param {...(string|Node)} children
 * @returns {HTMLElement}
 */
function createElement(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([key, val]) => {
    if (key === "className") el.className = val;
    else if (key === "textContent") el.textContent = val;
    else el.setAttribute(key, val);
  });
  children.forEach((child) => {
    if (typeof child === "string") el.appendChild(document.createTextNode(child));
    else if (child) el.appendChild(child);
  });
  return el;
}


/* =========================================================
   INPUT VALIDATION
   ========================================================= */

/**
 * Validate toàn bộ form input phía client.
 * Hiển thị lỗi dưới từng field nếu không hợp lệ.
 *
 * @returns {boolean} true nếu hợp lệ
 */
function validateForm() {
  const projectNameEl = getEl("input-project-name");
  const assetsEl      = getEl("input-assets");
  const errorName     = getEl("error-project-name");
  const errorAssets   = getEl("error-assets");

  let isValid = true;

  // --- Validate tên dự án ---
  if (!projectNameEl.value.trim()) {
    showFieldError(projectNameEl, errorName, "Vui lòng nhập tên dự án.");
    isValid = false;
  } else {
    clearFieldError(projectNameEl, errorName);
  }

  // --- Validate danh sách asset ---
  if (!assetsEl.value.trim()) {
    showFieldError(assetsEl, errorAssets, "Vui lòng nhập ít nhất 1 asset.");
    isValid = false;
  } else {
    clearFieldError(assetsEl, errorAssets);
  }

  return isValid;
}

/**
 * Đánh dấu field lỗi và hiển thị message.
 * @param {HTMLElement} field
 * @param {HTMLElement} errorEl
 * @param {string} message
 */
function showFieldError(field, errorEl, message) {
  field.classList.add("is-error");
  errorEl.textContent = message;
  field.focus();
}

/**
 * Xóa trạng thái lỗi của field.
 * @param {HTMLElement} field
 * @param {HTMLElement} errorEl
 */
function clearFieldError(field, errorEl) {
  field.classList.remove("is-error");
  errorEl.textContent = "";
}

/**
 * Xóa tất cả trạng thái lỗi trên form.
 */
function clearAllErrors() {
  clearFieldError(getEl("input-project-name"), getEl("error-project-name"));
  clearFieldError(getEl("input-assets"),       getEl("error-assets"));
  hideApiBanner();
}


/* =========================================================
   API CALL
   ========================================================= */

/**
 * Gọi backend API để phân tích và tổ chức asset.
 *
 * @param {string} projectName
 * @param {string} rawAssets
 * @returns {Promise<Object>} AssetOrganizeResponse từ server
 * @throws {Error} Khi API fail hoặc mạng lỗi
 */
async function callOrganizeAPI(projectName, rawAssets) {
  const payload = {
    project_name: projectName,
    raw_assets:   rawAssets,
  };

  let response;
  try {
    response = await fetch(API_ORGANIZE_URL, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
  } catch (networkError) {
    throw new Error(
      "Không thể kết nối đến server. " +
      "Vui lòng kiểm tra server đang chạy tại http://localhost:8000."
    );
  }

  if (!response.ok) {
    // Cố gắng đọc error message từ server
    let detail = `Lỗi server (HTTP ${response.status}).`;
    try {
      const errBody = await response.json();
      if (errBody.detail) detail = errBody.detail;
    } catch (_) { /* ignore parse error */ }
    throw new Error(detail);
  }

  return response.json();
}


/* =========================================================
   RENDER FUNCTIONS
   ========================================================= */

/**
 * Render phần 1: Asset đã phân nhóm theo không gian.
 * @param {Array<{group_name: string, assets: Array}>} groups
 */
function renderGroupedAssets(groups) {
  const container = getEl("result-groups");
  container.innerHTML = "";

  if (!groups || groups.length === 0) {
    container.textContent = "Không có dữ liệu phân nhóm.";
    return;
  }

  groups.forEach((group) => {
    const list = createElement("ul", { className: "group-block__list" });

    (group.assets || []).forEach((asset) => {
      const nameEl   = createElement("span", { className: "group-block__item-name",   textContent: asset.name   });
      const reasonEl = createElement("span", { className: "group-block__item-reason", textContent: asset.reason });
      const item     = createElement("li",   { className: "group-block__item" }, nameEl, reasonEl);
      list.appendChild(item);
    });

    const header = createElement("div", {
      className:   "group-block__header",
      textContent: `${group.group_name} (${(group.assets || []).length})`,
    });

    const block = createElement("div", { className: "group-block" }, header, list);
    container.appendChild(block);
  });
}

/**
 * Render phần 2: Slug tên file gợi ý.
 * @param {Array<{original_name: string, slug: string}>} slugMappings
 */
function renderSlugMappings(slugMappings) {
  const wrapper = getEl("result-slugs");
  wrapper.innerHTML = "";

  if (!slugMappings || slugMappings.length === 0) {
    wrapper.textContent = "Không có dữ liệu slug.";
    return;
  }

  const thead = createElement(
    "thead", {},
    createElement("tr", {},
      createElement("th", { textContent: "Tên gốc"      }),
      createElement("th", { textContent: "Slug gợi ý"   }),
    )
  );

  const tbody = createElement("tbody", {});
  slugMappings.forEach(({ original_name, slug }) => {
    const slugCell = createElement("td", {});
    slugCell.appendChild(createElement("code", { className: "slug-value", textContent: slug }));

    tbody.appendChild(
      createElement("tr", {},
        createElement("td", { textContent: original_name }),
        slugCell,
      )
    );
  });

  const table = createElement("table", { className: "slug-table" }, thead, tbody);
  wrapper.appendChild(table);
}

/**
 * Render phần 3: Metadata tóm tắt dự án.
 * @param {Object} metadata
 */
function renderMetadata(metadata) {
  const container = getEl("result-metadata");
  container.innerHTML = "";

  const items = [
    { label: "Tên dự án",      value: metadata.project_name },
    { label: "Tổng số asset",  value: `${metadata.total_assets} asset` },
    { label: "Số nhóm",        value: `${metadata.total_groups} nhóm` },
  ];

  const list = createElement("ul", { className: "metadata-list" });
  items.forEach(({ label, value }) => {
    const labelEl = createElement("span", { className: "metadata-item__label", textContent: label });
    const valueEl = createElement("span", { className: "metadata-item__value", textContent: value });
    list.appendChild(createElement("li", { className: "metadata-item" }, labelEl, valueEl));
  });

  container.appendChild(list);
}

/**
 * Render phần 4: Đề xuất cải thiện.
 * @param {string[]} improvements
 */
function renderImprovements(improvements) {
  const list = getEl("result-improvements");
  list.innerHTML = "";

  if (!improvements || improvements.length === 0) {
    list.appendChild(createElement("li", { textContent: "Không có đề xuất." }));
    return;
  }

  improvements.forEach((text) => {
    list.appendChild(createElement("li", { textContent: text }));
  });
}

/**
 * Render toàn bộ kết quả từ API response.
 * @param {Object} data — AssetOrganizeResponse
 */
function renderResult(data) {
  // Header kết quả
  getEl("result-project-name").textContent = data.metadata?.project_name || "Kết quả";
  getEl("result-meta-summary").textContent =
    `${data.metadata?.total_assets} asset · ${data.metadata?.total_groups} nhóm`;

  renderGroupedAssets(data.grouped_assets);
  renderSlugMappings(data.slug_mappings);
  renderMetadata(data.metadata);
  renderImprovements(data.improvements);
}


/* =========================================================
   UI STATE MANAGEMENT
   ========================================================= */

/**
 * Hiển thị loading state trên nút submit.
 */
function setLoadingState(isLoading) {
  const btn     = getEl("btn-submit");
  const btnText = getEl("btn-submit-text");
  const spinner = getEl("btn-submit-spinner");

  btn.disabled         = isLoading;
  spinner.hidden       = !isLoading;
  btnText.textContent  = isLoading ? "Đang phân tích..." : "Phân tích bằng AI";
}

/**
 * Hiển thị error banner bên dưới form (khi API fail).
 * @param {string} message
 */
function showApiBanner(message) {
  const banner = getEl("api-error-banner");
  getEl("api-error-message").textContent = message;
  banner.hidden = false;
  banner.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Ẩn error banner API.
 */
function hideApiBanner() {
  getEl("api-error-banner").hidden = true;
  getEl("api-error-message").textContent = "";
}

/**
 * Chuyển sang View kết quả.
 */
function showResultView() {
  const inputView  = getEl("view-input");
  const resultView = getEl("view-result");

  inputView.classList.remove("view--active");
  inputView.hidden  = true;
  resultView.hidden = false;
  resultView.classList.add("view--active");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/**
 * Quay về View nhập liệu (reset toàn bộ).
 */
function resetView() {
  const inputView  = getEl("view-input");
  const resultView = getEl("view-result");

  resultView.classList.remove("view--active");
  resultView.hidden = true;
  inputView.hidden  = false;
  inputView.classList.add("view--active");

  clearAllErrors();
  window.scrollTo({ top: 0, behavior: "smooth" });
}


/* =========================================================
   EVENT HANDLERS
   ========================================================= */

/**
 * Xử lý submit form — luồng chính:
 * validate → loading → API call → render result / show error
 */
async function handleFormSubmit(event) {
  event.preventDefault();
  clearAllErrors();

  if (!validateForm()) return;

  const projectName = getEl("input-project-name").value.trim();
  const rawAssets   = getEl("input-assets").value.trim();

  setLoadingState(true);

  try {
    const data = await callOrganizeAPI(projectName, rawAssets);
    renderResult(data);
    showResultView();
  } catch (error) {
    showApiBanner(error.message);
  } finally {
    setLoadingState(false);
  }
}

/**
 * Điền dữ liệu mẫu vào form để người dùng thử nhanh.
 */
function handleLoadSample() {
  getEl("input-project-name").value = SAMPLE_PROJECT_NAME;
  getEl("input-assets").value       = SAMPLE_ASSETS;
  clearAllErrors();
  getEl("input-project-name").focus();
}

/**
 * Xử lý nút "Phân tích lại" — reset về form nhập.
 */
function handleReset() {
  resetView();
}


/* =========================================================
   INIT — đăng ký event listeners khi DOM sẵn sàng
   ========================================================= */

function init() {
  getEl("form-organize").addEventListener("submit", handleFormSubmit);
  getEl("btn-load-sample").addEventListener("click", handleLoadSample);
  getEl("btn-reset").addEventListener("click", handleReset);

  // Xóa lỗi field khi người dùng bắt đầu gõ lại
  getEl("input-project-name").addEventListener("input", () => {
    clearFieldError(getEl("input-project-name"), getEl("error-project-name"));
  });
  getEl("input-assets").addEventListener("input", () => {
    clearFieldError(getEl("input-assets"), getEl("error-assets"));
    hideApiBanner();
  });
}

document.addEventListener("DOMContentLoaded", init);
