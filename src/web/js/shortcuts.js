import { state } from "./state.js";
import { els } from "./dom.js";
import { closeMobileSidebar, switchView } from "./sidebar.js";
import { closeDetailsModal } from "./details.js";
import { closeFilesModal } from "./files.js";
import { hideOnboarding } from "./onboarding.js";
import { hidePalette, showPalette } from "./palette.js";
import { closeLabelsModal } from "./labels.js";
import { closeSafetyModal } from "./safety.js";

export function showShortcuts() {
  els.shortcutsBackdrop.hidden = false;
  setTimeout(() => els.shortcutsClose && els.shortcutsClose.focus(), 50);
}
function hideShortcuts() { els.shortcutsBackdrop.hidden = true; }

export function bindShortcutsEvents() {
  if (els.shortcutsClose) els.shortcutsClose.addEventListener("click", hideShortcuts);
  if (els.shortcutsBackdrop) {
    els.shortcutsBackdrop.addEventListener("click", (e) => {
      if (e.target === els.shortcutsBackdrop) hideShortcuts();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && els.safetyBackdrop && !els.safetyBackdrop.hidden) {
      closeSafetyModal();
    } else if (e.key === "Escape" && els.detailsBackdrop && !els.detailsBackdrop.hidden) {
      closeDetailsModal();
    } else if (e.key === "Escape" && els.filesBackdrop && !els.filesBackdrop.hidden) {
      closeFilesModal();
    } else if (e.key === "Escape" && !els.onboardingBackdrop.hidden) {
      hideOnboarding();
    } else if (e.key === "Escape" && state.sidebarOpenMobile) {
      closeMobileSidebar();
    } else if (e.key === "Escape" && els.paletteBackdrop && !els.paletteBackdrop.hidden) {
      hidePalette();
    } else if (e.key === "Escape" && els.labelsBackdrop && !els.labelsBackdrop.hidden) {
      closeLabelsModal();
    } else if (e.key === "Escape" && els.shortcutsBackdrop && !els.shortcutsBackdrop.hidden) {
      hideShortcuts();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      showPalette();
    } else if (e.key === "/" && document.activeElement !== els.searchInput) {
      e.preventDefault();
      switchView("search");
      els.searchInput.focus();
      els.searchInput.select();
    } else if (e.key === "?" && document.activeElement !== els.searchInput) {
      e.preventDefault();
      showShortcuts();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "f") {
      e.preventDefault();
      switchView("search");
      els.searchInput.focus();
      els.searchInput.select();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "d") {
      e.preventDefault();
      switchView("downloads");
    } else if ((e.ctrlKey || e.metaKey) && e.key === ",") {
      e.preventDefault();
      switchView("settings");
    }
  });
}
