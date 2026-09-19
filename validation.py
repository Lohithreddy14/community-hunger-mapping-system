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

import math

ACCESS_OPTIONS = ("Good", "Moderate", "Poor")

NAME_MIN, NAME_MAX = 2, 100
NOTES_MAX = 500
POPULATION_MAX = 50_000_000
INCOME_MAX = 10_000_000
NEARBY_CENTERS_MAX = 100


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
