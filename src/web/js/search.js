import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { detectTorrentInput, escapeHtml } from "./util.js";
import { toast } from "./toasts.js";
import { switchView } from "./sidebar.js";
import { renderPagination, renderResults, resetSearchView, setSearchingState } from "./results.js";
import { parseAddResult, showDuplicateToast } from "./add.js";

function currentSearchOptions() {
  const sourceValue = els.sourceFilter.value || "stable";
  const sourceMap = {
    "multi-default": undefined,           // bridge picks the user's enabled vendor list
    "torrent-api-py-all": null,           // search every vendored site
    "1337x": ["1337x"],
  };
  const shared = {
    region: els.regionFilter.value,
    category: els.categoryFilter.value,
    quality: els.qualityFilter.value,
    sortBy: els.sortFilter.value,
  };
  if (sourceValue === "stable") {
    return { providerMode: "stable", ...shared };
  }
  const options = {
    providerMode: "multi",
    includeStable: sourceValue === "multi-default",
    ...shared,
    limitPerSite: sourceValue === "torrent-api-py-all" ? 4 : 8,
  };
  const sites = sourceMap[sourceValue];
  if (Array.isArray(sites)) options.sites = sites;
  return options;
}

export function saveFilters() {
  localStorage.setItem("yoink.searchFilters", JSON.stringify({
    region: els.regionFilter.value,
    category: els.categoryFilter.value,
    quality: els.qualityFilter.value,
    sortBy: els.sortFilter.value,
    source: els.sourceFilter.value,
  }));
}

export function loadFilters() {
  try {
    const saved = JSON.parse(
      localStorage.getItem("yoink.searchFilters") ||
      localStorage.getItem("torrentApp.searchFilters") ||
      "{}"
    );
    if (saved.region) els.regionFilter.value = saved.region;
    if (saved.category) els.categoryFilter.value = saved.category;
    if (saved.quality) els.qualityFilter.value = saved.quality;
    if (saved.sortBy) els.sortFilter.value = saved.sortBy;
    if (saved.source) {
      const normalized = saved.source === "all" ? "stable" : saved.source;
      els.sourceFilter.value = normalized;
    }
  } catch (_) {}
}

export function doSearch(query, page = 1) {
  const q = (query || "").trim();
  if (!q) {
    toast("error", "Enter a search query");
    els.searchInput.focus();
    return;
  }
  state.query = q;
  state.page = page;
  saveFilters();
  hideHistoryDropdown();
  setSearchingState(true, `Yoinking results for \u201c${q}\u201d...`);
  bridge.search(q, page, JSON.stringify(currentSearchOptions()));
  if (bridge.rememberSearch) {
    bridge.rememberSearch(q);
    loadSearchHistory();
  }
}

export function loadSearchHistory() {
  if (!bridge || !bridge.getSearchHistory) return;
  bridge.getSearchHistory((raw) => {
    try {
      state.searchHistory = JSON.parse(raw || "[]");
    } catch (_) {
      state.searchHistory = [];
    }
  });
}

function renderHistoryDropdown(query) {
  const items = (state.searchHistory || [])
    .filter((entry) => entry && entry.toLowerCase().includes((query || "").toLowerCase()))
    .slice(0, 8);
  els.searchHistoryList.innerHTML = "";
  if (!items.length) {
    hideHistoryDropdown();
    return;
  }
  items.forEach((entry) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "history-item";
    row.setAttribute("role", "option");
    row.innerHTML = `<svg viewBox="0 0 24 24" class="ic" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg><span>${escapeHtml(entry)}</span>`;
    row.addEventListener("mousedown", (e) => {
      e.preventDefault();
      els.searchInput.value = entry;
      hideHistoryDropdown();
      doSearch(entry, 1);
    });
    els.searchHistoryList.appendChild(row);
  });
  els.searchHistoryList.hidden = false;
  els.searchInput.setAttribute("aria-expanded", "true");
}

function hideHistoryDropdown() {
  els.searchHistoryList.hidden = true;
  els.searchInput.setAttribute("aria-expanded", "false");
}

let smartHint = null;
function showSmartHint(detection) {
  hideSmartHint();
  smartHint = document.createElement("div");
  smartHint.className = "search-mode-hint";
  smartHint.innerHTML = `
    <svg viewBox="0 0 24 24" class="ic" aria-hidden="true"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>
    <span>Found a ${detection.kind === "magnet" ? "<strong>magnet link</strong>" : "<strong>.torrent URL</strong>"}. Press <kbd>Enter</kbd> to add it to downloads.</span>
  `;
  const row = els.searchInput.closest(".search-row, .search-shell, form") || els.searchForm;
  row.style.position = row.style.position || "relative";
  row.appendChild(smartHint);
}
function hideSmartHint() {
  if (smartHint) { smartHint.remove(); smartHint = null; }
}

