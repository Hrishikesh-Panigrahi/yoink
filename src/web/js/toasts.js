import { bridge } from "./state.js";
import { els } from "./dom.js";

export function toast(kind, message) {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.setAttribute("role", kind === "error" ? "alert" : "status");
  el.textContent = message;
  els.toastStack.appendChild(el);
  setTimeout(() => {
    el.classList.add("fade-out");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, 3200);
}

export function connectToastsSignals() {
  bridge.toast.connect((kind, msg) => toast(kind, msg));
}
