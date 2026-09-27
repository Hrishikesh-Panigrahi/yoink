import { bridge } from "./state.js";
import { els } from "./dom.js";
import { THEMES, applyTheme } from "./theme.js";
import { showOnboarding } from "./onboarding.js";
import { showShortcuts } from "./shortcuts.js";

const palette = { commands: [], filtered: [], active: 0 };
export function loadPaletteCommands() {
  if (!bridge || !bridge.listCommands) return;
  bridge.listCommands((raw) => {
    try {
      palette.commands = JSON.parse(raw || "[]");
    } catch (_) {
      palette.commands = [];
    }
    THEMES.forEach((t) => palette.commands.push({ id: `theme:${t}`, label: `Theme: ${t}` }));
    palette.commands.push({ id: "ui:shortcuts", label: "Show keyboard shortcuts" });
    palette.commands.push({ id: "ui:onboarding", label: "Replay welcome tour" });
  });
}
export function showPalette() {
  els.paletteInput.value = "";
  filterPalette("");
  els.paletteBackdrop.hidden = false;
  setTimeout(() => els.paletteInput.focus(), 50);
}
export function hidePalette() { els.paletteBackdrop.hidden = true; }
function filterPalette(q) {
  const query = (q || "").trim().toLowerCase();
  palette.filtered = palette.commands.filter((c) =>
    !query || c.label.toLowerCase().includes(query)
  );
  palette.active = 0;
  renderPalette();
}
function renderPalette() {
  els.paletteList.innerHTML = "";
  palette.filtered.forEach((c, i) => {
    const li = document.createElement("li");
    li.textContent = c.label;
    li.setAttribute("role", "option");
    if (i === palette.active) li.classList.add("is-active");
    li.addEventListener("click", () => runPaletteCommand(c));
    els.paletteList.appendChild(li);
  });
}
function runPaletteCommand(cmd) {
  hidePalette();
  if (!cmd) return;
  if (cmd.id.startsWith("theme:")) {
    applyTheme(cmd.id.slice(6));
  } else if (cmd.id === "ui:shortcuts") {
    showShortcuts();
  } else if (cmd.id === "ui:onboarding") {
    showOnboarding();
  } else if (bridge && bridge.runCommand) {
    bridge.runCommand(cmd.id);
  }
}

export function bindPaletteEvents() {
  if (els.paletteInput) {
    els.paletteInput.addEventListener("input", (e) => filterPalette(e.target.value));
    els.paletteInput.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        palette.active = Math.min(palette.filtered.length - 1, palette.active + 1);
        renderPalette();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        palette.active = Math.max(0, palette.active - 1);
        renderPalette();
      } else if (e.key === "Enter") {
        e.preventDefault();
        runPaletteCommand(palette.filtered[palette.active]);
      }
    });
    els.paletteBackdrop.addEventListener("click", (e) => {
      if (e.target === els.paletteBackdrop) hidePalette();
    });
  }
}
