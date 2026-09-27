/* Playing a file while it is still downloading. */

import { bridge, state } from "./state.js";
import { toast } from "./toasts.js";

export function startStreamFromResult(r, btn) {
  if (state.streamingKey) {
    toast("info", "Already preparing a stream - one at a time.");
    return;
  }
  state.streamingKey = r.magnet;
  state.streamingPhase = "";
  btn.disabled = true;
  btn.classList.add("is-busy");
  btn.title = "Starting...";
  toast("info", "Preparing stream - this needs a few seconds of the file first.");
  bridge.playFromMagnet(r.magnet, (raw) => {
    let payload = {};
    try { payload = JSON.parse(raw || "{}"); } catch (e) {}
    if (!payload.hash) {
      // The bridge already showed a toast.
      resetStreamButton(btn);
      return;
    }
    state.streamingHash = payload.hash;
  });
}

function resetStreamButton(btn) {
  state.streamingKey = null;
  state.streamingHash = null;
  state.streamingPhase = "";
  btn.disabled = false;
  btn.classList.remove("is-busy");
  btn.title = "Stream now, without waiting for the download";
}

function currentStreamButton() {
  if (!state.streamingKey) return null;
  const entry = state.rowsByKey.get(state.streamingKey);
  return entry ? entry.node.querySelector(".result-play") : null;
}

// Show the button only if a player exists (checked once at startup) and the
// torrent holds a video. That needs metadata, which arrives after the row, so
// ask once per row and cache the answer on the node.
export function updatePlayButton(btn, node, t) {
  if (!state.playerAvailable) {
    btn.hidden = true;
    return;
  }
  const cached = node.dataset.playable;
  if (cached === "1" || cached === "0") {
    btn.hidden = cached !== "1";
    return;
  }
  btn.hidden = true;
  const metadataReady = !/metadata/i.test(t.status || "") && Boolean(t.name);
  if (!metadataReady || node.dataset.playablePending === "1") return;
  node.dataset.playablePending = "1";
  bridge.getPlayableFile(t.hash, (index) => {
    node.dataset.playablePending = "";
    node.dataset.playable = index >= 0 ? "1" : "0";
    btn.hidden = index < 0;
  });
}

export function loadPlayerStatus() {
  if (!bridge || !bridge.getPlayerStatus) return;
  bridge.getPlayerStatus((raw) => {
    try {
      const info = JSON.parse(raw || "{}");
      state.playerAvailable = Boolean(info.available);
      if (!info.available && info.reason) {
        console.info(`In-app player unavailable: ${info.reason}`);
      }
    } catch (e) {}
  });
}

export function connectStreamSignals() {
  if (bridge.streamProgress) {
    bridge.streamProgress.connect((payloadStr) => {
      let info = {};
      try { info = JSON.parse(payloadStr || "{}"); } catch (e) { return; }
      const btn = currentStreamButton();
      if (info.phase === "failed") {
        if (btn) resetStreamButton(btn);
        return;
      }
      // Progress goes in the tooltip so the row never changes width. Toast only
      // when the phase changes, not on every poll.
      if (btn && info.message) btn.title = info.message;
      if (info.phase && info.phase !== state.streamingPhase) {
        state.streamingPhase = info.phase;
        if (info.phase === "buffering") toast("info", "Got the file list - buffering the start.");
      }
      // The player window opens by itself once the start is buffered. Reset the
      // button so the same result can be played again.
      if (info.phase === "buffering" && (info.bufferProgress || 0) >= 100 && btn) {
        resetStreamButton(btn);
      }
    });
  }
}
