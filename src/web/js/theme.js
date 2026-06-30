/* theme.js — theme catalog and apply/init helpers.
 *
 * Mirrors the theme logic in main.js. main.js still applies the active theme
 * during boot for backwards compatibility; future cleanups should import
 * `applyTheme` and `initTheme` from this module instead.
 */

export const THEMES = new Set([
  "swarm",
  "paper",
  "pirate",
  "cobalt",
  "sunset",
  "terminal",
  "slate",
  "mint",
]);

const LEGACY_THEME_MAP = { dark: "swarm", light: "paper", auto: "swarm" };

export function normalizeTheme(name) {
  if (!name) return "swarm";
  if (THEMES.has(name)) return name;
  if (LEGACY_THEME_MAP[name]) return LEGACY_THEME_MAP[name];
  return "swarm";
}

export function applyTheme(name) {
  const theme = normalizeTheme(name);
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem("yoink.theme", theme);
  } catch (_) {
    /* private-mode storage failures are non-fatal */
  }
  return theme;
}

export function initTheme() {
  let saved = null;
  try {
    saved = localStorage.getItem("yoink.theme");
  } catch (_) {
    /* ignore */
  }
  return applyTheme(saved);
}
