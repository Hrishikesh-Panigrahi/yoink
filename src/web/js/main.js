/* Only sets the boot order: cache elements, restore local preferences, bind the UI,
 * then connect to Python and load the initial state. Each feature module wires its
 * own DOM events (bind*Events) and bridge signals (connect*Signals). */

import { setBridge } from "./state.js";
import { cacheEls } from "./dom.js";
import { bindThemeEvents, initTheme } from "./theme.js";
import { bindSidebarEvents } from "./sidebar.js";
import { bindResultsEvents, connectResultsSignals, initViewMode } from "./results.js";
import { connectStreamSignals, loadPlayerStatus } from "./stream.js";
import { bindDetailsEvents } from "./details.js";
import { bindSearchEvents, connectSearchSignals, loadFilters, loadSearchHistory } from "./search.js";
import {
  bindSettingsEvents,
  connectSettingsSignals,
  loadAboutInfo,
  loadFeeds,
  loadProxy,
  loadSaveFolder,
  loadSchedule,
  loadSettings,
  loadWatchFolder,
} from "./settings.js";
import { bindSourcesEvents, connectSourcesSignals, loadProviderChoices } from "./sources.js";
import { connectAddSignals } from "./add.js";
import { bindDownloadsEvents, connectDownloadsSignals, loadCompletedToday, loadDownloads } from "./downloads.js";
import { connectToastsSignals } from "./toasts.js";
import { bindFilesEvents } from "./files.js";
import { bindOnboardingEvents, maybeShowOnboarding } from "./onboarding.js";
import { bindShortcutsEvents } from "./shortcuts.js";
import { bindPaletteEvents, loadPaletteCommands } from "./palette.js";
import { bindLabelsEvents } from "./labels.js";
import { bindSafetyEvents } from "./safety.js";
import { bindDragDropEvents } from "./dragdrop.js";

function bindEvents() {
  bindSidebarEvents();
  bindSearchEvents();
  bindSafetyEvents();
  bindSettingsEvents();
  bindSourcesEvents();
  bindDragDropEvents();
  bindDownloadsEvents();
  bindThemeEvents();
  bindOnboardingEvents();
  bindDetailsEvents();
  bindFilesEvents();
  bindShortcutsEvents();
  bindResultsEvents();
  bindPaletteEvents();
  bindLabelsEvents();
}

function onBridgeReady(channel) {
  setBridge(channel.objects.bridge);

  connectSearchSignals();
  connectStreamSignals();
  connectSettingsSignals();
  connectSourcesSignals();
  connectResultsSignals();
  connectDownloadsSignals();
  connectToastsSignals();
  connectAddSignals();

  loadSaveFolder();
  loadDownloads();
  loadSettings();
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

document.addEventListener("DOMContentLoaded", init);
