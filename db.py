"""
db.py - SQLite database layer.

* Automatically manages the database schema and migrations.
* Stores communities and food-support centers in SQLite.
* Retains compatibility with legacy queries and views.
* Sample data is loaded once and user records survive restarts.
"""

import csv
import json
import os
import sqlite3

from flask import current_app, g

from scoring import haversine_km
from validation import validate_center, validate_community

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "community_hunger.db")
COMMUNITIES_CSV = os.path.join(BASE_DIR, "data", "sample_communities.csv")
CENTERS_CSV = os.path.join(BASE_DIR, "data", "sample_centers.csv")

SCHEMA = """
CREATE TABLE IF NOT EXISTS communities (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    name                        TEXT    NOT NULL,
    latitude                    REAL    NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude                   REAL    NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    population                  INTEGER NOT NULL CHECK (population > 0),
    total_families              INTEGER CHECK (total_families IS NULL OR total_families > 0),
    families_needing_assistance INTEGER NOT NULL CHECK (families_needing_assistance >= 0),
    avg_household_income        REAL    CHECK (avg_household_income IS NULL OR avg_household_income >= 0),
    food_accessibility          TEXT    CHECK (food_accessibility IS NULL
                                               OR food_accessibility IN ('Good', 'Moderate', 'Poor')),
    nearby_centers              INTEGER CHECK (nearby_centers IS NULL OR nearby_centers >= 0),
    notes                       TEXT,
    is_sample                   INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at                  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS food_support_centers (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    center_name                 TEXT    NOT NULL,
    name                        TEXT    NOT NULL,
    center_type                 TEXT    NOT NULL DEFAULT 'NGO',
    description                 TEXT,
    address                     TEXT,
    location                    TEXT,
    community_id                INTEGER REFERENCES communities(id) ON DELETE SET NULL,
    landmark                    TEXT,
    pincode                     TEXT,
    district                    TEXT,
    state                       TEXT,
    latitude                    REAL    NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude                   REAL    NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    location_source             TEXT    NOT NULL DEFAULT 'community_reference'
                                        CHECK (location_source IN ('actual', 'community_reference', 'approximate')),
    primary_contact_name        TEXT,
    contact_designation         TEXT,
    phone_number                TEXT    NOT NULL,
    alternative_phone           TEXT,
    email                       TEXT,
    website                     TEXT,
    whatsapp_number             TEXT,
    preferred_contact_method    TEXT    DEFAULT 'Phone Call',
    food_support_types          TEXT,
    meals_available             TEXT,
    distribution_schedule       TEXT,
    operating_days              TEXT,
    operating_hours             TEXT,
    people_served_per_day       INTEGER CHECK (people_served_per_day IS NULL OR people_served_per_day >= 0),
    eligibility_requirements    TEXT,
    registration_required       TEXT    DEFAULT 'Unknown' CHECK (registration_required IN ('Yes', 'No', 'Unknown')),
    availability_status         TEXT    DEFAULT 'Unknown' CHECK (availability_status IN ('Yes', 'No', 'Unknown')),
    information_status          TEXT    NOT NULL DEFAULT 'Newly Added'
                                        CHECK (information_status IN (
                                            'Newly Added', 'Not Contacted', 'Contacted',
                                            'Information Partially Verified', 'Verified',
                                            'Unable to Reach', 'Inactive'
                                        )),
    contact_attempt_date        TEXT,
    last_contacted_date         TEXT,
    next_followup_date          TEXT,
    contacted_by                TEXT,
    contact_notes               TEXT,
    information_source          TEXT,
    verification_notes          TEXT,
    is_sample                   INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at                  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

VIEW_AND_TRIGGER = """
CREATE VIEW IF NOT EXISTS food_centers AS
SELECT id, center_name AS name, COALESCE(address, location, '') AS location,
       latitude, longitude, description, is_sample, created_at
FROM food_support_centers;

CREATE TRIGGER IF NOT EXISTS trg_food_centers_insert
INSTEAD OF INSERT ON food_centers
FOR EACH ROW
BEGIN
    INSERT INTO food_support_centers (
        center_name, name, address, location, latitude, longitude,
        description, is_sample, phone_number, information_status
    ) VALUES (
        NEW.name, NEW.name, NEW.location, NEW.location, NEW.latitude, NEW.longitude,
        NEW.description, NEW.is_sample, '+91 98765 00000', 'Verified'
    );
