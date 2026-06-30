/* util.js — pure helpers reusable across modules.
 *
 * Today main.js still defines these helpers inside its IIFE; this module
 * mirrors them so callers can import without reaching into the closure.
 * Eventually the IIFE copies in main.js should be removed and replaced by
 * imports from this file.
 */

export function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
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

const MAGNET_RE = /^magnet:\?xt=urn:btih:[a-fA-F0-9]{32,40}/;
const TORRENT_URL_RE = /^https?:\/\/.+\.torrent(\?.*)?$/i;
const INFOHASH_RE = /^[a-fA-F0-9]{40}$/;

export function detectTorrentInput(raw) {
  const v = (raw || "").trim();
  if (!v) return null;
  if (MAGNET_RE.test(v)) return { kind: "magnet", value: v };
  if (TORRENT_URL_RE.test(v)) return { kind: "url", value: v };
  if (INFOHASH_RE.test(v)) return { kind: "magnet", value: `magnet:?xt=urn:btih:${v}` };
  return null;
}

export function arrayBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
