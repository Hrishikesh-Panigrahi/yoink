import { bridge } from "./state.js";
import { els } from "./dom.js";
import { escapeHtml } from "./util.js";
import { toast } from "./toasts.js";

const labelsState = { hash: "", labels: [], allLabels: [] };
export function openLabelsModal(hash, name) {
  labelsState.hash = hash;
  els.labelsSubtitle.textContent = name || "";
  bridge.getLabels(hash, (raw) => {
    try { labelsState.labels = JSON.parse(raw || "[]"); } catch (_) { labelsState.labels = []; }
    bridge.getAllLabels((rawAll) => {
      try { labelsState.allLabels = JSON.parse(rawAll || "[]"); } catch (_) { labelsState.allLabels = []; }
      renderLabelsEditor();
      els.labelsBackdrop.hidden = false;
      setTimeout(() => els.labelsInput && els.labelsInput.focus(), 50);
    });
  });
}
function renderLabelsEditor() {
  els.labelsChips.innerHTML = "";
  labelsState.labels.forEach((lbl) => {
    const pill = document.createElement("span");
    pill.className = "label-pill";
    pill.innerHTML = `${escapeHtml(lbl)}<button type="button" class="remove" aria-label="Remove ${escapeHtml(lbl)}">×</button>`;
    pill.querySelector(".remove").addEventListener("click", () => {
      labelsState.labels = labelsState.labels.filter((l) => l !== lbl);
      renderLabelsEditor();
    });
    els.labelsChips.appendChild(pill);
  });
  els.labelsSuggestions.innerHTML = "";
  labelsState.allLabels
    .filter((l) => !labelsState.labels.includes(l))
    .slice(0, 10)
    .forEach((lbl) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = lbl;
      chip.addEventListener("click", () => {
        labelsState.labels.push(lbl);
        renderLabelsEditor();
      });
      els.labelsSuggestions.appendChild(chip);
    });
}
export function closeLabelsModal() { els.labelsBackdrop.hidden = true; }
function applyLabels() {
  bridge.setLabels(labelsState.hash, JSON.stringify(labelsState.labels));
  closeLabelsModal();
  toast("success", "Labels saved");
}

export function bindLabelsEvents() {
  if (els.labelsInput) {
    els.labelsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const val = (els.labelsInput.value || "").trim();
        if (val && !labelsState.labels.includes(val)) {
          labelsState.labels.push(val);
          renderLabelsEditor();
        }
        els.labelsInput.value = "";
      }
    });
  }
  if (els.labelsCancel) els.labelsCancel.addEventListener("click", closeLabelsModal);
  if (els.labelsApply) els.labelsApply.addEventListener("click", applyLabels);
  if (els.labelsBackdrop) {
    els.labelsBackdrop.addEventListener("click", (e) => {
      if (e.target === els.labelsBackdrop) closeLabelsModal();
    });
  }
}
