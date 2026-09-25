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
  let currentLayer = "both";     // "both", "communities", "centers"

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
        '<div class="legend-title">Map Layers & Legend</div>' +
        '<div class="legend-row"><span class="legend-swatch" style="background:' + CATEGORIES.lower.color + '"></span>Green circle: Lower vulnerability</div>' +
        '<div class="legend-row"><span class="legend-swatch" style="background:' + CATEGORIES.moderate.color + '"></span>Yellow circle: Moderate vulnerability</div>' +
        '<div class="legend-row"><span class="legend-swatch" style="background:' + CATEGORIES.higher.color + '"></span>Red circle: Higher vulnerability</div>' +
        '<div class="legend-row mt-1"><span class="center-pin-sm" style="background:#1d7a58;">F</span>Verified Food Center</div>' +
        '<div class="legend-row"><span class="center-pin-sm" style="background:#2769ad;">F</span>Active Food Center</div>' +
        '<div class="legend-row"><span class="center-pin-sm" style="background:#6c757d;">F</span>Provisional Community Reference</div>' +
        '<div class="legend-note">Larger circles mean more families needing assistance. Square pins indicate food support centers.</div>';
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
      '<a href="/communities?view=' + c.id + '" class="btn btn-sm btn-outline-primary py-0 px-2" style="font-size:0.8rem;">See score breakdown</a>' +
      "</div>";
  }

  function centerPopup(k) {
    const name = escapeHtml(k.center_name || k.name);
    const comm = escapeHtml(k.community_name || "Unassigned");
    const type = escapeHtml(k.center_type || "NGO");
    const phone = k.phone_number
      ? '<a href="tel:' + escapeHtml(k.phone_number) + '">' + escapeHtml(k.phone_number) + '</a>'
      : "Not provided";
    const status = escapeHtml(k.information_status || "Newly Added");
    const isProvisional = k.location_source === "community_reference";

    let locNotice = "";
    if (isProvisional) {
      locNotice = '<div class="alert alert-warning py-1 px-2 my-1" style="font-size:0.75rem;">' +
        '<strong>Provisional Community Location:</strong> Coordinates reference the ' + comm + ' area. Exact facility location has not yet been pinpointed.</div>';
    } else if (k.distance_to_community_km !== null && k.distance_to_community_km !== undefined) {
      locNotice = '<div class="text-muted small mb-1">Pinpointed location &bull; approx. ' + k.distance_to_community_km + ' km from ' + comm + '</div>';
    }

    return '<div class="popup">' +
      '<div class="popup-title">' + name + "</div>" +
      '<div class="popup-tags">' +
        '<span class="badge bg-primary me-1">' + type + '</span>' +
        '<span class="badge bg-secondary me-1">' + status + '</span>' +
        sampleBadge(k) +
      "</div>" +
      locNotice +
      "<dl>" +
        "<dt>Community</dt><dd>" + comm + "</dd>" +
        "<dt>Phone</dt><dd>" + phone + "</dd>" +
        "<dt>Address</dt><dd>" + escapeHtml(k.address || k.location || "Not provided") + "</dd>" +
        "<dt>Coordinates</dt><dd>" + formatCoords(k.latitude, k.longitude) + "</dd>" +
      "</dl>" +
      (k.description ? '<div class="popup-note">' + escapeHtml(k.description) + "</div>" : "") +
      '<div class="mt-2 pt-2 border-top d-flex justify-content-between">' +
        '<a href="/centers/' + k.id + '" class="btn btn-sm btn-primary py-0 px-2" style="font-size:0.8rem;">View Center Details</a>' +
      '</div>' +
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

    updateCountAndList(visible);
  }

  function drawCenters() {
    centerLayer.clearLayers();
    Object.keys(centerMarkers).forEach(function (id) { delete centerMarkers[id]; });

    centers.forEach(function (k) {
      const isProv = k.location_source === "community_reference";
      const isVer = k.information_status === "Verified";
      const bg = isVer ? "#1d7a58" : (isProv ? "#6c757d" : "#2769ad");

      const icon = L.divIcon({
        className: "",
        html: '<div class="center-pin" style="background:' + bg + ';" aria-hidden="true" title="' + escapeHtml(k.center_name || k.name) + '">F</div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12]
      });
      const marker = L.marker([k.latitude, k.longitude], { icon: icon, title: k.center_name || k.name });
      marker.bindPopup(centerPopup(k), { maxWidth: 320 });
      marker.addTo(centerLayer);
      centerMarkers[k.id] = marker;
    });
  }

  function applyLayerFilter() {
    const showComm = currentLayer === "both" || currentLayer === "communities";
    const showCent = currentLayer === "both" || currentLayer === "centers";

    const commGroup = document.getElementById("communityFilterGroup");
    if (commGroup) {
      if (showComm) commGroup.classList.remove("d-none");
      else commGroup.classList.add("d-none");
    }

    if (showComm && !map.hasLayer(communityLayer)) map.addLayer(communityLayer);
    if (!showComm && map.hasLayer(communityLayer)) map.removeLayer(communityLayer);

    if (showCent && !map.hasLayer(centerLayer)) map.addLayer(centerLayer);
    if (!showCent && map.hasLayer(centerLayer)) map.removeLayer(centerLayer);

    const visibleComm = communities.filter(function (c) {
      return currentFilter === "all" || c.category === currentFilter;
    });
    updateCountAndList(visibleComm);
  }

  function updateCountAndList(visibleCommunities) {
    const list = document.getElementById("mapList");
    const countEl = $count();
    const headingEl = document.getElementById("listHeading");

    if (currentLayer === "centers") {
      headingEl.textContent = "Food centers shown (" + centers.length + ")";
      countEl.textContent = "Showing " + centers.length + " food-support centers";

      if (!centers.length) {
        list.innerHTML = '<li class="text-muted small">No food-support centers available.</li>';
        return;
      }

      list.innerHTML = centers.map(function (k) {
        const isVer = k.information_status === "Verified";
        const isProv = k.location_source === "community_reference";
        const dotBg = isVer ? "#1d7a58" : (isProv ? "#6c757d" : "#2769ad");

        return '<li><button type="button" data-center-id="' + k.id + '">' +
          '<span class="dot" style="background:' + dotBg + ';"></span>' +
          '<span><span class="map-list-name">' + escapeHtml(k.center_name || k.name) + '</span><br>' +
          '<span class="map-list-meta">' + escapeHtml(k.center_type || "NGO") + ' &bull; ' +
          escapeHtml(k.community_name || "Unassigned") + (isProv ? " (Provisional)" : "") +
          '</span></span></button></li>';
      }).join("");

    } else if (currentLayer === "communities") {
      headingEl.textContent = "Communities shown (" + visibleCommunities.length + ")";
      countEl.textContent = "Showing " + visibleCommunities.length + " of " + communities.length + " communities";

      if (!visibleCommunities.length) {
        list.innerHTML = '<li class="text-muted small">No communities in this category.</li>';
        return;
      }

      const sorted = visibleCommunities.slice().sort(function (a, b) { return b.score - a.score; });
      list.innerHTML = sorted.map(function (c) {
        return '<li><button type="button" data-id="' + c.id + '">' +
          '<span class="dot dot-' + c.category + '"></span>' +
          '<span><span class="map-list-name">' + escapeHtml(c.name) + '</span><br>' +
          '<span class="map-list-meta">' + formatNumber(c.families_needing_assistance) +
          ' families, score ' + c.score.toFixed(1) + '</span></span></button></li>';
      }).join("");

    } else {
      // Both
      headingEl.textContent = "Locations shown (" + (visibleCommunities.length + centers.length) + ")";
      countEl.textContent = visibleCommunities.length + " communities & " + centers.length + " centers";

      const commItems = visibleCommunities.slice().sort(function (a, b) { return b.score - a.score; }).map(function (c) {
        return '<li><button type="button" data-id="' + c.id + '">' +
          '<span class="dot dot-' + c.category + '"></span>' +
          '<span><span class="map-list-name">' + escapeHtml(c.name) + '</span><br>' +
          '<span class="map-list-meta">' + formatNumber(c.families_needing_assistance) +
          ' families, score ' + c.score.toFixed(1) + '</span></span></button></li>';
      });

      const centItems = centers.map(function (k) {
        const isVer = k.information_status === "Verified";
        const dotBg = isVer ? "#1d7a58" : "#2769ad";
        return '<li><button type="button" data-center-id="' + k.id + '">' +
          '<span class="dot" style="background:' + dotBg + '; border-radius: 2px;"></span>' +
          '<span><span class="map-list-name">' + escapeHtml(k.center_name || k.name) + '</span><br>' +
          '<span class="map-list-meta">Food Center &bull; ' + escapeHtml(k.community_name || "Unassigned") + '</span></span></button></li>';
      });

      list.innerHTML = commItems.concat(centItems).join("");
    }
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
    if (currentLayer === "communities") {
      currentLayer = "both";
      const rad = document.getElementById("l-both");
      if (rad) rad.checked = true;
      applyLayerFilter();
    }
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 14));
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

    // Layer filter radio change
    document.querySelectorAll('input[name="layerFilter"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        currentLayer = radio.value;
        applyLayerFilter();
      });
    });

    // Category filter radio change
    document.querySelectorAll('input[name="categoryFilter"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        currentFilter = radio.value;
        drawCommunities();
      });
    });

    // List click navigation
    document.getElementById("mapList").addEventListener("click", function (event) {
      const commBtn = event.target.closest("button[data-id]");
      if (commBtn) {
        focusCommunity(Number(commBtn.dataset.id));
        return;
      }
      const centBtn = event.target.closest("button[data-center-id]");
      if (centBtn) {
        focusCenter(Number(centBtn.dataset.centerId));
      }
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
    applyLayerFilter();
    fitToData();

    // Deep link query params
    const params = new URLSearchParams(window.location.search);
    if (params.get("focus")) {
      focusCommunity(Number(params.get("focus")));
    } else if (params.get("center")) {
      focusCenter(Number(params.get("center")));
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
