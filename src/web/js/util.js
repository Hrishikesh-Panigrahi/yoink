/* Small helpers with no DOM or bridge dependencies. */

const MAGNET_RE = /^magnet:\?xt=urn:btih:[a-z0-9]+/i;
const INFOHASH_RE = /^[a-f0-9]{40}$|^[a-z2-7]{32}$/i;
const TORRENT_URL_RE = /^https?:\/\/\S+\.torrent(\?\S*)?$/i;
export function detectTorrentInput(raw) {
  const v = (raw || "").trim();
  if (!v) return null;
  if (MAGNET_RE.test(v)) return { kind: "magnet", value: v };
  if (TORRENT_URL_RE.test(v)) return { kind: "url", value: v };
  if (INFOHASH_RE.test(v)) {
    return { kind: "magnet", value: `magnet:?xt=urn:btih:${v}` };
  }
  return null;
}

export function formatKB(kb) {
  if (kb == null || isNaN(kb)) return "0 KB/s";
  if (kb < 1024) return `${kb.toFixed(1)} KB/s`;
  return `${(kb / 1024).toFixed(2)} MB/s`;
}

export function shortPath(p) {
  if (!p) return "";
  if (p.length <= 28) return p;
  return "..." + p.slice(-25);
}

export function statusClass(status) {
  const s = (status || "").toLowerCase();
  if (s.includes("error")) return "error";
  if (s.includes("paused")) return "paused";
  if (s.includes("seed") || s.includes("finish") || s.includes("complete")) return "seeding";
  if (s.includes("download")) return "downloading";
  if (s.includes("metadata") || s.includes("check")) return "metadata";
  if (s.includes("queue")) return "queued";
  return "unknown";
}

export function isMobile() {
  return window.matchMedia("(max-width: 760px)").matches;
}

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
