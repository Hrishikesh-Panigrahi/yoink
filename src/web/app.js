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
    searchHistory: [],
    downloadsTab: "active",
    filesModal: { hash: null, files: [] },
    metadataByKey: new Map(),
    rowsByKey: new Map(),
    providerHealth: {},
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
    els.searchHistoryList = $("#searchHistoryList");
    els.regionFilter = $("#regionFilter");
    els.categoryFilter = $("#categoryFilter");
    els.qualityFilter = $("#qualityFilter");
    els.sortFilter = $("#sortFilter");
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
    els.pauseAllBtn = $("#pauseAllBtn");
    els.resumeAllBtn = $("#resumeAllBtn");
    els.dlTabs = $$("[data-dl-tab]");
    els.dlCountActive = $("#dlCountActive");
    els.dlCountCompleted = $("#dlCountCompleted");
    els.dlCountAll = $("#dlCountAll");
    els.filesBackdrop = $("#filesBackdrop");
    els.filesTitle = $("#filesTitle");
    els.filesSubtitle = $("#filesSubtitle");
    els.filesTable = $("#filesTable");
    els.filesSelectAll = $("#filesSelectAll");
    els.filesSelectNone = $("#filesSelectNone");
    els.filesSelectedCount = $("#filesSelectedCount");
    els.filesApply = $("#filesApply");
    els.filesCancel = $("#filesCancel");
    els.detailsBackdrop = $("#detailsBackdrop");
    els.detailsBackdropImg = $("#detailsBackdropImg");
    els.detailsClose = $("#detailsClose");
    els.detailsPoster = $("#detailsPoster");
    els.detailsTitle = $("#detailsTitle");
    els.detailsYear = $("#detailsYear");
    els.detailsRuntime = $("#detailsRuntime");
    els.detailsRating = $("#detailsRating");
    els.detailsGenres = $("#detailsGenres");
    els.detailsPlot = $("#detailsPlot");
    els.detailsTrailer = $("#detailsTrailer");
    els.detailsImdb = $("#detailsImdb");
    els.detailsTorrents = $("#detailsTorrents");
    els.settingTmdbKey = $("#settingTmdbKey");
    els.settingTmdbSave = $("#settingTmdbSave");
    els.tmdbHelpLink = $("#tmdbHelpLink");
    els.aboutVersion = $("#aboutVersion");
    els.sidebarVersion = $("#sidebarVersion");
    els.aboutHomepage = $("#aboutHomepage");
    els.aboutPlatform = $("#aboutPlatform");
    els.aboutUpdateStatus = $("#aboutUpdateStatus");
    els.checkUpdatesBtn = $("#checkUpdatesBtn");
    els.settingsNavItems = $$(".settings-nav-item");
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
    els.settingAutostart = $("#settingAutostart");
    els.settingDownLimit = $("#settingDownLimit");
    els.settingUpLimit = $("#settingUpLimit");
    els.settingMaxActiveDl = $("#settingMaxActiveDl");
    els.settingMaxActiveSeeds = $("#settingMaxActiveSeeds");
    els.settingSeedRatio = $("#settingSeedRatio");
    els.themeButtons = $$("[data-theme-set]");
    els.replayOnboardingBtn = $("#replayOnboardingBtn");
    els.clearHistoryBtn = $("#clearHistoryBtn");
    els.providerGrid = $("#providerGrid");
    els.refreshHealthBtn = $("#refreshHealthBtn");

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
  const THEMES = new Set([
    "swarm", "paper", "pirate", "cobalt", "sunset", "terminal", "slate", "mint",
  ]);
  const LEGACY_THEME_MAP = { dark: "swarm", light: "paper", auto: "swarm" };

  function normalizeTheme(name) {
    if (!name) return "swarm";
    if (THEMES.has(name)) return name;
    if (LEGACY_THEME_MAP[name]) return LEGACY_THEME_MAP[name];
    return "swarm";
  }

  function applyTheme(name) {
    const theme = normalizeTheme(name);
    state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    els.themeButtons.forEach((b) =>
      b.setAttribute("aria-pressed", b.dataset.themeSet === theme ? "true" : "false")
    );
    localStorage.setItem("yoink.theme", theme);
  }

  function initTheme() {
    const saved = localStorage.getItem("yoink.theme");
    applyTheme(saved);
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
    state.rowsByKey = new Map();
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

      const safetyEl = node.querySelector(".meta.safety-badge");
      if (safetyEl && r.safety) {
        if (r.safety.level === "risky") {
          safetyEl.textContent = "Risky";
          safetyEl.classList.add("risky");
          safetyEl.title = (r.safety.reasons || []).join("; ");
          safetyEl.hidden = false;
        } else if (r.safety.level === "caution") {
          safetyEl.textContent = "Check";
          safetyEl.classList.add("caution");
          safetyEl.title = (r.safety.reasons || []).join("; ");
          safetyEl.hidden = false;
        } else if (r.safety.level === "safe" && (r.safety.reasons || []).some((x) => /trusted/i.test(x))) {
          safetyEl.textContent = "Trusted";
          safetyEl.classList.add("safe");
          safetyEl.hidden = false;
        }
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

      const infoBtn = node.querySelector(".result-info");
      if (infoBtn) {
        infoBtn.addEventListener("click", () => openDetailsModal(r));
      }

      const key = r.magnet || r.infoHash || r.title;
      state.rowsByKey.set(key, { node, result: r });
      const cached = state.metadataByKey.get(key);
      if (cached) applyMetadataToRow(node, r, cached);

      frag.appendChild(node);
    });
    els.resultsList.appendChild(frag);
  }

  // ----- TMDB metadata enrichment -----
  function applyMetadataToRow(node, r, meta) {
    if (!meta) return;
    const posterImg = node.querySelector("img.poster");
    const posterPlaceholder = node.querySelector(".poster.placeholder");
    if (meta.poster && (!r.cover || posterImg.hidden)) {
      posterImg.src = meta.poster;
      posterImg.alt = r.title;
      posterImg.hidden = false;
      posterPlaceholder.hidden = true;
    }

    const runtimeEl = node.querySelector(".meta.runtime");
    if (runtimeEl.hidden && meta.runtime) {
      const h = Math.floor(meta.runtime / 60);
      const m = meta.runtime % 60;
      runtimeEl.textContent = h ? `${h}h ${m}m` : `${m}m`;
      runtimeEl.hidden = false;
    }

    const ratingEl = node.querySelector(".meta.rating");
    if (ratingEl.hidden && meta.rating > 0) {
      ratingEl.textContent = `\u2605 ${meta.rating.toFixed(1)}`;
      ratingEl.classList.add(meta.rating >= 7 ? "high" : meta.rating >= 5 ? "mid" : "low");
      ratingEl.hidden = false;
    }

    const imdbEl = node.querySelector(".meta.imdb-link");
    if (imdbEl.hidden && meta.imdbUrl) {
      imdbEl.href = meta.imdbUrl;
      imdbEl.hidden = false;
      imdbEl.addEventListener("click", (e) => {
        e.preventDefault();
        bridge.openExternal(meta.imdbUrl);
      });
    }

    const genresEl = node.querySelector(".result-genres");
    if (genresEl.hidden && Array.isArray(meta.genres) && meta.genres.length) {
      genresEl.innerHTML = "";
      meta.genres.slice(0, 4).forEach((g) => {
        const span = document.createElement("span");
        span.className = "meta genre";
        span.textContent = g;
        genresEl.appendChild(span);
      });
      genresEl.hidden = false;
    }

    const summaryEl = node.querySelector(".result-summary");
    if (summaryEl.hidden && meta.plot) {
      summaryEl.textContent = meta.plot;
      summaryEl.title = meta.plot;
      summaryEl.hidden = false;
    }
  }

  function handleMetadataEnriched(query, updates) {
    if (state.query !== query) return;
    updates.forEach(({ key, metadata }) => {
      state.metadataByKey.set(key, metadata);
      const entry = state.rowsByKey.get(key);
      if (entry) applyMetadataToRow(entry.node, entry.result, metadata);
    });
  }

  // ----- Movie details modal -----
  function openDetailsModal(result) {
    const key = result.magnet || result.infoHash || result.title;
    const meta = state.metadataByKey.get(key);
    els.detailsTitle.textContent = (meta && meta.title) || result.title || "";
    els.detailsYear.textContent = (meta && meta.year) ? meta.year : (result.year || "");
    els.detailsRuntime.textContent = (meta && meta.runtime)
      ? `${Math.floor(meta.runtime / 60)}h ${meta.runtime % 60}m`
      : "";
    if (meta && meta.rating > 0) {
      els.detailsRating.textContent = `\u2605 ${meta.rating.toFixed(1)}`;
      els.detailsRating.hidden = false;
    } else {
      els.detailsRating.textContent = "";
    }
    els.detailsGenres.innerHTML = "";
    ((meta && meta.genres) || []).forEach((g) => {
      const span = document.createElement("span");
      span.className = "details-chip";
      span.textContent = g;
      els.detailsGenres.appendChild(span);
    });
    els.detailsPlot.textContent = (meta && meta.plot) || result.summary || "No plot available yet.";
    els.detailsPoster.src = (meta && meta.poster) || result.cover || "";
    els.detailsPoster.alt = result.title;
    if (meta && meta.backdrop) {
      els.detailsBackdropImg.style.backgroundImage = `url("${meta.backdrop}")`;
      els.detailsBackdropImg.hidden = false;
    } else {
      els.detailsBackdropImg.hidden = true;
      els.detailsBackdropImg.style.backgroundImage = "";
    }
    if (meta && meta.trailerUrl) {
      els.detailsTrailer.href = meta.trailerUrl;
      els.detailsTrailer.hidden = false;
      els.detailsTrailer.onclick = (e) => {
        e.preventDefault();
        bridge.openExternal(meta.trailerUrl);
      };
    } else {
      els.detailsTrailer.hidden = true;
    }
    if (meta && meta.imdbUrl) {
      els.detailsImdb.href = meta.imdbUrl;
      els.detailsImdb.hidden = false;
      els.detailsImdb.onclick = (e) => {
        e.preventDefault();
        bridge.openExternal(meta.imdbUrl);
      };
    } else {
      els.detailsImdb.hidden = true;
    }

    renderDetailsTorrents(result, meta);
    els.detailsBackdrop.hidden = false;
    setTimeout(() => els.detailsClose && els.detailsClose.focus(), 50);
  }

  function renderDetailsTorrents(currentResult, meta) {
    els.detailsTorrents.innerHTML = "";
    const tmdbId = meta && meta.tmdbId;
    let group = [];
    if (tmdbId) {
      group = state.results.filter((r) => {
        const k = r.magnet || r.infoHash || r.title;
        const m = state.metadataByKey.get(k);
        return m && m.tmdbId === tmdbId;
      });
    }
    if (!group.length) group = [currentResult];

    group
      .slice()
      .sort((a, b) => (b.seeds || 0) - (a.seeds || 0))
      .forEach((r) => {
        const row = document.createElement("div");
        row.className = "details-torrent";
        row.setAttribute("role", "listitem");
        row.innerHTML = `
          <div class="dt-meta">
            <span class="dt-quality">${escapeHtml(r.quality || "?")}</span>
            <span class="dt-source">${escapeHtml(r.source || "")}</span>
            <span class="dt-size">${escapeHtml(r.size || "?")}</span>
            <span class="dt-seeds">${r.seeds ?? 0} seeders</span>
          </div>
          <button type="button" class="btn btn-primary dt-action">Download</button>
        `;
        row.querySelector(".dt-action").addEventListener("click", () => {
          addFromResult(r, row.querySelector(".dt-action"));
        });
        els.detailsTorrents.appendChild(row);
      });
  }

  function closeDetailsModal() {
    els.detailsBackdrop.hidden = true;
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
      "multi-default": undefined,           // bridge picks the user's enabled vendor list
      "torrent-api-py-all": null,           // search every vendored site
      "movies-core": ["1337x", "tgx", "yts", "bitsearch"],
      "1337x": ["1337x"],
      "tgx": ["tgx"],
      "yts": ["yts"],
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
      ...shared,
      limitPerSite: sourceValue === "torrent-api-py-all" ? 4 : 8,
    };
    const sites = sourceMap[sourceValue];
    if (Array.isArray(sites)) options.sites = sites;
    return options;
  }

  function saveFilters() {
    localStorage.setItem("yoink.searchFilters", JSON.stringify({
      region: els.regionFilter.value,
      category: els.categoryFilter.value,
      quality: els.qualityFilter.value,
      sortBy: els.sortFilter.value,
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
      if (saved.quality) els.qualityFilter.value = saved.quality;
      if (saved.sortBy) els.sortFilter.value = saved.sortBy;
      if (saved.source) {
        const normalized = saved.source === "all" ? "stable" : saved.source;
        els.sourceFilter.value = normalized;
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
    hideHistoryDropdown();
    setSearchingState(true, `Yoinking results for \u201c${q}\u201d...`);
    bridge.search(q, page, JSON.stringify(currentSearchOptions()));
    if (bridge.rememberSearch) {
      bridge.rememberSearch(q);
      loadSearchHistory();
    }
  }

  // ----- Search history dropdown -----
  function loadSearchHistory() {
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

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ----- Provider grid (Settings -> Sources) -----
  function loadProviderChoices() {
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
    const stable = choices.filter((c) => c.kind === "stable");
    const vendor = choices.filter((c) => c.kind === "vendor");

    const renderSection = (title, subtitle, items) => {
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

      items.forEach((choice) => {
        const tile = document.createElement("label");
        tile.className = "provider-tile";
        const enabled = !!choice.enabled;
        if (enabled) tile.classList.add("is-on");

        const health = state.providerHealth[choice.key];
        const status = health ? health.status : "unknown";
        const statusLabel = health
          ? (status === "ok" ? "Reachable" : status === "slow" ? "Slow" : status === "down" ? "Unreachable" : "Unknown")
          : "Not checked";
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
              <span class="health-dot ${status}" title="${escapeHtml(statusLabel)}"></span>
              <span class="provider-status-text">${escapeHtml(statusLabel)}${latency ? ` &middot; <span class="health-latency">${latency}</span>` : ""}</span>
            </div>
          </div>
        `;
        const checkbox = tile.querySelector("input");
        checkbox.addEventListener("change", () => {
          tile.classList.toggle("is-on", checkbox.checked);
          bridge.setProviderEnabled(choice.key, checkbox.checked);
          updateProviderCount(section, items);
        });
        grid.appendChild(tile);
      });

      section.querySelectorAll(".provider-bulk-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
          const target = btn.dataset.bulk === "all";
          items.forEach((choice) => {
            if (choice.enabled === target) return;
            choice.enabled = target;
            bridge.setProviderEnabled(choice.key, target);
          });
          grid.querySelectorAll("input[type=checkbox]").forEach((cb, idx) => {
            cb.checked = target;
            cb.closest(".provider-tile").classList.toggle("is-on", target);
          });
          updateProviderCount(section, items);
        });
      });

      els.providerGrid.appendChild(section);
    };

    renderSection(
      "Stable APIs",
      "Fast, reliable, recommended for everyday use.",
      stable
    );
    renderSection(
      "Multi-site scrapers",
      "Vendored Torrent-Api-py providers — wider coverage, more latency.",
      vendor
    );
  }

  function updateProviderCount(section, items) {
    const enabledCount = section.querySelectorAll(".provider-tile input:checked").length;
    const counter = section.querySelector(".provider-count");
    if (counter) counter.textContent = `${enabledCount}/${items.length} on`;
  }

  function addFromResult(result, btn) {
    const safety = result.safety;
    if (safety && safety.level === "risky") {
      const reasons = (safety.reasons || []).map((r) => `\u2022 ${r}`).join("\n");
      const ok = confirm(
        `This torrent looks risky:\n\n${reasons}\n\nAdd it anyway?`
      );
      if (!ok) return;
    }
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
  function isCompleted(t) {
    if ((t.progress || 0) >= 100) return true;
    return /seed|finish|complete/i.test(t.status || "");
  }
  function isActive(t) {
    return !isCompleted(t) && !/error/i.test(t.status || "");
  }

  function renderDownloads(items) {
    state.downloads = items;
    const total = items.length;
    const activeCount = items.filter(isActive).length;
    const completedCount = items.filter(isCompleted).length;
    const paused = items.filter((t) => /paused/i.test(t.status || "")).length;
    const errored = items.filter((t) => /error/i.test(t.status || "")).length;

    if (els.dlCountActive) els.dlCountActive.textContent = activeCount;
    if (els.dlCountCompleted) els.dlCountCompleted.textContent = completedCount;
    if (els.dlCountAll) els.dlCountAll.textContent = total;

    if (total === 0) {
      els.downloadsSummary.textContent = "No downloads yet.";
      els.downloadsBadge.hidden = true;
    } else {
      const parts = [`${total} total`, `${activeCount} active`];
      if (paused) parts.push(`${paused} paused`);
      if (errored) parts.push(`${errored} need attention`);
      els.downloadsSummary.textContent = parts.join("  \u00b7  ");
      if (activeCount > 0) {
        els.downloadsBadge.textContent = String(activeCount);
        els.downloadsBadge.hidden = false;
      } else {
        els.downloadsBadge.hidden = true;
      }
    }

    const visible = items.filter((t) => {
      if (state.downloadsTab === "active") return isActive(t);
      if (state.downloadsTab === "completed") return isCompleted(t);
      return true;
    });

    const hasItems = visible.length > 0;
    els.downloadsEmpty.hidden = hasItems;
    els.downloadsList.hidden = !hasItems;
    if (!hasItems) {
      els.downloadsList.innerHTML = "";
      return;
    }

    const existing = new Map();
    els.downloadsList.querySelectorAll(".download-row").forEach((n) => existing.set(n.dataset.hash, n));

    const frag = document.createDocumentFragment();
    visible.forEach((t) => {
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

    const kebabBtn = node.querySelector(".dl-kebab");
    const menu = node.querySelector(".dl-menu");
    kebabBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      closeAllKebabs(menu);
      const open = !menu.hidden;
      menu.hidden = open;
      kebabBtn.setAttribute("aria-expanded", String(!open));
    });

    node.querySelector(".dl-pick-files").addEventListener("click", () => {
      menu.hidden = true;
      kebabBtn.setAttribute("aria-expanded", "false");
      openFilesModal(hash);
    });
    node.querySelector(".dl-open-menu").addEventListener("click", () => {
      menu.hidden = true;
      const t = state.downloads.find((d) => d.hash === hash);
      bridge.openSaveFolder(t ? t.savePath : "");
    });
    node.querySelector(".dl-copy-magnet").addEventListener("click", () => {
      menu.hidden = true;
      navigator.clipboard.writeText(hash).then(
        () => toast("success", "Info hash copied"),
        () => toast("error", "Could not copy")
      );
    });
    node.querySelector(".dl-remove").addEventListener("click", () => {
      menu.hidden = true;
      bridge.removeTorrent(hash, false, () => {});
    });
    node.querySelector(".dl-remove-files").addEventListener("click", () => {
      menu.hidden = true;
      const t = state.downloads.find((d) => d.hash === hash);
      const ok = confirm(`Permanently delete files for "${t?.name || "this torrent"}"? This cannot be undone.`);
      if (ok) bridge.removeTorrent(hash, true, () => {});
    });
  }

  function closeAllKebabs(except) {
    document.querySelectorAll(".dl-menu").forEach((menu) => {
      if (menu === except) return;
      menu.hidden = true;
      const btn = menu.parentElement.querySelector(".dl-kebab");
      if (btn) btn.setAttribute("aria-expanded", "false");
    });
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

  // ----- File-selection modal -----
  function openFilesModal(hash) {
    state.filesModal = { hash, files: [] };
    const t = state.downloads.find((d) => d.hash === hash);
    els.filesTitle.textContent = "Pick files to download";
    els.filesSubtitle.textContent = t?.name || "Choose which files to include and tweak per-file priority.";
    els.filesTable.innerHTML = '<p class="muted small" style="padding:16px">Loading file list...</p>';
    els.filesBackdrop.hidden = false;
    bridge.getTorrentFiles(hash, (raw) => {
      try {
        const files = JSON.parse(raw || "[]");
        state.filesModal.files = files;
        renderFilesTable(files);
      } catch (e) {
        console.error(e);
        els.filesTable.innerHTML = '<p class="muted small" style="padding:16px">Could not load files (metadata might still be downloading).</p>';
      }
    });
  }

  function renderFilesTable(files) {
    if (!files.length) {
      els.filesTable.innerHTML = '<p class="muted small" style="padding:16px">Metadata not ready yet \u2014 try again in a few seconds.</p>';
      els.filesSelectedCount.textContent = "";
      return;
    }
    const rows = files
      .map(
        (f) => `
        <div class="files-row" role="row">
          <label class="files-check">
            <input type="checkbox" data-idx="${f.index}" ${f.priority > 0 ? "checked" : ""} aria-label="Include ${escapeHtml(f.path)}" />
          </label>
          <div class="files-name" title="${escapeHtml(f.path)}">${escapeHtml(f.path)}</div>
          <div class="files-size">${escapeHtml(f.sizeStr)}</div>
          <div class="files-progress">${(f.progress || 0).toFixed(0)}%</div>
          <select class="files-priority" data-idx="${f.index}" aria-label="Priority for ${escapeHtml(f.path)}">
            <option value="1" ${f.priority === 1 ? "selected" : ""}>Low</option>
            <option value="4" ${(!f.priority || f.priority === 4) ? "selected" : ""}>Normal</option>
            <option value="7" ${f.priority === 7 ? "selected" : ""}>High</option>
          </select>
        </div>`
      )
      .join("");
    els.filesTable.innerHTML = `
      <div class="files-row files-head" role="row">
        <span></span><span>File</span><span>Size</span><span>Done</span><span>Priority</span>
      </div>
      ${rows}
    `;
    els.filesTable.querySelectorAll("input[type=checkbox], select").forEach((control) => {
      control.addEventListener("change", updateFilesSelectionCount);
    });
    updateFilesSelectionCount();
  }

  function updateFilesSelectionCount() {
    const total = els.filesTable.querySelectorAll("input[type=checkbox]").length;
    const selected = els.filesTable.querySelectorAll("input[type=checkbox]:checked").length;
    els.filesSelectedCount.textContent = total ? `${selected} of ${total} files selected` : "";
  }

  function closeFilesModal() {
    els.filesBackdrop.hidden = true;
    state.filesModal = { hash: null, files: [] };
  }

  function applyFilesSelection() {
    const hash = state.filesModal.hash;
    if (!hash) return;
    const priorities = {};
    els.filesTable.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      const idx = cb.dataset.idx;
      if (!cb.checked) {
        priorities[idx] = 0;
      } else {
        const sel = els.filesTable.querySelector(`select[data-idx="${idx}"]`);
        priorities[idx] = sel ? parseInt(sel.value, 10) : 4;
      }
    });
    bridge.setFilePriorities(hash, JSON.stringify(priorities), (ok) => {
      if (ok) closeFilesModal();
    });
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

    if (bridge.updateAvailable) {
      bridge.updateAvailable.connect((payloadStr) => {
        let info = {};
        try { info = JSON.parse(payloadStr || "{}"); } catch (e) {}
        if (info && info.latest) {
          const message = `Update available: ${info.latest} (you have ${info.current})`;
          if (els.aboutUpdateStatus) {
            const checksumLink = info.checksumUrl
              ? ` - <a href="#" id="aboutChecksumLink">checksums</a>`
              : "";
            els.aboutUpdateStatus.innerHTML = `${escapeHtml(message)} - <a href="#" id="aboutReleaseLink">download</a>${checksumLink}`;
            const link = document.getElementById("aboutReleaseLink");
            if (link) {
              link.addEventListener("click", (e) => {
                e.preventDefault();
                bridge.openExternal(info.downloadUrl || info.url);
              });
            }
            const checksum = document.getElementById("aboutChecksumLink");
            if (checksum) {
              checksum.addEventListener("click", (e) => {
                e.preventDefault();
                bridge.openExternal(info.checksumUrl);
              });
            }
          }
          toast("success", message);
        } else if (els.aboutUpdateStatus) {
          els.aboutUpdateStatus.textContent = "You're on the latest version.";
        }
      });
    }

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

    if (bridge.metadataEnriched) {
      bridge.metadataEnriched.connect((query, payloadStr) => {
        try {
          const updates = JSON.parse(payloadStr || "[]");
          handleMetadataEnriched(query, updates);
        } catch (e) {
          console.error(e);
        }
      });
    }

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
    loadSearchHistory();
    loadProviderChoices();
    loadAboutInfo();
    if (bridge.checkForUpdates) bridge.checkForUpdates();
  }

  function setupSettingsScrollspy() {
    const sections = Array.from(document.querySelectorAll(".view-settings > .card[id^='settings-']"));
    if (!sections.length || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
          .slice(0, 1)
          .forEach((entry) => {
            const id = entry.target.id.replace(/^settings-/, "");
            els.settingsNavItems.forEach((b) =>
              b.classList.toggle("is-active", b.dataset.jump === id)
            );
          });
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.2, 0.5, 1] }
    );
    sections.forEach((s) => observer.observe(s));
  }

  function loadAboutInfo() {
    if (!bridge || !bridge.getAboutInfo || !els.aboutVersion) return;
    bridge.getAboutInfo((raw) => {
      try {
        const info = JSON.parse(raw || "{}");
        els.aboutVersion.textContent = info.version || "?";
        if (els.sidebarVersion) els.sidebarVersion.textContent = `Yoink v${info.version || "?"}`;
        if (els.aboutHomepage && info.homepage) {
          els.aboutHomepage.href = info.homepage;
          els.aboutHomepage.onclick = (e) => {
            e.preventDefault();
            bridge.openExternal(info.homepage);
          };
        }
        if (els.aboutPlatform) {
          els.aboutPlatform.textContent = `Running on ${info.platform || "?"} with Python ${info.python || "?"}`;
        }
      } catch (e) { console.error(e); }
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
    if (els.settingAutostart) els.settingAutostart.checked = !!s.launchAtLogin;
    if (els.settingDownLimit) els.settingDownLimit.value = s.downloadLimitKbS ?? 0;
    if (els.settingUpLimit) els.settingUpLimit.value = s.uploadLimitKbS ?? 0;
    if (els.settingMaxActiveDl) els.settingMaxActiveDl.value = s.maxActiveDownloads ?? 0;
    if (els.settingMaxActiveSeeds) els.settingMaxActiveSeeds.value = s.maxActiveSeeds ?? 0;
    if (els.settingSeedRatio) els.settingSeedRatio.value = s.seedRatioLimit ?? 0;
    if (els.settingTmdbKey) {
      els.settingTmdbKey.placeholder = s.tmdbConfigured ? "key saved — paste a new one to replace" : "paste TMDB v3 key";
    }
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
      renderHistoryDropdown(els.searchInput.value);
    });
    els.searchInput.addEventListener("focus", () => {
      renderHistoryDropdown(els.searchInput.value);
    });
    els.searchInput.addEventListener("blur", () => {
      setTimeout(hideHistoryDropdown, 120);
    });
    els.searchClear.addEventListener("click", () => {
      els.searchInput.value = "";
      els.searchClear.hidden = true;
      els.searchInput.focus();
      setSearchingState(false);
      resetSearchView();
      hideHistoryDropdown();
    });
    [els.regionFilter, els.categoryFilter, els.qualityFilter, els.sortFilter, els.sourceFilter].forEach((control) => {
      control.addEventListener("change", () => {
        saveFilters();
        if (state.query && !state.searching) doSearch(state.query, 1);
      });
    });
    els.resetFiltersBtn.addEventListener("click", () => {
      els.regionFilter.value = "any";
      els.categoryFilter.value = "movies";
      els.qualityFilter.value = "any";
      els.sortFilter.value = "relevance";
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
    if (els.settingAutostart) {
      els.settingAutostart.addEventListener("change", (e) => {
        bridge.setLaunchAtLogin(e.target.checked, (effective) => {
          els.settingAutostart.checked = !!effective;
          if (e.target.checked && !effective) {
            toast("error", "Could not register launch-at-login (Windows-only).");
          }
        });
      });
    }

    function bindIntSetting(input, key) {
      if (!input) return;
      let debounce;
      input.addEventListener("input", (e) => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
          const v = Math.max(0, parseInt(e.target.value || "0", 10) || 0);
          bridge.setIntSetting(key, v);
        }, 400);
      });
    }
    bindIntSetting(els.settingDownLimit, "download_limit_kb_s");
    bindIntSetting(els.settingUpLimit, "upload_limit_kb_s");
    bindIntSetting(els.settingMaxActiveDl, "max_active_downloads");
    bindIntSetting(els.settingMaxActiveSeeds, "max_active_seeds");
    if (els.settingSeedRatio) {
      let ratioDebounce;
      els.settingSeedRatio.addEventListener("input", (e) => {
        clearTimeout(ratioDebounce);
        ratioDebounce = setTimeout(() => {
          const v = Math.max(0, parseFloat(e.target.value || "0") || 0);
          bridge.setFloatSetting("seed_ratio_limit", v);
        }, 400);
      });
    }

    els.themeButtons.forEach((b) =>
      b.addEventListener("click", () => applyTheme(b.dataset.themeSet))
    );
    els.replayOnboardingBtn.addEventListener("click", showOnboarding);

    if (els.pauseAllBtn) {
      els.pauseAllBtn.addEventListener("click", () => bridge.pauseAll(() => {}));
    }
    if (els.resumeAllBtn) {
      els.resumeAllBtn.addEventListener("click", () => bridge.resumeAll(() => {}));
    }
    els.dlTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        state.downloadsTab = tab.dataset.dlTab;
        els.dlTabs.forEach((t) => {
          const active = t === tab;
          t.classList.toggle("is-active", active);
          t.setAttribute("aria-selected", String(active));
        });
        renderDownloads(state.downloads);
      });
    });

    if (els.detailsClose) els.detailsClose.addEventListener("click", closeDetailsModal);
    if (els.detailsBackdrop) {
      els.detailsBackdrop.addEventListener("click", (e) => {
        if (e.target === els.detailsBackdrop) closeDetailsModal();
      });
    }

    if (els.filesCancel) els.filesCancel.addEventListener("click", closeFilesModal);
    if (els.filesApply) els.filesApply.addEventListener("click", applyFilesSelection);
    if (els.filesBackdrop) {
      els.filesBackdrop.addEventListener("click", (e) => {
        if (e.target === els.filesBackdrop) closeFilesModal();
      });
    }
    if (els.filesSelectAll) {
      els.filesSelectAll.addEventListener("click", () => {
        els.filesTable.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = true; });
        updateFilesSelectionCount();
      });
    }
    if (els.filesSelectNone) {
      els.filesSelectNone.addEventListener("click", () => {
        els.filesTable.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = false; });
        updateFilesSelectionCount();
      });
    }

    document.addEventListener("click", (e) => {
      if (!e.target.closest(".dl-kebab-wrap")) closeAllKebabs(null);
    });

    if (els.clearHistoryBtn) {
      els.clearHistoryBtn.addEventListener("click", () => {
        if (!bridge || !bridge.clearSearchHistory) return;
        bridge.clearSearchHistory();
        state.searchHistory = [];
        hideHistoryDropdown();
        toast("success", "Search history cleared");
      });
    }

    if (els.refreshHealthBtn) {
      els.refreshHealthBtn.addEventListener("click", () => {
        els.refreshHealthBtn.disabled = true;
        els.refreshHealthBtn.textContent = "Checking...";
        bridge.refreshProviderHealth();
      });
    }

    if (els.checkUpdatesBtn) {
      els.checkUpdatesBtn.addEventListener("click", () => {
        if (els.aboutUpdateStatus) els.aboutUpdateStatus.textContent = "Checking GitHub...";
        bridge.checkForUpdates();
      });
    }

    if (els.settingsNavItems && els.settingsNavItems.length) {
      els.settingsNavItems.forEach((btn) => {
        btn.addEventListener("click", () => {
          const target = document.getElementById(`settings-${btn.dataset.jump}`);
          if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
          els.settingsNavItems.forEach((b) => b.classList.toggle("is-active", b === btn));
        });
      });
      setupSettingsScrollspy();
    }

    if (els.settingTmdbSave && els.settingTmdbKey) {
      els.settingTmdbSave.addEventListener("click", () => {
        bridge.setTmdbApiKey(els.settingTmdbKey.value || "");
        toast("success", els.settingTmdbKey.value ? "TMDB key saved" : "TMDB key cleared");
      });
    }
    if (els.tmdbHelpLink) {
      els.tmdbHelpLink.addEventListener("click", (e) => {
        e.preventDefault();
        bridge.openExternal(els.tmdbHelpLink.href);
      });
    }

    els.onboardingDone.addEventListener("click", hideOnboarding);
    els.onboardingBackdrop.addEventListener("click", (e) => {
      if (e.target === els.onboardingBackdrop) hideOnboarding();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && els.detailsBackdrop && !els.detailsBackdrop.hidden) {
        closeDetailsModal();
      } else if (e.key === "Escape" && els.filesBackdrop && !els.filesBackdrop.hidden) {
        closeFilesModal();
      } else if (e.key === "Escape" && !els.onboardingBackdrop.hidden) {
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
