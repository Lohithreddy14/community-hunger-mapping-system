"""
scoring.py - preliminary vulnerability scoring for the Community Hunger Mapping System.

IMPORTANT: this is a simple, transparent ACADEMIC model. It does not measure hunger
and it has not been validated against real-world data. It only produces an
*estimated relative vulnerability category* from the indicators a user has entered.

How it works (see documentation/methodology.md for a worked example)
--------------------------------------------------------------------
1. Every indicator is converted to a RISK VALUE between 0 (lowest concern) and
   100 (highest concern).
2. Each indicator has a WEIGHT. The weights add up to 1.0.
3. If an indicator is missing, it is skipped and the remaining weights are
   re-scaled so they add up to 1.0 again. Nothing is invented for missing values.
4. score = sum(weight_i x risk_i) over the available indicators   (0 - 100)
5. score < 35        -> Lower    (green)
   35 <= score < 65  -> Moderate (yellow)
   score >= 65       -> Higher   (red)
"""

from math import asin, cos, radians, sin, sqrt

# ---------------------------------------------------------------------------
# Model parameters (all in one place so they are easy to explain and change)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "need": 0.45,      # share of families reported as needing food assistance
    "access": 0.25,    # food accessibility rating
    "centers": 0.20,   # number of nearby food-support centers
    "income": 0.10,    # average household income (optional)
}

# Assumption used ONLY when the total number of families is not entered.
HOUSEHOLD_SIZE_ASSUMPTION = 4.5

# Indicator 1: if 40% (or more) of families need assistance, risk is 100.
NEED_FULL_RISK_PCT = 40.0

# Indicator 2: food accessibility rating -> risk value.
ACCESS_RISK = {"Good": 0.0, "Moderate": 50.0, "Poor": 100.0}

# Indicator 3: nearby food-support centers -> risk value (3 or more = 0).
CENTERS_RISK = {0: 100.0, 1: 60.0, 2: 30.0}

# Indicator 4: monthly household income in rupees (linear between the two limits).
INCOME_HIGH_RISK_AT_OR_BELOW = 10_000.0
INCOME_LOW_RISK_AT_OR_ABOVE = 40_000.0

# Category boundaries.
LOWER_BELOW = 35.0
HIGHER_FROM = 65.0

CATEGORIES = {
    "lower": {
        "key": "lower", "label": "Lower", "color": "green",
        "description": "Lower estimated vulnerability",
    },
    "moderate": {
        "key": "moderate", "label": "Moderate", "color": "yellow",
        "description": "Moderate estimated vulnerability",
    },
    "higher": {
        "key": "higher", "label": "Higher", "color": "red",
        "description": "Higher estimated vulnerability",
    },
}

