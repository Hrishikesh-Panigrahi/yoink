import { state } from "./state.js";
import { els } from "./dom.js";

export const THEMES = new Set([
  "swarm", "paper", "pirate", "cobalt", "sunset", "terminal", "slate", "mint",
]);
const LEGACY_THEME_MAP = { dark: "swarm", light: "paper", auto: "swarm" };

function normalizeTheme(name) {
  if (!name) return "swarm";
  if (THEMES.has(name)) return name;
  if (LEGACY_THEME_MAP[name]) return LEGACY_THEME_MAP[name];
  return "swarm";
}

export function applyTheme(name) {
  const theme = normalizeTheme(name);
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  els.themeButtons.forEach((b) =>
    b.setAttribute("aria-pressed", b.dataset.themeSet === theme ? "true" : "false")
  );
  localStorage.setItem("yoink.theme", theme);
}

export function initTheme() {
  const saved = localStorage.getItem("yoink.theme");
  applyTheme(saved);
}

export function bindThemeEvents() {
  els.themeButtons.forEach((b) =>
    b.addEventListener("click", () => applyTheme(b.dataset.themeSet))
  );
}
