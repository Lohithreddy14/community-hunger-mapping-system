/* dashboard.js - fills the dashboard using data from the Flask API (nothing is hard-coded). */

(function () {
  const $ = function (id) { return document.getElementById(id); };
  const KEYS = ["lower", "moderate", "higher"];

  function renderStats(stats) {
    $("statAreas").textContent = formatNumber(stats.total_areas);
    $("statAreasNote").textContent =
      stats.sample_records + " sample, " + stats.user_records + " added by users";
    $("statFamilies").textContent = formatNumber(stats.total_families_needing_assistance);
    $("statFamiliesNote").textContent =
      "Population of mapped areas: " + formatNumber(stats.total_population);
    $("statCenters").textContent = formatNumber(stats.total_centers);

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
