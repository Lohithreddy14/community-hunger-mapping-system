/* add_community.js - form validation, saving through the Flask API, and the coordinate picker map. */

(function () {
  const form = document.getElementById("communityForm");
  const editId = form.dataset.editId ? Number(form.dataset.editId) : null;

  const FIELDS = [
    "name", "latitude", "longitude", "population", "total_families",
    "families_needing_assistance", "avg_household_income",
    "food_accessibility", "nearby_centers", "notes"
  ];

  /* ---------------------------------------------------------------------
     Validation (the server repeats these checks - it is the final authority)
     --------------------------------------------------------------------- */
  function parseNumber(text) {
    const cleaned = String(text).trim().replace(/,/g, "");
    if (cleaned === "" || isNaN(Number(cleaned)) || !isFinite(Number(cleaned))) return NaN;
    return Number(cleaned);
  }

  function checkNumber(values, errors, key, label, opts) {
    const raw = String(values[key] || "").trim();
    if (raw === "") {
      if (opts.required) errors[key] = label + " is required.";
      return null;
    }
    const number = parseNumber(raw);
    if (isNaN(number)) {
      errors[key] = label + " must be " + (opts.integer ? "a whole number." : "a number.");
      return null;
    }
    if (opts.integer && !Number.isInteger(number)) {
      errors[key] = label + " must be a whole number.";
      return null;
    }
    if (opts.min !== undefined && number < opts.min) {
      errors[key] = opts.max !== undefined
        ? label + " must be between " + opts.min + " and " + opts.max + "."
        : label + " must be " + opts.min + " or more.";
      return null;
    }
    if (opts.max !== undefined && number > opts.max) {
      errors[key] = opts.min !== undefined
        ? label + " must be between " + opts.min + " and " + opts.max + "."
        : label + " must be " + opts.max + " or less.";
      return null;
    }
    return number;
  }

  function validate(values) {
    const errors = {};
    const name = String(values.name || "").trim();
    if (name === "") errors.name = "Community name is required.";
    else if (name.length < 2) errors.name = "Community name must be at least 2 characters.";
    else if (name.length > 100) errors.name = "Community name must be 100 characters or fewer.";

    checkNumber(values, errors, "latitude", "Latitude", { required: true, min: -90, max: 90 });
    checkNumber(values, errors, "longitude", "Longitude", { required: true, min: -180, max: 180 });
    const population = checkNumber(values, errors, "population", "Population",
      { required: true, integer: true, min: 1, max: 50000000 });
    const total = checkNumber(values, errors, "total_families", "Total families",
      { integer: true, min: 1, max: 50000000 });
    const needing = checkNumber(values, errors, "families_needing_assistance",
      "Families needing assistance", { required: true, integer: true, min: 0, max: 50000000 });
    checkNumber(values, errors, "avg_household_income", "Average household income",
      { min: 0, max: 10000000 });
    checkNumber(values, errors, "nearby_centers", "Nearby food-support centers",
      { integer: true, min: 0, max: 100 });

    if (population !== null && needing !== null && needing > population && !errors.families_needing_assistance) {
      errors.families_needing_assistance = "Families needing assistance cannot be more than the population.";
    }
    if (total !== null && !errors.total_families) {
      if (population !== null && total > population) {
        errors.total_families = "Total families cannot be more than the population.";
      } else if (needing !== null && total < needing) {
        errors.total_families = "Total families cannot be fewer than the families needing assistance.";
      }
    }
    if (String(values.notes || "").length > 500) errors.notes = "Notes must be 500 characters or fewer.";
    return errors;
  }

  /* ---------------------------------------------------------------------
     Showing and clearing errors
     --------------------------------------------------------------------- */
  function clearErrors() {
    form.querySelectorAll(".is-invalid").forEach(function (el) { el.classList.remove("is-invalid"); });
    form.querySelectorAll(".invalid-feedback").forEach(function (el) { el.textContent = ""; });
    document.getElementById("formError").classList.add("d-none");
  }

  function showErrors(errors) {
    let first = null;
    Object.keys(errors).forEach(function (key) {
      const input = form.elements[key];
      const message = form.querySelector('[data-error-for="' + key + '"]');
      if (input) {
        input.classList.add("is-invalid");
        if (!first) first = input;
      }
      if (message) message.textContent = errors[key];
    });
    if (errors._form) {
      const box = document.getElementById("formError");
      box.textContent = errors._form;
      box.classList.remove("d-none");
    }
    if (first) first.focus();
  }

  function readValues() {
    const values = {};
    FIELDS.forEach(function (key) { values[key] = form.elements[key].value; });
    return values;
  }

  function fillForm(record) {
    FIELDS.forEach(function (key) {
      const value = record[key];
      form.elements[key].value = value === null || value === undefined ? "" : value;
    });
  }

  /* ---------------------------------------------------------------------
     Saving
     --------------------------------------------------------------------- */
  function showResult(record, wasEdit) {
    const box = document.getElementById("resultBox");
    const a = record.analysis;
    box.className = "result-box";
    box.innerHTML =
      "<h2>" + (wasEdit ? "Changes saved" : "Community data saved") + "</h2>" +
      "<div>" + escapeHtml(record.name) + " is stored in the database. Estimated category: " +
        categoryChip(record.category) + " (score " + record.score.toFixed(1) + " out of 100, " +
        a.indicators_used + " of " + a.indicators_total + " indicators used).</div>" +
      '<div class="result-actions">' +
        '<a class="btn btn-primary btn-sm" href="/map?focus=' + record.id + '">View on map</a>' +
        '<a class="btn btn-outline-primary btn-sm" href="/">Go to dashboard</a>' +
        (wasEdit
          ? '<a class="btn btn-outline-secondary btn-sm" href="/communities">Back to community data</a>'
          : '<button type="button" class="btn btn-outline-secondary btn-sm" id="addAnother">Add another</button>') +
      "</div>";
    box.scrollIntoView({ behavior: "smooth", block: "start" });

    const another = document.getElementById("addAnother");
    if (another) {
      another.addEventListener("click", function () {
        resetForm();
        document.getElementById("name").focus();
      });
    }
  }

  async function onSubmit(event) {
    event.preventDefault();
    clearErrors();
    document.getElementById("resultBox").className = "d-none";

    const values = readValues();
    const errors = validate(values);
    if (Object.keys(errors).length) {
      showErrors(errors);
      return;
    }

    const button = document.getElementById("submitBtn");
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Saving...";

    try {
      const url = editId ? "/api/communities/" + editId : "/api/communities";
      const record = await apiFetch(url, { method: editId ? "PUT" : "POST", body: values });
      showResult(record, Boolean(editId));
      if (!editId) resetForm(true);
    } catch (err) {
      if (err.errors) {
        showErrors(err.errors);
      } else {
        const box = document.getElementById("formError");
        box.textContent = err.message;
        box.classList.remove("d-none");
      }
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }

  function resetForm(keepResult) {
    form.reset();
    clearErrors();
    if (!keepResult) document.getElementById("resultBox").className = "d-none";
    if (marker && picker) { picker.removeLayer(marker); }
    marker = null;
  }

  /* ---------------------------------------------------------------------
     Coordinate picker map
     --------------------------------------------------------------------- */
  let picker = null;
  let marker = null;

  function setMarker(lat, lon) {
    if (!picker) return;
    if (!marker) {
      marker = L.marker([lat, lon], { draggable: true }).addTo(picker);
      marker.on("dragend", function () {
        const pos = marker.getLatLng();
        setCoordinateInputs(pos.lat, pos.lng);
      });
    } else {
      marker.setLatLng([lat, lon]);
    }
  }

  function setCoordinateInputs(lat, lon) {
    form.elements.latitude.value = lat.toFixed(6);
    form.elements.longitude.value = lon.toFixed(6);
    ["latitude", "longitude"].forEach(function (key) {
      form.elements[key].classList.remove("is-invalid");
      form.querySelector('[data-error-for="' + key + '"]').textContent = "";
    });
  }

  function syncMarkerFromInputs() {
    const lat = parseNumber(form.elements.latitude.value);
    const lon = parseNumber(form.elements.longitude.value);
    if (picker && !isNaN(lat) && !isNaN(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) {
      setMarker(lat, lon);
      picker.panTo([lat, lon]);
    }
  }

  function buildPicker(existing) {
    picker = L.map("pickerMap").setView([12.97, 77.59], 10);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(picker);

    // Show existing communities as small grey dots for context, and centre on them.
    const points = [];
    (existing || []).forEach(function (c) {
      if (editId && c.id === editId) return;
      points.push([c.latitude, c.longitude]);
      L.circleMarker([c.latitude, c.longitude], {
        radius: 5, color: "#ffffff", weight: 1, fillColor: "#7b8d87", fillOpacity: 0.85
      }).bindTooltip(c.name).addTo(picker);
    });
    if (points.length) picker.fitBounds(L.latLngBounds(points).pad(0.2), { maxZoom: 13 });

    picker.on("click", function (event) {
      setMarker(event.latlng.lat, event.latlng.lng);
      setCoordinateInputs(event.latlng.lat, event.latlng.lng);
    });
    form.elements.latitude.addEventListener("change", syncMarkerFromInputs);
    form.elements.longitude.addEventListener("change", syncMarkerFromInputs);
  }

  /* ---------------------------------------------------------------------
     Start-up
     --------------------------------------------------------------------- */
  async function init() {
    form.addEventListener("submit", onSubmit);
    const clearButton = document.getElementById("clearBtn");
    if (clearButton) clearButton.addEventListener("click", function () { resetForm(false); });

    let existing = [];
    try { existing = await apiFetch("/api/communities"); } catch (err) { /* map still works without it */ }
    try {
      buildPicker(existing);
    } catch (err) {
      picker = null;
      document.getElementById("pickerMap").innerHTML =
        '<p class="p-3 small text-muted mb-0">The map could not be loaded (an internet connection is needed). ' +
        "You can still type the latitude and longitude.</p>";
    }

    if (editId) {
      try {
        const record = await apiFetch("/api/communities/" + editId);
        fillForm(record);
        syncMarkerFromInputs();
        if (picker) picker.setView([record.latitude, record.longitude], 13);
      } catch (err) {
        const box = document.getElementById("formError");
        box.textContent = "Could not load this record. " + err.message;
        box.classList.remove("d-none");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
