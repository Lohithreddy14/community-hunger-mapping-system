"""
db.py - SQLite database layer.

* The database file is created automatically the first time the app starts
  (or when you run init_db.py).
* The sample data is loaded only ONCE, when the database is first created.
  After that, your own data is never overwritten, so it survives restarts.
"""

import csv
import os
import sqlite3

from flask import current_app, g

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

CREATE TABLE IF NOT EXISTS food_centers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    location    TEXT NOT NULL,
    latitude    REAL NOT NULL CHECK (latitude  BETWEEN -90  AND 90),
    longitude   REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    description TEXT,
    is_sample   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

COMMUNITY_FIELDS = (
    "name", "latitude", "longitude", "population", "total_families",
    "families_needing_assistance", "avg_household_income",
    "food_accessibility", "nearby_centers", "notes",
)


# ---------------------------------------------------------------------------
# Connections
# ---------------------------------------------------------------------------
def get_connection(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
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
# Create the database and load the sample data
# ---------------------------------------------------------------------------
def init_db(path=None, reset=False):
    """
    Create the database if needed.
    Returns True if sample data was loaded during this call, otherwise False.
    """
    path = path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if reset and os.path.exists(path):
        os.remove(path)

    conn = get_connection(path)
    try:
        conn.executescript(SCHEMA)
        # PRAGMA user_version is 0 for a brand-new database. We use it to make
        # sure the sample data is loaded only once.
        version = conn.execute("PRAGMA user_version").fetchone()[0]
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
    """Insert the sample communities and centers (marked is_sample = 1)."""
    for line_no, row in enumerate(_read_csv(COMMUNITIES_CSV), start=2):
        clean, errors = validate_community(row)
        if errors:
            raise ValueError(f"Invalid row {line_no} in sample_communities.csv: {errors}")
        insert_community(conn, clean, is_sample=True)

    for line_no, row in enumerate(_read_csv(CENTERS_CSV), start=2):
        clean, errors = validate_center(row)
        if errors:
            raise ValueError(f"Invalid row {line_no} in sample_centers.csv: {errors}")
        conn.execute(
            """INSERT INTO food_centers (name, location, latitude, longitude, description, is_sample)
               VALUES (:name, :location, :latitude, :longitude, :description, 1)""",
            clean,
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
