/* state.js — shared UI state factory.
 *
 * Returns a fresh state object mirroring the one constructed inside main.js.
 * main.js still owns the active state instance today; future refactors that
 * pull search/downloads rendering out of main.js should import this factory
 * to keep field names consistent.
 */

export function createState() {
  return {
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
    theme: "swarm",
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
  };
}
