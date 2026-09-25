"""
validation.py - input validation for community and food-support-center records.

The same rules are used in three places:
  * the "Add community data" API (POST /api/communities)
  * the "Edit" API (PUT /api/communities/<id>)
  * the CSV loader that inserts the sample data

Each validate_* function returns (clean, errors):
  * clean  - a dictionary of cleaned values with the correct Python types
  * errors - a dictionary {field_name: message}; empty when the input is valid
"""

import json
import math
import re

ACCESS_OPTIONS = ("Good", "Moderate", "Poor")

NAME_MIN, NAME_MAX = 2, 100
NOTES_MAX = 500
POPULATION_MAX = 50_000_000
INCOME_MAX = 10_000_000
NEARBY_CENTERS_MAX = 100

CENTER_TYPES = (
    "NGO",
    "Community Kitchen",
    "Food Bank",
    "Charitable Organization",
    "Government Food Support Center",
    "Religious or Community Organization",
    "Food Distribution Center",
    "Other",
)

CONTACT_METHODS = (
    "Phone Call",
    "WhatsApp",
    "Email",
    "Website",
    "Visit in Person",
)

FOOD_SUPPORT_TYPES = (
    "Free Meals",
    "Groceries",
    "Food Packages",
    "Emergency Food Assistance",
    "Community Kitchen",
    "Child Nutrition Support",
    "Elderly Food Assistance",
    "Other",
)

INFO_STATUSES = (
    "Newly Added",
    "Not Contacted",
    "Contacted",
    "Information Partially Verified",
    "Verified",
    "Unable to Reach",
    "Inactive",
)

AVAILABILITY_STATUSES = ("Yes", "No", "Unknown")
REGISTRATION_REQUIRED_OPTIONS = ("Yes", "No", "Unknown")
LOCATION_SOURCES = ("actual", "community_reference", "approximate")

PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-()]{7,20}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def _to_number(value):
    """Convert a value (number or numeric string) to float, or raise ValueError."""
    if isinstance(value, bool):
        raise ValueError("boolean values are not numbers")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        number = float(value.strip().replace(",", ""))
    else:
        raise ValueError("unsupported type")
    if math.isnan(number) or math.isinf(number):
        raise ValueError("number is not finite")
    return number


def _fmt(number):
    if isinstance(number, int):
        return f"{number:,}"
    return f"{number:g}"


def _range_message(label, minimum, maximum):
    if minimum is not None and maximum is not None:
        return f"{label} must be between {_fmt(minimum)} and {_fmt(maximum)}."
    if minimum is not None:
        return f"{label} must be {_fmt(minimum)} or more."
    return f"{label} must be {_fmt(maximum)} or less."


def _read_number(data, key, label, errors, *, required, integer=False,
                 minimum=None, maximum=None):
    """Read one numeric field. Returns the number, or None if missing/invalid."""
    raw = data.get(key)

    if _is_blank(raw):
        if required:
            errors[key] = f"{label} is required."
        return None

    try:
        number = _to_number(raw)
    except (ValueError, TypeError):
        kind = "a whole number" if integer else "a number"
        errors[key] = f"{label} must be {kind}."
        return None

    if integer:
        if number != int(number):
            errors[key] = f"{label} must be a whole number."
            return None
        number = int(number)

    if (minimum is not None and number < minimum) or \
       (maximum is not None and number > maximum):
        errors[key] = _range_message(label, minimum, maximum)
        return None

    return number


def _read_text(data, key, label, errors, *, required, min_len=0, max_len=500):
    raw = data.get(key)
    if _is_blank(raw):
        if required:
            errors[key] = f"{label} is required."
        return None
    text = str(raw).strip()
    if len(text) < min_len:
        errors[key] = f"{label} must be at least {min_len} characters."
        return None
    if len(text) > max_len:
        errors[key] = f"{label} must be {max_len} characters or fewer."
        return None
    return text


