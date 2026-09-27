/* Cached element references. cacheEls() runs once, before any module binds events. */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

export const els = {};
export function cacheEls() {
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
  els.proxyFindBtn = $("#proxyFindBtn");

  els.scheduleEnabled = $("#scheduleEnabled");
  els.scheduleStart = $("#scheduleStart");
  els.scheduleEnd = $("#scheduleEnd");
  els.scheduleDown = $("#scheduleDown");
  els.scheduleUp = $("#scheduleUp");
  els.scheduleSaveBtn = $("#scheduleSaveBtn");
}
