/* common.js - helpers shared by all pages. Loaded before the page-specific script. */

const CATEGORIES = {
  lower:    { label: "Lower",    full: "Lower estimated vulnerability",    color: "#2e9e5b" },
  moderate: { label: "Moderate", full: "Moderate estimated vulnerability", color: "#e0a800" },
  higher:   { label: "Higher",   full: "Higher estimated vulnerability",   color: "#d64545" }
};

/**
 * Call the Flask API and return the parsed JSON.
 * Throws an Error (with .status and .errors when available) if the request fails.
 */
async function apiFetch(url, options) {
  const opts = Object.assign({ headers: {} }, options || {});
  if (opts.body && typeof opts.body !== "string") {
    opts.body = JSON.stringify(opts.body);
  }
  if (opts.body) {
    opts.headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(url, opts);
  } catch (networkError) {
    const err = new Error("Could not reach the server. Check that the Flask app is still running.");
    err.network = true;
    throw err;
  }

  let data = null;
  try { data = await response.json(); } catch (parseError) { /* body was not JSON */ }

  if (!response.ok) {
    const err = new Error((data && data.error) || "The request failed (status " + response.status + ").");
    err.status = response.status;
    err.errors = (data && data.errors) || null;
    throw err;
  }
  return data;
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString("en-IN");
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(String(value).replace(" ", "T"));
  if (isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function categoryChip(key) {
  const cat = CATEGORIES[key];
  if (!cat) return "";
  return '<span class="cat-chip cat-' + key + '">' + escapeHtml(cat.label) + "</span>";
}

function sampleBadge(record) {
  return record && record.is_sample ? ' <span class="badge-sample">Sample data</span>' : "";
}

function formatCoords(lat, lon) {
  return Number(lat).toFixed(4) + ", " + Number(lon).toFixed(4);
}

/** Show an error message in an alert box (element id "loadError" by default). */
function showLoadError(message, elementId) {
  const box = document.getElementById(elementId || "loadError");
  if (!box) return;
  box.textContent = message;
  box.classList.remove("d-none");
}

/** Score breakdown table used in the community details window. */
function renderBreakdown(analysis) {
  const rows = analysis.indicators.map(function (item) {
    const cls = item.available ? "" : ' class="text-muted"';
    return "<tr" + cls + ">" +
      "<td>" + escapeHtml(item.label) +
        '<div class="small text-muted">' + escapeHtml(item.detail) + "</div></td>" +
      "<td>" + escapeHtml(item.value) + "</td>" +
      '<td class="text-end">' + (item.available ? item.risk.toFixed(1) : "-") + "</td>" +
      '<td class="text-end">' + (item.available ? Math.round(item.effective_weight * 100) + "%" : "not used") + "</td>" +
      '<td class="text-end">' + (item.available ? item.contribution.toFixed(1) : "-") + "</td>" +
      "</tr>";
  }).join("");

  return '<div class="table-responsive"><table class="table breakdown align-middle mb-2">' +
    "<thead><tr><th>Indicator</th><th>Value</th>" +
    '<th class="text-end">Risk (0-100)</th><th class="text-end">Weight used</th>' +
    '<th class="text-end">Contribution</th></tr></thead>' +
    "<tbody>" + rows + "</tbody>" +
    '<tfoot><tr><th colspan="4" class="text-end">Total score (0-100)</th>' +
    '<th class="text-end">' + analysis.score.toFixed(1) + "</th></tr></tfoot>" +
    "</table></div>";
}
