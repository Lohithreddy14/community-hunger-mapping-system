/* add_center.js - Handles Quick Add Mode and Complete Registration Form for Food Support Centers */

(function () {
  let communities = [];
  let pickerMap = null;
  let centerMarker = null;
  let commRefMarker = null;
  let activeCommunity = null;

  const fullForm = document.getElementById("fullCenterForm");
  const quickForm = document.getElementById("quickCenterForm");
  const editId = fullForm && fullForm.dataset.editId ? Number(fullForm.dataset.editId) : null;

  function toRad(val) {
    return (val * Math.PI) / 180;
  }

  function haversineKm(lat1, lon1, lat2, lon2) {
    const R = 6371.0088;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  function updateDistanceDisplay() {
    const latInput = document.getElementById("f_latitude");
    const lonInput = document.getElementById("f_longitude");
    const locSource = document.getElementById("f_location_source").value;
    const distEl = document.getElementById("distanceCalcDisplay");
    const badgeEl = document.getElementById("locationSourceBadge");
    const textEl = document.getElementById("locationSourceText");

    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);

    if (locSource === "actual") {
      badgeEl.className = "badge bg-success me-2";
      badgeEl.textContent = "Actual Center Location";
      textEl.textContent = "Coordinates pinpointed directly on the map.";

      if (activeCommunity && !isNaN(lat) && !isNaN(lon)) {
        const km = haversineKm(lat, lon, activeCommunity.latitude, activeCommunity.longitude);
        distEl.innerHTML = '<span class="text-primary fw-medium">Distance:</span> Approx. ' +
          km.toFixed(2) + ' km from <strong>' + escapeHtml(activeCommunity.name) + '</strong> survey point.';
      } else {
        distEl.textContent = "";
      }
    } else {
      badgeEl.className = "badge bg-secondary me-2";
      badgeEl.textContent = "Community Reference Location (Provisional)";
      if (activeCommunity) {
        textEl.textContent = 'Using reference coordinates from "' + activeCommunity.name + '". Center has not been physically pinpointed yet.';
        distEl.innerHTML = '<span class="text-muted">Provisional: 0 km offset. Click map to set exact building position.</span>';
      } else {
        textEl.textContent = "Select a community above or click the map to select coordinates.";
        distEl.textContent = "";
      }
    }
  }

  function buildPickerMap() {
    const mapEl = document.getElementById("centerPickerMap");
    if (!mapEl) return;

    pickerMap = L.map("centerPickerMap").setView([12.97, 77.59], 11);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(pickerMap);

    pickerMap.on("click", function (e) {
      setCenterLocation(e.latlng.lat, e.latlng.lng, "actual");
    });
  }

  function setCenterLocation(lat, lon, source) {
    if (isNaN(lat) || isNaN(lon)) return;
    source = source || "actual";

    document.getElementById("f_latitude").value = lat.toFixed(6);
    document.getElementById("f_longitude").value = lon.toFixed(6);
    document.getElementById("f_location_source").value = source;

    if (!pickerMap) return;

    if (!centerMarker) {
      centerMarker = L.marker([lat, lon], { draggable: true }).addTo(pickerMap);
      centerMarker.on("dragend", function () {
        const pos = centerMarker.getLatLng();
        setCenterLocation(pos.lat, pos.lng, "actual");
      });
    } else {
      centerMarker.setLatLng([lat, lon]);
    }

    updateDistanceDisplay();
  }

  function onCommunityChange(commId, isQuick) {
    if (!commId) {
      activeCommunity = null;
      if (commRefMarker && pickerMap) {
        pickerMap.removeLayer(commRefMarker);
        commRefMarker = null;
      }
      updateDistanceDisplay();
      return;
    }

    const comm = communities.find(function (c) { return String(c.id) === String(commId); });
    if (!comm) return;

    activeCommunity = comm;

    if (!isQuick) {
      if (pickerMap) {
        if (!commRefMarker) {
          commRefMarker = L.circleMarker([comm.latitude, comm.longitude], {
            radius: 8,
            color: "#1d7a58",
            fillColor: "#e6f2ed",
            fillOpacity: 0.8,
            weight: 2
          }).addTo(pickerMap).bindTooltip("Community: " + comm.name);
        } else {
          commRefMarker.setLatLng([comm.latitude, comm.longitude]);
          commRefMarker.setTooltipContent("Community: " + comm.name);
        }

        // Only overwrite coords if current coords are provisional or empty
        const curSource = document.getElementById("f_location_source").value;
        const curLat = document.getElementById("f_latitude").value;
        if (!curLat || curSource === "community_reference") {
          setCenterLocation(comm.latitude, comm.longitude, "community_reference");
          pickerMap.setView([comm.latitude, comm.longitude], 13);
        }
      }
      updateDistanceDisplay();
    }
  }

  function clearErrors(formEl) {
    formEl.querySelectorAll(".is-invalid").forEach(function (el) { el.classList.remove("is-invalid"); });
    formEl.querySelectorAll(".invalid-feedback").forEach(function (el) { el.textContent = ""; });
    const errBox = document.getElementById("formError");
    errBox.classList.add("d-none");
    errBox.textContent = "";
  }

  function showErrors(formEl, errors) {
    let first = null;
    Object.keys(errors).forEach(function (key) {
      const input = formEl.elements[key] || formEl.querySelector('[name="' + key + '"]');
      const msg = formEl.querySelector('[data-error-for="' + key + '"]');
      if (input) {
        input.classList.add("is-invalid");
        if (!first) first = input;
      }
      if (msg) msg.textContent = errors[key];
    });

    if (errors._form) {
      const box = document.getElementById("formError");
      box.textContent = errors._form;
      box.classList.remove("d-none");
    }

    if (first) {
      first.focus();
      first.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function showSuccessResult(center, isEdit) {
    const box = document.getElementById("resultBox");
    box.className = "result-box mb-4";

    const name = center.center_name || center.name;
    const isProvisional = center.location_source === "community_reference";

    box.innerHTML =
      '<div class="d-flex align-items-center justify-content-between mb-2">' +
        '<h2 class="h5 mb-0 text-success">' +
          '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="me-2" aria-hidden="true">' +
            '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>' +
          '</svg>' +
          (isEdit ? 'Changes Saved Successfully' : 'Food-Support Center Saved!') +
        '</h2>' +
        '<span class="badge bg-success">Status: ' + escapeHtml(center.information_status) + '</span>' +
      '</div>' +
      '<p class="mb-2"><strong>' + escapeHtml(name) + '</strong> (ID: #' + center.id + ') is recorded in the database.</p>' +
      '<div class="small text-muted mb-3">' +
        '<span>Associated Area: <strong>' + escapeHtml(center.community_name || "Unassigned") + '</strong></span> &bull; ' +
        '<span>Location: ' + (isProvisional ? '<span class="badge bg-secondary">Provisional Community Coordinates</span>' : '<span class="badge bg-success">Actual Verified Coordinates</span>') + '</span> &bull; ' +
        '<span>Phone: ' + escapeHtml(center.phone_number) + '</span>' +
      '</div>' +
      '<div class="result-actions d-flex flex-wrap gap-2">' +
        '<a href="/centers/' + center.id + '" class="btn btn-primary btn-sm">Open Center Details</a>' +
        '<a href="/map?center=' + center.id + '" class="btn btn-outline-primary btn-sm">View on GIS Map</a>' +
        '<a href="/centers" class="btn btn-outline-secondary btn-sm">All Food Centers</a>' +
        (!isEdit ? '<button type="button" class="btn btn-outline-success btn-sm" id="btnAddNewAnother">Add Another Center</button>' : '') +
      '</div>';

    box.scrollIntoView({ behavior: "smooth", block: "start" });

    const addAnother = document.getElementById("btnAddNewAnother");
    if (addAnother) {
      addAnother.addEventListener("click", function () {
        box.className = "d-none";
        if (quickForm) quickForm.reset();
        if (fullForm) fullForm.reset();
        clearErrors(quickForm || fullForm);
        document.getElementById("q_center_name") ? document.getElementById("q_center_name").focus() : null;
      });
    }
  }

  /* -------------------------------------------------------------------
     Quick Add Submit
     ------------------------------------------------------------------- */
  async function onQuickSubmit(e) {
    e.preventDefault();
    clearErrors(quickForm);

    const submitBtn = document.getElementById("quickSubmitBtn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving Center...";

    const commId = quickForm.elements.community_id.value;
    const selectedComm = communities.find(function (c) { return String(c.id) === String(commId); });

    const payload = {
      center_name: quickForm.elements.center_name.value.trim(),
      center_type: quickForm.elements.center_type.value,
      community_id: commId ? Number(commId) : null,
      phone_number: quickForm.elements.phone_number.value.trim(),
      address: quickForm.elements.address.value.trim(),
      website: quickForm.elements.website.value.trim(),
      description: quickForm.elements.description.value.trim(),
      location_source: "community_reference",
      information_status: "Newly Added",
      availability_status: "Unknown",
      registration_required: "Unknown"
    };

    if (selectedComm) {
      payload.latitude = selectedComm.latitude;
      payload.longitude = selectedComm.longitude;
    }

    try {
      const created = await apiFetch("/api/centers", {
        method: "POST",
        body: payload
      });
      showSuccessResult(created, false);
      quickForm.reset();
    } catch (err) {
      if (err.errors) {
        showErrors(quickForm, err.errors);
      } else {
        const box = document.getElementById("formError");
        box.textContent = err.message || "Failed to save center.";
        box.classList.remove("d-none");
      }
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Save Center";
    }
  }

  /* -------------------------------------------------------------------
     Full Form Submit
     ------------------------------------------------------------------- */
  async function onFullSubmit(e) {
    e.preventDefault();
    clearErrors(fullForm);

    const submitBtn = document.getElementById("fullSubmitBtn");
    const origText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving...";

    // Collect food support types
    const checkedTypes = [];
    fullForm.querySelectorAll(".food-type-check:checked").forEach(function (chk) {
      checkedTypes.push(chk.value);
    });

    const commId = fullForm.elements.community_id.value;
    const centerType = fullForm.elements.center_type.value === "Other"
      ? (document.getElementById("f_custom_center_type").value.trim() || "Other")
      : fullForm.elements.center_type.value;

    const payload = {
      center_name: fullForm.elements.center_name.value.trim(),
      center_type: centerType,
      community_id: commId ? Number(commId) : null,
      landmark: fullForm.elements.landmark.value.trim(),
      address: fullForm.elements.address.value.trim(),
      pincode: fullForm.elements.pincode.value.trim(),
      district: fullForm.elements.district.value.trim(),
      state: fullForm.elements.state.value.trim(),
      description: fullForm.elements.description.value.trim(),

      latitude: fullForm.elements.latitude.value.trim() ? parseFloat(fullForm.elements.latitude.value) : null,
      longitude: fullForm.elements.longitude.value.trim() ? parseFloat(fullForm.elements.longitude.value) : null,
      location_source: fullForm.elements.location_source.value || "community_reference",

      primary_contact_name: fullForm.elements.primary_contact_name.value.trim(),
      contact_designation: fullForm.elements.contact_designation.value.trim(),
      phone_number: fullForm.elements.phone_number.value.trim(),
      alternative_phone: fullForm.elements.alternative_phone.value.trim(),
      email: fullForm.elements.email.value.trim(),
      website: fullForm.elements.website.value.trim(),
      whatsapp_number: fullForm.elements.whatsapp_number.value.trim(),
      preferred_contact_method: fullForm.elements.preferred_contact_method.value,

      food_support_types: checkedTypes,
      meals_available: fullForm.elements.meals_available.value.trim(),
      distribution_schedule: fullForm.elements.distribution_schedule.value.trim(),
      operating_days: fullForm.elements.operating_days.value.trim(),
      operating_hours: fullForm.elements.operating_hours.value.trim(),
      people_served_per_day: fullForm.elements.people_served_per_day.value ? parseInt(fullForm.elements.people_served_per_day.value, 10) : null,
      eligibility_requirements: fullForm.elements.eligibility_requirements.value.trim(),
      registration_required: fullForm.elements.registration_required.value,
      availability_status: fullForm.elements.availability_status.value,

      information_status: fullForm.elements.information_status.value,
      contact_attempt_date: fullForm.elements.contact_attempt_date.value,
      last_contacted_date: fullForm.elements.last_contacted_date.value,
      next_followup_date: fullForm.elements.next_followup_date.value,
      contacted_by: fullForm.elements.contacted_by.value.trim(),
      information_source: fullForm.elements.information_source.value.trim(),
      contact_notes: fullForm.elements.contact_notes.value.trim(),
      verification_notes: fullForm.elements.verification_notes.value.trim()
    };

    try {
      const url = editId ? "/api/centers/" + editId : "/api/centers";
      const method = editId ? "PUT" : "POST";
      const saved = await apiFetch(url, { method: method, body: payload });
      showSuccessResult(saved, Boolean(editId));
      if (!editId) fullForm.reset();
    } catch (err) {
      if (err.errors) {
        showErrors(fullForm, err.errors);
      } else {
        const box = document.getElementById("formError");
        box.textContent = err.message || "Failed to save center.";
        box.classList.remove("d-none");
      }
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = origText;
    }
  }

  async function populateExistingCenter(id) {
    try {
      const center = await apiFetch("/api/centers/" + id);
      fullForm.elements.center_name.value = center.center_name || center.name || "";

      // Type
      const knownTypes = ["NGO", "Community Kitchen", "Food Bank", "Charitable Organization",
                          "Government Food Support Center", "Religious or Community Organization",
                          "Food Distribution Center"];
      if (knownTypes.includes(center.center_type)) {
        fullForm.elements.center_type.value = center.center_type;
      } else {
        fullForm.elements.center_type.value = "Other";
        document.getElementById("customTypeWrap").classList.remove("d-none");
        document.getElementById("f_custom_center_type").value = center.center_type || "";
      }

      if (center.community_id) {
        fullForm.elements.community_id.value = center.community_id;
        onCommunityChange(center.community_id, false);
      }

      fullForm.elements.landmark.value = center.landmark || "";
      fullForm.elements.address.value = center.address || center.location || "";
      fullForm.elements.pincode.value = center.pincode || "";
      fullForm.elements.district.value = center.district || "";
      fullForm.elements.state.value = center.state || "";
      fullForm.elements.description.value = center.description || "";

      if (center.latitude && center.longitude) {
        setCenterLocation(Number(center.latitude), Number(center.longitude), center.location_source || "actual");
        if (pickerMap) pickerMap.setView([center.latitude, center.longitude], 13);
      }

      fullForm.elements.primary_contact_name.value = center.primary_contact_name || "";
      fullForm.elements.contact_designation.value = center.contact_designation || "";
      fullForm.elements.phone_number.value = center.phone_number || "";
      fullForm.elements.alternative_phone.value = center.alternative_phone || "";
      fullForm.elements.email.value = center.email || "";
      fullForm.elements.website.value = center.website || "";
      fullForm.elements.whatsapp_number.value = center.whatsapp_number || "";
      if (center.preferred_contact_method) {
        fullForm.elements.preferred_contact_method.value = center.preferred_contact_method;
      }

      // Checkboxes
      const typesList = center.food_support_types_list || [];
      fullForm.querySelectorAll(".food-type-check").forEach(function (chk) {
        chk.checked = typesList.includes(chk.value);
      });

      fullForm.elements.meals_available.value = center.meals_available || "";
      fullForm.elements.distribution_schedule.value = center.distribution_schedule || "";
      fullForm.elements.operating_days.value = center.operating_days || "";
      fullForm.elements.operating_hours.value = center.operating_hours || "";
      fullForm.elements.people_served_per_day.value = center.people_served_per_day || "";
      fullForm.elements.eligibility_requirements.value = center.eligibility_requirements || "";
      if (center.registration_required) fullForm.elements.registration_required.value = center.registration_required;
      if (center.availability_status) fullForm.elements.availability_status.value = center.availability_status;

      if (center.information_status) fullForm.elements.information_status.value = center.information_status;
      fullForm.elements.contact_attempt_date.value = center.contact_attempt_date || "";
      fullForm.elements.last_contacted_date.value = center.last_contacted_date || "";
      fullForm.elements.next_followup_date.value = center.next_followup_date || "";
      fullForm.elements.contacted_by.value = center.contacted_by || "";
      fullForm.elements.information_source.value = center.information_source || "";
      fullForm.elements.contact_notes.value = center.contact_notes || "";
      fullForm.elements.verification_notes.value = center.verification_notes || "";
    } catch (err) {
      const box = document.getElementById("formError");
      box.textContent = "Could not load center details: " + err.message;
      box.classList.remove("d-none");
    }
  }

  async function init() {
    buildPickerMap();

    // Load communities for dropdowns
    try {
      communities = await apiFetch("/api/communities");
      const quickSelect = document.getElementById("q_community_id");
      const fullSelect = document.getElementById("f_community_id");

      communities.forEach(function (c) {
        if (quickSelect) {
          const opt = document.createElement("option");
          opt.value = c.id;
          opt.textContent = c.name + " (" + c.population + " pop)";
          quickSelect.appendChild(opt);
        }
        if (fullSelect) {
          const opt2 = document.createElement("option");
          opt2.value = c.id;
          opt2.textContent = c.name + " (" + c.population + " pop)";
          fullSelect.appendChild(opt2);
        }
      });
    } catch (err) {
      console.warn("Could not load communities for dropdown", err);
    }

    // Community dropdown change handlers
    if (quickForm) {
      document.getElementById("q_community_id").addEventListener("change", function (e) {
        onCommunityChange(e.target.value, true);
      });
      quickForm.addEventListener("submit", onQuickSubmit);
    }

    if (fullForm) {
      document.getElementById("f_community_id").addEventListener("change", function (e) {
        onCommunityChange(e.target.value, false);
      });
      fullForm.addEventListener("submit", onFullSubmit);
    }

    // Toggle custom type input
    const typeSelect = document.getElementById("f_center_type");
    if (typeSelect) {
      typeSelect.addEventListener("change", function () {
        const customWrap = document.getElementById("customTypeWrap");
        if (typeSelect.value === "Other") customWrap.classList.remove("d-none");
        else customWrap.classList.add("d-none");
      });
    }

    // Toggle manual coordinates
    const toggleCoordsBtn = document.getElementById("toggleCoordsBtn");
    if (toggleCoordsBtn) {
      toggleCoordsBtn.addEventListener("click", function () {
        const row = document.getElementById("manualCoordsRow");
        row.classList.toggle("d-none");
      });
    }

    // Input coordinate listeners
    const latInp = document.getElementById("f_latitude");
    const lonInp = document.getElementById("f_longitude");
    if (latInp && lonInp) {
      const syncFromInputs = function () {
        const lat = parseFloat(latInp.value);
        const lon = parseFloat(lonInp.value);
        if (!isNaN(lat) && !isNaN(lon)) {
          setCenterLocation(lat, lon, "actual");
          if (pickerMap) pickerMap.setView([lat, lon], 13);
        }
      };
      latInp.addEventListener("change", syncFromInputs);
      lonInp.addEventListener("change", syncFromInputs);
    }

    // Quick verification buttons
    const btnContacted = document.getElementById("btnMarkContactedQuick");
    if (btnContacted) {
      btnContacted.addEventListener("click", function () {
        const today = new Date().toISOString().split("T")[0];
        document.getElementById("f_last_contacted_date").value = today;
        document.getElementById("f_information_status").value = "Contacted";
      });
    }

    const btnVerified = document.getElementById("btnMarkVerifiedQuick");
    if (btnVerified) {
      btnVerified.addEventListener("click", function () {
        document.getElementById("f_information_status").value = "Verified";
      });
    }

    // Handle URL parameters (e.g. ?mode=quick or ?mode=full or editing)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("mode") === "full" && !editId) {
      const fullTab = document.getElementById("full-tab");
      if (fullTab && window.bootstrap) {
        new bootstrap.Tab(fullTab).show();
      }
    }

    // Invalidate map size when tab switches
    const fullTabBtn = document.getElementById("full-tab");
    if (fullTabBtn) {
      fullTabBtn.addEventListener("shown.bs.tab", function () {
        if (pickerMap) pickerMap.invalidateSize();
      });
    }

    if (editId) {
      populateExistingCenter(editId);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
