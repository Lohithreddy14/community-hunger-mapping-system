# Review 2 Checklist

## A. Before the review (10 minutes)

- [ ] Extract the ZIP and open Command Prompt in the project folder.
- [ ] `venv\Scripts\activate` (create it first with `python -m venv venv` and run `pip install -r requirements.txt` if you have not yet).
- [ ] If you practised with your own records and want a clean start: stop the server, then run `python init_db.py --reset`.
- [ ] Optional: run `python -m unittest discover tests -v` and confirm it ends with **OK**.
- [ ] Start the server: `python app.py`.
- [ ] Open <http://127.0.0.1:5000> and confirm the dashboard shows **10** mapped areas, **1,505** families, **5** centers and 3 / 4 / 3 areas by category.
- [ ] **Check the internet connection.** The map tiles, Leaflet and Bootstrap load from the internet. Open the map page once to confirm the tiles appear.
- [ ] Keep the Command Prompt window visible but not closed.

## B. Demonstration workflow

| # | Step | What to say / show |
|---|---|---|
| 1 | Start the Flask app (`python app.py`) | "The backend is a Flask application. It creates the SQLite database automatically the first time it runs." |
| 2 | Open `http://127.0.0.1:5000` | Point out the sidebar navigation and the notice that the data is sample data. |
| 3 | View the **dashboard** | Totals, category counts, chart, highest scores, recent records. "These figures are calculated from the database, not typed into the page." (Optional: open `/api/stats` in a new tab to show the raw JSON.) |
| 4 | Click **Open interactive map** | OpenStreetMap base map, coloured community markers, blue centre markers, legend. |
| 5 | Click a community marker (for example *Riverside Settlement*) | |
| 6 | Read its popup | Name, families needing assistance, indicators, score and category. Click **See score breakdown** to show how the score is built. |
| 6b | Use the filter buttons (Higher / Moderate / Lower) | "The colours come from the scoring rules, not random." |
| 7 | Open **Add community data** | Show the required fields, the optional fields and the map picker. |
| 7b | Click **Save** with empty fields | Show the validation messages. |
| 8 | Add a new record | Example: *Demo Colony*, click the map to set the location, population 2500, total families 560, families needing assistance 210, income 11000, accessibility Poor, nearby centers 0. |
| 9 | Click **Save community data** | The success message appears, with the estimated category (Higher in this example). "The form sent JSON to Flask, Flask validated it and saved it in SQLite." |
| 10 | Click **Go to dashboard** | Mapped areas is now 11, families increased by 210, the Higher count went up, and the new record is at the top of recent data. |
| 11 | Click **Open interactive map** (or **View on map** in step 9) | The new marker is there. |
| 12 | Click the new marker | Shows its category. Then open **Community data**, click **View** to show the breakdown, and optionally **Edit** to change a value and see the category recalculate. |
| 13 | (Optional) Stop the server, start it again | Show that the new record is still there because it is stored in the database file. |
| 14 | (Optional) Delete the demo record | Use **Delete** on the Community data page; the dashboard returns to 10. |

## C. What is completed at Review 2

| Requirement | Status |
|---|---|
| Working website | Done |
| Interactive GIS map (Leaflet + OpenStreetMap) | Done |
| Sample community locations and centers | Done (fictional, labelled) |
| Basic dashboard, all figures from the database | Done |
| Community data entry form with validation | Done |
| Basic vulnerability analysis | Done (preliminary model) |
| Flask backend connected to SQLite | Done |
| Edit and delete records | Done |
| Data persists after restart | Done |

## D. Not done yet (planned for later reviews)

- [ ] Real data collection and validation of the scoring model.
- [ ] Area boundaries, choropleth or heat-map layers.
- [ ] Add/edit food-support centers from the website.
- [ ] Accessibility calculated automatically from distances.
- [ ] CSV import and export, reports.
- [ ] Login and user roles.
- [ ] Deployment beyond the local development server.

## E. Questions you may be asked

**Does this measure hunger?**
No. It gives an estimated relative vulnerability category from a few indicators. It is a planning aid and a preliminary model that still needs validation with real data.

**Is the data real?**
No. The records that come with the project are fictional sample data, labelled as such. Users can enter their own data.

**How is the colour decided?**
Each indicator is converted to a 0-100 risk value, multiplied by its weight and added up. Below 35 is green, 35 to below 65 is yellow, 65 or above is red. See `documentation/methodology.md`.

**What if some data is missing?**
The missing indicator is skipped and the remaining weights are re-scaled. Nothing is invented. The details window shows which indicators were used.

**Why these weights?**
They are documented assumptions: direct evidence of need has the largest weight, access and support-center availability have medium weights, and income (an indirect indicator) has the smallest. They need validation, and testing alternative weights (sensitivity analysis) is planned.

**How do the browser, Flask and the database communicate?**
The browser loads a page from Flask, then the page's JavaScript calls `/api/...` endpoints and receives JSON. Flask validates input, runs the scoring model and reads or writes SQLite. Leaflet displays the map using OpenStreetMap tiles.

**How do you know the numbers on the dashboard are not hard-coded?**
Add or delete a record and the numbers change. You can also open `/api/stats` to see the JSON that the dashboard reads.

**What happens if the server restarts?**
The data is stored in `database/community_hunger.db`, so it remains. The sample data is only loaded when the database is first created.
