/* Yoink - Frontend entry module.
 *
 * Loaded as a native ES module (`<script type="module">`). All UI wiring,
 * search/downloads rendering, theming and modals live in this file as a
 * single closure (`App`), which keeps the QWebChannel boot path predictable.
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
    completedToday: 0,
    completedTodayDate: "",
    completedSeen: new Set(),
    networkDown: 0,
    networkUp: 0,
    hadInitialDownloadsSnapshot: false,
    playerAvailable: false,
    streamingKey: null,
    streamingHash: null,
    streamingPhase: "",
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

    els.exampleChips = $("#exampleChips");
    els.dropOverlay = $("#dropOverlay");
    els.downloadsSummaryBar = $("#downloadsSummaryBar");
    els.dsbActive = $("#dsbActive");
    els.dsbDown = $("#dsbDown");
    els.dsbUp = $("#dsbUp");
    els.dsbCompletedToday = $("#dsbCompletedToday");
    els.safetyBackdrop = $("#safetyBackdrop");
    els.safetyTitle = $("#safetyTitle");
    els.safetyTag = $("#safetyTag");
    els.safetyReasons = $("#safetyReasons");
    els.safetyClose = $("#safetyClose");
    els.openDataFolderBtn = $("#openDataFolderBtn");

    els.viewToggleBtns = $$(".view-toggle-btn");
    els.settingClipboardWatcher = $("#settingClipboardWatcher");
    els.settingDnsOverHttps = $("#settingDnsOverHttps");
    els.exportSettingsBtn = $("#exportSettingsBtn");
    els.importSettingsBtn = $("#importSettingsBtn");
    els.shortcutsBackdrop = $("#shortcutsBackdrop");
    els.shortcutsClose = $("#shortcutsClose");

    els.wizardSteps = $$(".wizard-step");
    els.wizardDots = $$(".wizard-dot");
    els.wizardSkip = $("#wizardSkip");
    els.wizardBack = $("#wizardBack");
    els.wizardNext = $("#wizardNext");
    els.wizardFolderPath = $("#wizardFolderPath");
    els.wizardPickFolder = $("#wizardPickFolder");
    els.wizardPicks = $$(".wizard-pick");
    els.wizardTmdbKey = $("#wizardTmdbKey");
    els.wizardTmdbHelp = $("#wizardTmdbHelp");
    els.wizardMinimizeTray = $("#wizardMinimizeTray");
    els.wizardNotifications = $("#wizardNotifications");

    els.paletteBackdrop = $("#paletteBackdrop");
    els.paletteInput = $("#paletteInput");
    els.paletteList = $("#paletteList");

    els.labelsBackdrop = $("#labelsBackdrop");
    els.labelsSubtitle = $("#labelsSubtitle");
    els.labelsChips = $("#labelsChips");
    els.labelsInput = $("#labelsInput");
    els.labelsSuggestions = $("#labelsSuggestions");
    els.labelsCancel = $("#labelsCancel");
    els.labelsApply = $("#labelsApply");

    els.watchFolderPath = $("#watchFolderPath");
    els.watchFolderPick = $("#watchFolderPick");
    els.watchFolderClear = $("#watchFolderClear");

    els.feedsList = $("#feedsList");
    els.feedUrl = $("#feedUrl");
    els.feedName = $("#feedName");
    els.feedRegex = $("#feedRegex");
    els.feedMinSeeders = $("#feedMinSeeders");
    els.feedAddBtn = $("#feedAddBtn");

    els.proxyUrl = $("#proxyUrl");
    els.proxyUa = $("#proxyUa");
    els.proxySaveBtn = $("#proxySaveBtn");

    els.scheduleEnabled = $("#scheduleEnabled");
    els.scheduleStart = $("#scheduleStart");
    els.scheduleEnd = $("#scheduleEnd");
    els.scheduleDown = $("#scheduleDown");
    els.scheduleUp = $("#scheduleUp");
    els.scheduleSaveBtn = $("#scheduleSaveBtn");
  }

  // ----- Magnet / torrent URL detection (1.1) -----
  const MAGNET_RE = /^magnet:\?xt=urn:btih:[a-z0-9]+/i;
  const INFOHASH_RE = /^[a-f0-9]{40}$|^[a-z2-7]{32}$/i;
  const TORRENT_URL_RE = /^https?:\/\/\S+\.torrent(\?\S*)?$/i;
  function detectTorrentInput(raw) {
    const v = (raw || "").trim();
    if (!v) return null;
    if (MAGNET_RE.test(v)) return { kind: "magnet", value: v };
    if (TORRENT_URL_RE.test(v)) return { kind: "url", value: v };
    if (INFOHASH_RE.test(v)) {
      return { kind: "magnet", value: `magnet:?xt=urn:btih:${v}` };
    }
    return null;
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
        let level = null;
        if (r.safety.level === "risky") {
          safetyEl.textContent = "Risky";
          safetyEl.classList.add("risky");
          level = "risky";
        } else if (r.safety.level === "caution") {
          safetyEl.textContent = "Check";
          safetyEl.classList.add("caution");
          level = "caution";
        } else if (r.safety.level === "safe" && (r.safety.reasons || []).some((x) => /trusted/i.test(x))) {
          safetyEl.textContent = "Trusted";
          safetyEl.classList.add("safe");
          level = "safe";
        }
        if (level) {
          safetyEl.title = "Click to see why";
          safetyEl.hidden = false;
          safetyEl.setAttribute("role", "button");
          safetyEl.setAttribute("tabindex", "0");
          const open = (e) => {
            e.stopPropagation();
            openSafetyModal(level, r.safety.reasons || [], r.title);
          };
          safetyEl.addEventListener("click", open);
          safetyEl.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(e); }
          });
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

      const seedersLine = node.querySelector(".stat-line.seeders");
      seedersLine.querySelector(".num").textContent = r.seeds ?? 0;
      seedersLine.classList.add(seederHealthClass(r.seeds));
      const n = Number(r.seeds) || 0;
      const healthLabel = n > 50 ? "Excellent" : n >= 10 ? "OK" : "Risky";
      seedersLine.title =
        `Seeders: ${n} (${healthLabel}). Green >50, yellow 10-50, red <10. More seeders = faster download.`;
      node.querySelector(".stat-line.peers .num").textContent = r.peers ?? 0;

      const actionBtn = node.querySelector(".result-action");
      actionBtn.setAttribute("aria-label", `Download ${r.title}`);
      actionBtn.addEventListener("click", () => addFromResult(r, actionBtn));

      const infoBtn = node.querySelector(".result-info");
      if (infoBtn) {
        infoBtn.addEventListener("click", () => openDetailsModal(r));
      }

      // Streaming needs both a player and something to stream from. The file
      // list is not known until the torrent is added, so this only checks that
      // there is a magnet; the bridge reports back if it holds no video.
      const playBtn = node.querySelector(".result-play");
      if (playBtn && state.playerAvailable && r.magnet) {
        playBtn.hidden = false;
        playBtn.setAttribute("aria-label", `Play ${r.title}`);
        playBtn.addEventListener("click", () => startStreamFromResult(r, playBtn));
      }

      const key = r.magnet || r.infoHash || r.title;
      state.rowsByKey.set(key, { node, result: r });
      const cached = state.metadataByKey.get(key);
      if (cached) applyMetadataToRow(node, r, cached);

      frag.appendChild(node);
    });
    els.resultsList.appendChild(frag);
  }

  // ----- Streaming straight from a search result -----
  function startStreamFromResult(r, btn) {
    if (state.streamingKey) {
      toast("info", "Already preparing a stream - one at a time.");
      return;
    }
    state.streamingKey = r.magnet;
    state.streamingPhase = "";
    btn.disabled = true;
    btn.classList.add("is-busy");
    btn.title = "Starting...";
    toast("info", "Preparing stream - this needs a few seconds of the file first.");
    bridge.playFromMagnet(r.magnet, (raw) => {
      let payload = {};
      try { payload = JSON.parse(raw || "{}"); } catch (e) {}
      if (!payload.hash) {
        // The bridge already explained itself in a toast.
        resetStreamButton(btn);
        return;
      }
      state.streamingHash = payload.hash;
    });
  }

  function resetStreamButton(btn) {
    state.streamingKey = null;
    state.streamingHash = null;
    state.streamingPhase = "";
    btn.disabled = false;
    btn.classList.remove("is-busy");
    btn.title = "Stream now, without waiting for the download";
  }

  function currentStreamButton() {
    if (!state.streamingKey) return null;
    const entry = state.rowsByKey.get(state.streamingKey);
    return entry ? entry.node.querySelector(".result-play") : null;
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

  function parseAddResult(raw) {
    if (!raw) return { hash: "", wasExisting: false };
    if (typeof raw === "object") return raw;
    try {
      const obj = JSON.parse(raw);
      return obj && typeof obj === "object"
        ? { hash: obj.hash || "", wasExisting: !!obj.wasExisting, name: obj.name }
        : { hash: String(raw), wasExisting: false };
    } catch (_) {
      return { hash: String(raw), wasExisting: false };
    }
  }

  function focusDownloadRow(hash) {
    switchView("downloads");
    setTimeout(() => {
      const node = els.downloadsList.querySelector(`.download-row[data-hash="${hash}"]`);
      if (node) {
        node.scrollIntoView({ behavior: "smooth", block: "center" });
        node.classList.add("flash");
        setTimeout(() => node.classList.remove("flash"), 1500);
      }
    }, 250);
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
    bridge.addTorrent(result.magnet, (raw) => {
      const { hash, wasExisting } = parseAddResult(raw);
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<svg viewBox="0 0 24 24" class="ic" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg> Yoinked`;
      }
      if (!hash) return;
      if (wasExisting) {
        showDuplicateToast(hash);
      } else {
        toast("success", "Added to downloads");
        setTimeout(() => switchView("downloads"), 500);
      }
    });
  }

  function showClipboardOfferToast(magnet) {
    const el = document.createElement("div");
    el.className = "toast info";
    el.setAttribute("role", "status");
    el.innerHTML = `Clipboard magnet detected. <button type="button" class="toast-action add-it">Add</button> <button type="button" class="toast-action" style="background:transparent;color:var(--text);">Dismiss</button>`;
    const [add, dismiss] = el.querySelectorAll(".toast-action");
    add.addEventListener("click", () => {
      addByDetection({ kind: "magnet", value: magnet });
      el.remove();
    });
    dismiss.addEventListener("click", () => el.remove());
    els.toastStack.appendChild(el);
    setTimeout(() => {
      el.classList.add("fade-out");
      el.addEventListener("animationend", () => el.remove(), { once: true });
    }, 8000);
  }

  function showDuplicateToast(hash) {
    const el = document.createElement("div");
    el.className = "toast info";
    el.setAttribute("role", "status");
    el.innerHTML = `Already in your library. <button type="button" class="toast-action">Jump to it</button>`;
    el.querySelector(".toast-action").addEventListener("click", () => {
      focusDownloadRow(hash);
      el.remove();
    });
    els.toastStack.appendChild(el);
    setTimeout(() => {
      el.classList.add("fade-out");
      el.addEventListener("animationend", () => el.remove(), { once: true });
    }, 6000);
  }

  // ----- Seeder health color (1.7) -----
  function seederHealthClass(seeds) {
    const n = Number(seeds) || 0;
    if (n > 50) return "health-good";
    if (n >= 10) return "health-ok";
    return "health-poor";
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
    trackCompletions(items);
    updateSummaryBar(items);
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

    renderGroupedDownloads(visible);
  }

  // ----- Grouped downloads (3.2) -----
  const GROUP_DEFS = [
    { key: "downloading", title: "Downloading", match: (t) => /download|metadata/i.test(t.status || "") && (t.progress || 0) < 100 },
    { key: "queued",      title: "Queued",      match: (t) => /queue/i.test(t.status || "") },
    { key: "paused",      title: "Paused",      match: (t) => /paused/i.test(t.status || "") },
    { key: "seeding",     title: "Seeding",     match: (t) => /seed/i.test(t.status || "") },
    { key: "done",        title: "Done",        match: (t) => (t.progress || 0) >= 100 && !/seed/i.test(t.status || "") },
    { key: "error",       title: "Needs attention", match: (t) => /error/i.test(t.status || "") },
  ];

  function classifyGroup(t) {
    for (const def of GROUP_DEFS) {
      if (def.match(t)) return def.key;
    }
    return "other";
  }

  function renderGroupedDownloads(items) {
    const buckets = new Map(GROUP_DEFS.map((d) => [d.key, []]));
    items.forEach((t) => {
      const g = classifyGroup(t);
      if (!buckets.has(g)) buckets.set(g, []);
      buckets.get(g).push(t);
    });

    const existingRows = new Map();
    els.downloadsList.querySelectorAll(".download-row").forEach((n) => existingRows.set(n.dataset.hash, n));
    els.downloadsList.innerHTML = "";

    GROUP_DEFS.forEach((def) => {
      const list = buckets.get(def.key) || [];
      if (!list.length) return;
      const group = document.createElement("section");
      group.className = "dl-group";
      group.dataset.group = def.key;
      const collapsedKey = `yoink.dlGroup.${def.key}.collapsed`;
      if (localStorage.getItem(collapsedKey) === "1") group.classList.add("collapsed");
      const head = document.createElement("header");
      head.className = "dl-group-head";
      head.innerHTML = `
        <span class="dl-group-title">${def.title}</span>
        <span class="dl-group-count">${list.length}</span>
        <button type="button" class="dl-group-toggle" aria-label="Toggle ${def.title}">${group.classList.contains("collapsed") ? "+" : "−"}</button>
      `;
      head.addEventListener("click", () => {
        const wasCollapsed = group.classList.toggle("collapsed");
        head.querySelector(".dl-group-toggle").textContent = wasCollapsed ? "+" : "−";
        localStorage.setItem(collapsedKey, wasCollapsed ? "1" : "0");
      });
      group.appendChild(head);
      const body = document.createElement("div");
      body.className = "dl-group-items";
      list.forEach((t) => {
        let node = existingRows.get(t.hash);
        if (!node) {
          node = els.downloadTpl.content.firstElementChild.cloneNode(true);
          node.dataset.hash = t.hash;
          wireDownloadRow(node, t.hash);
        } else {
          existingRows.delete(t.hash);
        }
        updateDownloadRow(node, t);
        body.appendChild(node);
      });
      group.appendChild(body);
      els.downloadsList.appendChild(group);
    });
  }

  function wireDownloadRow(node, hash) {
    node.querySelector(".dl-pause").addEventListener("click", () => bridge.pauseTorrent(hash, () => {}));
    node.querySelector(".dl-resume").addEventListener("click", () => bridge.resumeTorrent(hash, () => {}));
    node.querySelector(".dl-open").addEventListener("click", () => {
      const t = state.downloads.find((d) => d.hash === hash);
      bridge.openSaveFolder(t ? t.savePath : "");
    });
    const openFileBtn = node.querySelector(".dl-open-file");
    if (openFileBtn) {
      openFileBtn.addEventListener("click", () => {
        bridge.getDownloadFile(hash, (path) => {
          if (path) bridge.openPath(path);
          else toast("error", "File not ready yet.");
        });
      });
    }
    const playBtn = node.querySelector(".dl-play");
    if (playBtn) {
      playBtn.addEventListener("click", () => {
        playBtn.disabled = true;
        bridge.playInApp(hash, -1, (raw) => {
          playBtn.disabled = false;
          let status = {};
          try { status = JSON.parse(raw || "{}"); } catch (e) {}
          // An empty payload means the bridge already explained itself in a toast.
          if (status.ready === false) toast("info", "Buffering the start of the file...");
        });
      });
    }

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
    const moveBtn = node.querySelector(".dl-move-folder");
    if (moveBtn) {
      moveBtn.addEventListener("click", () => {
        menu.hidden = true;
        bridge.pickAndMoveTorrent(hash, (path) => {
          if (path) toast("success", "Move queued");
        });
      });
    }
    const labelsBtn = node.querySelector(".dl-labels");
    if (labelsBtn) {
      labelsBtn.addEventListener("click", () => {
        menu.hidden = true;
        const t = state.downloads.find((d) => d.hash === hash);
        openLabelsModal(hash, t?.name || "");
      });
    }
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
    const cancelBtn = node.querySelector(".dl-cancel");
    if (cancelBtn) {
      let armed = false;
      let armTimer = null;
      const disarm = () => {
        armed = false;
        cancelBtn.classList.remove("is-armed");
        cancelBtn.title = "Cancel and remove";
        if (armTimer) {
          clearTimeout(armTimer);
          armTimer = null;
        }
      };
      cancelBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        if (!armed) {
          armed = true;
          cancelBtn.classList.add("is-armed");
          cancelBtn.title = "Click again to confirm removal";
          toast("Click again to cancel this download", "info");
          armTimer = setTimeout(disarm, 3000);
          return;
        }
        disarm();
        bridge.removeTorrent(hash, false, () => {});
      });
      cancelBtn.addEventListener("blur", disarm);
    }
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
    const completed = pct >= 100 || /seed|finish|complete/i.test(t.status || "");
    node.querySelector(".dl-pause").hidden = !isDownloading;
    node.querySelector(".dl-resume").hidden = !isPaused;
    const openFileBtn = node.querySelector(".dl-open-file");
    if (openFileBtn) openFileBtn.hidden = !completed;
    const playBtn = node.querySelector(".dl-play");
    if (playBtn) updatePlayButton(playBtn, node, t);
  }

  // The play control needs two answers: is there a player at all (asked once at
  // startup) and does this torrent hold a video (needs metadata, which lands
  // after the row does — so it is asked once per row and cached on the node).
  function updatePlayButton(btn, node, t) {
    if (!state.playerAvailable) {
      btn.hidden = true;
      return;
    }
    const cached = node.dataset.playable;
    if (cached === "1" || cached === "0") {
      btn.hidden = cached !== "1";
      return;
    }
    btn.hidden = true;
    const metadataReady = !/metadata/i.test(t.status || "") && Boolean(t.name);
    if (!metadataReady || node.dataset.playablePending === "1") return;
    node.dataset.playablePending = "1";
    bridge.getPlayableFile(t.hash, (index) => {
      node.dataset.playablePending = "";
      node.dataset.playable = index >= 0 ? "1" : "0";
      btn.hidden = index < 0;
    });
  }

  function loadPlayerStatus() {
    if (!bridge || !bridge.getPlayerStatus) return;
    bridge.getPlayerStatus((raw) => {
      try {
        const info = JSON.parse(raw || "{}");
        state.playerAvailable = Boolean(info.available);
        if (!info.available && info.reason) {
          console.info(`In-app player unavailable: ${info.reason}`);
        }
      } catch (e) {}
    });
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

  // ----- Onboarding wizard (6.1) -----
  const wizard = { step: 1, total: 4, category: "movies" };

  function showWizardStep(step) {
    wizard.step = step;
    els.wizardSteps.forEach((s) => s.classList.toggle("is-active", Number(s.dataset.step) === step));
    els.wizardDots.forEach((d, i) => d.classList.toggle("is-active", i < step));
    els.wizardBack.hidden = step <= 1;
    els.wizardNext.hidden = step >= wizard.total;
    els.onboardingDone.hidden = step < wizard.total;
  }
  function showOnboarding() {
    els.onboardingBackdrop.hidden = false;
    showWizardStep(1);
    setTimeout(() => els.wizardNext.focus(), 50);
  }
  function hideOnboarding() {
    els.onboardingBackdrop.hidden = true;
    localStorage.setItem("yoink.onboardingSeen", "1");
    els.searchInput && els.searchInput.focus();
  }
  function finishWizard() {
    // Apply choices
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
  function maybeShowOnboarding() {
    if (!localStorage.getItem("yoink.onboardingSeen")) {
      showOnboarding();
    }
  }

  // ----- Shortcuts panel (7.5) -----
  function showShortcuts() {
    els.shortcutsBackdrop.hidden = false;
    setTimeout(() => els.shortcutsClose && els.shortcutsClose.focus(), 50);
  }
  function hideShortcuts() { els.shortcutsBackdrop.hidden = true; }

  // ----- Command palette (7.4) -----
  const palette = { commands: [], filtered: [], active: 0 };
  function loadPaletteCommands() {
    if (!bridge || !bridge.listCommands) return;
    bridge.listCommands((raw) => {
      try {
        palette.commands = JSON.parse(raw || "[]");
      } catch (_) {
        palette.commands = [];
      }
      // Static UI-side commands
      THEMES.forEach((t) => palette.commands.push({ id: `theme:${t}`, label: `Theme: ${t}` }));
      palette.commands.push({ id: "ui:shortcuts", label: "Show keyboard shortcuts" });
      palette.commands.push({ id: "ui:onboarding", label: "Replay welcome tour" });
    });
  }
  function showPalette() {
    els.paletteInput.value = "";
    filterPalette("");
    els.paletteBackdrop.hidden = false;
    setTimeout(() => els.paletteInput.focus(), 50);
  }
  function hidePalette() { els.paletteBackdrop.hidden = true; }
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

  // ----- Labels (7.3) -----
  const labelsState = { hash: "", labels: [], allLabels: [] };
  function openLabelsModal(hash, name) {
    labelsState.hash = hash;
    els.labelsSubtitle.textContent = name || "";
    bridge.getLabels(hash, (raw) => {
      try { labelsState.labels = JSON.parse(raw || "[]"); } catch (_) { labelsState.labels = []; }
      bridge.getAllLabels((rawAll) => {
        try { labelsState.allLabels = JSON.parse(rawAll || "[]"); } catch (_) { labelsState.allLabels = []; }
        renderLabelsEditor();
        els.labelsBackdrop.hidden = false;
        setTimeout(() => els.labelsInput && els.labelsInput.focus(), 50);
      });
    });
  }
  function renderLabelsEditor() {
    els.labelsChips.innerHTML = "";
    labelsState.labels.forEach((lbl) => {
      const pill = document.createElement("span");
      pill.className = "label-pill";
      pill.innerHTML = `${escapeHtml(lbl)}<button type="button" class="remove" aria-label="Remove ${escapeHtml(lbl)}">×</button>`;
      pill.querySelector(".remove").addEventListener("click", () => {
        labelsState.labels = labelsState.labels.filter((l) => l !== lbl);
        renderLabelsEditor();
      });
      els.labelsChips.appendChild(pill);
    });
    els.labelsSuggestions.innerHTML = "";
    labelsState.allLabels
      .filter((l) => !labelsState.labels.includes(l))
      .slice(0, 10)
      .forEach((lbl) => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip";
        chip.textContent = lbl;
        chip.addEventListener("click", () => {
          labelsState.labels.push(lbl);
          renderLabelsEditor();
        });
        els.labelsSuggestions.appendChild(chip);
      });
  }
  function closeLabelsModal() { els.labelsBackdrop.hidden = true; }
  function applyLabels() {
    bridge.setLabels(labelsState.hash, JSON.stringify(labelsState.labels));
    closeLabelsModal();
    toast("success", "Labels saved");
  }

  // ----- Advanced settings: watch folder / feeds / proxy / schedule -----
  function loadWatchFolder() {
    const raw = localStorage.getItem("yoink.watchFolderCached") || "";
    if (raw) els.watchFolderPath.textContent = raw;
  }
  function loadFeeds() {
    if (!bridge || !bridge.getFeeds) return;
    bridge.getFeeds((raw) => {
      let payload = [];
      try { payload = JSON.parse(raw || "[]"); } catch (_) {}
      els.feedsList.innerHTML = "";
      payload.forEach((f) => {
        const li = document.createElement("li");
        li.innerHTML = `
          <div class="feed-meta">
            <span class="feed-name">${escapeHtml(f.name || f.url)}</span>
            <span class="feed-url">${escapeHtml(f.url)}${f.filterRegex ? ` &middot; filter: <code>${escapeHtml(f.filterRegex)}</code>` : ""}${f.minSeeders ? ` &middot; min seeds: ${f.minSeeders}` : ""}</span>
          </div>
          <button class="btn btn-ghost" type="button">Remove</button>
        `;
        li.querySelector("button").addEventListener("click", () => {
          bridge.removeFeed(f.id);
          setTimeout(loadFeeds, 200);
        });
        els.feedsList.appendChild(li);
      });
      if (!payload.length) {
        els.feedsList.innerHTML = '<li class="muted small" style="background:transparent;border:0;">No feeds yet.</li>';
      }
    });
  }
  function loadProxy() {
    if (!bridge || !bridge.getProxy) return;
    bridge.getProxy((raw) => {
      try {
        const p = JSON.parse(raw || "{}");
        els.proxyUrl.value = p.proxyUrl || "";
        els.proxyUa.value = p.userAgent || "";
      } catch (_) {}
    });
  }
  function loadSchedule() {
    if (!bridge || !bridge.getSchedule) return;
    bridge.getSchedule((raw) => {
      try {
        const s = JSON.parse(raw || "{}");
        els.scheduleEnabled.checked = !!s.enabled;
        els.scheduleStart.value = s.quietStart || "09:00";
        els.scheduleEnd.value = s.quietEnd || "18:00";
        els.scheduleDown.value = s.quietDownKbS || 0;
        els.scheduleUp.value = s.quietUpKbS || 0;
      } catch (_) {}
    });
  }

  // ----- Result view mode (1.6) -----
  function applyViewMode(mode) {
    const m = mode === "cards" ? "cards" : "list";
    els.resultsList.setAttribute("data-view-mode", m);
    els.viewToggleBtns.forEach((b) => {
      const active = b.dataset.viewMode === m;
      b.classList.toggle("is-active", active);
      b.setAttribute("aria-pressed", String(active));
    });
    localStorage.setItem("yoink.viewMode", m);
  }
  function initViewMode() {
    applyViewMode(localStorage.getItem("yoink.viewMode") || "list");
  }

  // ----- Safety modal (4.1) -----
  function openSafetyModal(level, reasons, title) {
    const tagText = level === "risky"
      ? "Risky — Yoink flagged several concerns"
      : level === "caution"
      ? "Check — proceed with care"
      : "Trusted — known good uploader / well-seeded";
    els.safetyTitle.textContent = `Safety: ${title || "this torrent"}`;
    els.safetyTag.textContent = tagText;
    els.safetyReasons.innerHTML = "";
    if (!reasons.length) {
      const li = document.createElement("li");
      li.textContent = "No specific concerns recorded.";
      els.safetyReasons.appendChild(li);
    } else {
      reasons.forEach((reason) => {
        const li = document.createElement("li");
        if (level === "caution") li.classList.add("is-caution");
        li.textContent = reason;
        els.safetyReasons.appendChild(li);
      });
    }
    els.safetyBackdrop.hidden = false;
    setTimeout(() => els.safetyClose && els.safetyClose.focus(), 50);
  }
  function closeSafetyModal() { els.safetyBackdrop.hidden = true; }

  // ----- Smart input bar (1.1) -----
  let smartHint = null;
  function showSmartHint(detection) {
    hideSmartHint();
    smartHint = document.createElement("div");
    smartHint.className = "search-mode-hint";
    smartHint.innerHTML = `
      <svg viewBox="0 0 24 24" class="ic" aria-hidden="true"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>
      <span>Detected ${detection.kind === "magnet" ? "<strong>magnet link</strong>" : "<strong>.torrent URL</strong>"} — press <kbd>Enter</kbd> to add it to downloads.</span>
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

  function addByDetection(detection) {
    if (detection.kind === "magnet") {
      bridge.addTorrent(detection.value, (raw) => {
        const { hash, wasExisting } = parseAddResult(raw);
        if (!hash) return;
        if (wasExisting) showDuplicateToast(hash);
        else { toast("success", "Added to downloads"); setTimeout(() => switchView("downloads"), 400); }
      });
    } else {
      toast("info", "Add via URL is coming soon — paste the magnet instead.");
    }
  }

  // ----- Drag and drop .torrent files (2.1) -----
  function arrayBufferToBase64(buf) {
    const bytes = new Uint8Array(buf);
    let bin = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(bin);
  }

  function isTorrentFile(file) {
    if (!file) return false;
    if ((file.name || "").toLowerCase().endsWith(".torrent")) return true;
    if (file.type === "application/x-bittorrent") return true;
    return false;
  }

  function showDropOverlay(show) {
    els.dropOverlay.hidden = !show;
  }

  function handleDroppedFiles(files) {
    const torrentFiles = Array.from(files || []).filter(isTorrentFile);
    if (!torrentFiles.length) {
      toast("error", "Only .torrent files can be dropped here.");
      return;
    }
    torrentFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = arrayBufferToBase64(reader.result);
        bridge.addTorrentFromBytes(file.name, base64, (raw) => {
          const { hash, wasExisting } = parseAddResult(raw);
          if (hash && !wasExisting) {
            setTimeout(() => switchView("downloads"), 400);
          } else if (hash && wasExisting) {
            showDuplicateToast(hash);
          }
        });
      };
      reader.onerror = () => toast("error", `Could not read ${file.name}`);
      reader.readAsArrayBuffer(file);
    });
  }

  function handleDroppedText(text) {
    const detection = detectTorrentInput(text);
    if (detection) addByDetection(detection);
    else toast("error", "Dropped text is not a magnet or torrent URL.");
  }

  // ----- Downloads summary bar (3.5) -----
  function todayStamp() {
    const d = new Date();
    return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
  }
  function loadCompletedToday() {
    try {
      const stamp = todayStamp();
      const stored = JSON.parse(localStorage.getItem("yoink.completedToday") || "{}");
      if (stored.date === stamp) {
        state.completedTodayDate = stamp;
        state.completedToday = stored.count || 0;
        state.completedSeen = new Set(stored.seen || []);
      } else {
        state.completedTodayDate = stamp;
        state.completedToday = 0;
        state.completedSeen = new Set();
        saveCompletedToday();
      }
    } catch (_) {
      state.completedToday = 0;
      state.completedSeen = new Set();
    }
  }
  function saveCompletedToday() {
    try {
      localStorage.setItem("yoink.completedToday", JSON.stringify({
        date: state.completedTodayDate,
        count: state.completedToday,
        seen: Array.from(state.completedSeen),
      }));
    } catch (_) {}
  }

  function updateSummaryBar(items) {
    if (!els.downloadsSummaryBar) return;
    if (!items.length) {
      els.downloadsSummaryBar.hidden = true;
      return;
    }
    els.downloadsSummaryBar.hidden = false;
    const active = items.filter(isActive).length;
    els.dsbActive.textContent = String(active);
    els.dsbDown.textContent = formatKB(state.networkDown);
    els.dsbUp.textContent = formatKB(state.networkUp);
    els.dsbCompletedToday.textContent = String(state.completedToday);
  }

  function trackCompletions(items) {
    if (!state.hadInitialDownloadsSnapshot) {
      items.filter(isCompleted).forEach((t) => state.completedSeen.add(t.hash));
      state.hadInitialDownloadsSnapshot = true;
      saveCompletedToday();
      return;
    }
    let changed = false;
    items.forEach((t) => {
      if (isCompleted(t) && !state.completedSeen.has(t.hash)) {
        state.completedSeen.add(t.hash);
        state.completedToday += 1;
        changed = true;
      }
    });
    if (changed) saveCompletedToday();
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

    if (bridge.streamProgress) {
      bridge.streamProgress.connect((payloadStr) => {
        let info = {};
        try { info = JSON.parse(payloadStr || "{}"); } catch (e) { return; }
        const btn = currentStreamButton();
        if (info.phase === "failed") {
          if (btn) resetStreamButton(btn);
          return;
        }
        // Progress lives in the tooltip so the row never changes width. A
        // toast only fires when the phase changes, not on every poll.
        if (btn && info.message) btn.title = info.message;
        if (info.phase && info.phase !== state.streamingPhase) {
          state.streamingPhase = info.phase;
          if (info.phase === "buffering") toast("info", "Got the file list - buffering the start.");
        }
        // The window opens by itself once the head is in; the button goes back
        // to normal so the same result can be replayed later.
        if (info.phase === "buffering" && (info.bufferProgress || 0) >= 100 && btn) {
          resetStreamButton(btn);
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
      state.networkDown = down;
      state.networkUp = up;
      els.netDown.textContent = formatKB(down);
      els.netUp.textContent = formatKB(up);
      if (els.dsbDown) els.dsbDown.textContent = formatKB(down);
      if (els.dsbUp) els.dsbUp.textContent = formatKB(up);
    });

    bridge.toast.connect((kind, msg) => toast(kind, msg));

    if (bridge.clipboardMagnet) {
      bridge.clipboardMagnet.connect((magnet) => showClipboardOfferToast(magnet));
    }

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
      try {
        const items = JSON.parse(payload || "[]");
        renderDownloads(items);
        // 3.1 — open Downloads by default if anything is active
        if (items.some(isActive) && state.view === "search") {
          switchView("downloads");
        }
      } catch (e) {}
    });
    bridge.getSettings((payload) => {
      try { applySettings(JSON.parse(payload)); } catch (e) {}
    });
    loadSearchHistory();
    loadProviderChoices();
    loadAboutInfo();
    loadPlayerStatus();
    loadPaletteCommands();
    loadWatchFolder();
    loadFeeds();
    loadProxy();
    loadSchedule();
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
    if (els.settingClipboardWatcher) els.settingClipboardWatcher.checked = !!s.clipboardWatcher;
    if (els.settingDnsOverHttps) els.settingDnsOverHttps.checked = !!s.dnsOverHttps;
    if (els.watchFolderPath) {
      els.watchFolderPath.textContent = s.watchFolder || "Not set";
      if (s.watchFolder) localStorage.setItem("yoink.watchFolderCached", s.watchFolder);
    }
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

    if (els.safetyClose) els.safetyClose.addEventListener("click", closeSafetyModal);
    if (els.safetyBackdrop) {
      els.safetyBackdrop.addEventListener("click", (e) => {
        if (e.target === els.safetyBackdrop) closeSafetyModal();
      });
    }

    if (els.openDataFolderBtn) {
      els.openDataFolderBtn.addEventListener("click", () => bridge.openDataFolder());
    }

    let dragDepth = 0;
    document.addEventListener("dragenter", (e) => {
      if (!e.dataTransfer) return;
      const types = Array.from(e.dataTransfer.types || []);
      if (types.includes("Files") || types.includes("text/uri-list") || types.includes("text/plain")) {
        dragDepth += 1;
        showDropOverlay(true);
      }
    });
    document.addEventListener("dragover", (e) => {
      if (e.dataTransfer) e.preventDefault();
    });
    document.addEventListener("dragleave", () => {
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) showDropOverlay(false);
    });
    document.addEventListener("drop", (e) => {
      e.preventDefault();
      dragDepth = 0;
      showDropOverlay(false);
      const dt = e.dataTransfer;
      if (!dt) return;
      if (dt.files && dt.files.length) {
        handleDroppedFiles(dt.files);
        return;
      }
      const text = dt.getData("text/uri-list") || dt.getData("text/plain");
      if (text) handleDroppedText(text);
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
      els.sourceFilter.value = "multi-default";
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

    if (els.shortcutsClose) els.shortcutsClose.addEventListener("click", hideShortcuts);
    if (els.shortcutsBackdrop) {
      els.shortcutsBackdrop.addEventListener("click", (e) => {
        if (e.target === els.shortcutsBackdrop) hideShortcuts();
      });
    }

    els.viewToggleBtns.forEach((btn) => {
      btn.addEventListener("click", () => applyViewMode(btn.dataset.viewMode));
    });

    if (els.settingClipboardWatcher) {
      els.settingClipboardWatcher.addEventListener("change", (e) =>
        bridge.setBoolSetting("clipboard_watcher_enabled", e.target.checked)
      );
    }
    if (els.settingDnsOverHttps) {
      els.settingDnsOverHttps.addEventListener("change", (e) => {
        bridge.setBoolSetting("dns_over_https_enabled", e.target.checked);
        toast("info", e.target.checked
          ? "Sources will be resolved over DNS-over-HTTPS."
          : "Back to your system's DNS resolver.");
      });
    }
    if (els.exportSettingsBtn) {
      els.exportSettingsBtn.addEventListener("click", () => bridge.exportSettings(() => {}));
    }
    if (els.importSettingsBtn) {
      els.importSettingsBtn.addEventListener("click", () => bridge.importSettings(() => {}));
    }

    // Command palette
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

    // Labels modal
    if (els.labelsInput) {
      els.labelsInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          const val = (els.labelsInput.value || "").trim();
          if (val && !labelsState.labels.includes(val)) {
            labelsState.labels.push(val);
            renderLabelsEditor();
          }
          els.labelsInput.value = "";
        }
      });
    }
    if (els.labelsCancel) els.labelsCancel.addEventListener("click", closeLabelsModal);
    if (els.labelsApply) els.labelsApply.addEventListener("click", applyLabels);
    if (els.labelsBackdrop) {
      els.labelsBackdrop.addEventListener("click", (e) => {
        if (e.target === els.labelsBackdrop) closeLabelsModal();
      });
    }

    // Advanced settings
    if (els.watchFolderPick) {
      els.watchFolderPick.addEventListener("click", () => {
        bridge.pickWatchFolder((folder) => {
          if (folder) {
            els.watchFolderPath.textContent = folder;
            localStorage.setItem("yoink.watchFolderCached", folder);
          }
        });
      });
    }
    if (els.watchFolderClear) {
      els.watchFolderClear.addEventListener("click", () => {
        bridge.clearWatchFolder();
        els.watchFolderPath.textContent = "Not set";
        localStorage.removeItem("yoink.watchFolderCached");
      });
    }
    if (els.feedAddBtn) {
      els.feedAddBtn.addEventListener("click", () => {
        const url = (els.feedUrl.value || "").trim();
        if (!url) { toast("error", "Feed URL is required"); return; }
        bridge.addFeed(
          url,
          (els.feedName.value || "").trim(),
          (els.feedRegex.value || "").trim(),
          parseInt(els.feedMinSeeders.value || "0", 10) || 0,
          () => {
            els.feedUrl.value = "";
            els.feedName.value = "";
            els.feedRegex.value = "";
            els.feedMinSeeders.value = "";
            setTimeout(loadFeeds, 200);
          }
        );
      });
    }
    if (els.proxySaveBtn) {
      els.proxySaveBtn.addEventListener("click", () => {
        bridge.setProxy(els.proxyUrl.value || "", els.proxyUa.value || "");
        toast("success", "Proxy settings saved");
      });
    }
    if (els.scheduleSaveBtn) {
      els.scheduleSaveBtn.addEventListener("click", () => {
        bridge.setSchedule(JSON.stringify({
          enabled: !!els.scheduleEnabled.checked,
          quietStart: els.scheduleStart.value || "09:00",
          quietEnd: els.scheduleEnd.value || "18:00",
          quietDownKbS: parseInt(els.scheduleDown.value || "0", 10) || 0,
          quietUpKbS: parseInt(els.scheduleUp.value || "0", 10) || 0,
        }));
        toast("success", "Schedule saved");
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

  function init() {
    cacheEls();
    initTheme();
    loadFilters();
    loadCompletedToday();
    initViewMode();
    bindEvents();
    maybeShowOnboarding();
    new QWebChannel(qt.webChannelTransport, onBridgeReady);
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
