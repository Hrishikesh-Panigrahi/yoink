import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { isMobile } from "./util.js";

function toggleSidebar() {
  if (isMobile()) {
    state.sidebarOpenMobile = !state.sidebarOpenMobile;
    els.app.classList.toggle("sidebar-open", state.sidebarOpenMobile);
  } else {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    els.sidebar.classList.toggle("collapsed", state.sidebarCollapsed);
  }
}

export function closeMobileSidebar() {
  if (state.sidebarOpenMobile) {
    state.sidebarOpenMobile = false;
    els.app.classList.remove("sidebar-open");
  }
}

export function switchView(name) {
  state.view = name;
  els.navItems.forEach((b) => {
    const active = b.dataset.view === name;
    b.classList.toggle("active", active);
    b.setAttribute("aria-selected", active ? "true" : "false");
  });
  els.views.forEach((v) => v.classList.toggle("hidden", v.dataset.view !== name));
  closeMobileSidebar();
}

function handleNavKey(e) {
  const items = els.navItems;
  const idx = items.indexOf(document.activeElement);
  if (idx < 0) return;
  if (e.key === "ArrowDown" || e.key === "ArrowRight") {
    e.preventDefault();
    items[(idx + 1) % items.length].focus();
  } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
    e.preventDefault();
    items[(idx - 1 + items.length) % items.length].focus();
  } else if (e.key === "Home") {
    e.preventDefault();
    items[0].focus();
  } else if (e.key === "End") {
    e.preventDefault();
    items[items.length - 1].focus();
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    document.activeElement.click();
  }
}

export function bindSidebarEvents() {
  els.brandBtn.addEventListener("click", toggleSidebar);
  els.menuToggles.forEach((b) => b.addEventListener("click", toggleSidebar));
  els.sidebarScrim.addEventListener("click", closeMobileSidebar);

  els.navItems.forEach((b) => {
    b.addEventListener("click", () => switchView(b.dataset.view));
    b.addEventListener("keydown", handleNavKey);
  });

  els.folderPill.addEventListener("click", () => bridge.openSaveFolder(""));
}