DISCLAIMER = (
    "Preliminary academic model. It gives an estimated relative vulnerability "
    "category from the indicators entered; it does not measure hunger and has not "
    "been validated with reliable real-world data."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def categorize(score):
    """Convert a 0-100 score into one of the three map categories."""
    if score < LOWER_BELOW:
        return CATEGORIES["lower"]
    if score < HIGHER_FROM:
        return CATEGORIES["moderate"]
    return CATEGORIES["higher"]


def centers_risk(count):
    """Risk value for the number of nearby food-support centers."""
    return CENTERS_RISK.get(count, 0.0)  # 3 or more centers -> 0


def income_risk(income):
    """Risk value (0-100) for monthly household income."""
    span = INCOME_LOW_RISK_AT_OR_ABOVE - INCOME_HIGH_RISK_AT_OR_BELOW
    risk = (INCOME_LOW_RISK_AT_OR_ABOVE - income) / span * 100.0
    return max(0.0, min(100.0, risk))


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometres."""
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(a))


def nearest_center(community, centers):
    """Nearest listed food-support center (information only - not used in the score)."""
    best = None
    for center in centers or []:
        distance = haversine_km(community["latitude"], community["longitude"],
                                center["latitude"], center["longitude"])
        if best is None or distance < best["distance_km"]:
            best = {"id": center["id"], "name": center["name"],
                    "distance_km": round(distance, 1)}
    return best


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------
def analyse_community(community, centers=None):
    """
    Analyse one community record (a dict) and return the score, category and a
    full indicator breakdown.
    """
    population = community["population"]
    needing = community["families_needing_assistance"]
    total_families = community.get("total_families")

    # --- Indicator 1: percentage of families needing assistance -------------
    if total_families:
        households = float(total_families)
        basis = "reported"
        need_detail = f"{needing:,} of {total_families:,} families (total reported)"
    else:
        households = population / HOUSEHOLD_SIZE_ASSUMPTION
        basis = "estimated"
        need_detail = (f"{needing:,} of about {round(households):,} families "
                       f"(estimated as population / {HOUSEHOLD_SIZE_ASSUMPTION:g})")
    pct_need = min(needing / households * 100.0, 100.0)
    need_risk = min(pct_need / NEED_FULL_RISK_PCT, 1.0) * 100.0

    indicators = [{
        "key": "need", "label": "Families needing assistance",
        "value": f"{pct_need:.1f}%", "detail": need_detail, "risk": need_risk,
    }]

    # --- Indicator 2: food accessibility ------------------------------------
    access = community.get("food_accessibility")
    indicators.append({
        "key": "access", "label": "Food accessibility",
        "value": access if access else "Not provided",
        "detail": "Good = 0, Moderate = 50, Poor = 100" if access else "Skipped - no rating entered",
        "risk": ACCESS_RISK.get(access) if access else None,
    })

    # --- Indicator 3: nearby food-support centers ---------------------------
    nearby = community.get("nearby_centers")
    indicators.append({
        "key": "centers", "label": "Nearby food-support centers",
        "value": str(nearby) if nearby is not None else "Not provided",
        "detail": "0 = 100, 1 = 60, 2 = 30, 3 or more = 0" if nearby is not None
                  else "Skipped - no count entered",
        "risk": centers_risk(nearby) if nearby is not None else None,
    })

    # --- Indicator 4: average household income ------------------------------
    income = community.get("avg_household_income")
    indicators.append({
        "key": "income", "label": "Average household income",
        "value": f"Rs. {income:,.0f} per month" if income is not None else "Not provided",
        "detail": (f"Rs. {INCOME_HIGH_RISK_AT_OR_BELOW:,.0f} or less = 100, "
                   f"Rs. {INCOME_LOW_RISK_AT_OR_ABOVE:,.0f} or more = 0")
                  if income is not None else "Skipped - no income entered",
        "risk": income_risk(income) if income is not None else None,
    })

    # --- Combine: weighted average of the available indicators --------------
    available_weight = sum(WEIGHTS[i["key"]] for i in indicators if i["risk"] is not None)
    score = 0.0
    for indicator in indicators:
        weight = WEIGHTS[indicator["key"]]
        indicator["weight"] = weight
        indicator["available"] = indicator["risk"] is not None
        if indicator["available"]:
            effective = weight / available_weight
            indicator["effective_weight"] = round(effective, 3)
            indicator["contribution"] = round(effective * indicator["risk"], 2)
            score += effective * indicator["risk"]
            indicator["risk"] = round(indicator["risk"], 1)
        else:
            indicator["effective_weight"] = 0.0
            indicator["contribution"] = 0.0

    score = round(score, 1)
    used = sum(1 for i in indicators if i["available"])

    return {
        "score": score,
        "category": categorize(score),
        "indicators": indicators,
        "indicators_used": used,
        "indicators_total": len(indicators),
        "pct_need": round(pct_need, 1),
        "households": round(households),
        "households_basis": basis,
        "nearest_center": nearest_center(community, centers),
    }


# ---------------------------------------------------------------------------
# Description of the method (returned by GET /api/analysis, shown on the dashboard)
# ---------------------------------------------------------------------------
def methodology():
    return {
        "title": "Preliminary vulnerability score",
        "disclaimer": DISCLAIMER,
        "formula": "score = sum(weight x risk value) over the available indicators, "
                   "with weights re-scaled when an indicator is missing",
        "indicators": [
            {"key": "need", "label": "Families needing assistance", "weight": WEIGHTS["need"],
             "rule": f"Share of families needing assistance; {NEED_FULL_RISK_PCT:g}% or more "
                     f"scores 100, scaled linearly below that."},
            {"key": "access", "label": "Food accessibility", "weight": WEIGHTS["access"],
             "rule": "Good scores 0, Moderate 50, Poor 100."},
            {"key": "centers", "label": "Nearby food-support centers", "weight": WEIGHTS["centers"],
             "rule": "0 centers scores 100, 1 scores 60, 2 scores 30, 3 or more scores 0."},
            {"key": "income", "label": "Average household income", "weight": WEIGHTS["income"],
             "rule": f"Monthly income of Rs. {INCOME_HIGH_RISK_AT_OR_BELOW:,.0f} or less scores 100, "
                     f"Rs. {INCOME_LOW_RISK_AT_OR_ABOVE:,.0f} or more scores 0, linear in between."},
        ],
        "thresholds": {
            "lower_below": LOWER_BELOW,
            "higher_from": HIGHER_FROM,
            "text": f"Below {LOWER_BELOW:g} is Lower (green); {LOWER_BELOW:g} to below "
                    f"{HIGHER_FROM:g} is Moderate (yellow); {HIGHER_FROM:g} or above is Higher (red).",
        },
        "household_size_assumption": HOUSEHOLD_SIZE_ASSUMPTION,
        "missing_values": "Missing indicators are skipped and the remaining weights are "
                          "re-scaled. If total families is blank, it is estimated as "
                          f"population / {HOUSEHOLD_SIZE_ASSUMPTION:g}.",
    }
