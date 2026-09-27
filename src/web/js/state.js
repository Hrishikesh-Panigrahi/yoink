/* Shared UI state. bridge stays null until QWebChannel connects. */

export let bridge = null;

export function setBridge(value) {
  bridge = value;
}

export const state = {
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
