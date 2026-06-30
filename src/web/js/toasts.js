/* toasts.js — transient notification helper.
 *
 * Exposes the toast() function used across the UI. main.js still defines
 * its own copy bound to the cached `els.toastStack`; this module is the
 * portable alternative that resolves the stack at call time.
 */

export function toast(kind, message, opts = {}) {
  const stack = document.getElementById("toastStack");
  if (!stack) return null;
  const el = document.createElement("div");
  el.className = `toast ${kind || "info"}`;
  el.setAttribute("role", kind === "error" ? "alert" : "status");
  el.textContent = String(message ?? "");
  stack.appendChild(el);
  const ttl = Number.isFinite(opts.ttl) ? opts.ttl : 3200;
  setTimeout(() => {
    el.classList.add("fade-out");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, ttl);
  return el;
}
