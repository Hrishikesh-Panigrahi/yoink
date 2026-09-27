/* Adding torrents from search results or the clipboard, and handling duplicates. */

import { bridge } from "./state.js";
import { els } from "./dom.js";
import { toast } from "./toasts.js";
import { switchView } from "./sidebar.js";
import { addByDetection } from "./search.js";

export function parseAddResult(raw) {
  if (!raw) return { hash: "", wasExisting: false };
  if (typeof raw === "object") return raw;
  try {
    const obj = JSON.parse(raw);
    return obj && typeof obj === "object"
      ? { hash: obj.hash || "", wasExisting: !!obj.wasExisting, name: obj.name }
      : { hash: String(raw), wasExisting: false };
  } catch (_) {
    return { hash: String(raw), wasExisting: false };
  }
}

function focusDownloadRow(hash) {
  switchView("downloads");
  setTimeout(() => {
    const node = els.downloadsList.querySelector(`.download-row[data-hash="${hash}"]`);
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
      node.classList.add("flash");
      setTimeout(() => node.classList.remove("flash"), 1500);
    }
  }, 250);
}

export function addFromResult(result, btn) {
  const safety = result.safety;
  if (safety && safety.level === "risky") {
    const reasons = (safety.reasons || []).map((r) => `\u2022 ${r}`).join("\n");
    const ok = confirm(
      `This torrent looks risky:\n\n${reasons}\n\nAdd it anyway?`
    );
    if (!ok) return;
  }
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Adding...";
  }
  bridge.addTorrent(result.magnet, (raw) => {
    const { hash, wasExisting } = parseAddResult(raw);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<svg viewBox="0 0 24 24" class="ic" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg> Yoinked`;
    }
    if (!hash) return;
    if (wasExisting) {
      showDuplicateToast(hash);
    } else {
      toast("success", "Added to downloads");
      setTimeout(() => switchView("downloads"), 500);
    }
  });
}

function showClipboardOfferToast(magnet) {
  const el = document.createElement("div");
  el.className = "toast info";
  el.setAttribute("role", "status");
  el.innerHTML = `Clipboard magnet detected. <button type="button" class="toast-action add-it">Add</button> <button type="button" class="toast-action" style="background:transparent;color:var(--text);">Dismiss</button>`;
  const [add, dismiss] = el.querySelectorAll(".toast-action");
  add.addEventListener("click", () => {
    addByDetection({ kind: "magnet", value: magnet });
    el.remove();
  });
  dismiss.addEventListener("click", () => el.remove());
  els.toastStack.appendChild(el);
  setTimeout(() => {
    el.classList.add("fade-out");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, 8000);
}

export function showDuplicateToast(hash) {
  const el = document.createElement("div");
  el.className = "toast info";
  el.setAttribute("role", "status");
  el.innerHTML = `Already in your library. <button type="button" class="toast-action">Jump to it</button>`;
  el.querySelector(".toast-action").addEventListener("click", () => {
    focusDownloadRow(hash);
    el.remove();
  });
  els.toastStack.appendChild(el);
  setTimeout(() => {
    el.classList.add("fade-out");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, 6000);
}

export function connectAddSignals() {
  if (bridge.clipboardMagnet) {
    bridge.clipboardMagnet.connect((magnet) => showClipboardOfferToast(magnet));
  }
}
