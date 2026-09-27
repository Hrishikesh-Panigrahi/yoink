import { els } from "./dom.js";

export function openSafetyModal(level, reasons, title) {
  const tagText = level === "risky"
    ? "Risky: Yoink flagged several concerns"
    : level === "caution"
    ? "Check: be careful with this one"
    : "Trusted: known good uploader, well seeded";
  els.safetyTitle.textContent = `Safety: ${title || "this torrent"}`;
  els.safetyTag.textContent = tagText;
  els.safetyReasons.innerHTML = "";
  if (!reasons.length) {
    const li = document.createElement("li");
    li.textContent = "No specific concerns recorded.";
    els.safetyReasons.appendChild(li);
  } else {
    reasons.forEach((reason) => {
      const li = document.createElement("li");
      if (level === "caution") li.classList.add("is-caution");
      li.textContent = reason;
      els.safetyReasons.appendChild(li);
    });
  }
  els.safetyBackdrop.hidden = false;
  setTimeout(() => els.safetyClose && els.safetyClose.focus(), 50);
}
export function closeSafetyModal() { els.safetyBackdrop.hidden = true; }

export function bindSafetyEvents() {
  if (els.safetyClose) els.safetyClose.addEventListener("click", closeSafetyModal);
  if (els.safetyBackdrop) {
    els.safetyBackdrop.addEventListener("click", (e) => {
      if (e.target === els.safetyBackdrop) closeSafetyModal();
    });
  }
}
