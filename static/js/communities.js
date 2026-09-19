/* communities.js - community records table with search, filter, details, edit link and delete. */

(function () {
  const $ = function (id) { return document.getElementById(id); };

  let records = [];
  let pendingDelete = null;
  let detailModal;
  let deleteModal;

  function showMessage(type, text) {
    const box = $("actionMessage");
    box.className = "alert alert-" + type;
    box.textContent = text;
  }

  /* ---------- Table ---------- */
  function filteredRecords() {
    const query = $("searchBox").value.trim().toLowerCase();
    const category = $("categorySelect").value;
    return records.filter(function (c) {
      return (category === "all" || c.category === category) &&
             (query === "" || c.name.toLowerCase().indexOf(query) !== -1);
    });
  }

  function renderTable() {
    const rows = filteredRecords();
    const body = $("communityBody");
    $("rowCount").textContent = "Showing " + rows.length + " of " + records.length + " records";

    if (!records.length) {
      body.innerHTML = '<tr><td colspan="6" class="empty-row">No community records yet. ' +
        '<a href="/add">Add the first record</a>.</td></tr>';
      return;
    }
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="6" class="empty-row">No records match your search or filter.</td></tr>';
      return;
    }

    body.innerHTML = rows.map(function (c) {
      return "<tr>" +
        "<td>" + escapeHtml(c.name) + sampleBadge(c) + "</td>" +
        '<td class="text-end num">' + formatNumber(c.population) + "</td>" +
        '<td class="text-end num">' + formatNumber(c.families_needing_assistance) + "</td>" +
        "<td>" + categoryChip(c.category) +
          ' <span class="small text-muted num">' + c.score.toFixed(1) + "</span></td>" +
        '<td class="coords">' + formatCoords(c.latitude, c.longitude) + "</td>" +
        '<td class="text-end"><span class="row-actions">' +
          '<button type="button" class="btn btn-outline-primary btn-sm" data-action="view" data-id="' + c.id + '">View</button>' +
          '<a class="btn btn-outline-secondary btn-sm" href="/edit/' + c.id + '">Edit</a>' +
          '<button type="button" class="btn btn-outline-danger btn-sm" data-action="delete" data-id="' + c.id + '">Delete</button>' +
        "</span></td></tr>";
    }).join("");
  }

  /* ---------- Details window ---------- */
  function detailItem(label, value) {
    return "<div><dt>" + escapeHtml(label) + "</dt><dd>" + value + "</dd></div>";
  }

  function openDetails(id) {
    const c = records.find(function (r) { return r.id === id; });
    if (!c) return;
    const a = c.analysis;

    $("detailTitle").innerHTML = escapeHtml(c.name) + sampleBadge(c);
    $("detailMapLink").href = "/map?focus=" + c.id;
    $("detailEditLink").href = "/edit/" + c.id;

    const nearest = a.nearest_center
      ? escapeHtml(a.nearest_center.name) + " (" + a.nearest_center.distance_km + " km)"
      : "None listed";

    $("detailBody").innerHTML =
      '<p class="mb-3">' + categoryChip(c.category) + ' <span class="ms-1">' +
        escapeHtml(CATEGORIES[c.category].full) + ", score " + c.score.toFixed(1) + " out of 100.</span></p>" +
      '<dl class="detail-grid">' +
        detailItem("Population", formatNumber(c.population)) +
        detailItem("Total families", c.total_families !== null ? formatNumber(c.total_families)
          : "Not provided (about " + formatNumber(a.households) + " estimated)") +
        detailItem("Families needing assistance", formatNumber(c.families_needing_assistance) +
          " (" + a.pct_need.toFixed(1) + "%)") +
        detailItem("Food accessibility", escapeHtml(c.food_accessibility || "Not provided")) +
        detailItem("Nearby centers (reported)", c.nearby_centers !== null ? c.nearby_centers : "Not provided") +
        detailItem("Average household income", c.avg_household_income !== null
          ? "Rs. " + formatNumber(c.avg_household_income) + " per month" : "Not provided") +
        detailItem("Coordinates", formatCoords(c.latitude, c.longitude)) +
        detailItem("Nearest listed center", nearest) +
        detailItem("Added", escapeHtml(formatDate(c.created_at))) +
      "</dl>" +
      (c.notes ? '<p class="mb-3"><strong>Notes:</strong> ' + escapeHtml(c.notes) + "</p>" : "") +
      '<h3 class="fs-6">How the score was calculated</h3>' +
      renderBreakdown(a) +
      '<p class="small text-muted mb-0">' + a.indicators_used + " of " + a.indicators_total +
        " indicators were available. Missing indicators are skipped and the remaining weights are re-scaled. " +
        "This is a preliminary academic estimate, not a measurement of hunger.</p>";

    detailModal.show();
  }

  /* ---------- Delete ---------- */
  function askDelete(id) {
    const c = records.find(function (r) { return r.id === id; });
    if (!c) return;
    pendingDelete = c;
    $("deleteText").textContent = 'You are about to delete "' + c.name +
      '". It will be removed from the database, the dashboard and the map. This cannot be undone.';
    deleteModal.show();
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const target = pendingDelete;
    const button = $("confirmDelete");
    button.disabled = true;
    try {
      await apiFetch("/api/communities/" + target.id, { method: "DELETE" });
      records = records.filter(function (r) { return r.id !== target.id; });
      renderTable();
      showMessage("success", '"' + target.name + '" was deleted.');
    } catch (err) {
      showMessage("danger", "Could not delete the record. " + err.message);
    } finally {
      button.disabled = false;
      pendingDelete = null;
      deleteModal.hide();
    }
  }

  /* ---------- Start-up ---------- */
  async function init() {
    detailModal = new bootstrap.Modal($("detailModal"));
    deleteModal = new bootstrap.Modal($("deleteModal"));

    $("searchBox").addEventListener("input", renderTable);
    $("categorySelect").addEventListener("change", renderTable);
    $("confirmDelete").addEventListener("click", confirmDelete);
    $("communityBody").addEventListener("click", function (event) {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const id = Number(button.dataset.id);
      if (button.dataset.action === "view") openDetails(id);
      if (button.dataset.action === "delete") askDelete(id);
    });

    try {
      records = await apiFetch("/api/communities");
    } catch (err) {
      showLoadError("Could not load community records. " + err.message);
      $("communityBody").innerHTML = '<tr><td colspan="6" class="empty-row">Records unavailable.</td></tr>';
      return;
    }
    renderTable();

    // Deep link from the map: /communities?view=<id>
    const view = new URLSearchParams(window.location.search).get("view");
    if (view) openDetails(Number(view));
  }

  document.addEventListener("DOMContentLoaded", init);
})();
