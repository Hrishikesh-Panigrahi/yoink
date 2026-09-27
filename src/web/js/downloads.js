import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { formatKB, statusClass } from "./util.js";
import { toast } from "./toasts.js";
import { switchView } from "./sidebar.js";
import { updatePlayButton } from "./stream.js";
import { openFilesModal } from "./files.js";
import { openLabelsModal } from "./labels.js";

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

function findDownload(hash) {
  return state.downloads.find((d) => d.hash === hash);
}

function openDownloadFolder(hash) {
  const t = findDownload(hash);
  bridge.openSaveFolder(t ? t.savePath : "");
}

function wireDownloadRow(node, hash) {
  wireRowButtons(node, hash);
  wireRowMenu(node, hash);
  wireCancelButton(node, hash);
}

function wireRowButtons(node, hash) {
  node.querySelector(".dl-pause").addEventListener("click", () => bridge.pauseTorrent(hash, () => {}));
  node.querySelector(".dl-resume").addEventListener("click", () => bridge.resumeTorrent(hash, () => {}));
  node.querySelector(".dl-open").addEventListener("click", () => openDownloadFolder(hash));

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
        // An empty payload means the bridge already showed a toast.
        if (status.ready === false) toast("info", "Buffering the start of the file...");
      });
    });
  }
}

function wireRowMenu(node, hash) {
  const kebabBtn = node.querySelector(".dl-kebab");
  const menu = node.querySelector(".dl-menu");
  kebabBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    closeAllKebabs(menu);
    const open = !menu.hidden;
    menu.hidden = open;
    kebabBtn.setAttribute("aria-expanded", String(!open));
  });

  const onItem = (selector, action) => {
    const item = node.querySelector(selector);
    if (!item) return;
    item.addEventListener("click", () => {
      menu.hidden = true;
      action();
    });
  };

  onItem(".dl-pick-files", () => {
    kebabBtn.setAttribute("aria-expanded", "false");
    openFilesModal(hash);
  });
  onItem(".dl-open-menu", () => openDownloadFolder(hash));
  onItem(".dl-move-folder", () => {
    bridge.pickAndMoveTorrent(hash, (path) => {
      if (path) toast("success", "Move queued");
    });
  });
  onItem(".dl-labels", () => openLabelsModal(hash, findDownload(hash)?.name || ""));
  onItem(".dl-copy-magnet", () => {
    navigator.clipboard.writeText(hash).then(
      () => toast("success", "Info hash copied"),
      () => toast("error", "Could not copy")
    );
  });
  onItem(".dl-remove", () => bridge.removeTorrent(hash, false, () => {}));
  onItem(".dl-remove-files", () => {
    const name = findDownload(hash)?.name || "this torrent";
    const ok = confirm(`Permanently delete files for "${name}"? This cannot be undone.`);
    if (ok) bridge.removeTorrent(hash, true, () => {});
  });
}

// The bin button needs a second click within 3 seconds, so one stray click
// can't remove a download.
function wireCancelButton(node, hash) {
  const cancelBtn = node.querySelector(".dl-cancel");
  if (!cancelBtn) return;
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
      toast("info", "Click again to cancel this download");
      armTimer = setTimeout(disarm, 3000);
      return;
    }
    disarm();
    bridge.removeTorrent(hash, false, () => {});
  });
  cancelBtn.addEventListener("blur", disarm);
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

function todayStamp() {
  const d = new Date();
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}
export function loadCompletedToday() {
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

export function connectDownloadsSignals() {
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
}

export function loadDownloads() {
  bridge.getDownloads((payload) => {
    try {
      const items = JSON.parse(payload || "[]");
      renderDownloads(items);
      if (items.some(isActive) && state.view === "search") {
        switchView("downloads");
      }
    } catch (e) {}
  });
}

export function bindDownloadsEvents() {
  els.changeFolderBtn.addEventListener("click", () => bridge.pickSaveFolder(() => {}));
  els.addTorrentBtn.addEventListener("click", () => bridge.pickAndAddTorrentFile(() => {}));

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

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".dl-kebab-wrap")) closeAllKebabs(null);
  });
}
