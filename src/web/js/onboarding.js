import { bridge } from "./state.js";
import { els } from "./dom.js";
import { saveFilters } from "./search.js";

const wizard = { step: 1, total: 4, category: "other" };

function showWizardStep(step) {
  wizard.step = step;
  els.wizardSteps.forEach((s) => s.classList.toggle("is-active", Number(s.dataset.step) === step));
  els.wizardDots.forEach((d, i) => d.classList.toggle("is-active", i < step));
  els.wizardBack.hidden = step <= 1;
  els.wizardNext.hidden = step >= wizard.total;
  els.onboardingDone.hidden = step < wizard.total;
}
export function showOnboarding() {
  els.onboardingBackdrop.hidden = false;
  showWizardStep(1);
  setTimeout(() => els.wizardNext.focus(), 50);
}
export function hideOnboarding() {
  els.onboardingBackdrop.hidden = true;
  localStorage.setItem("yoink.onboardingSeen", "1");
  els.searchInput && els.searchInput.focus();
}
function finishWizard() {
  if (wizard.category && els.categoryFilter) {
    const map = { movies: "movies", tv: "tv", anime: "anime", other: "any" };
    const val = map[wizard.category];
    if (val) {
      els.categoryFilter.value = val;
      saveFilters();
    }
  }
  if (bridge && bridge.setBoolSetting) {
    bridge.setBoolSetting("minimize_to_tray", !!els.wizardMinimizeTray.checked);
    bridge.setBoolSetting("notifications_enabled", !!els.wizardNotifications.checked);
  }
  if (bridge && bridge.setTmdbApiKey) {
    const key = (els.wizardTmdbKey.value || "").trim();
    if (key) bridge.setTmdbApiKey(key);
  }
  hideOnboarding();
}
export function maybeShowOnboarding() {
  if (!localStorage.getItem("yoink.onboardingSeen")) {
    showOnboarding();
  }
}

export function bindOnboardingEvents() {
  els.replayOnboardingBtn.addEventListener("click", showOnboarding);

  els.onboardingDone.addEventListener("click", finishWizard);
  els.onboardingBackdrop.addEventListener("click", (e) => {
    if (e.target === els.onboardingBackdrop) hideOnboarding();
  });
  els.wizardSkip.addEventListener("click", hideOnboarding);
  els.wizardBack.addEventListener("click", () => showWizardStep(Math.max(1, wizard.step - 1)));
  els.wizardNext.addEventListener("click", () => showWizardStep(Math.min(wizard.total, wizard.step + 1)));
  els.wizardPickFolder.addEventListener("click", () => {
    bridge.pickSaveFolder((folder) => {
      if (folder) els.wizardFolderPath.textContent = folder;
    });
  });
  els.wizardPicks.forEach((btn) => {
    btn.addEventListener("click", () => {
      els.wizardPicks.forEach((b) => b.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      wizard.category = btn.dataset.category;
    });
  });
  if (els.wizardTmdbHelp) {
    els.wizardTmdbHelp.addEventListener("click", (e) => {
      e.preventDefault();
      bridge.openExternal(els.wizardTmdbHelp.href);
    });
  }
}
