# Project Overview - Community Hunger Mapping System

**Stage:** Review 2 (about 50% completion) - academic mini-project
**Type:** Web-based GIS application

---

## Abstract

The Community Hunger Mapping System is a web-based GIS application that helps NGOs and community organisations identify areas that may be vulnerable to food insecurity. It stores community-level indicators (population, families reported as needing food assistance, income, food accessibility, nearby food-support centers) in a database, estimates a relative vulnerability category for each area using a simple and transparent scoring model, and shows the results on an interactive map and a dashboard. The current prototype is built with Flask, SQLite, Leaflet.js and OpenStreetMap, and runs on a normal laptop with no paid services. It uses fictional sample data for demonstration and is a preliminary academic model that requires validation with reliable real-world data.

## Introduction

Food insecurity is unevenly distributed. Some neighbourhoods have good access to affordable food and support services, while others have many households in need but few nearby resources. Organisations that distribute food often work with limited information about where the need is greatest. A map-based tool that brings scattered indicators together can help them ask better questions about where to focus attention.

## Problem statement

Information about community needs and food-support resources is often scattered across surveys, spreadsheets and personal knowledge. Without a single, visual view, it is difficult for organisations to compare areas, see where support centers are missing, or explain their planning decisions. This project addresses the need for a simple, low-cost tool that organises this information spatially and highlights areas that may need further attention.

## Objectives

1. Store community-level food-security indicators in a structured database.
2. Display communities and food-support centers on an interactive map.
3. Estimate a transparent vulnerability category (lower, moderate, higher) for every area.
4. Provide a dashboard that summarises the situation using figures calculated from the database.
5. Allow users to add, view, edit and delete community records through a validated web form.

## Proposed solution

A web application with a Python/Flask backend and a SQLite database. The browser displays a dashboard, an interactive Leaflet map, a data-entry form, and record and center listings. The backend validates data, saves it, and runs a weighted scoring model that converts the available indicators into one of three categories. The map colours each community green, yellow or red according to that category.

The system supports planning discussions. It does **not** measure hunger and does not identify individual hungry people.

## Methodology

1. **Data collection:** community indicators are entered through the web form (or loaded from the sample CSV files at first start).
2. **Validation:** every record is checked for required fields, valid ranges and consistency (for example, families needing assistance cannot exceed the population).
3. **Storage:** validated records are saved in SQLite.
4. **Analysis:** each indicator is converted to a risk value from 0 to 100, and a weighted average of the available indicators gives a score from 0 to 100. Missing indicators are skipped and the remaining weights re-scaled.
5. **Classification:** score below 35 is Lower, 35 to below 65 is Moderate, 65 or above is Higher.
6. **Visualisation:** the map and dashboard display the results, always read from the database.

The formula, weights and worked examples are in [`methodology.md`](methodology.md).

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| GIS and map | Leaflet.js, OpenStreetMap tiles |
| Backend | Python 3, Flask |
| Database | SQLite |
| Data processing | Python (standard library `csv`, `sqlite3`, `math`) |

## System architecture

```
Browser (HTML, CSS, JavaScript, Leaflet)
   |  page requests -> HTML          fetch('/api/...') -> JSON
   v
Flask backend (app.py)
   |-- validation.py  (input checks)
   |-- scoring.py     (vulnerability analysis)
   |-- db.py          (database access)
   v
SQLite database (database/community_hunger.db)
```

The browser never touches the database directly. All reads and writes go through the Flask API, which validates input and calculates the vulnerability category.

## Current implementation (Review 2)

Implemented and tested:

- Dashboard with figures calculated from the database: mapped areas, families reported as needing assistance, food-support centers, and the number of areas per vulnerability category. It also has a category chart and table, a highest-scores list, a recent-records table and a summary of the scoring method.
- Interactive Leaflet map on OpenStreetMap: colour-coded community markers, food-support center markers, popups, legend, category filter, center toggle and an area list.
- Add community data form with browser-side and server-side validation, a click-to-pick coordinate map and a success message.
- Community data page with search, category filter, details window with score breakdown, edit and delete.
- Food-support centers page.
- Flask JSON API for statistics, communities (create, read, update, delete), centers and analysis.
- SQLite database created automatically on first start; data persists across restarts.
- Sample data: 10 fictional communities and 5 fictional centers, clearly labelled.
- Scoring model with missing-value handling.
- 28 automated backend tests.

## Expected output

A working website that can be demonstrated end to end: open the dashboard, view the map, click a community to see its indicators, add a new community through the form, and see the dashboard figures, map markers and vulnerability category update from the database.

## Current limitations

- All shipped records are **fictional sample data** with approximate coordinates.
- The scoring weights and thresholds are **preliminary assumptions** and have not been validated.
- "Nearby food-support centers" is a user-entered count; the nearest listed center is shown for information only.
- If total families is not entered, it is estimated as population divided by 4.5, which is an assumption.
- No login: anyone with access can edit or delete records.
- Centers cannot yet be added or edited through the website.
- No area boundaries, heat map or advanced spatial analysis yet.
- Uses the Flask development server, suitable for demonstration only.
- Requires an internet connection for map tiles and front-end libraries.

## Future scope

- Collect real data and validate the scoring model with domain experts.
- Add area boundaries (GeoJSON) with a choropleth or heat-map view.
- Calculate food accessibility automatically from distance to centers.
- Add and edit food-support centers in the website; CSV import and export.
- Add user accounts and roles.
- Generate reports for NGOs and support distribution planning.
- Deploy on a production server.
