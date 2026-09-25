/* center_detail.js - Displays and manages details for an individual food support center. */

(function () {
  let centerId = null;
  let centerData = null;
  let detailMap = null;
  let contactedModal = null;
  let verifiedModal = null;
  let deleteModal = null;

  function getCenterIdFromUrl() {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const last = parts[parts.length - 1];
    return Number(last);
  }

  function renderStatusBadges(center) {
    const vBadge = document.getElementById("verificationBadge");
    const st = center.information_status || "Newly Added";
    let vCls = "bg-secondary";
    if (st === "Verified") vCls = "bg-success";
    else if (st === "Contacted") vCls = "bg-primary";
    else if (st === "Information Partially Verified") vCls = "bg-warning text-dark";
    else if (st === "Newly Added") vCls = "bg-info text-dark";
    else if (st === "Unable to Reach" || st === "Inactive") vCls = "bg-danger";

    vBadge.className = "badge " + vCls;
    vBadge.textContent = "Status: " + st;

    const aBadge = document.getElementById("availabilityBadge");
    const av = center.availability_status || "Unknown";
    let aCls = "border text-muted";
    let aTxt = "Availability: Unknown";
    if (av === "Yes") {
      aCls = "text-success border-success bg-light";
      aTxt = "Currently Active & Serving";
    } else if (av === "No") {
      aCls = "text-danger border-danger bg-light";
      aTxt = "Food Distribution Paused";
    }
    aBadge.className = "badge " + aCls;
    aBadge.textContent = aTxt;
  }

  function renderActionButtons(center) {
    const container = document.getElementById("actionButtonsContainer");
    const buttons = [];

    // Call Center
    if (center.phone_number) {
      buttons.push(
        '<a href="tel:' + escapeHtml(center.phone_number) + '" class="btn btn-outline-primary btn-sm d-inline-flex align-items-center">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-1" aria-hidden="true">' +
            '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>' +
          '</svg>' +
          'Call Center (' + escapeHtml(center.phone_number) + ')' +
        '</a>'
      );
    }

    // WhatsApp
    const waNum = center.whatsapp_number || (center.phone_number && center.preferred_contact_method === "WhatsApp" ? center.phone_number : null);
    if (waNum) {
      const cleanDigits = waNum.replace(/[^0-9]/g, "");
      if (cleanDigits.length >= 7) {
        buttons.push(
          '<a href="https://wa.me/' + cleanDigits + '" target="_blank" rel="noopener noreferrer" class="btn btn-outline-success btn-sm d-inline-flex align-items-center">' +
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-1" aria-hidden="true">' +
              '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>' +
            '</svg>' +
            'WhatsApp' +
          '</a>'
        );
      }
    }

    // Send Email
    if (center.email) {
      buttons.push(
        '<a href="mailto:' + escapeHtml(center.email) + '" class="btn btn-outline-secondary btn-sm d-inline-flex align-items-center">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-1" aria-hidden="true">' +
            '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline>' +
          '</svg>' +
          'Send Email' +
        '</a>'
      );
    }

    // Open Website
    if (center.website) {
      buttons.push(
        '<a href="' + escapeHtml(center.website) + '" target="_blank" rel="noopener noreferrer" class="btn btn-outline-secondary btn-sm d-inline-flex align-items-center">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-1" aria-hidden="true">' +
            '<circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line>' +
            '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>' +
          '</svg>' +
          'Open Website' +
        '</a>'
      );
    }

    // Open Directions (Maps)
    if (center.latitude && center.longitude) {
      buttons.push(
        '<a href="https://www.google.com/maps/dir/?api=1&destination=' + center.latitude + ',' + center.longitude + '" target="_blank" rel="noopener noreferrer" class="btn btn-outline-dark btn-sm d-inline-flex align-items-center">' +
          '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-1" aria-hidden="true">' +
            '<polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>' +
          '</svg>' +
          'Map Directions' +
        '</a>'
      );
    }

    container.innerHTML = buttons.join("") || '<span class="text-muted small">No direct contact links available.</span>';
  }

  function renderMap(center) {
    const lat = center.latitude;
    const lon = center.longitude;
    const isProvisional = center.location_source === "community_reference";

    const badge = document.getElementById("mapStatusBadge");
    if (isProvisional) {
      badge.className = "badge bg-secondary";
      badge.textContent = "Provisional Reference";
      document.getElementById("provisionalLocationAlert").classList.remove("d-none");
      document.getElementById("provisionalCommName").textContent = center.community_name || "surveyed";
    } else {
      badge.className = "badge bg-success";
      badge.textContent = "Actual Location";
      document.getElementById("provisionalLocationAlert").classList.add("d-none");
    }

    document.getElementById("coordDisplay").textContent = "Lat: " + Number(lat).toFixed(4) + ", Lon: " + Number(lon).toFixed(4);

    const distEl = document.getElementById("distanceDisplay");
    if (isProvisional) {
      distEl.textContent = "Provisional 0 km offset";
    } else if (center.distance_to_community_km !== null && center.distance_to_community_km !== undefined) {
      distEl.textContent = center.distance_to_community_km + " km to " + (center.community_name || "community");
    } else {
      distEl.textContent = "";
    }

    document.getElementById("btnFullGisLink").href = "/map?center=" + center.id;

    if (!detailMap) {
      detailMap = L.map("detailMap").setView([lat, lon], 14);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(detailMap);

      const centerIcon = L.divIcon({
        className: "",
        html: '<div class="center-pin" style="background: ' + (isProvisional ? '#6c757d' : '#2769ad') + ';" aria-hidden="true">F</div>',
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      });

      L.marker([lat, lon], { icon: centerIcon })
        .addTo(detailMap)
        .bindPopup('<strong>' + escapeHtml(center.center_name || center.name) + '</strong><br>' +
          (isProvisional ? 'Provisional reference coordinates' : 'Verified location'))
        .openPopup();

      if (center.community_latitude && center.community_longitude && !isProvisional) {
        L.circleMarker([center.community_latitude, center.community_longitude], {
          radius: 7,
          color: "#1d7a58",
          fillColor: "#e6f2ed",
          fillOpacity: 0.85,
          weight: 2
        }).addTo(detailMap).bindTooltip("Community: " + escapeHtml(center.community_name || ""));

        L.polyline([[lat, lon], [center.community_latitude, center.community_longitude]], {
          color: "#2769ad",
          dashArray: "4, 6",
          weight: 2
        }).addTo(detailMap);
      }
    } else {
      detailMap.setView([lat, lon], 14);
    }
  }

  function displayCenter(center) {
    centerData = center;

    const name = center.center_name || center.name;
    document.getElementById("centerName").textContent = name;
    document.title = name + " - Food Support Centers";

    document.getElementById("centerTypeBadge").textContent = center.center_type || "NGO";

    if (center.is_sample) {
      document.getElementById("headerSampleBadge").innerHTML = '<span class="badge-sample">Sample data</span>';
    }

    renderStatusBadges(center);
    renderActionButtons(center);

    // Basic Info
    document.getElementById("dtAddress").textContent = center.address || center.location || "Not provided";
    document.getElementById("dtCommunity").innerHTML = center.community_name
      ? '<a href="/communities?view=' + center.community_id + '" class="text-decoration-none fw-medium">' + escapeHtml(center.community_name) + '</a>'
      : '<span class="text-muted">Unassigned</span>';
    document.getElementById("dtLandmark").textContent = center.landmark || "None specified";
    document.getElementById("dtDistrictState").textContent =
      [center.district, center.state].filter(Boolean).join(", ") || "Not provided";
    document.getElementById("dtPincode").textContent = center.pincode || "Not provided";
    document.getElementById("dtDescription").textContent = center.description || "No description recorded.";

    // Food Support
    const foodTypesEl = document.getElementById("dtFoodTypes");
    const typesList = center.food_support_types_list || [];
    if (typesList.length) {
      foodTypesEl.innerHTML = typesList.map(function (t) {
        return '<span class="badge bg-light text-dark border">' + escapeHtml(t) + '</span>';
      }).join("");
    } else {
      foodTypesEl.innerHTML = '<span class="text-muted small">Not specified during registration.</span>';
    }

    document.getElementById("dtMeals").textContent = center.meals_available || "Not specified";
    document.getElementById("dtSchedule").textContent = center.distribution_schedule || "Not specified";
    document.getElementById("dtHours").textContent =
      [center.operating_days, center.operating_hours].filter(Boolean).join(" &bull; ") || "Not specified";
    document.getElementById("dtPeopleServed").textContent = center.people_served_per_day ? formatNumber(center.people_served_per_day) + " people / day" : "Not specified";
    document.getElementById("dtEligibility").textContent = center.eligibility_requirements || "Open to all needy individuals";
    document.getElementById("dtRegistration").textContent = center.registration_required || "Unknown";
    document.getElementById("dtAvailability").textContent = center.availability_status === "Yes" ? "Currently Active & Distributing" : (center.availability_status === "No" ? "Temporarily Paused" : "Status Unknown");

    // Verification & Follow-Up
    document.getElementById("dtInfoStatus").innerHTML = verificationBadge(center.information_status);
    document.getElementById("dtLastContacted").textContent = formatDate(center.last_contacted_date);
    document.getElementById("dtAttemptDate").textContent = formatDate(center.contact_attempt_date);
    document.getElementById("dtNextFollowup").textContent = formatDate(center.next_followup_date);
    document.getElementById("dtContactedBy").textContent = center.contacted_by || "Not recorded";
    document.getElementById("dtInfoSource").textContent = center.information_source || "Field registration";
    document.getElementById("dtContactNotes").textContent = center.contact_notes || "No contact notes recorded.";
    document.getElementById("dtVerificationNotes").textContent = center.verification_notes || "No verification notes recorded.";
    document.getElementById("dtUpdatedAt").textContent = "Updated: " + formatDate(center.updated_at || center.created_at);

    // Contact Directory
    document.getElementById("dtContactPerson").textContent =
      [center.primary_contact_name, center.contact_designation ? "(" + center.contact_designation + ")" : null].filter(Boolean).join(" ") || "Not provided";
    document.getElementById("dtPhone").innerHTML = center.phone_number
      ? '<a href="tel:' + escapeHtml(center.phone_number) + '">' + escapeHtml(center.phone_number) + '</a>'
      : "Not provided";
    document.getElementById("dtAltPhone").innerHTML = center.alternative_phone
      ? '<a href="tel:' + escapeHtml(center.alternative_phone) + '">' + escapeHtml(center.alternative_phone) + '</a>'
      : "None";
    document.getElementById("dtEmail").innerHTML = center.email
      ? '<a href="mailto:' + escapeHtml(center.email) + '">' + escapeHtml(center.email) + '</a>'
      : "None";
    document.getElementById("dtWebsite").innerHTML = center.website
      ? '<a href="' + escapeHtml(center.website) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(center.website) + '</a>'
      : "None";
    document.getElementById("dtWhatsApp").innerHTML = center.whatsapp_number
      ? '<a href="https://wa.me/' + center.whatsapp_number.replace(/[^0-9]/g, "") + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(center.whatsapp_number) + '</a>'
      : "None";
    document.getElementById("dtPrefMethod").textContent = center.preferred_contact_method || "Phone Call";

    // Map
    if (center.latitude && center.longitude) {
      renderMap(center);
    }
  }

  /* -------------------------------------------------------------------
     Status Modals (Mark Contacted & Mark Verified)
     ------------------------------------------------------------------- */
  async function submitContacted() {
    const btn = document.getElementById("btnSubmitContacted");
    btn.disabled = true;
    btn.textContent = "Saving...";

    const payload = {
      action: "mark_contacted",
      last_contacted_date: document.getElementById("m_last_contacted_date").value,
      contacted_by: document.getElementById("m_contacted_by").value.trim(),
      contact_notes: document.getElementById("m_contact_notes").value.trim(),
      next_followup_date: document.getElementById("m_next_followup_date").value
    };

    try {
      const updated = await apiFetch("/api/centers/" + centerId + "/status", {
        method: "PATCH",
        body: payload
      });
      if (contactedModal) contactedModal.hide();
      displayCenter(updated);

      const alertEl = document.getElementById("actionAlert");
      alertEl.textContent = "Contact attempt recorded successfully. Status updated to Contacted.";
      alertEl.classList.remove("d-none");
      setTimeout(function () { alertEl.classList.add("d-none"); }, 4000);
    } catch (err) {
      alert("Failed to update status: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Save Contact Record";
    }
  }

  async function submitVerified() {
    const btn = document.getElementById("btnSubmitVerified");
    btn.disabled = true;
    btn.textContent = "Verifying...";

    const payload = {
      action: "mark_verified",
      verification_notes: document.getElementById("m_verification_notes").value.trim()
    };

    try {
      const updated = await apiFetch("/api/centers/" + centerId + "/status", {
        method: "PATCH",
        body: payload
      });
      if (verifiedModal) verifiedModal.hide();
      displayCenter(updated);

      const alertEl = document.getElementById("actionAlert");
      alertEl.textContent = "Center marked as Verified successfully.";
      alertEl.classList.remove("d-none");
      setTimeout(function () { alertEl.classList.add("d-none"); }, 4000);
    } catch (err) {
      alert("Failed to verify center: " + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Confirm Verification";
    }
  }

  async function submitDelete() {
    const btn = document.getElementById("btnConfirmDelete");
    btn.disabled = true;
    btn.textContent = "Deleting...";

    try {
      await apiFetch("/api/centers/" + centerId, { method: "DELETE" });
      if (deleteModal) deleteModal.hide();
      window.location.href = "/centers";
    } catch (err) {
      alert("Failed to delete center: " + err.message);
      btn.disabled = false;
      btn.textContent = "Delete Center";
    }
  }

  async function init() {
    centerId = getCenterIdFromUrl();
    if (!centerId || isNaN(centerId)) {
      showLoadError("Invalid Center ID in URL.");
      return;
    }

    // Initialize Bootstrap Modals
    if (window.bootstrap) {
      const mC = document.getElementById("modalContacted");
      if (mC) contactedModal = new bootstrap.Modal(mC);
      const mV = document.getElementById("modalVerified");
      if (mV) verifiedModal = new bootstrap.Modal(mV);
      const mD = document.getElementById("modalDelete");
      if (mD) deleteModal = new bootstrap.Modal(mD);
    }

    // Modal button triggers
    const btnOpenC = document.getElementById("btnOpenContactedModal");
    if (btnOpenC) {
      btnOpenC.addEventListener("click", function () {
        document.getElementById("m_last_contacted_date").value = new Date().toISOString().split("T")[0];
        if (contactedModal) contactedModal.show();
      });
    }

    const btnOpenV = document.getElementById("btnOpenVerifyModal");
    if (btnOpenV) {
      btnOpenV.addEventListener("click", function () {
        if (verifiedModal) verifiedModal.show();
      });
    }

    const btnOpenD = document.getElementById("btnOpenDeleteModal");
    if (btnOpenD) {
      btnOpenD.addEventListener("click", function () {
        if (deleteModal) deleteModal.show();
      });
    }

    // Modal submit triggers
    const btnSubC = document.getElementById("btnSubmitContacted");
    if (btnSubC) btnSubC.addEventListener("click", submitContacted);

    const btnSubV = document.getElementById("btnSubmitVerified");
    if (btnSubV) btnSubV.addEventListener("click", submitVerified);

    const btnSubD = document.getElementById("btnConfirmDelete");
    if (btnSubD) btnSubD.addEventListener("click", submitDelete);

    // Fetch and display center details
    try {
      const center = await apiFetch("/api/centers/" + centerId);
      displayCenter(center);
    } catch (err) {
      showLoadError("Could not load food-support center details. " + err.message);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
