/* map.js - Leaflet map of communities and food-support centers, loaded from the Flask API. */

(function () {
  const DEFAULT_VIEW = [12.97, 77.59];   // used only if the database has no records

  let map;
  let communities = [];
  let centers = [];
  const communityLayer = L.layerGroup();
  const centerLayer = L.layerGroup();
  const communityMarkers = {};   // community id -> Leaflet marker
  const centerMarkers = {};      // center id -> Leaflet marker
  let currentFilter = "all";

  function buildMap() {
    map = L.map("map").setView(DEFAULT_VIEW, 11);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    communityLayer.addTo(map);
    centerLayer.addTo(map);
    addLegend();
  }

  function addLegend() {
    const legend = L.control({ position: "bottomright" });
    legend.onAdd = function () {
      const div = L.DomUtil.create("div", "map-legend");
      div.innerHTML =
        '<div class="legend-title">Estimated vulnerability</div>' +
        '<div class="legend-row"><span class="legend-swatch" style="background:' + CATEGORIES.lower.color + '"></span>Green: lower</div>' +
        '<div class="legend-row"><span class="legend-swatch" style="background:' + CATEGORIES.moderate.color + '"></span>Yellow: moderate</div>' +
        '<div class="legend-row"><span class="legend-swatch" style="background:' + CATEGORIES.higher.color + '"></span>Red: higher</div>' +
        '<div class="legend-row mt-1"><span class="legend-square"></span>Food-support center</div>' +
        '<div class="legend-note">Larger circles mean more families reported as needing assistance. Colors come from the preliminary scoring model.</div>';
      L.DomEvent.disableClickPropagation(div);
      return div;
    };
    legend.addTo(map);
  }

  /* ---------- Popups ---------- */
  function communityPopup(c) {
    const a = c.analysis;
    const basis = a.households_basis === "estimated" ? "estimated" : "reported";
    const nearest = a.nearest_center
      ? escapeHtml(a.nearest_center.name) + ", " + a.nearest_center.distance_km + " km"
      : "None listed";
    const income = c.avg_household_income !== null
      ? "Rs. " + formatNumber(c.avg_household_income) + " / month" : "Not provided";

    return '<div class="popup">' +
      '<div class="popup-title">' + escapeHtml(c.name) + "</div>" +
      '<div class="popup-tags">' + categoryChip(c.category) +
        '<span class="text-muted">Score ' + c.score.toFixed(1) + " / 100</span>" + sampleBadge(c) + "</div>" +
      "<dl>" +
        "<dt>Families needing assistance</dt><dd>" + formatNumber(c.families_needing_assistance) +
          " (" + a.pct_need.toFixed(1) + "%)</dd>" +
        "<dt>Population</dt><dd>" + formatNumber(c.population) + "</dd>" +
        "<dt>Food accessibility</dt><dd>" + escapeHtml(c.food_accessibility || "Not provided") + "</dd>" +
        "<dt>Nearby centers (reported)</dt><dd>" +
          (c.nearby_centers !== null ? c.nearby_centers : "Not provided") + "</dd>" +
        "<dt>Household income</dt><dd>" + escapeHtml(income) + "</dd>" +
        "<dt>Nearest listed center</dt><dd>" + nearest + "</dd>" +
      "</dl>" +
      '<div class="popup-note">Family share is based on ' + basis + " total families. " +
        a.indicators_used + " of " + a.indicators_total + " indicators available.</div>" +
      '<a href="/communities?view=' + c.id + '">See score breakdown</a>' +
      "</div>";
  }

  function centerPopup(k) {
    return '<div class="popup">' +
      '<div class="popup-title">' + escapeHtml(k.name) + "</div>" +
      '<div class="popup-tags"><span class="text-muted">Food-support center</span>' + sampleBadge(k) + "</div>" +
      "<dl><dt>Location</dt><dd>" + escapeHtml(k.location) + "</dd>" +
      "<dt>Coordinates</dt><dd>" + formatCoords(k.latitude, k.longitude) + "</dd></dl>" +
      (k.description ? '<div class="popup-note">' + escapeHtml(k.description) + "</div>" : "") +
      "</div>";
  }

  /* ---------- Drawing ---------- */
  function markerRadius(c) {
    return 8 + Math.min(Math.sqrt(c.families_needing_assistance) / 2, 10);
  }

  function drawCommunities() {
    communityLayer.clearLayers();
    Object.keys(communityMarkers).forEach(function (id) { delete communityMarkers[id]; });

    const visible = communities.filter(function (c) {
      return currentFilter === "all" || c.category === currentFilter;
    });

    visible.forEach(function (c) {
      const marker = L.circleMarker([c.latitude, c.longitude], {
        radius: markerRadius(c),
        color: "#ffffff",
        weight: 2,
        fillColor: CATEGORIES[c.category].color,
        fillOpacity: 0.92
      });
      marker.bindPopup(communityPopup(c), { maxWidth: 320 });
      marker.bindTooltip(c.name);
      marker.addTo(communityLayer);
      communityMarkers[c.id] = marker;
    });

    $count().textContent = "Showing " + visible.length + " of " + communities.length + " communities";
    drawList(visible);
  }

  function drawCenters() {
    centerLayer.clearLayers();
    centers.forEach(function (k) {
      const icon = L.divIcon({
        className: "",
        html: '<div class="center-pin" aria-hidden="true">F</div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12]
      });
      const marker = L.marker([k.latitude, k.longitude], { icon: icon, title: k.name });
      marker.bindPopup(centerPopup(k), { maxWidth: 300 });
      marker.addTo(centerLayer);
      centerMarkers[k.id] = marker;
    });
    applyCenterToggle();
  }

  function applyCenterToggle() {
    const show = document.getElementById("toggleCenters").checked;
    if (show && !map.hasLayer(centerLayer)) map.addLayer(centerLayer);
    if (!show && map.hasLayer(centerLayer)) map.removeLayer(centerLayer);
  }

  function drawList(visible) {
    const list = document.getElementById("mapList");
    if (!visible.length) {
      list.innerHTML = '<li class="text-muted small">No communities in this category.</li>';
      return;
    }
    const sorted = visible.slice().sort(function (a, b) { return b.score - a.score; });
    list.innerHTML = sorted.map(function (c) {
      return '<li><button type="button" data-id="' + c.id + '">' +
        '<span class="dot dot-' + c.category + '"></span>' +
        "<span><span class=\"map-list-name\">" + escapeHtml(c.name) + "</span><br>" +
        '<span class="map-list-meta">' + formatNumber(c.families_needing_assistance) +
        " families, score " + c.score.toFixed(1) + "</span></span></button></li>";
    }).join("");
  }

  function $count() { return document.getElementById("filterCount"); }

  /* ---------- Focus helpers ---------- */
  function focusCommunity(id) {
    const marker = communityMarkers[id];
    if (!marker) return false;
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 13));
    marker.openPopup();
    return true;
  }

  function focusCenter(id) {
    const marker = centerMarkers[id];
    if (!marker) return false;
    if (!map.hasLayer(centerLayer)) {
      document.getElementById("toggleCenters").checked = true;
      applyCenterToggle();
    }
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 13));
    marker.openPopup();
    return true;
  }

  function fitToData() {
    const points = communities.map(function (c) { return [c.latitude, c.longitude]; })
      .concat(centers.map(function (k) { return [k.latitude, k.longitude]; }));
    if (points.length) {
      map.fitBounds(L.latLngBounds(points).pad(0.15), { maxZoom: 14 });
    }
  }

  /* ---------- Start-up ---------- */
  async function init() {
    buildMap();

    document.querySelectorAll('input[name="categoryFilter"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        currentFilter = radio.value;
        drawCommunities();
      });
    });
    document.getElementById("toggleCenters").addEventListener("change", applyCenterToggle);
    document.getElementById("mapList").addEventListener("click", function (event) {
      const button = event.target.closest("button[data-id]");
      if (button) focusCommunity(Number(button.dataset.id));
    });

    try {
      const results = await Promise.all([apiFetch("/api/communities"), apiFetch("/api/centers")]);
      communities = results[0];
      centers = results[1];
    } catch (err) {
      showLoadError("Could not load map data. " + err.message);
      $count().textContent = "Map data unavailable";
      return;
    }

    drawCenters();
    drawCommunities();
    fitToData();

    // Optional deep links: /map?focus=<community id> or /map?center=<center id>
    const params = new URLSearchParams(window.location.search);
    if (params.get("focus")) focusCommunity(Number(params.get("focus")));
    else if (params.get("center")) focusCenter(Number(params.get("center")));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
