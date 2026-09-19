# Community Hunger Mapping System

A minimal, working web-based GIS application that helps NGOs and community organisations see which areas may need additional food assistance.
It stores community-level information in a database, estimates a **relative vulnerability category** for each area, and shows the results on an interactive map and dashboard.

> **Project stage:** Review 2 (about 50% completion) - academic mini-project.
>
> **Important:** this system does **not** measure hunger and does not identify every hungry person. It gives an *estimated relative vulnerability category* from a simple, preliminary scoring model that has **not** been validated with real-world data. All records that ship with the project are **fictional SAMPLE DATA** for demonstration.

---

## Table of contents

1. [Project objectives](#1-project-objectives)
2. [Technology stack](#2-technology-stack)
3. [Features](#3-features)
4. [Project architecture](#4-project-architecture)
5. [Project structure](#5-project-structure)
6. [Database structure](#6-database-structure)
7. [Vulnerability scoring methodology](#7-vulnerability-scoring-methodology)
8. [How to run the project on Windows](#8-how-to-run-the-project-on-windows)
9. [How to add community records](#9-how-to-add-community-records)
10. [API endpoints](#10-api-endpoints)
11. [Running the automated tests](#11-running-the-automated-tests)
12. [Troubleshooting](#12-troubleshooting)
13. [Limitations and future work](#13-limitations-and-future-work)

---

## 1. Project objectives

1. Collect and organise community-level food-security indicators in one database.
2. Show community locations and food-support centers on an interactive map.
3. Estimate a transparent, explainable vulnerability category (lower, moderate, higher) for each area.
4. Give NGOs a dashboard that summarises the situation and helps them decide where to look first.
5. Let users add, view, edit and delete community records through a web form.

## 2. Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 (loaded from a CDN) |
| GIS and map | Leaflet.js with OpenStreetMap tiles (no API key needed) |
| Backend | Python 3 and Flask |
| Database | SQLite (a single file, created automatically) |
| Data processing | Python (scoring model, CSV loading, distance calculation) |

Pandas is **not** required. The sample CSV files are read with Python's built-in `csv` module, which keeps installation simple for beginners.

## 3. Features

Implemented for Review 2:

- **Dashboard**: totals for mapped areas, families reported as needing assistance, and food-support centers; number of areas in each vulnerability category; a category chart and table; the highest-scoring areas; recent records; a summary of the scoring method. Every figure is calculated from the database.
- **Interactive GIS map** (Leaflet + OpenStreetMap): community markers coloured green / yellow / red by the scoring model, marker size based on families reported as needing assistance, food-support center markers, popups with indicators, a legend, a category filter, a switch to hide the centers, and a clickable list of areas.
- **Add community data**: validated form (browser and server checks), click-the-map coordinate picker, and a success message showing the estimated category.
- **Community data**: searchable and filterable table, a details window with the full score breakdown, edit, and delete (with confirmation).
- **Food-support centers**: list with location, coordinates and description. Sample records are clearly labelled.
- **Vulnerability analysis**: a simple weighted score that handles missing values without inventing data.
- **Database**: SQLite, created automatically on first start. Your data is kept when the application restarts.
- **Responsive layout**: sidebar navigation on desktop, slide-out menu on phones and tablets.

## 4. Project architecture

```
 Browser (HTML + CSS + JavaScript + Leaflet)
        |
        |  1) page requests   GET /, /map, /add ...       -> Flask returns HTML
        |  2) data requests   fetch('/api/...') as JSON   -> Flask returns JSON
        v
 Flask backend (app.py)
        |-- validation.py   checks every form submission
        |-- scoring.py      calculates score + category (the analysis)
        |-- db.py           reads and writes the database
        v
 SQLite database (database/community_hunger.db)
```

- The **browser** loads a page from Flask, then the page's JavaScript calls the Flask API with `fetch`.
- **Flask** validates input, runs the scoring model in Python, and reads or writes SQLite.
- The **dashboard, map and tables** never contain hard-coded numbers. They always display what the API returns from the database, so a record saved on the form appears on the dashboard and map immediately.
- The **vulnerability category is not stored**. It is calculated every time from the saved indicators, so changing the scoring rules in `scoring.py` updates every record consistently.

## 5. Project structure

```
community-hunger-mapping-system/
|-- app.py                  Flask app: page routes + JSON API
|-- db.py                   SQLite schema, connections, insert/update/delete, sample-data loader
|-- scoring.py              Vulnerability scoring model (formula, weights, thresholds)
|-- validation.py           Input validation rules
|-- init_db.py              Optional script to create / reset the database
|-- requirements.txt        Python dependency list (Flask)
|-- run_windows.bat         Optional one-click helper for Windows
|-- README.md
|-- database/               The SQLite file community_hunger.db is created here
|-- data/
|   |-- sample_communities.csv   10 fictional sample communities
|   `-- sample_centers.csv       5 fictional sample food-support centers
|-- templates/              HTML pages (Jinja2)
|   |-- base.html  dashboard.html  map.html  add_community.html
|   |-- communities.html  centers.html  404.html
|-- static/
|   |-- css/style.css
|   `-- js/  common.js  dashboard.js  map.js  add_community.js  communities.js  centers.js
|-- tests/test_app.py       28 automated tests
`-- documentation/          project_overview.md, methodology.md, review2_checklist.md
```

## 6. Database structure

The database has two tables.

**`communities`**

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER, primary key | Record number |
| `name` | TEXT, required | Community or area name |
| `latitude`, `longitude` | REAL, required | Location (validated ranges) |
| `population` | INTEGER, required | Number of residents |
| `total_families` | INTEGER, optional | Total families in the area |
| `families_needing_assistance` | INTEGER, required | Families reported as needing food assistance |
| `avg_household_income` | REAL, optional | Average monthly household income (Rs.) |
| `food_accessibility` | TEXT, optional | `Good`, `Moderate` or `Poor` |
| `nearby_centers` | INTEGER, optional | Number of nearby food-support centers reported |
| `notes` | TEXT, optional | Free-text notes / data source |
| `is_sample` | INTEGER | 1 = fictional sample record, 0 = entered by a user |
| `created_at`, `updated_at` | TEXT | Timestamps (local time) |

**`food_centers`**

| Column | Type | Meaning |
|---|---|---|
| `id` | INTEGER, primary key | Record number |
| `name` | TEXT, required | Center name |
| `location` | TEXT, required | Location description |
| `latitude`, `longitude` | REAL, required | Position |
| `description` | TEXT | What the center does |
| `is_sample` | INTEGER | 1 = fictional sample record |
| `created_at` | TEXT | Timestamp |

The sample data is loaded **once**, when the database is first created. It is not re-loaded on later starts, so your own records (and any sample records you delete) stay as you left them.

## 7. Vulnerability scoring methodology

The full explanation, with worked examples, is in [`documentation/methodology.md`](documentation/methodology.md). In short:

1. Each indicator is converted to a **risk value from 0 (lowest concern) to 100 (highest concern)**.
2. Each indicator has a **weight**. The weights add up to 1.0.
3. **score = sum of (weight x risk value)** over the indicators that are available. If an indicator is missing, it is skipped and the remaining weights are re-scaled. Nothing is invented for missing data.
4. The 0-100 score is converted to a map category.

| Indicator | Weight | Risk value |
|---|---|---|
| Families needing assistance (as % of total families) | 45% | 40% or more = 100, scaled linearly below that |
| Food accessibility | 25% | Good = 0, Moderate = 50, Poor = 100 |
| Nearby food-support centers | 20% | 0 = 100, 1 = 60, 2 = 30, 3 or more = 0 |
| Average household income (monthly) | 10% | Rs. 10,000 or less = 100, Rs. 40,000 or more = 0, linear between |

| Score | Category | Map colour |
|---|---|---|
| below 35 | Lower estimated vulnerability | Green |
| 35 to below 65 | Moderate estimated vulnerability | Yellow |
| 65 or above | Higher estimated vulnerability | Red |

If *total families* is not entered, it is estimated as `population / 4.5` (an assumption stated in the code and shown in the details window). All weights, cut-offs and thresholds are **preliminary academic assumptions** that need validation with reliable real-world data. All of them are defined in one place at the top of `scoring.py`.

## 8. How to run the project on Windows

### What you need

- **Python 3.9 or newer** from <https://www.python.org/downloads/>. During installation, tick **"Add python.exe to PATH"**.
- An **internet connection** when you use the website. The map tiles (OpenStreetMap), Leaflet, Bootstrap and the font are loaded from the internet. The Flask server itself runs locally.
- A web browser (Chrome, Edge or Firefox).

To check Python, open Command Prompt and run: `python --version`

### Step-by-step (Command Prompt)

1. Extract `community-hunger-mapping-system-review2.zip`. Right-click the ZIP and choose **Extract All**.
2. Open **Command Prompt** and go into the extracted folder (adjust the path to where you extracted it):

   ```
   cd C:\Users\YourName\Downloads\community-hunger-mapping-system
   ```

3. Create a virtual environment:

   ```
   python -m venv venv
   ```

4. Activate it. You should see `(venv)` at the start of the line:

   ```
   venv\Scripts\activate
   ```

5. Install the dependency:

   ```
   pip install -r requirements.txt
   ```

6. Create the database with the sample data (optional, because the app also does this by itself on first start):

   ```
   python init_db.py
   ```

7. Start the Flask server:

   ```
   python app.py
   ```

8. Open your browser and go to:

   ```
   http://127.0.0.1:5000
   ```

9. To stop the server, click the Command Prompt window and press **Ctrl + C**.

### Step-by-step (PowerShell)

Steps 1-3 and 5-9 are the same. Only the activation command differs:

```
.\venv\Scripts\Activate.ps1
```

If PowerShell says *"running scripts is disabled on this system"*, run this once in the same window and then activate again:

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Next time you want to run it

```
cd C:\Users\YourName\Downloads\community-hunger-mapping-system
venv\Scripts\activate
python app.py
```

### Optional shortcut

Double-click **`run_windows.bat`**. It creates the virtual environment (first time only), installs Flask, prepares the database and starts the server. (This helper is provided for convenience; the manual steps above are the tested route.)

### Resetting the database

To delete all records and restore the original sample data, **stop the server first**, then run:

```
python init_db.py --reset
```

## 9. How to add community records

1. Click **Add community data** in the sidebar (or the button on the dashboard).
2. Enter the community name.
3. Enter the latitude and longitude, or **click the small map** to fill them in. You can also drag the pin.
4. Enter the population and the number of families reported as needing food assistance (both required).
5. Fill in any optional fields you know: total families, average monthly household income, food accessibility, nearby center count, notes. Leave unknown fields **blank**; the scoring model skips them.
6. Click **Save community data**. If something is wrong, a message appears under the field. Otherwise a green message shows the estimated category, with buttons to **View on map** or go to the **dashboard**.

Records you add are saved in SQLite and remain after you restart the server. They appear on the dashboard, map and community table straight away.

## 10. API endpoints

| Method and path | Purpose |
|---|---|
| `GET /api/stats` | Dashboard statistics, recent records, highest scores |
| `GET /api/communities` | All communities with score and category (`?category=lower\|moderate\|higher` to filter) |
| `GET /api/communities/<id>` | One community with the full score breakdown |
| `POST /api/communities` | Add a community (JSON body, validated) |
| `PUT /api/communities/<id>` | Update a community |
| `DELETE /api/communities/<id>` | Delete a community |
| `GET /api/centers` | Food-support centers |
| `GET /api/analysis` | Analysis results for every community plus a description of the method |

You can open the `GET` links directly in the browser, for example <http://127.0.0.1:5000/api/stats>, which is a good way to show in a viva that the dashboard numbers come from the backend.

## 11. Running the automated tests

With the virtual environment active:

```
python -m unittest discover tests -v
```

The tests use a temporary database, so your real data is not touched. They check database creation, page loading, dashboard statistics, saving records, persistence across restarts, form validation, edit/delete, and the scoring model (including missing data).

## 12. Troubleshooting

| Problem | What to do |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick **Add python.exe to PATH**, or try `py` instead of `python` (for example `py -m venv venv`). Close and reopen Command Prompt afterwards. |
| `ModuleNotFoundError: No module named 'flask'` | The virtual environment is not active or the install was skipped. Run `venv\Scripts\activate` and then `pip install -r requirements.txt`. |
| PowerShell: *running scripts is disabled* | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again. |
| `Address already in use` / port 5000 busy | Another program (or an earlier copy of this app) is using port 5000. Close it, or open `app.py`, change `port=5000` in the last line to `port=5050`, and browse to `http://127.0.0.1:5050`. |
| The map area is grey or blank | Leaflet and the map tiles come from the internet. Check your connection and refresh with **Ctrl + F5**. Some college networks block map tiles; try a different network or a mobile hotspot. |
| The page looks unstyled | Bootstrap is loaded from a CDN, so it also needs internet. Refresh with **Ctrl + F5**. |
| `PermissionError` when running `init_db.py --reset` | The server is still running and using the database. Stop it with Ctrl + C first. |
| "Could not reach the server" message in the browser | The Flask window was closed or stopped. Start it again with `python app.py`. |
| Changes to the code do not appear | The server restarts automatically in debug mode. Refresh with **Ctrl + F5** to bypass the browser cache. |
| Want a completely fresh start | Stop the server, delete `database\community_hunger.db`, and start again. |

## 13. Limitations and future work

**Current limitations**

- The sample data is fictional. Coordinates are approximate and none of the records represent real communities or real hunger statistics.
- The scoring weights and thresholds are preliminary assumptions, not a validated model.
- "Nearby food-support centers" is a count typed in by the user. The map also shows the *nearest listed* center as extra information, but it is not used in the score.
- There is no login. Anyone who can open the site can edit or delete records.
- Food-support centers can be viewed but not added or edited from the website yet.
- The built-in Flask development server is used. It is suitable for demonstration, not for public deployment.

**Planned for later reviews**

- Real data collection and validation of the scoring model with domain experts.
- Area boundaries (GeoJSON) and a heat-map or choropleth view.
- Automatic accessibility from distance to centers, instead of a typed count.
- Add/edit food-support centers in the website; CSV import and export.
- Login and user roles; reports for NGOs; deployment to a server.

See `documentation/` for the project overview, methodology and the Review 2 checklist.
