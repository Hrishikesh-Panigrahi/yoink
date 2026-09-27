import { bridge, state } from "./state.js";
import { els } from "./dom.js";
import { escapeHtml } from "./util.js";
import { addFromResult } from "./add.js";

export function openDetailsModal(result) {
  const key = result.magnet || result.infoHash || result.title;
  const meta = state.metadataByKey.get(key);
  els.detailsTitle.textContent = (meta && meta.title) || result.title || "";
  els.detailsYear.textContent = (meta && meta.year) ? meta.year : (result.year || "");
  els.detailsRuntime.textContent = (meta && meta.runtime)
    ? `${Math.floor(meta.runtime / 60)}h ${meta.runtime % 60}m`
    : "";
  if (meta && meta.rating > 0) {
    els.detailsRating.textContent = `\u2605 ${meta.rating.toFixed(1)}`;
    els.detailsRating.hidden = false;
  } else {
    els.detailsRating.textContent = "";
  }
  els.detailsGenres.innerHTML = "";
  ((meta && meta.genres) || []).forEach((g) => {
    const span = document.createElement("span");
    span.className = "details-chip";
    span.textContent = g;
    els.detailsGenres.appendChild(span);
  });
  els.detailsPlot.textContent = (meta && meta.plot) || result.summary || "No plot available yet.";
  els.detailsPoster.src = (meta && meta.poster) || result.cover || "";
  els.detailsPoster.alt = result.title;
  if (meta && meta.backdrop) {
    els.detailsBackdropImg.style.backgroundImage = `url("${meta.backdrop}")`;
    els.detailsBackdropImg.hidden = false;
  } else {
    els.detailsBackdropImg.hidden = true;
    els.detailsBackdropImg.style.backgroundImage = "";
  }
  if (meta && meta.trailerUrl) {
    els.detailsTrailer.href = meta.trailerUrl;
    els.detailsTrailer.hidden = false;
    els.detailsTrailer.onclick = (e) => {
      e.preventDefault();
      bridge.openExternal(meta.trailerUrl);
    };
  } else {
    els.detailsTrailer.hidden = true;
  }
  if (meta && meta.imdbUrl) {
    els.detailsImdb.href = meta.imdbUrl;
    els.detailsImdb.hidden = false;
    els.detailsImdb.onclick = (e) => {
      e.preventDefault();
      bridge.openExternal(meta.imdbUrl);
    };
  } else {
    els.detailsImdb.hidden = true;
  }

  renderDetailsTorrents(result, meta);
  els.detailsBackdrop.hidden = false;
  setTimeout(() => els.detailsClose && els.detailsClose.focus(), 50);
}

function renderDetailsTorrents(currentResult, meta) {
  els.detailsTorrents.innerHTML = "";
  const tmdbId = meta && meta.tmdbId;
  let group = [];
  if (tmdbId) {
    group = state.results.filter((r) => {
      const k = r.magnet || r.infoHash || r.title;
      const m = state.metadataByKey.get(k);
      return m && m.tmdbId === tmdbId;
    });
  }
  if (!group.length) group = [currentResult];

  group
    .slice()
    .sort((a, b) => (b.seeds || 0) - (a.seeds || 0))
    .forEach((r) => {
      const row = document.createElement("div");
      row.className = "details-torrent";
      row.setAttribute("role", "listitem");
      row.innerHTML = `
        <div class="dt-meta">
          <span class="dt-quality">${escapeHtml(r.quality || "?")}</span>
          <span class="dt-source">${escapeHtml(r.source || "")}</span>
          <span class="dt-size">${escapeHtml(r.size || "?")}</span>
          <span class="dt-seeds">${r.seeds ?? 0} seeders</span>
        </div>
        <button type="button" class="btn btn-primary dt-action">Download</button>
      `;
      row.querySelector(".dt-action").addEventListener("click", () => {
        addFromResult(r, row.querySelector(".dt-action"));
      });
      els.detailsTorrents.appendChild(row);
    });
}

export function closeDetailsModal() {
  els.detailsBackdrop.hidden = true;
}

export function bindDetailsEvents() {
  if (els.detailsClose) els.detailsClose.addEventListener("click", closeDetailsModal);
  if (els.detailsBackdrop) {
    els.detailsBackdrop.addEventListener("click", (e) => {
      if (e.target === els.detailsBackdrop) closeDetailsModal();
    });
  }
}
