import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { escapeHtml } from "./util.js";

export function openFilesModal(hash) {
  state.filesModal = { hash, files: [] };
  const t = state.downloads.find((d) => d.hash === hash);
  els.filesTitle.textContent = "Pick files to download";
  els.filesSubtitle.textContent = t?.name || "Choose which files to include and tweak per-file priority.";
  els.filesTable.innerHTML = '<p class="muted small" style="padding:16px">Loading file list...</p>';
  els.filesBackdrop.hidden = false;
  bridge.getTorrentFiles(hash, (raw) => {
    try {
      const files = JSON.parse(raw || "[]");
      state.filesModal.files = files;
      renderFilesTable(files);
    } catch (e) {
      console.error(e);
      els.filesTable.innerHTML = '<p class="muted small" style="padding:16px">Could not load files (metadata might still be downloading).</p>';
    }
  });
}

function renderFilesTable(files) {
  if (!files.length) {
    els.filesTable.innerHTML = '<p class="muted small" style="padding:16px">Metadata not ready yet \u2014 try again in a few seconds.</p>';
    els.filesSelectedCount.textContent = "";
    return;
  }
  const rows = files
    .map(
      (f) => `
      <div class="files-row" role="row">
        <label class="files-check">
          <input type="checkbox" data-idx="${f.index}" ${f.priority > 0 ? "checked" : ""} aria-label="Include ${escapeHtml(f.path)}" />
        </label>
        <div class="files-name" title="${escapeHtml(f.path)}">${escapeHtml(f.path)}</div>
        <div class="files-size">${escapeHtml(f.sizeStr)}</div>
        <div class="files-progress">${(f.progress || 0).toFixed(0)}%</div>
        <select class="files-priority" data-idx="${f.index}" aria-label="Priority for ${escapeHtml(f.path)}">
          <option value="1" ${f.priority === 1 ? "selected" : ""}>Low</option>
          <option value="4" ${(!f.priority || f.priority === 4) ? "selected" : ""}>Normal</option>
          <option value="7" ${f.priority === 7 ? "selected" : ""}>High</option>
        </select>
      </div>`
    )
    .join("");
  els.filesTable.innerHTML = `
    <div class="files-row files-head" role="row">
      <span></span><span>File</span><span>Size</span><span>Done</span><span>Priority</span>
    </div>
    ${rows}
  `;
  els.filesTable.querySelectorAll("input[type=checkbox], select").forEach((control) => {
    control.addEventListener("change", updateFilesSelectionCount);
  });
  updateFilesSelectionCount();
}

function updateFilesSelectionCount() {
  const total = els.filesTable.querySelectorAll("input[type=checkbox]").length;
  const selected = els.filesTable.querySelectorAll("input[type=checkbox]:checked").length;
  els.filesSelectedCount.textContent = total ? `${selected} of ${total} files selected` : "";
}

export function closeFilesModal() {
  els.filesBackdrop.hidden = true;
  state.filesModal = { hash: null, files: [] };
}

function applyFilesSelection() {
  const hash = state.filesModal.hash;
  if (!hash) return;
  const priorities = {};
  els.filesTable.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    const idx = cb.dataset.idx;
    if (!cb.checked) {
      priorities[idx] = 0;
    } else {
      const sel = els.filesTable.querySelector(`select[data-idx="${idx}"]`);
      priorities[idx] = sel ? parseInt(sel.value, 10) : 4;
    }
  });
  bridge.setFilePriorities(hash, JSON.stringify(priorities), (ok) => {
    if (ok) closeFilesModal();
  });
}

export function bindFilesEvents() {
  if (els.filesCancel) els.filesCancel.addEventListener("click", closeFilesModal);
  if (els.filesApply) els.filesApply.addEventListener("click", applyFilesSelection);
  if (els.filesBackdrop) {
    els.filesBackdrop.addEventListener("click", (e) => {
      if (e.target === els.filesBackdrop) closeFilesModal();
    });
  }
  if (els.filesSelectAll) {
    els.filesSelectAll.addEventListener("click", () => {
      els.filesTable.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = true; });
      updateFilesSelectionCount();
    });
  }
  if (els.filesSelectNone) {
    els.filesSelectNone.addEventListener("click", () => {
      els.filesTable.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = false; });
      updateFilesSelectionCount();
    });
  }
}
