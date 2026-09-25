/* dashboard.js - fills the dashboard using data from the Flask API (nothing is hard-coded). */

(function () {
  const $ = function (id) { return document.getElementById(id); };
  const KEYS = ["lower", "moderate", "higher"];

  function verificationBadge(status) {
    status = status || "Newly Added";
    let cls = "bg-secondary";
    if (status === "Verified") cls = "bg-success";
    else if (status === "Contacted") cls = "bg-primary";
    else if (status === "Information Partially Verified") cls = "bg-warning text-dark";
    else if (status === "Newly Added") cls = "bg-info text-dark";
    else if (status === "Unable to Reach" || status === "Inactive") cls = "bg-danger";

    return '<span class="badge ' + cls + '">' + escapeHtml(status) + '</span>';
  }

  function renderStats(stats) {
    $("statAreas").textContent = formatNumber(stats.total_areas);
    $("statAreasNote").textContent =
      stats.sample_records + " sample, " + stats.user_records + " added by users";
    $("statFamilies").textContent = formatNumber(stats.total_families_needing_assistance);
    $("statFamiliesNote").textContent =
      "Population of mapped areas: " + formatNumber(stats.total_population);

    $("statCenters").textContent = formatNumber(stats.total_centers);
    if ($("statCentersVerified")) $("statCentersVerified").textContent = formatNumber(stats.verified_centers || 0);
    if ($("statCentersAwaiting")) $("statCentersAwaiting").textContent = formatNumber(stats.awaiting_contact_centers || 0);

    if ($("fscTotalCount")) $("fscTotalCount").textContent = formatNumber(stats.total_centers);
    if ($("fscVerifiedCount")) $("fscVerifiedCount").textContent = formatNumber(stats.verified_centers || 0);
    if ($("fscAwaitingCount")) $("fscAwaitingCount").textContent = formatNumber(stats.awaiting_contact_centers || 0);
    if ($("fscIncompleteCount")) $("fscIncompleteCount").textContent = formatNumber(stats.incomplete_centers || 0);
    if ($("fscInactiveCount")) $("fscInactiveCount").textContent = formatNumber(stats.inactive_centers || 0);

    const total = stats.total_areas;
    const parts = [];
    KEYS.forEach(function (key) {
      const count = stats.category_counts[key];
      $("count-" + key).textContent = count;
      $("seg-" + key).style.width = (total ? (count / total) * 100 : 0) + "%";
      parts.push(count + " " + CATEGORIES[key].label.toLowerCase());
    });
    $("distBar").setAttribute("aria-label", "Areas by category: " + parts.join(", "));

    const totalFamilies = stats.total_families_needing_assistance;
    $("catTableBody").innerHTML = KEYS.map(function (key) {
      const families = stats.families_by_category[key];
      const share = totalFamilies ? (families / totalFamilies) * 100 : 0;
      return "<tr><td>" + categoryChip(key) + "</td>" +
        '<td class="text-end num">' + stats.category_counts[key] + "</td>" +
        '<td class="text-end num">' + formatNumber(families) + "</td>" +
        '<td class="text-end num">' + share.toFixed(1) + "%</td></tr>";
    }).join("");
  }

  function renderPriority(list) {
    const el = $("priorityList");
    if (!list.length) {
      el.innerHTML = '<li class="text-muted">No areas yet. Add community data to see scores here.</li>';
      return;
    }
    el.innerHTML = list.map(function (c) {
      return "<li>" +
        '<span class="rank-name">' + escapeHtml(c.name) + sampleBadge(c) + "</span>" +
        categoryChip(c.category) +
        '<span class="rank-score" title="Score out of 100">' + c.score.toFixed(1) + "</span>" +
        "</li>";
    }).join("");
  }

  function renderRecent(list) {
    const body = $("recentBody");
    if (!list.length) {
      body.innerHTML = '<tr><td colspan="4" class="empty-row">No community data yet. ' +
        '<a href="/add">Add the first record</a>.</td></tr>';
      return;
    }
    body.innerHTML = list.map(function (c) {
      return "<tr>" +
        "<td>" + escapeHtml(c.name) + sampleBadge(c) +
          '<div class="small text-muted">Added ' + escapeHtml(formatDate(c.created_at)) + "</div></td>" +
        '<td class="text-end num">' + formatNumber(c.population) + "</td>" +
        '<td class="text-end num">' + formatNumber(c.families_needing_assistance) + "</td>" +
        "<td>" + categoryChip(c.category) + "</td>" +
        "</tr>";
    }).join("");
  }

  function renderRecentCenters(list) {
    const body = $("recentCentersBody");
    if (!body) return;
    if (!list || !list.length) {
      body.innerHTML = '<tr><td colspan="4" class="empty-row">No food-support centers registered yet. ' +
        '<a href="/centers/add?mode=quick">Quick add the first center</a>.</td></tr>';
      return;
    }

    body.innerHTML = list.map(function (k) {
      const name = k.center_name || k.name;
      return "<tr>" +
        "<td>" +
          '<a href="/centers/' + k.id + '" class="fw-medium text-decoration-none">' +
            escapeHtml(name) +
          '</a>' + sampleBadge(k) +
          '<div class="small text-muted">' + escapeHtml(k.phone_number || "No phone") + '</div>' +
        "</td>" +
        '<td><span class="badge bg-light text-primary border">' + escapeHtml(k.center_type || "NGO") + '</span></td>' +
        '<td>' + escapeHtml(k.community_name || "Unassigned") + '</td>' +
        '<td>' + verificationBadge(k.information_status) + '</td>' +
        "</tr>";
    }).join("");
  }

  function renderMethod(method) {
    $("methodList").innerHTML = method.indicators.map(function (item) {
      return "<li><strong>" + escapeHtml(item.label) + "</strong> (weight " +
        Math.round(item.weight * 100) + "%). " + escapeHtml(item.rule) + "</li>";
    }).join("") +
      "<li>" + escapeHtml(method.thresholds.text) + "</li>";
    $("methodNote").textContent = method.disclaimer;
  }

  async function init() {
    try {
      const stats = await apiFetch("/api/stats");
      renderStats(stats);
      renderPriority(stats.highest_scores);
      renderRecent(stats.recent);
      renderRecentCenters(stats.recent_centers);
    } catch (err) {
      showLoadError("Could not load dashboard figures. " + err.message);
    }

    try {
      const analysis = await apiFetch("/api/analysis");
      renderMethod(analysis.method);
    } catch (err) {
      $("methodList").innerHTML = '<li class="text-muted">Method details could not be loaded.</li>';
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
