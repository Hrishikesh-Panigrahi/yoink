import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { startStreamFromResult } from "./stream.js";
import { openDetailsModal } from "./details.js";
import { doSearch } from "./search.js";
import { addFromResult } from "./add.js";
import { openSafetyModal } from "./safety.js";

export function setSearchingState(isSearching, msg) {
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

export function resetSearchView() {
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
    'Type a title above and press <kbd>Enter</kbd>. Stable search uses The Pirate Bay; advanced search uses Torrent-Api-py.';
}

export function renderResults(results) {
  els.resultsList.innerHTML = "";
  state.rowsByKey = new Map();
  if (!results.length) {
    showNoResults();
    return;
  }
  els.searchEmpty.hidden = true;
  els.resultsList.hidden = false;
  const frag = document.createDocumentFragment();
  results.forEach((r) => frag.appendChild(buildResultRow(r)));
  els.resultsList.appendChild(frag);
}

function showNoResults() {
  els.resultsList.hidden = true;
  els.searchEmpty.hidden = false;
  els.searchEmpty.querySelector("h3").textContent = "No results";
  els.searchEmpty.querySelector("p").textContent = "Try a different title, category or region, or switch to another source.";
  els.pagination.hidden = true;
}

function buildResultRow(r) {
  const node = els.resultTpl.content.firstElementChild.cloneNode(true);
  fillPoster(node, r);
  fillMeta(node, r);
  fillSafetyBadge(node, r);
  fillGenresAndSummary(node, r);
  fillStats(node, r);
  wireResultActions(node, r);

  const key = r.magnet || r.infoHash || r.title;
  state.rowsByKey.set(key, { node, result: r });
  const cached = state.metadataByKey.get(key);
  if (cached) applyMetadataToRow(node, r, cached);
  return node;
}

function fillPoster(node, r) {
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
}

function formatRuntime(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h ${m}m` : `${m}m`;
}

function fillMeta(node, r) {
  node.querySelector(".result-title").textContent = r.title;
  node.querySelector(".result-title").title = r.title;

  const source = node.querySelector(".meta.source");
  source.textContent = r.source;

  node.querySelector(".meta.size").textContent = r.size || "?";

  const dateEl = node.querySelector(".meta.date");
  if (r.date) { dateEl.textContent = r.date; dateEl.hidden = false; }

  const runtimeEl = node.querySelector(".meta.runtime");
  if (r.runtime && Number(r.runtime) > 0) {
    runtimeEl.textContent = formatRuntime(Number(r.runtime));
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
}

function safetyBadgeFor(safety) {
  if (safety.level === "risky") return { level: "risky", label: "Risky" };
  if (safety.level === "caution") return { level: "caution", label: "Check" };
  if (safety.level === "safe" && (safety.reasons || []).some((x) => /trusted/i.test(x))) {
    return { level: "safe", label: "Trusted" };
  }
  return null;
}

function fillSafetyBadge(node, r) {
  const safetyEl = node.querySelector(".meta.safety-badge");
  if (!safetyEl || !r.safety) return;
  const badge = safetyBadgeFor(r.safety);
  if (!badge) return;

  safetyEl.textContent = badge.label;
  safetyEl.classList.add(badge.level);
  safetyEl.title = "Click to see why";
  safetyEl.hidden = false;
  safetyEl.setAttribute("role", "button");
  safetyEl.setAttribute("tabindex", "0");
  const open = (e) => {
    e.stopPropagation();
    openSafetyModal(badge.level, r.safety.reasons || [], r.title);
  };
  safetyEl.addEventListener("click", open);
  safetyEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(e); }
  });
}

function fillGenresAndSummary(node, r) {
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
}

function fillStats(node, r) {
  const seedersLine = node.querySelector(".stat-line.seeders");
  seedersLine.querySelector(".num").textContent = r.seeds ?? 0;
  seedersLine.classList.add(seederHealthClass(r.seeds));
  const n = Number(r.seeds) || 0;
  const healthLabel = n > 50 ? "Excellent" : n >= 10 ? "OK" : "Risky";
  seedersLine.title =
    `Seeders: ${n} (${healthLabel}). Green >50, yellow 10-50, red <10. More seeders = faster download.`;
  node.querySelector(".stat-line.peers .num").textContent = r.peers ?? 0;
}

function wireResultActions(node, r) {
  const actionBtn = node.querySelector(".result-action");
  actionBtn.setAttribute("aria-label", `Download ${r.title}`);
  actionBtn.addEventListener("click", () => addFromResult(r, actionBtn));

  const infoBtn = node.querySelector(".result-info");
  if (infoBtn) {
    infoBtn.addEventListener("click", () => openDetailsModal(r));
  }

  // The file list is unknown until the torrent is added, so only check for a
  // magnet here. The bridge reports back if there is no video.
  const playBtn = node.querySelector(".result-play");
  if (playBtn && state.playerAvailable && r.magnet) {
    playBtn.hidden = false;
    playBtn.setAttribute("aria-label", `Play ${r.title}`);
    playBtn.addEventListener("click", () => startStreamFromResult(r, playBtn));
  }
}

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

export function renderPagination() {
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

function seederHealthClass(seeds) {
  const n = Number(seeds) || 0;
  if (n > 50) return "health-good";
  if (n >= 10) return "health-ok";
  return "health-poor";
}

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
export function initViewMode() {
  applyViewMode(localStorage.getItem("yoink.viewMode") || "list");
}

export function connectResultsSignals() {
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
}

export function bindResultsEvents() {
  els.viewToggleBtns.forEach((btn) => {
    btn.addEventListener("click", () => applyViewMode(btn.dataset.viewMode));
  });
}
