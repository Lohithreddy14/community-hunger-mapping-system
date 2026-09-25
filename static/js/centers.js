/* centers.js - Management page for food-support centers. */

(function () {
  let allCenters = [];
  let communities = [];
  let centerToDelete = null;
  let deleteModal = null;

  function verificationBadge(status) {
    status = status || "Newly Added";
    let cls = "bg-secondary";
    if (status === "Verified") cls = "bg-success";
    else if (status === "Contacted") cls = "bg-primary";
    else if (status === "Information Partially Verified") cls = "bg-warning text-dark";
    else if (status === "Newly Added") cls = "bg-info text-dark";
    else if (status === "Unable to Reach" || status === "Inactive") cls = "bg-danger";

    return '<span class="badge ' + cls + ' me-1">' + escapeHtml(status) + '</span>';
  }

  function availabilityBadge(status) {
    status = status || "Unknown";
    let cls = "border text-muted";
    let text = "Availability: Unknown";
    if (status === "Yes") {
      cls = "text-success border-success bg-light";
      text = "Active & Serving";
    } else if (status === "No") {
      cls = "text-danger border-danger bg-light";
      text = "Service Paused";
    }
    return '<span class="badge ' + cls + ' me-1">' + escapeHtml(text) + '</span>';
  }

  function formatCenterCard(center) {
    const isSample = Boolean(center.is_sample);
    const commName = center.community_name || "Unassigned";

    let distText = "";
    if (center.location_source === "community_reference") {
      distText = '<span class="badge bg-light text-muted border ms-1" title="Using community reference point">Provisional Reference</span>';
    } else if (center.distance_to_community_km !== null && center.distance_to_community_km !== undefined) {
      distText = '<span class="badge bg-light text-dark border ms-1">' +
        center.distance_to_community_km + ' km from ' + escapeHtml(commName) + '</span>';
    }

    const phoneHtml = center.phone_number
      ? '<a href="tel:' + escapeHtml(center.phone_number) + '" class="text-decoration-none fw-medium text-dark">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-1" aria-hidden="true">' +
            '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>' +
          '</svg>' +
          escapeHtml(center.phone_number) +
        '</a>'
      : '<span class="text-muted">No phone</span>';

    return (
      '<div class="col-12 col-md-6 col-xl-4">' +
        '<article class="panel center-card p-3 d-flex flex-column h-100">' +
          '<div class="d-flex justify-content-between align-items-start mb-2">' +
            '<span class="badge bg-light text-primary border">' + escapeHtml(center.center_type || "NGO") + '</span>' +
            '<div>' + (isSample ? '<span class="badge-sample">Sample data</span>' : '') + '</div>' +
          '</div>' +
          '<h2 class="h5 mb-1 text-truncate" title="' + escapeHtml(center.center_name || center.name) + '">' +
            '<a href="/centers/' + center.id + '" class="text-dark text-decoration-none">' +
              escapeHtml(center.center_name || center.name) +
            '</a>' +
          '</h2>' +
          '<div class="small text-muted mb-2 d-flex align-items-center flex-wrap">' +
            '<span>' + escapeHtml(center.address || center.location || "Address not provided") + '</span>' +
          '</div>' +
          '<div class="mb-2 d-flex align-items-center flex-wrap gap-1">' +
            '<span class="small fw-medium text-secondary">Area: ' + escapeHtml(commName) + '</span>' +
            distText +
          '</div>' +
          '<div class="mb-3">' +
            verificationBadge(center.information_status) +
            availabilityBadge(center.availability_status) +
          '</div>' +
          '<div class="small mb-3">' + phoneHtml + '</div>' +
          '<p class="small text-muted text-truncate-2 mb-3 flex-grow-1">' +
            escapeHtml(center.description || "No description provided.") +
          '</p>' +
          '<div class="d-flex justify-content-between align-items-center border-top pt-2 mt-auto">' +
            '<a href="/centers/' + center.id + '" class="btn btn-sm btn-outline-primary">View Details</a>' +
            '<div class="d-flex gap-1">' +
              '<a href="/centers/' + center.id + '/edit" class="btn btn-sm btn-outline-secondary" title="Edit Center">Edit</a>' +
              '<button type="button" class="btn btn-sm btn-outline-danger delete-btn" data-id="' + center.id + '" data-name="' + escapeHtml(center.center_name || center.name) + '" title="Delete Center">Delete</button>' +
            '</div>' +
          '</div>' +
        '</article>' +
      '</div>'
    );
  }

  function applyFilters() {
    const search = document.getElementById("searchBox").value.trim().toLowerCase();
    const commFilter = document.getElementById("communityFilter").value;
    const typeFilter = document.getElementById("typeFilter").value;
    const statusFilter = document.getElementById("statusFilter").value;
    const availFilter = document.getElementById("availFilter").value;

    const filtered = allCenters.filter(function (center) {
      if (search) {
        const name = (center.center_name || center.name || "").toLowerCase();
        const addr = (center.address || center.location || "").toLowerCase();
        const desc = (center.description || "").toLowerCase();
        const contact = (center.primary_contact_name || "").toLowerCase();
        const phone = (center.phone_number || "").toLowerCase();
        if (!name.includes(search) && !addr.includes(search) && !desc.includes(search) && !contact.includes(search) && !phone.includes(search)) {
          return false;
        }
      }

      if (commFilter !== "all" && String(center.community_id) !== String(commFilter)) {
        return false;
      }

      if (typeFilter !== "all" && center.center_type !== typeFilter) {
        return false;
      }

      if (statusFilter !== "all" && center.information_status !== statusFilter) {
        return false;
      }

      if (availFilter !== "all" && center.availability_status !== availFilter) {
        return false;
      }

      return true;
    });

    renderGrid(filtered);
  }

  function renderGrid(centers) {
    const grid = document.getElementById("centerGrid");
    const countEl = document.getElementById("centerCount");
    countEl.textContent = centers.length + " of " + allCenters.length + " centers";

    if (!centers.length) {
      grid.innerHTML =
        '<div class="col-12">' +
          '<div class="panel empty-row text-center p-4">' +
            '<p class="text-muted mb-3">No food-support centers match the selected criteria.</p>' +
            '<div class="d-flex justify-content-center gap-2">' +
              '<a href="/centers/add?mode=quick" class="btn btn-success btn-sm">Quick Add Center</a>' +
              '<a href="/centers/add" class="btn btn-primary btn-sm">Add New Center</a>' +
              '<button type="button" class="btn btn-outline-secondary btn-sm" id="resetFiltersBtn">Reset Filters</button>' +
            '</div>' +
          '</div>' +
        '</div>';

      const resetBtn = document.getElementById("resetFiltersBtn");
      if (resetBtn) {
        resetBtn.addEventListener("click", function () {
          document.getElementById("searchBox").value = "";
          document.getElementById("communityFilter").value = "all";
          document.getElementById("typeFilter").value = "all";
          document.getElementById("statusFilter").value = "all";
          document.getElementById("availFilter").value = "all";
          applyFilters();
        });
      }
      return;
    }

    grid.innerHTML = centers.map(formatCenterCard).join("");

    // Wire up delete buttons
    grid.querySelectorAll(".delete-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        centerToDelete = {
          id: btn.dataset.id,
          name: btn.dataset.name
        };
        document.getElementById("deleteCenterName").textContent = centerToDelete.name;
        if (deleteModal) deleteModal.show();
      });
    });
  }

  async function confirmDelete() {
    if (!centerToDelete) return;
    const btn = document.getElementById("confirmDeleteCenterBtn");
    btn.disabled = true;
    btn.textContent = "Deleting...";

    try {
      await apiFetch("/api/centers/" + centerToDelete.id, { method: "DELETE" });
      if (deleteModal) deleteModal.hide();
      allCenters = allCenters.filter(function (c) { return String(c.id) !== String(centerToDelete.id); });
      applyFilters();

      const alertEl = document.getElementById("actionAlert");
      alertEl.textContent = 'Center "' + centerToDelete.name + '" was deleted successfully.';
      alertEl.classList.remove("d-none");
      setTimeout(function () { alertEl.classList.add("d-none"); }, 4000);
    } catch (err) {
      alert("Could not delete center: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Delete Center";
      centerToDelete = null;
    }
  }

  async function init() {
    const modalEl = document.getElementById("deleteCenterModal");
    if (modalEl && window.bootstrap) {
      deleteModal = new bootstrap.Modal(modalEl);
    }
    const confirmBtn = document.getElementById("confirmDeleteCenterBtn");
    if (confirmBtn) confirmBtn.addEventListener("click", confirmDelete);

    // Filter event listeners
    document.getElementById("searchBox").addEventListener("input", applyFilters);
    document.getElementById("communityFilter").addEventListener("change", applyFilters);
    document.getElementById("typeFilter").addEventListener("change", applyFilters);
    document.getElementById("statusFilter").addEventListener("change", applyFilters);
    document.getElementById("availFilter").addEventListener("change", applyFilters);

    try {
      const [loadedCommunities, loadedCenters] = await Promise.all([
        apiFetch("/api/communities"),
        apiFetch("/api/centers")
      ]);
      communities = loadedCommunities;
      allCenters = loadedCenters;

      // Populate communities dropdown
      const commSelect = document.getElementById("communityFilter");
      communities.forEach(function (c) {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        commSelect.appendChild(opt);
      });

      applyFilters();
    } catch (err) {
      showLoadError("Could not load food-support centers. " + err.message);
      document.getElementById("centerGrid").innerHTML = "";
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
