/* The Sources tab in Settings: provider toggles and health checks. */

import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { escapeHtml } from "./util.js";

export function loadProviderChoices() {
  if (!bridge || !bridge.getProviderChoices) return;
  bridge.getProviderChoices((raw) => {
    try {
      const choices = JSON.parse(raw || "[]");
      renderProviderGrid(choices);
    } catch (e) {
      console.error(e);
    }
  });
}

function renderProviderGrid(choices) {
  if (!els.providerGrid) return;
  els.providerGrid.innerHTML = "";
  if (!choices.length) {
    els.providerGrid.innerHTML = '<p class="muted small">No providers detected.</p>';
    return;
  }
  renderProviderSection(
    "Stable APIs",
    "Fast, reliable, recommended for everyday use.",
    choices.filter((c) => c.kind === "stable")
  );
  renderProviderSection(
    "Multi-site scrapers",
    "Vendored Torrent-Api-py providers. More sites, but slower.",
    choices.filter((c) => c.kind === "vendor")
  );
}

function renderProviderSection(title, subtitle, items) {
  if (!items.length) return;
  const enabledCount = items.filter((c) => c.enabled).length;

  const section = document.createElement("section");
  section.className = "provider-section";
  section.innerHTML = `
    <header class="provider-section-head">
      <div>
        <h3 class="provider-section-title">${escapeHtml(title)}</h3>
        <p class="provider-section-sub">${escapeHtml(subtitle)} <span class="provider-count">${enabledCount}/${items.length} on</span></p>
      </div>
      <div class="provider-bulk">
        <button type="button" class="provider-bulk-btn" data-bulk="all">Enable all</button>
        <button type="button" class="provider-bulk-btn" data-bulk="none">Disable all</button>
      </div>
    </header>
    <div class="provider-list"></div>
  `;
  const grid = section.querySelector(".provider-list");
  items.forEach((choice) => grid.appendChild(buildProviderTile(choice, section, items)));
  wireBulkButtons(section, grid, items);
  els.providerGrid.appendChild(section);
}

function statusLabel(status) {
  if (status === "ok") return "Reachable";
  if (status === "slow") return "Slow";
  if (status === "down") return "Unreachable";
  return "Unknown";
}

function buildProviderTile(choice, section, items) {
  const tile = document.createElement("label");
  tile.className = "provider-tile";
  const enabled = !!choice.enabled;
  if (enabled) tile.classList.add("is-on");

  const health = state.providerHealth[choice.key];
  const status = health ? health.status : "unknown";
  const label = health ? statusLabel(status) : "Not checked";
  const latency = health && health.latencyMs ? `${Math.round(health.latencyMs)}ms` : "";

  tile.innerHTML = `
    <input type="checkbox" ${enabled ? "checked" : ""} aria-label="${escapeHtml(choice.label)}" />
    <span class="provider-tick" aria-hidden="true">
      <svg viewBox="0 0 24 24" class="ic"><path d="M5 12l5 5L20 7"/></svg>
    </span>
    <div class="provider-body">
      <div class="provider-name-row">
        <span class="provider-name">${escapeHtml(choice.label)}</span>
        ${choice.defaultOn ? '<span class="provider-default-dot" title="Recommended default"></span>' : ""}
      </div>
      <div class="provider-status">
        <span class="health-dot ${status}" title="${escapeHtml(label)}"></span>
        <span class="provider-status-text">${escapeHtml(label)}${latency ? ` &middot; <span class="health-latency">${latency}</span>` : ""}</span>
      </div>
    </div>
  `;
  const checkbox = tile.querySelector("input");
  checkbox.addEventListener("change", () => {
    tile.classList.toggle("is-on", checkbox.checked);
    bridge.setProviderEnabled(choice.key, checkbox.checked);
    updateProviderCount(section, items);
  });
  return tile;
}

function wireBulkButtons(section, grid, items) {
  section.querySelectorAll(".provider-bulk-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.bulk === "all";
      items.forEach((choice) => {
        if (choice.enabled === target) return;
        choice.enabled = target;
        bridge.setProviderEnabled(choice.key, target);
      });
      grid.querySelectorAll("input[type=checkbox]").forEach((cb) => {
        cb.checked = target;
        cb.closest(".provider-tile").classList.toggle("is-on", target);
      });
      updateProviderCount(section, items);
    });
  });
}

function updateProviderCount(section, items) {
  const enabledCount = section.querySelectorAll(".provider-tile input:checked").length;
  const counter = section.querySelector(".provider-count");
  if (counter) counter.textContent = `${enabledCount}/${items.length} on`;
}

export function connectSourcesSignals() {
  if (bridge.providerHealth) {
    bridge.providerHealth.connect((payloadStr) => {
      try {
        state.providerHealth = JSON.parse(payloadStr || "{}");
        loadProviderChoices();
        if (els.refreshHealthBtn) {
          els.refreshHealthBtn.disabled = false;
          els.refreshHealthBtn.textContent = "Check health";
        }
      } catch (e) {
        console.error(e);
      }
    });
  }
}

export function bindSourcesEvents() {
  if (els.refreshHealthBtn) {
    els.refreshHealthBtn.addEventListener("click", () => {
      els.refreshHealthBtn.disabled = true;
      els.refreshHealthBtn.textContent = "Checking...";
      bridge.refreshProviderHealth();
    });
  }
}