# ---------------------------------------------------------------------------
# Community records
# ---------------------------------------------------------------------------
def validate_community(data):
    """Validate one community record. Returns (clean, errors)."""
    if not isinstance(data, dict):
        return None, {"_form": "The request must contain a JSON object."}

    errors = {}
    clean = {}

    clean["name"] = _read_text(data, "name", "Community name", errors,
                               required=True, min_len=NAME_MIN, max_len=NAME_MAX)

    lat = _read_number(data, "latitude", "Latitude", errors,
                       required=True, minimum=-90, maximum=90)
    lon = _read_number(data, "longitude", "Longitude", errors,
                       required=True, minimum=-180, maximum=180)
    clean["latitude"] = round(lat, 6) if lat is not None else None
    clean["longitude"] = round(lon, 6) if lon is not None else None

    clean["population"] = _read_number(
        data, "population", "Population", errors,
        required=True, integer=True, minimum=1, maximum=POPULATION_MAX)

    clean["total_families"] = _read_number(
        data, "total_families", "Total families", errors,
        required=False, integer=True, minimum=1, maximum=POPULATION_MAX)

    clean["families_needing_assistance"] = _read_number(
        data, "families_needing_assistance", "Families needing assistance", errors,
        required=True, integer=True, minimum=0, maximum=POPULATION_MAX)

    clean["avg_household_income"] = _read_number(
        data, "avg_household_income", "Average household income", errors,
        required=False, minimum=0, maximum=INCOME_MAX)

    clean["nearby_centers"] = _read_number(
        data, "nearby_centers", "Nearby food-support centers", errors,
        required=False, integer=True, minimum=0, maximum=NEARBY_CENTERS_MAX)

    # Food accessibility: one of Good / Moderate / Poor, or blank (unknown).
    access_raw = data.get("food_accessibility")
    clean["food_accessibility"] = None
    if not _is_blank(access_raw):
        match = next((o for o in ACCESS_OPTIONS
                      if o.lower() == str(access_raw).strip().lower()), None)
        if match is None:
            errors["food_accessibility"] = "Choose Good, Moderate or Poor, or leave it blank."
        else:
            clean["food_accessibility"] = match

    clean["notes"] = _read_text(data, "notes", "Notes", errors,
                                required=False, max_len=NOTES_MAX)

    # Cross-field checks (only when the individual fields were valid).
    population = clean["population"]
    needing = clean["families_needing_assistance"]
    total = clean["total_families"]

    if population is not None and needing is not None and needing > population:
        errors.setdefault("families_needing_assistance",
                          "Families needing assistance cannot be more than the population.")
    if total is not None:
        if population is not None and total > population:
            errors.setdefault("total_families",
                              "Total families cannot be more than the population.")
        elif needing is not None and total < needing:
            errors.setdefault("total_families",
                              "Total families cannot be fewer than the families needing assistance.")

    return clean, errors


# ---------------------------------------------------------------------------
# Food-support center records (used when loading the sample CSV)
# ---------------------------------------------------------------------------
def validate_center(data):
    """Validate one food-support center record. Returns (clean, errors)."""
    if not isinstance(data, dict):
        return None, {"_form": "The record must be an object."}

    errors = {}
    clean = {}
    clean["name"] = _read_text(data, "name", "Center name", errors,
                               required=True, min_len=2, max_len=100)
    clean["location"] = _read_text(data, "location", "Location", errors,
                                   required=True, max_len=200)
    lat = _read_number(data, "latitude", "Latitude", errors,
                       required=True, minimum=-90, maximum=90)
    lon = _read_number(data, "longitude", "Longitude", errors,
                       required=True, minimum=-180, maximum=180)
    clean["latitude"] = round(lat, 6) if lat is not None else None
    clean["longitude"] = round(lon, 6) if lon is not None else None
    clean["description"] = _read_text(data, "description", "Description", errors,
                                      required=False, max_len=500)
    return clean, errors


# ---------------------------------------------------------------------------
# Comprehensive Food-support center validation
# ---------------------------------------------------------------------------
def _clean_phone(raw):
    if _is_blank(raw):
        return None
    val = str(raw).strip()
    digits = sum(1 for c in val if c.isdigit())
    if not PHONE_PATTERN.match(val) or digits < 7:
        raise ValueError("Enter a valid telephone/mobile number (at least 7 digits).")
    return val


def _clean_url(raw):
    if _is_blank(raw):
        return None
    val = str(raw).strip()
    if not (val.startswith("http://") or val.startswith("https://")):
        val = "https://" + val
    if not URL_PATTERN.match(val):
        raise ValueError("Enter a valid website link (e.g. https://example.org).")
    return val