END;
"""

COMMUNITY_FIELDS = (
    "name", "latitude", "longitude", "population", "total_families",
    "families_needing_assistance", "avg_household_income",
    "food_accessibility", "nearby_centers", "notes",
)

CENTER_FIELDS = (
    "center_name", "center_type", "description", "address", "location",
    "community_id", "landmark", "pincode", "district", "state",
    "latitude", "longitude", "location_source",
    "primary_contact_name", "contact_designation", "phone_number",
    "alternative_phone", "email", "website", "whatsapp_number",
    "preferred_contact_method", "food_support_types", "meals_available",
    "distribution_schedule", "operating_days", "operating_hours",
    "people_served_per_day", "eligibility_requirements",
    "registration_required", "availability_status", "information_status",
    "contact_attempt_date", "last_contacted_date", "next_followup_date",
    "contacted_by", "contact_notes", "information_source", "verification_notes",
)


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------
def get_connection(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Return the database connection for the current Flask request."""
    if "db" not in g:
        g.db = get_connection(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# ---------------------------------------------------------------------------
# Safe Migration and Database Setup
# ---------------------------------------------------------------------------
def migrate_database(conn):
    """
    Ensure food_support_centers table exists and migrate data from legacy
    food_centers table if present.
    """
    # 1. Base tables
    conn.executescript(SCHEMA)

    master_info = conn.execute(
        "SELECT name, type FROM sqlite_master WHERE name IN ('food_centers', 'food_support_centers')"
    ).fetchall()
    tables = {r["name"]: r["type"] for r in master_info}

    # If food_centers is a physical table (legacy), migrate its records
    if tables.get("food_centers") == "table":
        old_rows = conn.execute("SELECT * FROM food_centers").fetchall()
        for row in old_rows:
            r = dict(row)
            conn.execute(
                """INSERT OR IGNORE INTO food_support_centers (
                    id, center_name, name, address, location, latitude, longitude,
                    description, is_sample, phone_number, information_status,
                    location_source, created_at, updated_at
                ) VALUES (
                    :id, :name, :name, :location, :location, :latitude, :longitude,
                    :description, :is_sample, '+91 98450 12345', 'Verified',
                    'actual', :created_at, :created_at
                )""",
                r,
            )
        conn.execute("DROP TABLE food_centers")

    # 2. View and trigger for food_centers
    conn.executescript(VIEW_AND_TRIGGER)
    conn.commit()


def init_db(path=None, reset=False):
    """
    Create or upgrade the database if needed.
    Returns True if sample data was loaded during this call, otherwise False.
    """
    path = path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if reset and os.path.exists(path):
        os.remove(path)

    conn = get_connection(path)
    try:
        # Check if already initialized
        version_row = conn.execute("PRAGMA user_version").fetchone()
        version = version_row[0] if version_row else 0

        migrate_database(conn)

        if version == 0:
            load_sample_data(conn)
            conn.execute("PRAGMA user_version = 1")
            conn.commit()
            return True
        return False
    finally:
        conn.close()


def _read_csv(path):
    if not os.path.exists(path):
        print(f"Warning: sample file not found: {path}")
        return []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_sample_data(conn):
    """Insert the sample communities and rich food-support centers (marked is_sample = 1)."""
    # 1. Insert sample communities
    for line_no, row in enumerate(_read_csv(COMMUNITIES_CSV), start=2):
        clean, errors = validate_community(row)
        if errors:
            raise ValueError(f"Invalid row {line_no} in sample_communities.csv: {errors}")
        insert_community(conn, clean, is_sample=True)

    # 2. Insert sample centers with rich, realistic demonstration attributes
    sample_centers_meta = [
        {
            "center_type": "Food Bank",
            "community_id": 1,
            "landmark": "Near Central Market Metro Station",
            "pincode": "560001",
            "district": "Bengaluru Urban",
            "state": "Karnataka",
            "primary_contact_name": "Rajesh Kumar",
            "contact_designation": "Facility Coordinator",
            "phone_number": "+91 98450 11001",
            "alternative_phone": "+91 80 2234 5678",
            "email": "contact@centralfoodbank.sample.org",
            "website": "https://example.org/central-foodbank",
            "whatsapp_number": "+91 98450 11001",
            "preferred_contact_method": "Phone Call",
            "food_support_types": json.dumps(["Groceries", "Food Packages", "Emergency Food Assistance"]),
            "meals_available": "Dry Rations (Rice, Wheat, Pulses, Cooking Oil)",
            "distribution_schedule": "Wednesdays & Saturdays: 10:00 AM - 1:00 PM",
            "operating_days": "Monday - Saturday",
            "operating_hours": "9:30 AM - 5:30 PM",
            "people_served_per_day": 120,
            "eligibility_requirements": "Open to low-income families and ration card holders",
            "registration_required": "Yes",
            "availability_status": "Yes",
            "information_status": "Verified",
            "location_source": "actual",
            "last_contacted_date": "2026-09-15",
            "contacted_by": "System Admin",
            "contact_notes": "Sample verified partner organisation.",
            "information_source": "Sample Demonstration Dataset",
            "verification_notes": "SAMPLE DATA - fictional demonstration center."
        },
        {
            "center_type": "Community Kitchen",
            "community_id": 2,
            "landmark": "Opposite Community Park",
            "pincode": "560034",
            "district": "Bengaluru Urban",
            "state": "Karnataka",
            "primary_contact_name": "Meenakshi Sundaram",
            "contact_designation": "Kitchen Supervisor",
            "phone_number": "+91 98450 11002",
            "email": "kitchen@neighbourhoodcare.sample.org",
            "website": "https://example.org/neighbourhood-kitchen",
            "whatsapp_number": "+91 98450 11002",
            "preferred_contact_method": "WhatsApp",
            "food_support_types": json.dumps(["Free Meals", "Community Kitchen"]),
            "meals_available": "Hot Lunch (Rice, Sambar, Vegetables)",
            "distribution_schedule": "Daily: 12:30 PM - 2:30 PM",
            "operating_days": "Every Day",
            "operating_hours": "11:00 AM - 3:30 PM",
            "people_served_per_day": 250,
            "eligibility_requirements": "Open to all without restrictions",
            "registration_required": "No",
            "availability_status": "Yes",
            "information_status": "Verified",
            "location_source": "actual",
            "last_contacted_date": "2026-09-18",
            "contacted_by": "Field Officer Ananya",
            "contact_notes": "Community kitchen operating smoothly.",
            "information_source": "Sample Demonstration Dataset",
            "verification_notes": "SAMPLE DATA - fictional demonstration center."
        },
        {
            "center_type": "Charitable Organization",
            "community_id": 4,
            "landmark": "Near Riverside Bridge",
            "pincode": "560061",
            "district": "Bengaluru Urban",
            "state": "Karnataka",
            "primary_contact_name": "Father Joseph",
            "contact_designation": "Relief Director",
            "phone_number": "+91 98450 11003",
            "email": "riverside.relief@sample.org",
            "whatsapp_number": "+91 98450 11003",
            "preferred_contact_method": "Phone Call",
            "food_support_types": json.dumps(["Emergency Food Assistance", "Food Packages"]),
            "meals_available": "Weekend Rations & Emergency Food Packs",
            "distribution_schedule": "Saturdays & Sundays: 11:00 AM - 3:00 PM",
            "operating_days": "Weekends",
            "operating_hours": "10:00 AM - 4:00 PM",
            "people_served_per_day": 80,
            "eligibility_requirements": "Needy families in the settlement area",
            "registration_required": "No",
            "availability_status": "Yes",
            "information_status": "Verified",
            "location_source": "actual",
            "last_contacted_date": "2026-09-10",
            "contacted_by": "Reviewer Team",
            "contact_notes": "Volunteer team coordinates weekend supplies.",
            "information_source": "Sample Demonstration Dataset",
            "verification_notes": "SAMPLE DATA - fictional demonstration center."
        },
        {
            "center_type": "Government Food Support Center",
            "community_id": 6,
            "landmark": "Near Ward Office",
            "pincode": "560092",
            "district": "Bengaluru Urban",
            "state": "Karnataka",
            "primary_contact_name": "S. Narayana",
            "contact_designation": "Centre In-Charge",
            "phone_number": "+91 98450 11004",
            "preferred_contact_method": "Phone Call",
            "food_support_types": json.dumps(["Groceries", "Food Packages"]),
            "meals_available": "Subsidised Grain & Essential Commodities",
            "distribution_schedule": "1st to 15th of each month: 9:00 AM - 1:00 PM",
            "operating_days": "Monday - Saturday",
            "operating_hours": "9:00 AM - 1:00 PM, 3:00 PM - 6:00 PM",
            "people_served_per_day": 300,
            "eligibility_requirements": "Valid Government food security / ration card holders",
            "registration_required": "Yes",
            "availability_status": "Yes",
            "information_status": "Verified",
            "location_source": "actual",
            "last_contacted_date": "2026-09-12",
            "contacted_by": "System Admin",
            "contact_notes": "Government subsidised distribution center.",
            "information_source": "Sample Demonstration Dataset",
            "verification_notes": "SAMPLE DATA - fictional demonstration center."
        },
        {
            "center_type": "NGO",
            "community_id": 7,
            "landmark": "Near Wholesale Market Gate 3",
            "pincode": "560037",
            "district": "Bengaluru Urban",
            "state": "Karnataka",
            "primary_contact_name": "Dr. Sunita Rao",
            "contact_designation": "Programme Lead",
            "phone_number": "+91 98450 11005",
            "alternative_phone": "+91 98450 99005",
            "email": "sunita@eastside-meals.sample.org",
            "website": "https://example.org/eastside-meals",
            "whatsapp_number": "+91 98450 11005",
            "preferred_contact_method": "Email",
            "food_support_types": json.dumps(["Child Nutrition Support", "Elderly Food Assistance", "Free Meals"]),
            "meals_available": "Nutritious Breakfast & Warm Lunch for Children and Elders",
            "distribution_schedule": "Daily: 8:00 AM - 9:30 AM (Breakfast), 12:30 PM - 2:00 PM (Lunch)",
            "operating_days": "Monday - Saturday",
            "operating_hours": "7:30 AM - 4:00 PM",
            "people_served_per_day": 180,
            "eligibility_requirements": "Prioritises school-age children and senior citizens",
            "registration_required": "No",
            "availability_status": "Yes",
            "information_status": "Verified",
            "location_source": "actual",
            "last_contacted_date": "2026-09-20",
            "contacted_by": "Field Officer Ananya",
            "contact_notes": "High nutritional standards maintained.",
            "information_source": "Sample Demonstration Dataset",
            "verification_notes": "SAMPLE DATA - fictional demonstration center."
        }
    ]

    for idx, row in enumerate(_read_csv(CENTERS_CSV)):
        clean, errors = validate_center(row)
        if errors:
            raise ValueError(f"Invalid row {idx + 2} in sample_centers.csv: {errors}")

        meta = sample_centers_meta[idx] if idx < len(sample_centers_meta) else {}
        values = {
            "center_name": clean["name"],
            "name": clean["name"],
            "center_type": meta.get("center_type", "NGO"),
            "description": clean.get("description"),
            "address": clean["location"],
            "location": clean["location"],
            "community_id": meta.get("community_id"),
            "landmark": meta.get("landmark"),
            "pincode": meta.get("pincode"),
            "district": meta.get("district"),
            "state": meta.get("state"),
            "latitude": clean["latitude"],
            "longitude": clean["longitude"],
            "location_source": meta.get("location_source", "actual"),
            "primary_contact_name": meta.get("primary_contact_name"),
            "contact_designation": meta.get("contact_designation"),
            "phone_number": meta.get("phone_number", "+91 98450 12345"),
            "alternative_phone": meta.get("alternative_phone"),
            "email": meta.get("email"),
            "website": meta.get("website"),
            "whatsapp_number": meta.get("whatsapp_number"),
            "preferred_contact_method": meta.get("preferred_contact_method", "Phone Call"),
            "food_support_types": meta.get("food_support_types", json.dumps(["Free Meals"])),
            "meals_available": meta.get("meals_available"),
            "distribution_schedule": meta.get("distribution_schedule"),
            "operating_days": meta.get("operating_days"),
            "operating_hours": meta.get("operating_hours"),
            "people_served_per_day": meta.get("people_served_per_day"),
            "eligibility_requirements": meta.get("eligibility_requirements"),
            "registration_required": meta.get("registration_required", "No"),
            "availability_status": meta.get("availability_status", "Yes"),
            "information_status": meta.get("information_status", "Verified"),
            "contact_attempt_date": meta.get("contact_attempt_date"),
            "last_contacted_date": meta.get("last_contacted_date"),
            "next_followup_date": meta.get("next_followup_date"),
            "contacted_by": meta.get("contacted_by"),
            "contact_notes": meta.get("contact_notes"),
            "information_source": meta.get("information_source", "Sample Demonstration Dataset"),
            "verification_notes": meta.get("verification_notes", "SAMPLE DATA - fictional demonstration center."),
            "is_sample": 1,
        }

        cols = ", ".join(values.keys())
        placeholders = ", ".join(f":{k}" for k in values.keys())
        conn.execute(
            f"INSERT INTO food_support_centers ({cols}) VALUES ({placeholders})",
            values,
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Community queries
# ---------------------------------------------------------------------------
def insert_community(conn, clean, is_sample=False):
    """Insert a validated community record and return its new id."""
    values = {field: clean.get(field) for field in COMMUNITY_FIELDS}
    values["is_sample"] = 1 if is_sample else 0
    cursor = conn.execute(
        """INSERT INTO communities
              (name, latitude, longitude, population, total_families,
               families_needing_assistance, avg_household_income,
               food_accessibility, nearby_centers, notes, is_sample)
           VALUES
              (:name, :latitude, :longitude, :population, :total_families,
               :families_needing_assistance, :avg_household_income,
               :food_accessibility, :nearby_centers, :notes, :is_sample)""",
        values,
    )
    conn.commit()
    return cursor.lastrowid


def update_community(conn, community_id, clean):
    """Update a community record. Returns True if a row was changed."""
    values = {field: clean.get(field) for field in COMMUNITY_FIELDS}
    values["id"] = community_id
    cursor = conn.execute(
        """UPDATE communities SET
              name = :name, latitude = :latitude, longitude = :longitude,
              population = :population, total_families = :total_families,
              families_needing_assistance = :families_needing_assistance,
              avg_household_income = :avg_household_income,
              food_accessibility = :food_accessibility,
              nearby_centers = :nearby_centers, notes = :notes,
              updated_at = datetime('now', 'localtime')
           WHERE id = :id""",
        values,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_community(conn, community_id):
    """Delete a community record. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM communities WHERE id = ?", (community_id,))
    conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Food-Support Center queries
# ---------------------------------------------------------------------------
def format_center_row(row):
    """Convert an SQLite Row for a center to a Python dictionary with distance."""
    if row is None:
        return None
    d = dict(row)
    d["is_sample"] = bool(d.get("is_sample", 0))

    # Parse food_support_types JSON if string
    fst = d.get("food_support_types")
    if isinstance(fst, str) and fst.strip():
        try:
            d["food_support_types_list"] = json.loads(fst)
        except Exception:
            d["food_support_types_list"] = [t.strip() for t in fst.split(",") if t.strip()]
    elif isinstance(fst, list):
        d["food_support_types_list"] = fst
    else:
        d["food_support_types_list"] = []

    # Calculate distance to associated community if coordinates are available
    c_lat = d.get("community_latitude")
    c_lon = d.get("community_longitude")
    lat = d.get("latitude")
    lon = d.get("longitude")

    if c_lat is not None and c_lon is not None and lat is not None and lon is not None:
        if d.get("location_source") == "community_reference":
            d["distance_to_community_km"] = 0.0
            d["is_provisional_location"] = True
        else:
            dist = haversine_km(lat, lon, c_lat, c_lon)
            d["distance_to_community_km"] = round(dist, 2)
            d["is_provisional_location"] = False
    else:
        d["distance_to_community_km"] = None
        d["is_provisional_location"] = d.get("location_source") == "community_reference"

    return d


def insert_center(conn, clean, is_sample=False):
    """Insert a validated food-support center record and return its new id."""
    values = {field: clean.get(field) for field in CENTER_FIELDS}
    values["name"] = clean.get("center_name")
    values["location"] = clean.get("address") or ""
    values["is_sample"] = 1 if is_sample else 0

    cols = ", ".join(["name", "location", "is_sample"] + list(CENTER_FIELDS))
    placeholders = ", ".join([":name", ":location", ":is_sample"] + [f":{f}" for f in CENTER_FIELDS])

    cursor = conn.execute(
        f"INSERT INTO food_support_centers ({cols}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    return cursor.lastrowid


def update_center(conn, center_id, clean):
    """Update a food-support center record. Returns True if a row was changed."""
    values = {field: clean.get(field) for field in CENTER_FIELDS}
    values["name"] = clean.get("center_name")
    values["location"] = clean.get("address") or ""
    values["id"] = center_id

    set_clauses = [f"{f} = :{f}" for f in CENTER_FIELDS]
    set_clauses.extend(["name = :name", "location = :location", "updated_at = datetime('now', 'localtime')"])

    cursor = conn.execute(
        f"UPDATE food_support_centers SET {', '.join(set_clauses)} WHERE id = :id",
        values,
    )
    conn.commit()
    return cursor.rowcount > 0


def update_center_status(conn, center_id, status_data):
    """Update verification / contact status for a center."""
    allowed = (
        "information_status", "availability_status", "contact_attempt_date",
        "last_contacted_date", "next_followup_date", "contacted_by",
        "contact_notes", "information_source", "verification_notes",
    )
    updates = {k: v for k, v in status_data.items() if k in allowed}
    if not updates:
        return False

    updates["id"] = center_id
    clauses = [f"{k} = :{k}" for k in updates.keys() if k != "id"]
    clauses.append("updated_at = datetime('now', 'localtime')")

    cursor = conn.execute(
        f"UPDATE food_support_centers SET {', '.join(clauses)} WHERE id = :id",
        updates,
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_center(conn, center_id):
    """Delete a food-support center record. Returns True if deleted."""
    cursor = conn.execute("DELETE FROM food_support_centers WHERE id = ?", (center_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_center(conn, center_id):
    """Get single center by ID with joined community details."""
    query = """
    SELECT c.*,
           com.name AS community_name,
           com.latitude AS community_latitude,
           com.longitude AS community_longitude
    FROM food_support_centers c
    LEFT JOIN communities com ON c.community_id = com.id
    WHERE c.id = ?
    """
    row = conn.execute(query, (center_id,)).fetchone()
    return format_center_row(row)


def list_centers(conn, filters=None):
    """List centers with optional search and filters."""
    filters = filters or {}
    clauses = []
    params = []

    if filters.get("search"):
        s = f"%{filters['search'].strip()}%"
        clauses.append("(c.center_name LIKE ? OR c.description LIKE ? OR c.address LIKE ? OR c.primary_contact_name LIKE ?)")
        params.extend([s, s, s, s])

    if filters.get("community_id"):
        clauses.append("c.community_id = ?")
        params.append(filters["community_id"])

    if filters.get("center_type") and filters["center_type"] != "all":
        clauses.append("c.center_type = ?")
        params.append(filters["center_type"])

    if filters.get("information_status") and filters["information_status"] != "all":
        clauses.append("c.information_status = ?")
        params.append(filters["information_status"])

    if filters.get("availability_status") and filters["availability_status"] != "all":
        clauses.append("c.availability_status = ?")
        params.append(filters["availability_status"])

    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"""
    SELECT c.*,
           com.name AS community_name,
           com.latitude AS community_latitude,
           com.longitude AS community_longitude
    FROM food_support_centers c
    LEFT JOIN communities com ON c.community_id = com.id
    {where_sql}
    ORDER BY c.is_sample ASC, c.id DESC
    """
    rows = conn.execute(query, params).fetchall()
    return [format_center_row(r) for r in rows]


def get_center_stats(conn):
    """Return summary statistics about registered food-support centers."""
    rows = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN information_status = 'Verified' THEN 1 ELSE 0 END) AS verified,
            SUM(CASE WHEN information_status IN ('Newly Added', 'Not Contacted') THEN 1 ELSE 0 END) AS awaiting_contact,
            SUM(CASE WHEN information_status = 'Information Partially Verified' THEN 1 ELSE 0 END) AS incomplete,
            SUM(CASE WHEN information_status = 'Inactive' THEN 1 ELSE 0 END) AS inactive,
            SUM(CASE WHEN is_sample = 1 THEN 1 ELSE 0 END) AS sample_centers,
            SUM(CASE WHEN is_sample = 0 THEN 1 ELSE 0 END) AS user_centers
        FROM food_support_centers
    """).fetchone()

    stats = dict(rows) if rows else {
        "total": 0, "verified": 0, "awaiting_contact": 0,
        "incomplete": 0, "inactive": 0, "sample_centers": 0, "user_centers": 0
    }

    recent_rows = conn.execute("""
        SELECT c.*, com.name AS community_name
        FROM food_support_centers c
        LEFT JOIN communities com ON c.community_id = com.id
        ORDER BY c.id DESC
        LIMIT 5
    """).fetchall()

    return {
        "total": stats["total"] or 0,
        "verified": stats["verified"] or 0,
        "awaiting_contact": stats["awaiting_contact"] or 0,
        "incomplete": stats["incomplete"] or 0,
        "inactive": stats["inactive"] or 0,
        "sample_centers": stats["sample_centers"] or 0,
        "user_centers": stats["user_centers"] or 0,
        "recent": [format_center_row(r) for r in recent_rows],
    }
