"""
init_db.py - create the SQLite database and load the sample data.

Usage (Windows Command Prompt or PowerShell, with the virtual environment active):

    python init_db.py            Create the database if it does not exist yet.
                                 If it already exists, nothing is changed.
    python init_db.py --reset    DELETE the existing database and rebuild it
                                 with the original sample data.

Note: running this script is optional. app.py creates the database
automatically the first time it starts.
"""

import argparse
import os
import sqlite3
import sys

import db


def count_rows(path):
    conn = sqlite3.connect(path)
    try:
        communities = conn.execute("SELECT COUNT(*) FROM communities").fetchone()[0]
        samples = conn.execute(
            "SELECT COUNT(*) FROM communities WHERE is_sample = 1").fetchone()[0]
        centers = conn.execute("SELECT COUNT(*) FROM food_centers").fetchone()[0]
        return communities, samples, centers
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Create or reset the project database.")
    parser.add_argument("--reset", action="store_true",
                        help="delete the existing database and rebuild it with sample data")
    args = parser.parse_args()

    existed = os.path.exists(db.DB_PATH)

    try:
        loaded = db.init_db(reset=args.reset)
    except PermissionError:
        print("ERROR: the database file is in use. Stop the Flask server "
              "(Ctrl+C in its window) and try again.")
        sys.exit(1)

    communities, samples, centers = count_rows(db.DB_PATH)

    if loaded:
        action = "reset and re-created" if (args.reset and existed) else "created"
        print(f"Database {action}: {db.DB_PATH}")
        print("Sample data was loaded.")
    else:
        print(f"Database already exists: {db.DB_PATH}")
        print("Nothing was changed. Use  python init_db.py --reset  to rebuild it "
              "with the original sample data (this deletes your own records).")

    print(f"Communities: {communities} ({samples} sample, {communities - samples} added by users)")
    print(f"Food-support centers: {centers}")


if __name__ == "__main__":
    main()
