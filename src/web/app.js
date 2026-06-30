/* Yoink - Frontend
   Vanilla JS, no build step. Talks to Python via QWebChannel.
*/

const App = (() => {
  let bridge = null;

  const state = {
    view: "search",
    sidebarCollapsed: false,
    sidebarOpenMobile: false,
    query: "",
    page: 1,
    pages: 0,
    total: 0,
    searching: false,
    results: [],
    downloads: [],
    saveFolder: "",
    theme: "dark",
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  // ----- DOM refs -----
  const els = {};
  function cacheEls() {
    els.app = $("#app");
    els.sidebar = $("#sidebar");
    els.sidebarScrim = $("#sidebarScrim");
    els.brandBtn = $("#brandBtn");
    els.menuToggles = $$("#menuToggle, [data-menu-toggle]");
    els.navItems = $$(".nav-item");
    els.views = $$(".view");

    els.searchForm = $("#searchForm");
    els.searchInput = $("#searchInput");
    els.searchBtn = $("#searchBtn");
    els.searchClear = $("#searchClear");
    els.regionFilter = $("#regionFilter");
    els.categoryFilter = $("#categoryFilter");
    els.sourceFilter = $("#sourceFilter");
    els.resetFiltersBtn = $("#resetFiltersBtn");
    els.resultsBody = $("#resultsBody");
    els.searchEmpty = $("#searchEmpty");
    els.searchLoader = $("#searchLoader");
    els.searchLoaderText = $("#searchLoaderText");
    els.resultsList = $("#resultsList");
    els.resultsCount = $("#resultsCount");
    els.pagination = $("#pagination");
    els.pageInfo = $("#pageInfo");
    els.prevBtn = $("#prevBtn");
    els.nextBtn = $("#nextBtn");
    els.pageNumbers = $("#pageNumbers");

    els.downloadsSummary = $("#downloadsSummary");
    els.downloadsBadge = $("#downloadsBadge");
    els.downloadsEmpty = $("#downloadsEmpty");
    els.downloadsList = $("#downloadsList");
    els.changeFolderBtn = $("#changeFolderBtn");
    els.addTorrentBtn = $("#addTorrentBtn");

    els.netDown = $("#netDown");
    els.netUp = $("#netUp");
    els.folderText = $("#folderText");
    els.folderPill = $("#folderPill");

    els.toastStack = $("#toastStack");

    els.settingFolderPath = $("#settingFolderPath");
    els.settingChangeFolder = $("#settingChangeFolder");
    els.settingNotifications = $("#settingNotifications");
    els.settingMinimizeTray = $("#settingMinimizeTray");
    els.themeButtons = $$("[data-theme-set]");
    els.replayOnboardingBtn = $("#replayOnboardingBtn");

    els.onboardingBackdrop = $("#onboardingBackdrop");
    els.onboardingDone = $("#onboardingDone");

    els.resultTpl = $("#resultRowTpl");
    els.downloadTpl = $("#downloadRowTpl");
  }

  // ----- Helpers -----
  function formatKB(kb) {
    if (kb == null || isNaN(kb)) return "0 KB/s";
    if (kb < 1024) return `${kb.toFixed(1)} KB/s`;
    return `${(kb / 1024).toFixed(2)} MB/s`;
  }

  function shortPath(p) {
    if (!p) return "";
    if (p.length <= 28) return p;
    return "..." + p.slice(-25);
  }

  function statusClass(status) {
    const s = (status || "").toLowerCase();
    if (s.includes("error")) return "error";
    if (s.includes("paused")) return "paused";
    if (s.includes("seed") || s.includes("finish") || s.includes("complete")) return "seeding";
    if (s.includes("download")) return "downloading";
    if (s.includes("metadata") || s.includes("check")) return "metadata";
    if (s.includes("queue")) return "queued";
    return "unknown";
  }

  function isMobile() {
    return window.matchMedia("(max-width: 760px)").matches;
  }

  // ----- Toasts -----
  function toast(kind, message) {
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

  // ----- Theme -----
  const systemPrefersDark = () =>
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  function resolvedTheme(pref) {
    if (pref === "light") return "light";
    if (pref === "dark") return "dark";
    return systemPrefersDark() ? "dark" : "light";
  }

  function applyTheme(pref) {
    state.theme = pref;
    document.documentElement.setAttribute("data-theme", resolvedTheme(pref));
    els.themeButtons.forEach((b) =>
      b.setAttribute("aria-pressed", b.dataset.themeSet === pref ? "true" : "false")
    );
    localStorage.setItem("yoink.theme", pref);
  }

  function initTheme() {
    const saved = localStorage.getItem("yoink.theme") || "dark";
    applyTheme(saved);
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (state.theme === "auto") applyTheme("auto");
    });
  }

  // ----- Sidebar -----
  function toggleSidebar() {
    if (isMobile()) {
      state.sidebarOpenMobile = !state.sidebarOpenMobile;
      els.app.classList.toggle("sidebar-open", state.sidebarOpenMobile);
    } else {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      els.sidebar.classList.toggle("collapsed", state.sidebarCollapsed);
    }
  }

  function closeMobileSidebar() {
    if (state.sidebarOpenMobile) {
      state.sidebarOpenMobile = false;
      els.app.classList.remove("sidebar-open");
    }
  }

  function switchView(name) {
    state.view = name;
    els.navItems.forEach((b) => {
      const active = b.dataset.view === name;
      b.classList.toggle("active", active);
      b.setAttribute("aria-selected", active ? "true" : "false");
    });
    els.views.forEach((v) => v.classList.toggle("hidden", v.dataset.view !== name));
    closeMobileSidebar();
  }

  // ----- Search rendering -----
  function setSearchingState(isSearching, msg) {
    state.searching = isSearching;
    els.searchBtn.disabled = isSearching;
    els.searchInput.disabled = isSearching;
    els.searchLoader.hidden = !isSearching;
    if (isSearching) {
      els.searchLoaderText.textContent = msg || "Searching...";
      els.resultsList.hidden = true;
      els.searchEmpty.hidden = true;
      els.pagination.hidden = true;
    }
  }

  function resetSearchView() {
    state.query = "";
    state.results = [];
    state.total = 0;
    state.pages = 0;
    state.page = 1;
    els.resultsList.innerHTML = "";
    els.resultsList.hidden = true;
    els.pagination.hidden = true;
    els.resultsCount.textContent = "";
    els.searchEmpty.hidden = false;
    els.searchEmpty.querySelector("h3").textContent = "Find something to yoink";
    els.searchEmpty.querySelector("p").innerHTML =
      'Type a title above and press <kbd>Enter</kbd>. Stable search uses The Pirate Bay and YTS; advanced search uses Torrent-Api-py.';
  }

  function renderResults(results) {
    els.resultsList.innerHTML = "";
    if (!results.length) {
      els.resultsList.hidden = true;
      els.searchEmpty.hidden = false;
      els.searchEmpty.querySelector("h3").textContent = "No results";
      els.searchEmpty.querySelector("p").textContent = "Try a different title, change the region, or switch source to Torrent-Api-py.";
      els.pagination.hidden = true;
      return;
    }
    els.searchEmpty.hidden = true;
    els.resultsList.hidden = false;
    const frag = document.createDocumentFragment();
    results.forEach((r) => {
      const node = els.resultTpl.content.firstElementChild.cloneNode(true);

      const posterImg = node.querySelector("img.poster");
      const posterPlaceholder = node.querySelector(".poster.placeholder");
      if (r.cover) {
        posterImg.src = r.cover;
        posterImg.alt = r.title;
        posterImg.hidden = false;
        posterImg.addEventListener("error", () => {
          posterImg.hidden = true;
          posterPlaceholder.hidden = false;
        }, { once: true });
        posterPlaceholder.hidden = true;
      }

      node.querySelector(".result-title").textContent = r.title;
      node.querySelector(".result-title").title = r.title;

      const source = node.querySelector(".meta.source");
      source.textContent = r.source;
      if ((r.source || "").toUpperCase() === "YTS") source.classList.add("yts");

      node.querySelector(".meta.size").textContent = r.size || "?";

      const dateEl = node.querySelector(".meta.date");
      if (r.date) { dateEl.textContent = r.date; dateEl.hidden = false; }

      const runtimeEl = node.querySelector(".meta.runtime");
      if (r.runtime && Number(r.runtime) > 0) {
        const mins = Number(r.runtime);
        const h = Math.floor(mins / 60);
        const m = mins % 60;
        runtimeEl.textContent = h ? `${h}h ${m}m` : `${m}m`;
        runtimeEl.hidden = false;
      }

      const qualityEl = node.querySelector(".meta.quality");
      if (r.quality) { qualityEl.textContent = r.quality; qualityEl.hidden = false; }

      const ratingEl = node.querySelector(".meta.rating");
      if (r.rating && Number(r.rating) > 0) {
        const v = Number(r.rating);
        ratingEl.textContent = `\u2605 ${v.toFixed(1)}`;
        ratingEl.classList.add(v >= 7 ? "high" : v >= 5 ? "mid" : "low");
        ratingEl.hidden = false;
      }

      const imdbEl = node.querySelector(".meta.imdb-link");
      if (r.imdbCode) {
        imdbEl.href = `https://www.imdb.com/title/${r.imdbCode}/`;
        imdbEl.hidden = false;
        imdbEl.addEventListener("click", (e) => {
          e.preventDefault();
          bridge.openExternal(imdbEl.href);
        });
      }

      const genresEl = node.querySelector(".result-genres");
      if (Array.isArray(r.genres) && r.genres.length) {
        genresEl.innerHTML = "";
        r.genres.slice(0, 4).forEach((g) => {
          const span = document.createElement("span");
          span.className = "meta genre";
          span.textContent = g;
          genresEl.appendChild(span);
        });
        genresEl.hidden = false;
      }

      const summaryEl = node.querySelector(".result-summary");
      if (r.summary) {
        summaryEl.textContent = r.summary;
        summaryEl.title = r.summary;
        summaryEl.hidden = false;
      }

      node.querySelector(".stat-line.seeders .num").textContent = r.seeds ?? 0;
      node.querySelector(".stat-line.peers .num").textContent = r.peers ?? 0;

      const actionBtn = node.querySelector(".result-action");
      actionBtn.setAttribute("aria-label", `Download ${r.title}`);
      actionBtn.addEventListener("click", () => addFromResult(r, actionBtn));

      frag.appendChild(node);
    });
    els.resultsList.appendChild(frag);
  }

  function renderPagination() {
    if (state.pages <= 1) {
      els.pagination.hidden = true;
      return;
    }
    els.pagination.hidden = false;
    els.pageInfo.textContent = `${state.total} results`;
    els.prevBtn.disabled = state.page <= 1;
    els.nextBtn.disabled = state.page >= state.pages;
    els.pageNumbers.innerHTML = "";

    const pages = pageWindow(state.page, state.pages);
    pages.forEach((p) => {
      const btn = document.createElement("button");
      if (p === "...") {
        btn.className = "page-num ellipsis";
        btn.textContent = "...";
        btn.disabled = true;
        btn.setAttribute("aria-hidden", "true");
      } else {
        btn.className = "page-num" + (p === state.page ? " active" : "");
        btn.textContent = String(p);
        btn.setAttribute("aria-label", `Page ${p}`);
        if (p === state.page) btn.setAttribute("aria-current", "page");
        btn.addEventListener("click", () => doSearch(state.query, p));
      }
      els.pageNumbers.appendChild(btn);
    });
  }

  function pageWindow(current, total) {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages = [1];
    const start = Math.max(2, current - 2);
    const end = Math.min(total - 1, current + 2);
    if (start > 2) pages.push("...");
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < total - 1) pages.push("...");
    pages.push(total);
    return pages;
  }

  // ----- Search actions -----
  function currentSearchOptions() {
    const sourceValue = els.sourceFilter.value || "stable";
    const sourceMap = {
      "torrent-api-py-all": null,
      "movies-core": ["1337x", "tgx", "yts", "bitsearch"],
      "1337x": ["1337x"],
      "tgx": ["tgx"],
      "yts": ["yts"],
    };
    if (sourceValue === "stable" || sourceValue === "all") {
      return {
        providerMode: "stable",
        region: els.regionFilter.value,
        category: els.categoryFilter.value,
      };
    }
    return {
      providerMode: "multi",
      region: els.regionFilter.value,
      category: els.categoryFilter.value,
      sites: sourceMap[sourceValue],
      limitPerSite: sourceValue === "torrent-api-py-all" ? 4 : 8,
    };
  }

  function saveFilters() {
    localStorage.setItem("yoink.searchFilters", JSON.stringify({
      region: els.regionFilter.value,
      category: els.categoryFilter.value,
      source: els.sourceFilter.value,
    }));
  }

  function loadFilters() {
    try {
      const saved = JSON.parse(
        localStorage.getItem("yoink.searchFilters") ||
        localStorage.getItem("torrentApp.searchFilters") ||
        "{}"
      );
      if (saved.region) els.regionFilter.value = saved.region;
      if (saved.category) els.categoryFilter.value = saved.category;
      if (saved.source) {
        els.sourceFilter.value = saved.source === "all" ? "stable" : saved.source;
      }
    } catch (_) {}
  }

  function doSearch(query, page = 1) {
    const q = (query || "").trim();
    if (!q) {
      toast("error", "Enter a search query");
      els.searchInput.focus();
      return;
    }
    state.query = q;
    state.page = page;
    saveFilters();
    setSearchingState(true, `Yoinking results for \u201c${q}\u201d...`);
    bridge.search(q, page, JSON.stringify(currentSearchOptions()));
  }

  function addFromResult(result, btn) {
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Adding...";
    }
    bridge.addTorrent(result.magnet, (hash) => {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<svg viewBox="0 0 24 24" class="ic" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg> Yoinked`;
      }
      if (hash) {
        toast("success", "Added to downloads");
        setTimeout(() => switchView("downloads"), 500);
      }
    });
  }

  // ----- Downloads rendering -----
  function renderDownloads(items) {
    state.downloads = items;
    const total = items.length;
    const active = items.filter((t) => /download|metadata/i.test(t.status || "")).length;
    const paused = items.filter((t) => /paused/i.test(t.status || "")).length;
    const errored = items.filter((t) => /error/i.test(t.status || "")).length;

    if (total === 0) {
      els.downloadsSummary.textContent = "No downloads yet.";
      els.downloadsBadge.hidden = true;
    } else {
      const parts = [`${total} total`, `${active} active`];
      if (paused) parts.push(`${paused} paused`);
      if (errored) parts.push(`${errored} need attention`);
      els.downloadsSummary.textContent = parts.join("  \u00b7  ");
      if (active > 0) {
        els.downloadsBadge.textContent = String(active);
        els.downloadsBadge.hidden = false;
      } else {
        els.downloadsBadge.hidden = true;
      }
    }

    els.downloadsEmpty.hidden = total > 0;
    els.downloadsList.hidden = total === 0;
    if (total === 0) {
      els.downloadsList.innerHTML = "";
      return;
    }

    const existing = new Map();
    els.downloadsList.querySelectorAll(".download-row").forEach((n) => existing.set(n.dataset.hash, n));

    const frag = document.createDocumentFragment();
    items.forEach((t) => {
      let node = existing.get(t.hash);
      if (!node) {
        node = els.downloadTpl.content.firstElementChild.cloneNode(true);
        node.dataset.hash = t.hash;
        wireDownloadRow(node, t.hash);
      } else {
        existing.delete(t.hash);
      }
      updateDownloadRow(node, t);
      frag.appendChild(node);
    });
    existing.forEach((node) => node.remove());
    els.downloadsList.innerHTML = "";
    els.downloadsList.appendChild(frag);
  }

  function wireDownloadRow(node, hash) {
    node.querySelector(".dl-pause").addEventListener("click", () => bridge.pauseTorrent(hash, () => {}));
    node.querySelector(".dl-resume").addEventListener("click", () => bridge.resumeTorrent(hash, () => {}));
    node.querySelector(".dl-open").addEventListener("click", () => {
      const t = state.downloads.find((d) => d.hash === hash);
      bridge.openSaveFolder(t ? t.savePath : "");
    });
    node.querySelector(".dl-remove").addEventListener("click", () => bridge.removeTorrent(hash, false, () => {}));
  }

  function updateDownloadRow(node, t) {
    node.querySelector(".dl-name").textContent = t.name || "Loading metadata...";
    node.querySelector(".dl-name").title = t.name || "";
    const chip = node.querySelector(".status-chip");
    chip.textContent = t.status || "Unknown";
    chip.className = `status-chip ${statusClass(t.status)}`;

    const pct = Math.max(0, Math.min(100, t.progress || 0));
    node.querySelector(".dl-bar").style.width = `${pct}%`;
    node.querySelector(".dl-progress-text").textContent = `${pct.toFixed(1)}%`;
    const progressEl = node.querySelector(".dl-progress");
    progressEl.setAttribute("aria-valuenow", String(Math.round(pct)));
    progressEl.setAttribute("aria-label", `${t.name || "torrent"} ${pct.toFixed(1)}% complete`);
    node.classList.toggle("completed", pct >= 100);

    node.querySelector(".dl-size").textContent = t.size || "?";
    node.querySelector(".dl-down").textContent = t.downloadSpeed || "0 KB/s";
    node.querySelector(".dl-eta").textContent = t.eta || "-";
    node.querySelector(".dl-seeds").textContent = t.seeds ?? 0;
    node.querySelector(".dl-peers").textContent = t.peers ?? 0;

    const isPaused = /paused/i.test(t.status || "");
    const isDownloading = /download|metadata/i.test(t.status || "");
    node.querySelector(".dl-pause").hidden = !isDownloading;
    node.querySelector(".dl-resume").hidden = !isPaused;
  }

  // ----- Onboarding -----
  function showOnboarding() {
    els.onboardingBackdrop.hidden = false;
    setTimeout(() => els.onboardingDone.focus(), 50);
  }
  function hideOnboarding() {
    els.onboardingBackdrop.hidden = true;
    localStorage.setItem("yoink.onboardingSeen", "1");
    els.searchInput.focus();
  }
  function maybeShowOnboarding() {
    if (!localStorage.getItem("yoink.onboardingSeen")) {
      showOnboarding();
    }
  }

  // ----- Bridge event wiring -----
  function onBridgeReady(channel) {
    bridge = channel.objects.bridge;

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

    bridge.downloadsUpdated.connect((payloadStr) => {
      try { renderDownloads(JSON.parse(payloadStr)); } catch (e) { console.error(e); }
    });

    bridge.networkSpeed.connect((down, up) => {
      els.netDown.textContent = formatKB(down);
      els.netUp.textContent = formatKB(up);
    });

    bridge.toast.connect((kind, msg) => toast(kind, msg));

    bridge.saveFolderChanged.connect((folder) => {
      state.saveFolder = folder;
      els.folderText.textContent = shortPath(folder);
      els.folderPill.title = folder;
      els.settingFolderPath.textContent = folder;
      els.settingFolderPath.title = folder;
    });

    bridge.settingsChanged.connect((payload) => {
      try { applySettings(JSON.parse(payload)); } catch (e) {}
    });

    // Initial pulls
    bridge.getSaveFolder((folder) => {
      state.saveFolder = folder;
      els.folderText.textContent = shortPath(folder);
      els.folderPill.title = folder;
      els.settingFolderPath.textContent = folder;
      els.settingFolderPath.title = folder;
    });
    bridge.getDownloads((payload) => {
      try { renderDownloads(JSON.parse(payload || "[]")); } catch (e) {}
    });
    bridge.getSettings((payload) => {
      try { applySettings(JSON.parse(payload)); } catch (e) {}
    });
  }

  function applySettings(s) {
    if (!s) return;
    if (s.saveFolder) {
      els.settingFolderPath.textContent = s.saveFolder;
      els.settingFolderPath.title = s.saveFolder;
    }
    els.settingNotifications.checked = !!s.notifications;
    els.settingMinimizeTray.checked = !!s.minimizeToTray;
  }

  // ----- Keyboard nav for sidebar (arrow keys between tabs) -----
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

  // ----- Wiring -----
  function bindEvents() {
    els.brandBtn.addEventListener("click", toggleSidebar);
    els.menuToggles.forEach((b) => b.addEventListener("click", toggleSidebar));
    els.sidebarScrim.addEventListener("click", closeMobileSidebar);

    els.navItems.forEach((b) => {
      b.addEventListener("click", () => switchView(b.dataset.view));
      b.addEventListener("keydown", handleNavKey);
    });

    els.searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      doSearch(els.searchInput.value);
    });
    els.searchInput.addEventListener("input", () => {
      els.searchClear.hidden = !els.searchInput.value;
    });
    els.searchClear.addEventListener("click", () => {
      els.searchInput.value = "";
      els.searchClear.hidden = true;
      els.searchInput.focus();
      setSearchingState(false);
      resetSearchView();
    });
    [els.regionFilter, els.categoryFilter, els.sourceFilter].forEach((control) => {
      control.addEventListener("change", () => {
        saveFilters();
        if (state.query && !state.searching) doSearch(state.query, 1);
      });
    });
    els.resetFiltersBtn.addEventListener("click", () => {
      els.regionFilter.value = "any";
      els.categoryFilter.value = "movies";
      els.sourceFilter.value = "stable";
      saveFilters();
      if (state.query && !state.searching) doSearch(state.query, 1);
    });
    els.prevBtn.addEventListener("click", () => doSearch(state.query, Math.max(1, state.page - 1)));
    els.nextBtn.addEventListener("click", () => doSearch(state.query, Math.min(state.pages, state.page + 1)));

    els.changeFolderBtn.addEventListener("click", () => bridge.pickSaveFolder(() => {}));
    els.addTorrentBtn.addEventListener("click", () => bridge.pickAndAddTorrentFile(() => {}));
    els.folderPill.addEventListener("click", () => bridge.openSaveFolder(""));

    els.settingChangeFolder.addEventListener("click", () => bridge.pickSaveFolder(() => {}));
    els.settingNotifications.addEventListener("change", (e) =>
      bridge.setBoolSetting("notifications_enabled", e.target.checked)
    );
    els.settingMinimizeTray.addEventListener("change", (e) =>
      bridge.setBoolSetting("minimize_to_tray", e.target.checked)
    );

    els.themeButtons.forEach((b) =>
      b.addEventListener("click", () => applyTheme(b.dataset.themeSet))
    );
    els.replayOnboardingBtn.addEventListener("click", showOnboarding);

    els.onboardingDone.addEventListener("click", hideOnboarding);
    els.onboardingBackdrop.addEventListener("click", (e) => {
      if (e.target === els.onboardingBackdrop) hideOnboarding();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !els.onboardingBackdrop.hidden) {
        hideOnboarding();
      } else if (e.key === "Escape" && state.sidebarOpenMobile) {
        closeMobileSidebar();
      } else if (e.key === "/" && document.activeElement !== els.searchInput) {
        e.preventDefault();
        switchView("search");
        els.searchInput.focus();
        els.searchInput.select();
      }
    });
  }

  function init() {
    cacheEls();
    initTheme();
    loadFilters();
    bindEvents();
    maybeShowOnboarding();
    new QWebChannel(qt.webChannelTransport, onBridgeReady);
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
