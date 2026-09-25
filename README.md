# Community Hunger Mapping System

A minimal, working web-based GIS platform that helps NGOs, community groups, and food security administrators identify vulnerable hunger hotspots and coordinate food-support operations.
It stores surveyed community information, calculates transparent **relative vulnerability categories**, tracks **food-support centers** (NGOs, community kitchens, food banks, relief points), and visualises everything on an interactive Leaflet map and real-time dashboard.

> **Project stage:** Review 2 Prototype (Enhanced with Full Food-Support Center Management).
>
> **Important:** This system does **not** measure clinical hunger and does not identify every individual. It provides an *estimated relative vulnerability category* from a transparent, academic scoring model. Sample records provided for demonstration are fictional. Records registered by users are stored securely in SQLite and survive server restarts.

---

## Table of contents

1. [Project objectives](#1-project-objectives)
2. [Technology stack](#2-technology-stack)
3. [Features](#3-features)
4. [Food-Support Centers Feature](#4-food-support-centers-feature)
5. [Project architecture](#5-project-architecture)
6. [Project structure](#6-project-structure)
7. [Database structure](#7-database-structure)
8. [Vulnerability scoring methodology](#8-vulnerability-scoring-methodology)
9. [How to run the project on Windows](#9-how-to-run-the-project-on-windows)
10. [How to add and manage Food-Support Centers](#10-how-to-add-and-manage-food-support-centers)
11. [API endpoints](#11-api-endpoints)
12. [Running the automated tests](#12-running-the-automated-tests)
13. [Troubleshooting](#13-troubleshooting)
14. [How to demonstrate this project to your guide](#14-how-to-demonstrate-this-project-to-your-guide)

---

## 1. Project objectives

1. Collect and organise community-level food-security indicators in one database.
2. Provide a fast, reliable registration and verification pipeline for food-support centers (NGOs, community kitchens, food banks).
3. Display surveyed communities and relief facilities together on an interactive GIS map.
4. Estimate an explainable vulnerability score (Lower, Moderate, Higher) for each surveyed community.
5. Provide a comprehensive dashboard showing hotspot statistics and food-support center operational metrics.
6. Enable full CRUD operations (Create, Read, Update, Delete) with search and filtering for both communities and food centers.

---

## 2. Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5 (CDN) |
| GIS and Mapping | Leaflet.js with OpenStreetMap tiles (no paid API keys required) |
| Backend | Python 3 and Flask |
| Database | SQLite (`database/community_hunger.db`), foreign keys enabled |
| Spatial Calculations | Great-circle Haversine formula (pure Python & JS, no external spatial libraries) |
| Testing | Python built-in `unittest` test suite |

---

## 3. Features

- **Dashboard**:
  - Live counts for surveyed areas, families needing assistance, and food-support centers.
  - Verification & operational status breakdown: Verified centers, Awaiting contact, Partially verified, and Inactive centers.
  - Recent community data and recent food-support center activity feed.
  - Vulnerability distribution bar and ranked high-need areas.
- **Interactive GIS Map**:
  - Communities rendered as color-coded circle markers (Green: Lower, Yellow: Moderate, Red: Higher vulnerability).
  - Food-Support Centers rendered with distinctive pins (Green: Verified, Blue: Active, Gray: Provisional).
  - Layer Filter: Toggle between **Both**, **Communities only**, or **Food-Support Centers only**.
  - Rich popups with center name, type, associated community, phone (clickable `tel:`), address, and direct link to view full details.
  - Deep-linking support via URL (`/map?focus=<community_id>` or `/map?center=<center_id>`).
- **Food Support Centers Management**:
  - **Quick Add Mode**: Register centers in ~15 seconds without manually looking up coordinates.
  - **Complete Registration Form**: Structured across 5 clear sections (Basic Info, Location & Interactive Map, Contact Directory, Food Support Services, and Verification & Follow-Up).
  - **Center Directory**: Search by center name, address, or contact person; filter by community, center type, verification status, and availability.
  - **Center Details Page**: Direct contact buttons (**Call Center**, **WhatsApp**, **Send Email**, **Open Website**, **Map Directions**), service details, and verification history.
  - **Verification Pipeline**: Record contact attempts, notes, follow-up dates, and mark centers as Contacted or Verified.
- **Vulnerability Analysis**:
  - Transparent weighted scoring model evaluating need ratio, food accessibility rating, nearby centers, and household income.

---

## 4. Food-Support Centers Feature

### Quick Add Mode (Under 15 Seconds)
When field workers or volunteers identify a food provider, they often only have the center's name, community area, and phone number.
- Quick Add displays only 4 core fields: Center Name, Center Type, Community Area dropdown, and Primary Phone (plus optional address, website, and short notes).
- Selecting a community automatically assigns that community's coordinates to the center with `location_source = 'community_reference'`.
- No manual coordinate typing is needed.
- Center is saved with initial status **Newly Added** (unverified).

### Location & Coordinate Handling
1. **Community Reference (Provisional)**:
   - When registered via Quick Add or when exact coordinates are not known, the center is linked to an existing community.
   - The system clearly marks these coordinates as **Provisional Reference Coordinates** and never misrepresents them as the exact physical building location.
2. **Actual Center Location**:
   - An interactive Leaflet map allows the user to click or drag a pin to pinpoint the center's exact building position.
   - The great-circle distance (in kilometers) between the actual facility coordinates and the associated community is calculated automatically.
   - Manual coordinate inputs are kept available inside an optional toggleable section.

### Verification and Follow-Up
- Records information status: `Newly Added`, `Not Contacted`, `Contacted`, `Information Partially Verified`, `Verified`, `Unable to Reach`, `Inactive`.
- One-click actions:
  - **Mark as Contacted Today**: Records the current date, contact notes, and updates status to Contacted.
  - **Mark as Verified**: Explicit confirmation with verification notes.

---

## 5. Project architecture

```
 Browser (HTML5 + Bootstrap 5 + Vanilla JavaScript + Leaflet.js)
        |
        |  1) Page Requests   (GET /, /map, /centers, /centers/add, /centers/<id> ...)
        |  2) API Requests    (fetch('/api/...', {method: 'GET'|'POST'|'PUT'|'PATCH'|'DELETE'}))
        v
 Flask Application (app.py)
        |-- validation.py   Input checks for communities and food-support centers
        |-- scoring.py      Vulnerability analysis & Haversine distance calculations
        |-- db.py           SQLite abstraction layer, schema migrations, and queries
        v
 SQLite Database (database/community_hunger.db)
```

---

## 6. Project structure

```
community-hunger-mapping-system/
|-- app.py                  Flask backend: HTML page routes + REST API endpoints
|-- db.py                   SQLite schema, migrations, queries, and sample data loader
|-- scoring.py              Vulnerability scoring model and Haversine distance formula
|-- validation.py           Input validation rules and regexes
|-- init_db.py              Database initialization and migration CLI script
|-- requirements.txt        Python dependencies (Flask)
|-- run_windows.bat         Windows one-click runner batch script
|-- README.md               Project documentation
|-- database/               SQLite storage folder
|   `-- community_hunger.db Generated database file
|-- data/
|   |-- sample_communities.csv   10 fictional demonstration communities
|   `-- sample_centers.csv       5 sample food-support centers
|-- templates/
|   |-- base.html           Base layout with sidebar and responsive offcanvas menu
|   |-- dashboard.html      Dashboard with hotspot and food-center statistics
|   |-- map.html            Interactive Leaflet GIS map with layer filters
|   |-- add_community.html  Add / Edit community data form
|   |-- communities.html    Community records table, filter, and score breakdown modal
|   |-- centers.html        Food Support Centers management directory & filter bar
|   |-- add_center.html     Quick Add Mode + Complete 5-section registration form
|   |-- center_detail.html  Comprehensive Center Details page with quick action buttons
|   `-- 404.html            Friendly 404 error page
|-- static/
|   |-- css/style.css       Application theme styles, badges, and card layouts
|   `-- js/
|       |-- common.js       Shared helpers (escapeHtml, apiFetch, formatting)
|       |-- dashboard.js    Dashboard figures and recent data renderer
|       |-- map.js          Leaflet GIS map implementation with layer filtering
|       |-- add_community.js Community form coordinate picker
|       |-- communities.js  Community table search, filter, and delete
|       |-- centers.js      Food Support Centers directory and filtering
|       |-- add_center.js   Quick Add + Full Center form logic & distance calculation
|       `-- center_detail.js Center details view, action buttons & status modals
`-- tests/
    |-- test_app.py                 28 baseline unit tests
    `-- test_food_support_centers.py 10 comprehensive food-support center unit tests
```

---

## 7. Database structure

### `communities` Table
Stores surveyed geographical communities and vulnerability indicators:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `name`: TEXT NOT NULL
- `latitude`, `longitude`: REAL NOT NULL (-90..90, -180..180)
- `population`: INTEGER NOT NULL (>0)
- `total_families`: INTEGER (Optional)
- `families_needing_assistance`: INTEGER NOT NULL (>=0)
- `avg_household_income`: REAL (Optional)
- `food_accessibility`: TEXT (`Good`, `Moderate`, `Poor`)
- `nearby_centers`: INTEGER (Optional count)
- `notes`: TEXT
- `is_sample`: INTEGER (1 = Sample, 0 = User Record)
- `created_at`, `updated_at`: TEXT timestamps

### `food_support_centers` Table
Stores food banks, community kitchens, and relief organizations:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `center_name`: TEXT NOT NULL (and legacy mirror `name`)
- `center_type`: TEXT NOT NULL (`NGO`, `Community Kitchen`, `Food Bank`, etc.)
- `description`: TEXT
- `address`: TEXT (and legacy mirror `location`)
- `community_id`: INTEGER REFERENCES `communities(id)` ON DELETE SET NULL
- `landmark`, `pincode`, `district`, `state`: TEXT
- `latitude`, `longitude`: REAL NOT NULL
- `location_source`: TEXT (`actual`, `community_reference`, `approximate`)
- `primary_contact_name`, `contact_designation`: TEXT
- `phone_number`: TEXT NOT NULL
- `alternative_phone`, `email`, `website`, `whatsapp_number`: TEXT
- `preferred_contact_method`: TEXT (`Phone Call`, `WhatsApp`, `Email`, `Website`, `Visit in Person`)
- `food_support_types`: TEXT (JSON array of strings)
- `meals_available`, `distribution_schedule`: TEXT
- `operating_days`, `operating_hours`: TEXT
- `people_served_per_day`: INTEGER
- `eligibility_requirements`: TEXT
- `registration_required`: TEXT (`Yes`, `No`, `Unknown`)
- `availability_status`: TEXT (`Yes`, `No`, `Unknown`)
- `information_status`: TEXT (`Newly Added`, `Not Contacted`, `Contacted`, `Information Partially Verified`, `Verified`, `Unable to Reach`, `Inactive`)
- `contact_attempt_date`, `last_contacted_date`, `next_followup_date`: TEXT
- `contacted_by`, `contact_notes`, `information_source`, `verification_notes`: TEXT
- `is_sample`: INTEGER (1 = Sample, 0 = User Record)
- `created_at`, `updated_at`: TEXT timestamps

### `food_centers` View & Trigger
A SQL View and `INSTEAD OF INSERT` trigger provide 100% backward compatibility for existing queries.

---

## 8. Vulnerability scoring methodology

Vulnerability scores are calculated transparently using 4 weighted indicators:
1. **Families needing food assistance ratio** (Weight: 45%)
2. **Food accessibility rating** (Weight: 25%)
3. **Reported nearby centers** (Weight: 20%)
4. **Average household income** (Weight: 10%)

Categories:
- **Score < 35**: Lower vulnerability (Green)
- **35 &le; Score < 65**: Moderate vulnerability (Yellow)
- **Score &ge; 65**: Higher vulnerability (Red)

Missing indicators are skipped dynamically and the remaining weights are rescaled so they always sum to 1.0 without fabricating values.

---

## 9. How to run the project on Windows

### Step 1: Open Terminal in the project directory
Open Windows Command Prompt or PowerShell:
```powershell
cd C:\Users\ADMIN\Downloads\community-hunger-mapping-system-review2\community-hunger-mapping-system
```

### Step 2: Activate the Virtual Environment
Command Prompt:
```cmd
venv\Scripts\activate.bat
```
PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```
*(If PowerShell says script execution is disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once).*

### Step 3: Install dependencies (if needed)
```cmd
pip install -r requirements.txt
```

### Step 4: Run database migration / initialization (optional)
```cmd
python init_db.py
```

### Step 5: Start the Flask application
```cmd
python app.py
```

### Step 6: Open the browser
Navigate to:
```
http://127.0.0.1:5000
```
To stop the server, press **Ctrl + C** in the terminal.

---

## 10. How to add and manage Food-Support Centers

### Workflow A: Quick Add Mode (Fastest)
1. Click **Food Support Centers** in the sidebar.
2. Click **Quick Add Center** (or go to `/centers/add`).
3. Enter the **Center Name** (e.g. `Akshaya Community Kitchen`).
4. Select the **Center Type** (e.g. `Community Kitchen`).
5. Select the **Community Area** from the dropdown (e.g. `Lakeview Colony`).
6. Enter the **Primary Phone Number** (e.g. `+91 98450 12345`).
7. Optionally enter address, website, or short remarks.
8. Click **Save Center**.
9. The center is instantly saved to SQLite with provisional coordinates from Lakeview Colony and status `Newly Added`.
10. Click **Open Center Details** to view the record or **Add Another Center**.

### Workflow B: Complete Registration with Interactive Map
1. Click **Add New Center** (or switch to the "Complete Registration Form" tab).
2. Fill in basic information (Sections A, C, D, E).
3. In Section B (Location), click anywhere on the Leaflet map to pinpoint the exact facility building.
4. The system calculates and displays the approximate distance in kilometers from the associated community center point.
5. Click **Save Food-Support Center**.

### Workflow C: Verification and Follow-Up
1. Open any center's details page (`/centers/<id>`).
2. Click **Call Center** to initiate a telephone call.
3. Click **Mark Contacted** to log who called, the date, and discussion notes.
4. Click **Mark Verified** when documentation or in-person verification is confirmed.

---

## 11. API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Dashboard statistics, center operational counts, recent records |
| `GET` | `/api/center-stats` | Detailed Food-Support Center summary metrics |
| `GET` | `/api/communities` | List all communities (`?category=lower\|moderate\|higher`) |
| `GET` | `/api/communities/<id>` | Single community with indicator breakdown |
| `POST` | `/api/communities` | Create community record |
| `PUT` | `/api/communities/<id>` | Update community record |
| `DELETE` | `/api/communities/<id>` | Delete community record |
| `GET` | `/api/centers` | List centers (`?search=...&community_id=...&center_type=...&status=...&availability=...`) |
| `GET` | `/api/centers/<id>` | Single center complete details with distance |
| `POST` | `/api/centers` | Create food-support center (Quick Add & Full Add) |
| `PUT` | `/api/centers/<id>` | Update food-support center |
| `PATCH` | `/api/centers/<id>/status` | Update verification/contact status (`mark_contacted`, `mark_verified`) |
| `DELETE` | `/api/centers/<id>` | Delete food-support center |
| `GET` | `/api/analysis` | Vulnerability analysis results and formula metadata |

---

## 12. Running the automated tests

To execute the test suite (38 automated tests covering all features and workflows):
```powershell
python -m unittest discover tests -v
```
All tests run against an isolated in-memory/temporary SQLite database, preserving your project database records.

---

## 13. Troubleshooting

- **Port 5000 in use**: Run `python app.py` on a different port by editing `app.run(port=5050)` or closing conflicting programs.
- **Database permission error**: Close the running Flask server before executing `python init_db.py --reset`.
- **Map tiles not appearing**: Ensure an active internet connection so Leaflet can fetch OpenStreetMap tiles.

---

## 14. How to demonstrate this project to your guide

Here is a recommended 5-minute walkthrough for your project guide:

1. **Dashboard Overview**:
   - Open `http://127.0.0.1:5000`.
   - Point out the new **Food Support Center Network Overview** cards (Total, Verified, Awaiting Contact, Inactive).
   - Show that all figures are computed live from the SQLite database.
2. **Quick Add Demo (~15 Seconds)**:
   - Click **Quick Add Center**.
   - Type a sample center name (`Annapurna Kitchen`) and phone number (`+91 98450 11223`).
   - Select `Lakeview Colony` from the community dropdown.
   - Click **Save Center**. Explain to your guide: *"In emergency or field surveys, workers don't know the exact GPS coordinates. The system instantly links the center to the community's provisional reference coordinates so it can be saved in seconds."*
3. **Interactive Map (GIS)**:
   - Click **Interactive map**.
   - Show the layer filter: switch between **Communities**, **Food-Support Centers**, and **Both**.
   - Click the marker for `Annapurna Kitchen`. Show the popup indicating *"Provisional Community Location"*.
4. **Center Details & Contact Actions**:
   - Click **View Center Details**.
   - Demonstrate the quick action buttons: **Call Center**, **WhatsApp**, **Send Email**, and **Map Directions**.
   - Click **Mark Contacted** and record a quick note. Show the status update in real time.
   - Click **Mark Verified** to demonstrate that verification requires explicit user confirmation and is never fabricated.
5. **Distance Calculation**:
   - Click **Edit Center**.
   - Move the map marker slightly away from the community center.
   - Show the live distance calculation: *"Approx. 1.2 km from Lakeview Colony"*.
   - Save and show that the status badge updates to **Actual Center Location**.
6. **Automated Tests**:
   - Run `python -m unittest discover tests -v` in terminal to prove that all 38 test cases pass.
