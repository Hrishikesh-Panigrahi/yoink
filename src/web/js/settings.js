import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { escapeHtml, shortPath } from "./util.js";
import { toast } from "./toasts.js";

export function loadWatchFolder() {
  const raw = localStorage.getItem("yoink.watchFolderCached") || "";
  if (raw) els.watchFolderPath.textContent = raw;
}
export function loadFeeds() {
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
export function loadProxy() {
  if (!bridge || !bridge.getProxy) return;
  bridge.getProxy((raw) => {
    try {
      const p = JSON.parse(raw || "{}");
      els.proxyUrl.value = p.proxyUrl || "";
      els.proxyUa.value = p.userAgent || "";
    } catch (_) {}
  });
}
export function loadSchedule() {
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

export function loadAboutInfo() {
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
    els.settingTmdbKey.placeholder = s.tmdbConfigured ? "key saved, paste a new one to replace it" : "paste TMDB v3 key";
  }
}

export function connectSettingsSignals() {
  bridge.saveFolderChanged.connect(showSaveFolder);

  if (bridge.freeProxyProgress) {
    bridge.freeProxyProgress.connect((raw) => {
      const p = JSON.parse(raw || "{}");
      els.proxyFindBtn.textContent = `Testing ${p.tested} of ${p.total}, ${p.working} working...`;
    });
  }
  if (bridge.freeProxyFound) {
    bridge.freeProxyFound.connect((raw) => {
      const found = JSON.parse(raw || "{}");
      els.proxyFindBtn.disabled = false;
      els.proxyFindBtn.textContent = "Find a free proxy";
      if (!found.proxy) {
        toast("error", "No free proxy answered right now. Try again in a while.");
        return;
      }
      els.proxyUrl.value = found.proxy;
      toast("success", found.reachesBlocked
        ? `Using ${found.proxy} (${found.latency}s). It gets past the block.`
        : `Using ${found.proxy} (${found.latency}s). It works, but blocked sites may still fail.`);
    });
  }

  bridge.settingsChanged.connect((payload) => {
    try { applySettings(JSON.parse(payload)); } catch (e) {}
  });
}

function showSaveFolder(folder) {
  state.saveFolder = folder;
  els.folderText.textContent = shortPath(folder);
  els.folderPill.title = folder;
  els.settingFolderPath.textContent = folder;
  els.settingFolderPath.title = folder;
}

export function loadSaveFolder() {
  bridge.getSaveFolder(showSaveFolder);
}

export function loadSettings() {
  bridge.getSettings((payload) => {
    try { applySettings(JSON.parse(payload)); } catch (e) {}
  });
}

export function bindSettingsEvents() {
  if (els.openDataFolderBtn) {
    els.openDataFolderBtn.addEventListener("click", () => bridge.openDataFolder());
  }

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
      bridge.setProxy(els.proxyUrl.value || "", els.proxyUa.value || "", (error) => {
        if (error) toast("error", error);
        else toast("success", els.proxyUrl.value ? "Searches now go through the proxy" : "Proxy turned off");
      });
    });
  }
  if (els.proxyFindBtn) {
    els.proxyFindBtn.addEventListener("click", () => {
      els.proxyFindBtn.disabled = true;
      els.proxyFindBtn.textContent = "Getting proxy lists...";
      bridge.findFreeProxy();
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
}
