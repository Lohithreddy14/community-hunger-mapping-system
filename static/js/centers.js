/* centers.js - lists the food-support centers returned by the Flask API. */

(function () {
  function card(center) {
    return '<div class="col-12 col-md-6 col-xl-4">' +
      '<article class="panel center-card">' +
        "<h2>" + escapeHtml(center.name) + "</h2>" +
        "<div>" + (center.is_sample ? '<span class="badge-sample">Sample data</span>' : "") + "</div>" +
        '<div class="center-loc">' + escapeHtml(center.location) + "</div>" +
        '<div class="center-coords">Latitude ' + Number(center.latitude).toFixed(4) +
          ", longitude " + Number(center.longitude).toFixed(4) + "</div>" +
        "<p>" + escapeHtml(center.description || "No description provided.") + "</p>" +
        '<a class="center-link" href="/map?center=' + center.id + '">Show on map</a>' +
      "</article></div>";
  }

  async function init() {
    const grid = document.getElementById("centerGrid");
    try {
      const centers = await apiFetch("/api/centers");
      if (!centers.length) {
        grid.innerHTML = '<div class="col-12"><div class="panel empty-row">No food-support centers are stored yet.</div></div>';
        return;
      }
      grid.innerHTML = centers.map(card).join("");
    } catch (err) {
      grid.innerHTML = "";
      showLoadError("Could not load food-support centers. " + err.message);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