def _clean_email(raw):
    if _is_blank(raw):
        return None
    val = str(raw).strip()
    if not EMAIL_PATTERN.match(val):
        raise ValueError("Enter a valid email address.")
    return val.lower()


def validate_food_support_center(data, allow_missing_coords=False):
    """
    Validate a food support center registration record.
    Returns (clean, errors).
    """
    if not isinstance(data, dict):
        return None, {"_form": "The request must contain a JSON object."}

    errors = {}
    clean = {}

    # Center name (accept 'center_name' or fallback 'name')
    name_val = data.get("center_name")
    if _is_blank(name_val):
        name_val = data.get("name")
    clean["center_name"] = _read_text({"center_name": name_val}, "center_name", "Center name", errors,
                                      required=True, min_len=2, max_len=150)
    if "center_name" in errors:
        errors["name"] = errors["center_name"]
    clean["name"] = clean["center_name"]

    # Center type
    raw_type = data.get("center_type") or data.get("custom_center_type") or "NGO"
    clean_type = str(raw_type).strip() if raw_type else "NGO"
    if len(clean_type) > 100:
        clean_type = clean_type[:100]
    clean["center_type"] = clean_type or "NGO"

    # Community ID
    clean["community_id"] = _read_number(data, "community_id", "Community", errors,
                                         required=False, integer=True, minimum=1)

    # Address & Location
    clean["address"] = _read_text(data, "address", "Address", errors,
                                  required=False, max_len=500)
    clean["location"] = clean["address"] or ""
    clean["landmark"] = _read_text(data, "landmark", "Landmark", errors,
                                   required=False, max_len=150)
    clean["pincode"] = _read_text(data, "pincode", "Pincode", errors,
                                  required=False, max_len=20)
    clean["district"] = _read_text(data, "district", "District", errors,
                                   required=False, max_len=100)
    clean["state"] = _read_text(data, "state", "State", errors,
                                required=False, max_len=100)
    clean["description"] = _read_text(data, "description", "Description", errors,
                                      required=False, max_len=1000)

    # Location Source
    loc_src = str(data.get("location_source") or "community_reference").strip().lower()
    if loc_src not in LOCATION_SOURCES:
        loc_src = "community_reference"
    clean["location_source"] = loc_src

    # Latitude and Longitude
    has_lat = not _is_blank(data.get("latitude"))
    has_lon = not _is_blank(data.get("longitude"))

    if has_lat or has_lon or not (allow_missing_coords or clean["community_id"]):
        lat = _read_number(data, "latitude", "Latitude", errors,
                           required=True, minimum=-90, maximum=90)
        lon = _read_number(data, "longitude", "Longitude", errors,
                           required=True, minimum=-180, maximum=180)
        clean["latitude"] = round(lat, 6) if lat is not None else None
        clean["longitude"] = round(lon, 6) if lon is not None else None
    else:
        clean["latitude"] = None
        clean["longitude"] = None

    # Contact Details
    clean["primary_contact_name"] = _read_text(data, "primary_contact_name",
                                               "Primary contact name", errors,
                                               required=False, max_len=100)
    clean["contact_designation"] = _read_text(data, "contact_designation",
                                              "Contact designation", errors,
                                              required=False, max_len=100)

    # Primary phone (required)
    raw_phone = data.get("phone_number")
    if _is_blank(raw_phone):
        errors["phone_number"] = "Primary phone number is required."
        clean["phone_number"] = None
    else:
        try:
            clean["phone_number"] = _clean_phone(raw_phone)
        except ValueError as e:
            errors["phone_number"] = str(e)
            clean["phone_number"] = None

    # Alternative phone
    raw_alt = data.get("alternative_phone")
    if not _is_blank(raw_alt):
        try:
            clean["alternative_phone"] = _clean_phone(raw_alt)
        except ValueError as e:
            errors["alternative_phone"] = str(e)
            clean["alternative_phone"] = None
    else:
        clean["alternative_phone"] = None

    # Email
    raw_email = data.get("email")
    if not _is_blank(raw_email):
        try:
            clean["email"] = _clean_email(raw_email)
        except ValueError as e:
            errors["email"] = str(e)
            clean["email"] = None
    else:
        clean["email"] = None

    # Website
    raw_web = data.get("website")
    if not _is_blank(raw_web):
        try:
            clean["website"] = _clean_url(raw_web)
        except ValueError as e:
            errors["website"] = str(e)
            clean["website"] = None
    else:
        clean["website"] = None

    # WhatsApp
    raw_wa = data.get("whatsapp_number")
    if not _is_blank(raw_wa):
        try:
            clean["whatsapp_number"] = _clean_phone(raw_wa)
        except ValueError as e:
            errors["whatsapp_number"] = str(e)
            clean["whatsapp_number"] = None
    else:
        clean["whatsapp_number"] = None

    # Preferred Contact Method
    pref = data.get("preferred_contact_method")
    if not _is_blank(pref):
        clean_pref = str(pref).strip()
        matched_pref = next((m for m in CONTACT_METHODS if m.lower() == clean_pref.lower()), None)
        clean["preferred_contact_method"] = matched_pref or "Phone Call"
    else:
        clean["preferred_contact_method"] = "Phone Call"

    # Food-support details
    food_types = data.get("food_support_types")
    if isinstance(food_types, list):
        clean["food_support_types"] = json.dumps([str(t).strip() for t in food_types if str(t).strip()])
    elif isinstance(food_types, str) and food_types.strip():
        # Could be comma-separated or json string
        try:
            parsed = json.loads(food_types)
            if isinstance(parsed, list):
                clean["food_support_types"] = json.dumps(parsed)
            else:
                clean["food_support_types"] = json.dumps([s.strip() for s in food_types.split(",") if s.strip()])
        except Exception:
            clean["food_support_types"] = json.dumps([s.strip() for s in food_types.split(",") if s.strip()])
    else:
        clean["food_support_types"] = json.dumps([])

    clean["meals_available"] = _read_text(data, "meals_available", "Meals available",
                                          errors, required=False, max_len=200)
    clean["distribution_schedule"] = _read_text(data, "distribution_schedule",
                                                "Distribution schedule", errors,
                                                required=False, max_len=200)
    clean["operating_days"] = _read_text(data, "operating_days", "Operating days",
                                         errors, required=False, max_len=150)
    clean["operating_hours"] = _read_text(data, "operating_hours", "Operating hours",
                                          errors, required=False, max_len=150)
    clean["people_served_per_day"] = _read_number(data, "people_served_per_day",
                                                  "People served per day", errors,
                                                  required=False, integer=True, minimum=0)
    clean["eligibility_requirements"] = _read_text(data, "eligibility_requirements",
                                                   "Eligibility requirements", errors,
                                                   required=False, max_len=300)

    # Registration & Availability
    reg = str(data.get("registration_required") or "Unknown").strip().capitalize()
    clean["registration_required"] = reg if reg in REGISTRATION_REQUIRED_OPTIONS else "Unknown"

    avail = str(data.get("availability_status") or "Unknown").strip().capitalize()
    clean["availability_status"] = avail if avail in AVAILABILITY_STATUSES else "Unknown"

    # Verification & Follow-up
    raw_status = data.get("information_status")
    if not _is_blank(raw_status):
        matched_st = next((s for s in INFO_STATUSES if s.lower() == str(raw_status).strip().lower()), None)
        clean["information_status"] = matched_st or "Newly Added"
    else:
        clean["information_status"] = "Newly Added"

    clean["contact_attempt_date"] = _read_text(data, "contact_attempt_date", "Contact attempt date",
                                               errors, required=False, max_len=30)
    clean["last_contacted_date"] = _read_text(data, "last_contacted_date", "Last contacted date",
                                              errors, required=False, max_len=30)
    clean["next_followup_date"] = _read_text(data, "next_followup_date", "Next follow-up date",
                                             errors, required=False, max_len=30)
    clean["contacted_by"] = _read_text(data, "contacted_by", "Contacted by",
                                       errors, required=False, max_len=100)
    clean["contact_notes"] = _read_text(data, "contact_notes", "Contact notes",
                                        errors, required=False, max_len=1000)
    clean["information_source"] = _read_text(data, "information_source", "Information source",
                                             errors, required=False, max_len=200)
    clean["verification_notes"] = _read_text(data, "verification_notes", "Verification notes",
                                             errors, required=False, max_len=1000)

    return clean, errors
