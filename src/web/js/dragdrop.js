import { bridge } from "./state.js";
import { els } from "./dom.js";
import { detectTorrentInput } from "./util.js";
import { toast } from "./toasts.js";
import { switchView } from "./sidebar.js";
import { addByDetection } from "./search.js";
import { parseAddResult, showDuplicateToast } from "./add.js";

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

export function bindDragDropEvents() {
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
}