function submitSearchOrAdd() {
  const raw = els.searchInput.value;
  const detection = detectTorrentInput(raw);
  if (detection) {
    hideSmartHint();
    addByDetection(detection);
    els.searchInput.value = "";
    els.searchClear.hidden = true;
    return;
  }
  doSearch(raw);
}

export function addByDetection(detection) {
  if (detection.kind === "magnet") {
    bridge.addTorrent(detection.value, (raw) => {
      const { hash, wasExisting } = parseAddResult(raw);
      if (!hash) return;
      if (wasExisting) showDuplicateToast(hash);
      else { toast("success", "Added to downloads"); setTimeout(() => switchView("downloads"), 400); }
    });
  } else {
    toast("info", "Adding from a URL isn't supported yet. Paste the magnet link instead.");
  }
}

export function connectSearchSignals() {
  bridge.searchCompleted.connect((payloadStr) => {
    setSearchingState(false);
    try {
      const payload = JSON.parse(payloadStr);
      if (state.query && payload.query !== state.query) return;
      state.results = payload.results;
      state.total = payload.total;
      state.pages = payload.pages;
      state.page = payload.page;
      renderResults(payload.results);
      renderPagination();
      els.resultsCount.textContent = payload.total ? `${payload.total} results` : "";
    } catch (e) {
      console.error(e);
    }
  });

  bridge.searchError.connect((msg) => {
    setSearchingState(false);
    resetSearchView();
    toast("error", msg || "Search failed");
  });
}

export function bindSearchEvents() {
  els.searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitSearchOrAdd();
  });
  const searchWrap = els.searchInput.closest(".input-wrap");
  const refreshInputAffordance = () => {
    const hasValue = !!els.searchInput.value;
    els.searchClear.hidden = !hasValue;
    if (searchWrap) searchWrap.classList.toggle("has-value", hasValue);
  };
  refreshInputAffordance();
  els.searchInput.addEventListener("input", () => {
    refreshInputAffordance();
    const detection = detectTorrentInput(els.searchInput.value);
    if (detection) {
      hideHistoryDropdown();
      showSmartHint(detection);
    } else {
      hideSmartHint();
      renderHistoryDropdown(els.searchInput.value);
    }
  });
  els.searchInput.addEventListener("focus", () => {
    renderHistoryDropdown(els.searchInput.value);
  });
  els.searchInput.addEventListener("blur", () => {
    setTimeout(hideHistoryDropdown, 120);
  });
  els.searchClear.addEventListener("click", () => {
    els.searchInput.value = "";
    refreshInputAffordance();
    els.searchInput.focus();
    setSearchingState(false);
    resetSearchView();
    hideHistoryDropdown();
    hideSmartHint();
  });

  if (els.exampleChips) {
    els.exampleChips.querySelectorAll("[data-example]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const q = btn.dataset.example;
        els.searchInput.value = q;
        refreshInputAffordance();
        doSearch(q, 1);
      });
    });
  }

  [els.regionFilter, els.categoryFilter, els.qualityFilter, els.sortFilter, els.sourceFilter].forEach((control) => {
    control.addEventListener("change", () => {
      saveFilters();
      if (state.query && !state.searching) doSearch(state.query, 1);
    });
  });
  els.resetFiltersBtn.addEventListener("click", () => {
    els.regionFilter.value = "any";
    els.categoryFilter.value = "any";
    els.qualityFilter.value = "any";
    els.sortFilter.value = "relevance";
    els.sourceFilter.value = "multi-default";
    saveFilters();
    if (state.query && !state.searching) doSearch(state.query, 1);
  });
  els.prevBtn.addEventListener("click", () => doSearch(state.query, Math.max(1, state.page - 1)));
  els.nextBtn.addEventListener("click", () => doSearch(state.query, Math.min(state.pages, state.page + 1)));

  if (els.clearHistoryBtn) {
    els.clearHistoryBtn.addEventListener("click", () => {
      if (!bridge || !bridge.clearSearchHistory) return;
      bridge.clearSearchHistory();
      state.searchHistory = [];
      hideHistoryDropdown();
      toast("success", "Search history cleared");
    });
  }
}
